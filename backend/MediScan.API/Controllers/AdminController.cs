using MediScan.Core.DTOs.Common;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Core.Services;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using System.Security.Claims;

namespace MediScan.API.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
[Authorize(Roles = "Admin")]
[Produces("application/json")]
public class AdminController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IAuditService _audit;

    public AdminController(
        AppDbContext db,
        UserManager<ApplicationUser> userManager,
        IAuditService audit)
    {
        _db = db;
        _userManager = userManager;
        _audit = audit;
    }

    // ── Dashboard Stats ───────────────────────────────────────

    /// <summary>Get dashboard statistics for admin overview</summary>
    [HttpGet("stats")]
    public async Task<IActionResult> GetStats()
    {
        var now   = DateTime.UtcNow;
        var today = now.Date;

        var totalUsers  = await _db.Users.CountAsync();
        var totalScans  = await _db.ScanRecords.CountAsync();
        var scansToday  = await _db.ScanRecords.CountAsync(s => s.CreatedAt >= today);

        // Active users last 7 days (users who scanned)
        var sevenDaysAgo = now.AddDays(-7);
        var activeUsers  = await _db.ScanRecords
            .Where(s => s.CreatedAt >= sevenDaysAgo)
            .Select(s => s.UserId)
            .Distinct()
            .CountAsync();

        // Scans by type
        var scansByType = await _db.ScanRecords
            .GroupBy(s => s.ScanType)
            .Select(g => new { Type = g.Key.ToString(), Count = g.Count() })
            .ToDictionaryAsync(x => x.Type, x => x.Count);

        // Scans last 7 days (per day)
        var scansLast7 = await _db.ScanRecords
            .Where(s => s.CreatedAt >= sevenDaysAgo)
            .GroupBy(s => s.CreatedAt.Date)
            .Select(g => new { Date = g.Key, Count = g.Count() })
            .OrderBy(x => x.Date)
            .ToListAsync();

        var scansLast7Days = Enumerable.Range(0, 7)
            .Select(i => today.AddDays(-6 + i))
            .Select(d => new
            {
                date  = d.ToString("yyyy-MM-dd"),
                count = scansLast7.FirstOrDefault(x => x.Date == d)?.Count ?? 0,
            })
            .ToList();

        // Top detection results
        var topDetections = await _db.ScanRecords
            .Where(s => s.DetectionResult != null && s.Status == ScanStatus.Completed)
            .GroupBy(s => s.DetectionResult!)
            .Select(g => new { Result = g.Key, Count = g.Count() })
            .OrderByDescending(x => x.Count)
            .Take(10)
            .ToListAsync();

        // Model accuracy from evaluation reports (if available)
        var modelAccuracy = new Dictionary<string, double>();
        var reportsDir = Path.Combine(Directory.GetCurrentDirectory(), "..", "ai-server", "models", "reports");
        if (Directory.Exists(reportsDir))
        {
            foreach (var file in Directory.GetFiles(reportsDir, "*_eval.json"))
            {
                try
                {
                    var json = await System.IO.File.ReadAllTextAsync(file);
                    var doc  = System.Text.Json.JsonDocument.Parse(json);
                    if (doc.RootElement.TryGetProperty("model", out var modelEl) &&
                        doc.RootElement.TryGetProperty("accuracy", out var accEl))
                    {
                        modelAccuracy[modelEl.GetString()!] = accEl.GetDouble();
                    }
                }
                catch { /* ignore malformed files */ }
            }
        }

        var stats = new
        {
            totalUsers,
            totalScans,
            scansToday,
            activeUsers,
            scansByType,
            scansLast7Days,
            topDetections = topDetections.Select(x => new { result = x.Result, count = x.Count }),
            modelAccuracy,
        };

        return Ok(ApiResponse<object>.Ok(stats));
    }

    // ── Users ─────────────────────────────────────────────────

    /// <summary>Get paginated user list with optional search</summary>
    [HttpGet("users")]
    public async Task<IActionResult> GetUsers(
        [FromQuery] string? search,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 20)
    {
        if (page < 1) page = 1;
        if (pageSize < 1 || pageSize > 100) pageSize = 20;

        var query = _db.Users.AsNoTracking().AsQueryable();

        if (!string.IsNullOrEmpty(search))
        {
            var lower = search.ToLower();
            query = query.Where(u =>
                u.FullName.ToLower().Contains(lower) ||
                (u.Email != null && u.Email.ToLower().Contains(lower)));
        }

        var total = await query.CountAsync();

        var users = await query
            .OrderByDescending(u => u.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .Select(u => new
            {
                id        = u.Id,
                fullName  = u.FullName,
                email     = u.Email,
                role      = u.Role,
                isActive  = u.IsActive,
                createdAt = u.CreatedAt,
                scanCount = _db.ScanRecords.Count(s => s.UserId == u.Id),
            })
            .ToListAsync();

        var result = new
        {
            items      = users,
            totalCount = total,
            page,
            pageSize,
            totalPages = (int)Math.Ceiling((double)total / pageSize),
        };

        return Ok(ApiResponse<object>.Ok(result));
    }

    /// <summary>Update user active status</summary>
    [HttpPatch("users/{userId}")]
    public async Task<IActionResult> UpdateUserStatus(string userId, [FromBody] UpdateStatusRequest req)
    {
        await using var transaction = await AccountMutationLock.AcquireAsync(_db);
        if (!await ActingAdminIsCurrent()) return Unauthorized();
        var user = await _userManager.FindByIdAsync(userId);
        if (user == null)
            return NotFound(ApiResponse<object>.Fail("User not found."));

        if (req.IsActive && await _db.AccountDeletionJobs.AnyAsync(j => j.UserId == userId))
            return Conflict(ApiResponse<object>.Fail("An account pending deletion cannot be reactivated."));
        if (!req.IsActive && user.IsActive && user.Role == "Admin" && await _db.Users.CountAsync(u => u.Role == "Admin" && u.IsActive) < 2)
            return Conflict(ApiResponse<object>.Fail("Transfer administrator access before disabling the last administrator."));
        user.IsActive = req.IsActive;
        user.SecurityStamp = Guid.NewGuid().ToString("N");
        var updated = await _userManager.UpdateAsync(user);
        if (!updated.Succeeded) return Conflict(ApiResponse<object>.Fail("Account update failed."));
        await _db.RefreshTokens.Where(t => t.UserId == userId).ExecuteDeleteAsync();

        var adminId = User.FindFirstValue(ClaimTypes.NameIdentifier);
        await _audit.LogAsync("Admin.UpdateUserStatus", "User", userId, adminId,
            newValues: $"isActive={req.IsActive}");
        await transaction.CommitAsync();

        return Ok(ApiResponse<object>.Ok(null!, "User status updated."));
    }

    /// <summary>Update user role</summary>
    [HttpPatch("users/{userId}/role")]
    public async Task<IActionResult> UpdateUserRole(string userId, [FromBody] UpdateRoleRequest req)
    {
        await using var transaction = await AccountMutationLock.AcquireAsync(_db);
        if (!await ActingAdminIsCurrent()) return Unauthorized();
        var user = await _userManager.FindByIdAsync(userId);
        if (user == null)
            return NotFound(ApiResponse<object>.Fail("User not found."));

        var validRoles = new[] { "User", "Doctor", "Admin" };
        if (!validRoles.Contains(req.Role))
            return BadRequest(ApiResponse<object>.Fail("Invalid role."));
        if (user.Role == "Admin" && user.IsActive && req.Role != "Admin" && await _db.Users.CountAsync(u => u.Role == "Admin" && u.IsActive) < 2)
            return Conflict(ApiResponse<object>.Fail("Transfer administrator access before demoting the last administrator."));

        var oldRole = user.Role;
        user.Role = req.Role;
        user.SecurityStamp = Guid.NewGuid().ToString("N");
        if (!(await _userManager.UpdateAsync(user)).Succeeded)
            return Conflict(ApiResponse<object>.Fail("Account update failed."));

        // Update Identity roles
        var currentRoles = await _userManager.GetRolesAsync(user);
        if (!(await _userManager.RemoveFromRolesAsync(user, currentRoles)).Succeeded ||
            !(await _userManager.AddToRoleAsync(user, req.Role)).Succeeded)
            return Conflict(ApiResponse<object>.Fail("Role update failed."));
        await _db.RefreshTokens.Where(t => t.UserId == userId).ExecuteDeleteAsync();

        var adminId = User.FindFirstValue(ClaimTypes.NameIdentifier);
        await _audit.LogAsync("Admin.UpdateUserRole", "User", userId, adminId,
            oldValues: $"role={oldRole}", newValues: $"role={req.Role}");
        await transaction.CommitAsync();

        return Ok(ApiResponse<object>.Ok(null!, "User role updated."));
    }

    private async Task<bool> ActingAdminIsCurrent()
    {
        var id = User.FindFirstValue(ClaimTypes.NameIdentifier);
        var stamp = User.FindFirstValue("sst");
        return !string.IsNullOrEmpty(stamp) && await _db.Users.AsNoTracking()
            .AnyAsync(u => u.Id == id && u.IsActive && u.Role == "Admin" && u.SecurityStamp == stamp);
    }

    // ── Scans ─────────────────────────────────────────────────

    /// <summary>Get all scans (admin view — all users)</summary>
    [HttpGet("scans")]
    public async Task<IActionResult> GetScans(
        [FromQuery] string? scanType,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 25)
    {
        if (page < 1) page = 1;
        if (pageSize < 1 || pageSize > 100) pageSize = 25;

        var query = _db.ScanRecords
            .Include(s => s.User)
            .AsNoTracking()
            .AsQueryable();

        if (!string.IsNullOrEmpty(scanType) &&
            Enum.TryParse<ScanType>(scanType, out var parsedType))
        {
            query = query.Where(s => s.ScanType == parsedType);
        }

        var total = await query.CountAsync();
        var scans = await query
            .OrderByDescending(s => s.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .Select(s => new
            {
                id              = s.Id,
                userId          = s.UserId,
                userEmail       = s.User != null ? s.User.Email : null,
                scanType        = s.ScanType.ToString(),
                status          = s.Status.ToString(),
                detectionResult = s.DetectionResult,
                confidenceScore = s.ConfidenceScore,
                createdAt       = s.CreatedAt,
                completedAt     = s.CompletedAt,
            })
            .ToListAsync();

        var result = new
        {
            items      = scans,
            totalCount = total,
            page,
            pageSize,
            totalPages = (int)Math.Ceiling((double)total / pageSize),
        };

        return Ok(ApiResponse<object>.Ok(result));
    }

    // ── Audit Logs ────────────────────────────────────────────

    /// <summary>Get audit logs with filters</summary>
    [HttpGet("audit")]
    public async Task<IActionResult> GetAuditLogs(
        [FromQuery] string? userId,
        [FromQuery] string? action,
        [FromQuery] DateTime? from,
        [FromQuery] DateTime? to,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 50)
    {
        if (page < 1) page = 1;
        if (pageSize < 1 || pageSize > 200) pageSize = 50;

        var logs = await _audit.GetLogsAsync(userId, action, from, to, page, pageSize);

        var total = logs.Count; // simplified — would need COUNT query for exact total
        var result = new
        {
            items      = logs,
            totalCount = total,
            page,
            pageSize,
            totalPages = Math.Max(1, (int)Math.Ceiling((double)total / pageSize)),
        };

        return Ok(ApiResponse<object>.Ok(result));
    }
}

public class UpdateStatusRequest { public bool IsActive { get; set; } }
public class UpdateRoleRequest   { public string Role { get; set; } = "User"; }
