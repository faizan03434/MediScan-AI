using MediScan.Core.DTOs.Scan;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Core.Services;

// Note: IAppDbContext would be better for testability, using generic approach here
// Infra layer will register AppDbContext which implements this via DI
public interface IAppDbContext
{
    DbSet<ScanRecord> ScanRecords { get; }
    DbSet<MedicationRecord> MedicationRecords { get; }
    DbSet<PrescriptionRecord> PrescriptionRecords { get; }
    DbSet<DrugCache> DrugCaches { get; }
    DbSet<AuditLog> AuditLogs { get; }
    Task<int> SaveChangesAsync(CancellationToken cancellationToken = default);
}

public class ScanService : IScanService
{
    private readonly IAppDbContext _db;
    private readonly IStorageService _storage;
    private readonly IAiInferenceService _aiService;
    private readonly IRecommendationService _recommendation;
    private readonly IAuditService _audit;

    public ScanService(
        IAppDbContext db,
        IStorageService storage,
        IAiInferenceService aiService,
        IRecommendationService recommendation,
        IAuditService audit)
    {
        _db = db;
        _storage = storage;
        _aiService = aiService;
        _recommendation = recommendation;
        _audit = audit;
    }

    public async Task<ScanResultDto> CreateScanAsync(
        string userId, CreateScanDto dto, Stream? imageStream, string? contentType)
    {
        var scan = new ScanRecord
        {
            UserId = userId,
            ScanType = dto.ScanType,
            Status = ScanStatus.Processing
        };

        _db.ScanRecords.Add(scan);
        await _db.SaveChangesAsync();

        try
        {
            // Upload image if provided
            if (imageStream != null && !string.IsNullOrEmpty(contentType))
            {
                var (url, blobName) = await _storage.UploadAsync(
                    imageStream,
                    $"{dto.ScanType}_{scan.Id}.jpg",
                    contentType,
                    $"scans/{userId}");

                scan.ImageUrl = url;
                scan.ImageBlobName = blobName;

                // Reset stream for AI inference
                imageStream.Position = 0;

                // Run AI inference
                var aiResult = await _aiService.RunInferenceAsync(dto.ScanType, imageStream, contentType);

                scan.DetectionResult = aiResult.DetectionResult;
                scan.ConfidenceScore = aiResult.ConfidenceScore;
                scan.DetectionDetails = aiResult.DetectionDetails;
                scan.AiRecommendation = aiResult.Recommendation;

                // ── GPT-4o post-scan lifestyle advice ──────────
                try
                {
                    var advice = await _recommendation.GetScanAdviceAsync(
                        dto.ScanType,
                        aiResult.DetectionResult,
                        aiResult.ConfidenceScore);

                    // Append GPT advice to AI recommendation
                    scan.AiRecommendation = string.IsNullOrEmpty(aiResult.Recommendation)
                        ? FormatAdvice(advice)
                        : aiResult.Recommendation + "\n\n" + FormatAdvice(advice);

                    if (aiResult.NextScanDays == null && advice.NextScanDays > 0)
                    {
                        scan.NextScanRecommendation = $"Scan again in {advice.NextScanDays} days — {advice.NextScanReason}";
                        scan.NextScanDate = DateTime.UtcNow.AddDays(advice.NextScanDays);
                    }
                }
                catch { /* GPT-4o unavailable — fallback already in aiResult.Recommendation */ }

                if (aiResult.NextScanDays.HasValue && scan.NextScanDate == null)
                {
                    scan.NextScanRecommendation = $"Scan again in {aiResult.NextScanDays} days";
                    scan.NextScanDate = DateTime.UtcNow.AddDays(aiResult.NextScanDays.Value);
                }
            }

            scan.Status = ScanStatus.Completed;
            scan.CompletedAt = DateTime.UtcNow;
            await _db.SaveChangesAsync();

            await _audit.LogAsync("Scan.Create", "ScanRecord", scan.Id.ToString(), userId);
        }
        catch (Exception ex)
        {
            scan.Status = ScanStatus.Failed;
            await _db.SaveChangesAsync();
            await _audit.LogAsync("Scan.Create", "ScanRecord", scan.Id.ToString(),
                userId, success: false, errorMessage: ex.Message);
            throw;
        }

        return MapToDto(scan);
    }

    public async Task<ScanResultDto?> GetScanByIdAsync(Guid scanId, string userId)
    {
        var scan = await _db.ScanRecords
            .FirstOrDefaultAsync(s => s.Id == scanId && s.UserId == userId);

        return scan == null ? null : MapToDto(scan);
    }

    public async Task<ScanHistoryDto> GetScanHistoryAsync(
        string userId, ScanType? type, int page, int pageSize)
    {
        var query = _db.ScanRecords
            .Where(s => s.UserId == userId)
            .AsQueryable();

        if (type.HasValue)
            query = query.Where(s => s.ScanType == type.Value);

        var total = await query.CountAsync();
        var scans = await query
            .OrderByDescending(s => s.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return new ScanHistoryDto
        {
            Scans = scans.Select(MapToDto).ToList(),
            TotalCount = total,
            Page = page,
            PageSize = pageSize
        };
    }

    public async Task<List<ScanResultDto>> GetRecentScansAsync(string userId, int count = 5)
    {
        var scans = await _db.ScanRecords
            .Where(s => s.UserId == userId)
            .OrderByDescending(s => s.CreatedAt)
            .Take(count)
            .ToListAsync();

        return scans.Select(MapToDto).ToList();
    }

    public async Task<ScanResultDto> CompareScanAsync(Guid scanId1, Guid scanId2, string userId)
    {
        // Returns the newer scan with comparison data in DetectionDetails
        var scan1 = await _db.ScanRecords.FirstOrDefaultAsync(s => s.Id == scanId1 && s.UserId == userId);
        var scan2 = await _db.ScanRecords.FirstOrDefaultAsync(s => s.Id == scanId2 && s.UserId == userId);

        if (scan1 == null || scan2 == null)
            throw new KeyNotFoundException("One or both scans not found.");

        var newer = scan1.CreatedAt > scan2.CreatedAt ? scan1 : scan2;
        var older = scan1.CreatedAt > scan2.CreatedAt ? scan2 : scan1;

        // Attach comparison note
        var dto = MapToDto(newer);
        dto.DetectionDetails = System.Text.Json.JsonSerializer.Serialize(new
        {
            CurrentScan = newer.DetectionResult,
            CurrentConfidence = newer.ConfidenceScore,
            PreviousScan = older.DetectionResult,
            PreviousConfidence = older.ConfidenceScore,
            DaysDifference = (newer.CreatedAt - older.CreatedAt).Days
        });

        return dto;
    }

    public async Task DeleteScanAsync(Guid scanId, string userId)
    {
        var scan = await _db.ScanRecords
            .FirstOrDefaultAsync(s => s.Id == scanId && s.UserId == userId);

        if (scan == null)
            throw new KeyNotFoundException("Scan not found.");

        scan.IsDeleted = true;
        await _db.SaveChangesAsync();
        await _audit.LogAsync("Scan.Delete", "ScanRecord", scanId.ToString(), userId);
    }

    private static ScanResultDto MapToDto(ScanRecord scan) => new()
    {
        Id = scan.Id,
        ScanType = scan.ScanType,
        Status = scan.Status,
        ImageUrl = scan.ImageUrl,
        DetectionResult = scan.DetectionResult,
        ConfidenceScore = scan.ConfidenceScore,
        DetectionDetails = scan.DetectionDetails,
        AiRecommendation = scan.AiRecommendation,
        NextScanRecommendation = scan.NextScanRecommendation,
        NextScanDate = scan.NextScanDate,
        CreatedAt = scan.CreatedAt,
        CompletedAt = scan.CompletedAt
    };

    private static string FormatAdvice(ScanRecommendation advice)
    {
        var sb = new System.Text.StringBuilder();
        if (!string.IsNullOrEmpty(advice.LifestyleAdvice))
            sb.AppendLine("💡 Lifestyle: " + advice.LifestyleAdvice);
        if (!string.IsNullOrEmpty(advice.DietAdvice))
            sb.AppendLine("🥗 Diet: " + advice.DietAdvice);
        if (!string.IsNullOrEmpty(advice.WhenToSeeDoctor))
            sb.AppendLine("⚕️ See Doctor When: " + advice.WhenToSeeDoctor);
        if (advice.KeyPoints.Count > 0)
            sb.AppendLine("📌 Key Points:\n" + string.Join("\n", advice.KeyPoints.Select(p => "• " + p)));
        return sb.ToString().Trim();
    }
}
