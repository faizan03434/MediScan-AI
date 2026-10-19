namespace MediScan.Core.Entities;

public sealed class AccountDeletionJob
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string? UserId { get; set; }
    public string ReceiptHash { get; set; } = "";
    public DateTime RequestedAt { get; set; }
    public DateTime NextAttemptAt { get; set; }
    public DateTime? LeaseUntil { get; set; }
    public string? LeaseToken { get; set; }
    public DateTime? CompletedAt { get; set; }
    public int Attempts { get; set; }
}

// Inventory is independent of health-record creation, so in-flight uploads are discoverable.
public sealed class StoredMedia
{
    public string BlobName { get; set; } = "";
    public string UserId { get; set; } = "";
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}
