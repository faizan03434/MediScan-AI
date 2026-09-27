using MediScan.Core.DTOs.Medication;

namespace MediScan.Core.Interfaces;

public interface IMedicationService
{
    // ── Drug search ───────────────────────────────────────────
    Task<DrugInfoDto> SearchByNameAsync(string query, string? country = null);
    Task<DrugInfoDto> SearchByBarcodeAsync(string barcode);

    // ── Save to user history ──────────────────────────────────
    Task<MedicationRecordDto> SaveMedicationAsync(string userId, SaveMedicationRequest request);
    Task<MedicationHistoryDto> GetHistoryAsync(string userId, int page = 1, int pageSize = 20);
    Task<MedicationRecordDto?> GetByIdAsync(Guid id, string userId);
    Task DeleteAsync(Guid id, string userId);

    // ── Prescription ──────────────────────────────────────────
    Task<PrescriptionAnalysisDto> AnalyzePrescriptionAsync(
        string userId, SubmitPrescriptionRequest request,
        Stream imageStream, string contentType);

    Task<List<PrescriptionSummaryDto>> GetPrescriptionsAsync(string userId);
    Task<PrescriptionAnalysisDto?> GetPrescriptionByIdAsync(Guid id, string userId);
}
