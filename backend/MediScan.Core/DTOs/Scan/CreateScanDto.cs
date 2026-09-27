using MediScan.Core.Entities;
using System.ComponentModel.DataAnnotations;

namespace MediScan.Core.DTOs.Scan;

public class CreateScanDto
{
    [Required]
    public ScanType ScanType { get; set; }

    // Base64 encoded image OR multipart form — handled in controller
    public string? ImageBase64 { get; set; }
}

public class ScanResultDto
{
    public Guid Id { get; set; }
    public ScanType ScanType { get; set; }
    public ScanStatus Status { get; set; }
    public string? ImageUrl { get; set; }
    public string? DetectionResult { get; set; }
    public float? ConfidenceScore { get; set; }
    public string? DetectionDetails { get; set; }
    public string? AiRecommendation { get; set; }
    public string? NextScanRecommendation { get; set; }
    public DateTime? NextScanDate { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
}

public class ScanHistoryDto
{
    public List<ScanResultDto> Scans { get; set; } = new();
    public int TotalCount { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
}
