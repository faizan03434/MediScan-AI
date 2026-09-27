using System.Text.Json;
using MediScan.Core.DTOs.Medication;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using Microsoft.EntityFrameworkCore;

namespace MediScan.Core.Services;

public class MedicationService : IMedicationService
{
    private readonly IAppDbContext _db;
    private readonly IDrugDataService _drugData;
    private readonly IRecommendationService _ai;
    private readonly IStorageService _storage;
    private readonly IAuditService _audit;

    public MedicationService(
        IAppDbContext db,
        IDrugDataService drugData,
        IRecommendationService ai,
        IStorageService storage,
        IAuditService audit)
    {
        _db = db;
        _drugData = drugData;
        _ai = ai;
        _storage = storage;
        _audit = audit;
    }

    // ── Drug search by name ───────────────────────────────────
    public async Task<DrugInfoDto> SearchByNameAsync(string query, string? country = null)
    {
        var result = await _drugData.FetchByNameAsync(query.Trim(), country);

        if (result == null)
            return new DrugInfoDto
            {
                BrandName = query,
                Source = "NotFound",
                Warnings = new List<string>
                {
                    $"No information found for \"{query}\" in our database.",
                    "Try searching with a different name or the generic (chemical) name.",
                    "Consult a pharmacist for accurate information."
                }
            };

        // Optionally enrich with GPT-4o if info is sparse
        if (string.IsNullOrEmpty(result.Indication) && string.IsNullOrEmpty(result.AiAnalysis))
        {
            try
            {
                var rawInfo = $"Brand: {result.BrandName}, Generic: {result.GenericName}, Form: {result.DosageForm}";
                result.AiAnalysis = await _ai.EnrichDrugInfoAsync(query, rawInfo);
            }
            catch { /* Non-critical — continue without AI enrichment */ }
        }

        return result;
    }

    // ── Drug search by barcode ────────────────────────────────
    public async Task<DrugInfoDto> SearchByBarcodeAsync(string barcode)
    {
        var result = await _drugData.FetchByBarcodeAsync(barcode.Trim());

        if (result == null)
            return new DrugInfoDto
            {
                BrandName = barcode,
                Source = "NotFound",
                Warnings = new List<string>
                {
                    "Barcode not found in our database.",
                    "This product may not be registered in the OpenFDA database.",
                    "For Pakistani medicines, check the DAP website: https://www.dap.gov.pk",
                    "Consult your pharmacist."
                }
            };

        return result;
    }

    // ── Save medication to user history ───────────────────────
    public async Task<MedicationRecordDto> SaveMedicationAsync(string userId, SaveMedicationRequest request)
    {
        // Fetch latest drug info to store full details
        DrugInfoDto? drugInfo = null;
        try { drugInfo = await _drugData.FetchByNameAsync(request.DrugName); } catch { }

        if (!Enum.TryParse<MedicationInputMethod>(request.InputMethod, out var inputMethod))
            inputMethod = MedicationInputMethod.ManualEntry;

        var record = new MedicationRecord
        {
            UserId             = userId,
            DrugName           = request.DrugName,
            GenericName        = request.GenericName ?? drugInfo?.GenericName,
            Manufacturer       = drugInfo?.Manufacturer,
            Barcode            = request.Barcode,
            DosageForm         = request.DosageForm ?? drugInfo?.DosageForm,
            Strength           = request.Strength ?? drugInfo?.Strength,
            Indication         = drugInfo?.Indication,
            SideEffects        = drugInfo?.SideEffects.Count > 0
                                    ? JsonSerializer.Serialize(drugInfo.SideEffects) : null,
            Warnings           = drugInfo?.Warnings.Count > 0
                                    ? JsonSerializer.Serialize(drugInfo.Warnings) : null,
            DrugInteractions   = drugInfo?.Interactions.Count > 0
                                    ? JsonSerializer.Serialize(drugInfo.Interactions) : null,
            Contraindications  = drugInfo?.Contraindications.Count > 0
                                    ? JsonSerializer.Serialize(drugInfo.Contraindications) : null,
            StorageInfo        = drugInfo?.StorageInfo,
            AiAnalysis         = drugInfo?.AiAnalysis,
            HasSafetyWarning   = drugInfo?.HasSafetyWarning ?? false,
            InputMethod        = inputMethod,
            IsPrescription     = request.IsPrescription,
            PrescribedBy       = request.PrescribedBy,
            PrescribedDate     = request.PrescribedDate,
            PrescriptionRecordId = request.PrescriptionRecordId,
            CreatedAt          = DateTime.UtcNow,
        };

        _db.MedicationRecords.Add(record);
        await _db.SaveChangesAsync();
        await _audit.LogAsync("Medication.Save", "MedicationRecord", record.Id.ToString(), userId);

        return MapToDto(record);
    }

    // ── Get medication history ────────────────────────────────
    public async Task<MedicationHistoryDto> GetHistoryAsync(string userId, int page = 1, int pageSize = 20)
    {
        var query = _db.MedicationRecords.Where(m => m.UserId == userId);
        var total = await query.CountAsync();
        var items = await query
            .OrderByDescending(m => m.CreatedAt)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync();

        return new MedicationHistoryDto
        {
            Items     = items.Select(MapToDto).ToList(),
            TotalCount = total,
            Page      = page,
            PageSize  = pageSize,
        };
    }

    // ── Get single medication ─────────────────────────────────
    public async Task<MedicationRecordDto?> GetByIdAsync(Guid id, string userId)
    {
        var record = await _db.MedicationRecords
            .FirstOrDefaultAsync(m => m.Id == id && m.UserId == userId);
        return record == null ? null : MapToDto(record);
    }

    // ── Delete medication ─────────────────────────────────────
    public async Task DeleteAsync(Guid id, string userId)
    {
        var record = await _db.MedicationRecords
            .FirstOrDefaultAsync(m => m.Id == id && m.UserId == userId)
            ?? throw new KeyNotFoundException("Medication record not found.");

        record.IsDeleted = true;
        await _db.SaveChangesAsync();
        await _audit.LogAsync("Medication.Delete", "MedicationRecord", id.ToString(), userId);
    }

    // ── Analyze prescription image (OCR + GPT-4o) ────────────
    public async Task<PrescriptionAnalysisDto> AnalyzePrescriptionAsync(
        string userId, SubmitPrescriptionRequest request,
        Stream imageStream, string contentType)
    {
        // 1. Upload image to Azure Blob
        string? imageUrl = null;
        string? blobName = null;
        try
        {
            var (url, blob) = await _storage.UploadAsync(
                imageStream, $"prescription_{Guid.NewGuid()}.jpg",
                contentType, $"prescriptions/{userId}");
            imageUrl = url;
            blobName = blob;
        }
        catch { /* Storage not configured in dev — continue without image */ }

        // 2. Create prescription record
        var prescription = new PrescriptionRecord
        {
            UserId        = userId,
            DoctorName    = request.DoctorName,
            DoctorSpecialty = request.DoctorSpecialty,
            ClinicName    = request.ClinicName,
            PrescribedDate = request.PrescribedDate,
            Notes         = request.Notes,
            ImageUrl      = imageUrl,
            ImageBlobName = blobName,
            Status        = PrescriptionStatus.Active,
            CreatedAt     = DateTime.UtcNow,
        };

        _db.PrescriptionRecords.Add(prescription);
        await _db.SaveChangesAsync();

        // 3. OCR — In Phase 3 we'll integrate Google ML Kit OCR via mobile.
        //    For now the API accepts manually typed drug names in Notes field.
        //    The mobile app sends parsed text from ML Kit to this endpoint.
        var ocrText = request.Notes ?? "";
        prescription.OcrRawText = ocrText;

        // 4. Parse drug names from OCR text (simple line-based extraction)
        var drugNames = ExtractDrugNames(ocrText);

        // 5. Fetch drug info for each parsed drug
        var parsedDrugs = new List<ParsedPrescriptionDrug>();
        foreach (var name in drugNames.Take(10)) // limit to 10 drugs
        {
            var drugInfo = await _drugData.FetchByNameAsync(name);
            parsedDrugs.Add(new ParsedPrescriptionDrug
            {
                DrugName   = name,
                IsKnownDrug = drugInfo?.Source != "NotFound",
                DrugInfo   = drugInfo,
            });

            // Save each drug to medication history
            if (drugInfo != null)
            {
                var medRecord = new MedicationRecord
                {
                    UserId               = userId,
                    DrugName             = name,
                    GenericName          = drugInfo.GenericName,
                    Manufacturer         = drugInfo.Manufacturer,
                    DosageForm           = drugInfo.DosageForm,
                    Strength             = drugInfo.Strength,
                    Indication           = drugInfo.Indication,
                    SideEffects          = JsonSerializer.Serialize(drugInfo.SideEffects),
                    Warnings             = JsonSerializer.Serialize(drugInfo.Warnings),
                    DrugInteractions     = JsonSerializer.Serialize(drugInfo.Interactions),
                    HasSafetyWarning     = drugInfo.HasSafetyWarning,
                    InputMethod          = MedicationInputMethod.OcrScan,
                    IsPrescription       = true,
                    PrescribedBy         = request.DoctorName,
                    PrescribedDate       = request.PrescribedDate,
                    PrescriptionRecordId = prescription.Id,
                };
                _db.MedicationRecords.Add(medRecord);
            }
        }
        await _db.SaveChangesAsync();

        // 6. GPT-4o safety analysis
        DrugSafetyAnalysis? safety = null;
        if (drugNames.Count > 0)
        {
            try
            {
                safety = await _ai.AnalyzePrescriptionSafetyAsync(drugNames);
                prescription.AiAnalysis     = safety.Summary;
                prescription.HasSafetyWarnings = safety.HasCriticalWarning;
                prescription.AiParsedJson   = JsonSerializer.Serialize(parsedDrugs);
                await _db.SaveChangesAsync();
            }
            catch { /* GPT-4o unavailable — continue */ }
        }

        await _audit.LogAsync("Prescription.Analyze", "PrescriptionRecord",
            prescription.Id.ToString(), userId);

        return new PrescriptionAnalysisDto
        {
            Id              = prescription.Id,
            DoctorName      = prescription.DoctorName,
            PrescribedDate  = prescription.PrescribedDate,
            ImageUrl        = imageUrl,
            Medications     = parsedDrugs,
            AiAnalysis      = safety?.Summary ?? "Analysis pending — configure Azure OpenAI for automatic analysis.",
            HasSafetyWarnings = safety?.HasCriticalWarning ?? false,
            Warnings        = safety?.Warnings ?? new(),
            Interactions    = safety?.Interactions ?? new(),
            OcrRawText      = ocrText,
            CreatedAt       = prescription.CreatedAt,
        };
    }

    // ── Get prescriptions ─────────────────────────────────────
    public async Task<List<PrescriptionSummaryDto>> GetPrescriptionsAsync(string userId)
    {
        var prescriptions = await _db.PrescriptionRecords
            .Where(p => p.UserId == userId)
            .OrderByDescending(p => p.CreatedAt)
            .Take(50)
            .ToListAsync();

        return prescriptions.Select(p => new PrescriptionSummaryDto
        {
            Id               = p.Id,
            DoctorName       = p.DoctorName,
            Diagnosis        = p.Diagnosis,
            MedicationCount  = p.Medications?.Count ?? 0,
            HasSafetyWarnings = p.HasSafetyWarnings,
            ImageUrl         = p.ImageUrl,
            CreatedAt        = p.CreatedAt,
            Status           = p.Status.ToString(),
        }).ToList();
    }

    // ── Get single prescription ───────────────────────────────
    public async Task<PrescriptionAnalysisDto?> GetPrescriptionByIdAsync(Guid id, string userId)
    {
        var p = await _db.PrescriptionRecords
            .Include(x => x.Medications)
            .FirstOrDefaultAsync(x => x.Id == id && x.UserId == userId);

        if (p == null) return null;

        List<ParsedPrescriptionDrug> drugs = new();
        if (!string.IsNullOrEmpty(p.AiParsedJson))
        {
            try { drugs = JsonSerializer.Deserialize<List<ParsedPrescriptionDrug>>(p.AiParsedJson) ?? new(); }
            catch { }
        }

        return new PrescriptionAnalysisDto
        {
            Id             = p.Id,
            DoctorName     = p.DoctorName,
            PrescribedDate = p.PrescribedDate,
            ImageUrl       = p.ImageUrl,
            Medications    = drugs,
            AiAnalysis     = p.AiAnalysis,
            HasSafetyWarnings = p.HasSafetyWarnings,
            OcrRawText     = p.OcrRawText ?? "",
            CreatedAt      = p.CreatedAt,
        };
    }

    // ── Helpers ───────────────────────────────────────────────
    private static List<string> ExtractDrugNames(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return new();

        return text
            .Split(new[] { '\n', ',', ';', '|' }, StringSplitOptions.RemoveEmptyEntries)
            .Select(s => s.Trim())
            .Where(s => s.Length >= 3 && s.Length <= 100)
            .Where(s => !s.All(char.IsDigit)) // skip pure numbers
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Take(10)
            .ToList();
    }

    private static MedicationRecordDto MapToDto(MedicationRecord m)
    {
        var dto = new MedicationRecordDto
        {
            Id             = m.Id,
            DrugName       = m.DrugName,
            GenericName    = m.GenericName,
            Manufacturer   = m.Manufacturer,
            DosageForm     = m.DosageForm,
            Strength       = m.Strength,
            Indication     = m.Indication,
            AiAnalysis     = m.AiAnalysis,
            HasSafetyWarning = m.HasSafetyWarning,
            ImageUrl       = m.ImageUrl,
            InputMethod    = m.InputMethod.ToString(),
            IsPrescription = m.IsPrescription,
            PrescribedBy   = m.PrescribedBy,
            PrescribedDate = m.PrescribedDate,
            CreatedAt      = m.CreatedAt,
        };

        if (!string.IsNullOrEmpty(m.SideEffects))
            try { dto.SideEffects = JsonSerializer.Deserialize<List<string>>(m.SideEffects) ?? new(); } catch { }
        if (!string.IsNullOrEmpty(m.Warnings))
            try { dto.Warnings = JsonSerializer.Deserialize<List<string>>(m.Warnings) ?? new(); } catch { }

        return dto;
    }
}
