using System.Security.Claims;
using MediScan.Core.DTOs.Common;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Controllers;

public sealed record AccountActivityItem(Guid Id, string Action, string Category, bool Success, DateTime CreatedAt);

[ApiController]
[Route("api/v1/account/activity")]
[Authorize]
[ResponseCache(NoStore = true, Location = ResponseCacheLocation.None)]
public class AccountActivityController(AppDbContext db) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> Get([FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        CancellationToken cancellationToken = default)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (string.IsNullOrWhiteSpace(userId)) return Unauthorized();
        if (page < 1 || page > 100000 || pageSize < 1 || pageSize > 50)
            return BadRequest(ApiResponse<object>.Fail("Use page 1–100000 and page size 1–50."));
        var query = db.AuditLogs.AsNoTracking().Where(log => log.UserId == userId);
        var total = await query.CountAsync(cancellationToken);
        var items = await query.OrderByDescending(log => log.CreatedAt).ThenBy(log => log.Id)
            .Skip((page - 1) * pageSize).Take(pageSize)
            .Select(log => new AccountActivityItem(log.Id, log.Action, log.EntityType, log.Success, log.CreatedAt))
            .ToListAsync(cancellationToken);
        Response.Headers.CacheControl = "private, no-store";
        return Ok(ApiResponse<PagedResponse<AccountActivityItem>>.Ok(new()
        { Items = items, TotalCount = total, Page = page, PageSize = pageSize }));
    }
}
