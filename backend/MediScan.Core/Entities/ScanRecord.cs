namespace MediScan.Core.Entities;

public enum ScanType
{
    Anemia,
    SkinDisease,
    Posture,
    EyeDisease,
    Wound,
    TongueDiagnosis,
    Retina
}

public enum ScanStatus
{
    Pending,
    Processing,
    Completed,
    Failed
}

public class ScanRecord
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string UserId { get; set; } = string.Empty;
    public ScanType ScanType { get; set; }
    public ScanStatus Status { get; set; } = ScanStatus.Pending;

    // Image
    public string? ImageUrl { get; set; }        // Azure Blob URL
    public string? ImageBlobName { get; set; }   // Internal blob name

    // AI Result
    public string? DetectionResult { get; set; }     // e.g. "Anemia Detected"
    public float? ConfidenceScore { get; set; }      // 0.0 - 1.0
    public string? DetectionDetails { get; set; }    // JSON: bounding boxes, class probabilities
    public string? AiRecommendation { get; set; }    // Lifestyle tips from GPT-4o
    public string? NextScanRecommendation { get; set; }  // "Scan again in 7 days"
    public DateTime? NextScanDate { get; set; }

    // Metadata
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? CompletedAt { get; set; }
    public bool IsDeleted { get; set; } = false;

    // Navigation
    public ApplicationUser? User { get; set; }
}
