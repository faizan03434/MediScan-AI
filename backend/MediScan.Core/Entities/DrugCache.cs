namespace MediScan.Core.Entities;

/// <summary>
/// Caches drug info fetched from OpenFDA / Pakistan DAP
/// so we don't hit external APIs repeatedly for the same drug.
/// </summary>
public class DrugCache
{
    public Guid Id { get; set; } = Guid.NewGuid();

    /// <summary>Normalized drug name (lowercase, trimmed) used as lookup key.</summary>
    public string NormalizedName { get; set; } = string.Empty;

    public string? Barcode { get; set; }
    public string BrandName { get; set; } = string.Empty;
    public string? GenericName { get; set; }
    public string? Manufacturer { get; set; }
    public string? DosageForm { get; set; }
    public string? Strength { get; set; }
    public string? Indication { get; set; }
    public string? SideEffectsJson { get; set; }   // JSON array
    public string? WarningsJson { get; set; }       // JSON array
    public string? InteractionsJson { get; set; }   // JSON array
    public string? ContraindicationsJson { get; set; }
    public string? StorageInfo { get; set; }
    public string? CountryOfOrigin { get; set; }    // "PK" | "US" | etc.
    public string? Source { get; set; }             // "OpenFDA" | "PakistanDAP" | "Manual"
    public string? RawResponseJson { get; set; }    // Full API response for debugging

    public DateTime FetchedAt { get; set; } = DateTime.UtcNow;
    public DateTime ExpiresAt { get; set; } = DateTime.UtcNow.AddDays(7); // Re-fetch weekly
    public bool IsExpired => DateTime.UtcNow > ExpiresAt;
}
