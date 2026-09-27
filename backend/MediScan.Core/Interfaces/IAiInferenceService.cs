using MediScan.Core.Entities;

namespace MediScan.Core.Interfaces;

public class AiInferenceResult
{
    public string DetectionResult { get; set; } = string.Empty;
    public float ConfidenceScore { get; set; }
    public string? DetectionDetails { get; set; }  // JSON
    public string? Recommendation { get; set; }
    public int? NextScanDays { get; set; }
}

public interface IAiInferenceService
{
    Task<AiInferenceResult> RunInferenceAsync(ScanType scanType, Stream imageStream, string contentType);
}
