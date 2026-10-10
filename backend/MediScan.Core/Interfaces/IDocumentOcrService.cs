using System.Text.Json.Serialization;

namespace MediScan.Core.Interfaces;

public sealed class DocumentOcrLine
{
    public string Text { get; set; } = "";
    public double? Confidence { get; set; }
    public List<float[]> Box { get; set; } = [];
    [JsonPropertyName("needs_review")] public bool NeedsReview { get; set; }
}
public sealed class DocumentOcrResult
{
    public string Text { get; set; } = "";
    public List<DocumentOcrLine> Lines { get; set; } = [];
    public string Engine { get; set; } = "";
    public string Status { get; set; } = "";
    public string Message { get; set; } = "";
    public bool RequiresConfirmation => true;
    public bool PrescriptionVerified => false;
}
public interface IDocumentOcrService
{
    Task<DocumentOcrResult> ExtractAsync(Stream image, string contentType, CancellationToken cancellationToken);
}
