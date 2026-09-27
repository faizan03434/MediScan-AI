using MediScan.Core.DTOs.Medication;

namespace MediScan.Core.Interfaces;

/// <summary>
/// Fetches drug info from external APIs: OpenFDA and Pakistan DAP.
/// Results are cached in DrugCache table.
/// </summary>
public interface IDrugDataService
{
    Task<DrugInfoDto?> FetchByNameAsync(string drugName, string? country = null);
    Task<DrugInfoDto?> FetchByBarcodeAsync(string barcode);
}
