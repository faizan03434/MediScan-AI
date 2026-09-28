using MediScan.Core.DTOs.Doctor;
using MediScan.Core.DTOs.Scan;

namespace MediScan.Core.Interfaces;

public interface IDoctorService
{
    // ── Consent management ─────────────────────────────────────
    /// <summary>Doctor requests access to a patient's scans.</summary>
    Task<ConsentSummaryDto> RequestConsentAsync(string doctorUserId, RequestConsentDto dto);

    /// <summary>Patient accepts or rejects a doctor's consent request.</summary>
    Task<ConsentSummaryDto> RespondToConsentAsync(string patientUserId, Guid consentId, RespondConsentDto dto);

    /// <summary>Patient revokes previously granted consent.</summary>
    Task RevokeConsentAsync(string patientUserId, Guid consentId);

    /// <summary>Get all consent requests received by this doctor.</summary>
    Task<List<ConsentSummaryDto>> GetDoctorConsentsAsync(string doctorUserId);

    /// <summary>Get all consent requests sent to this patient.</summary>
    Task<List<ConsentSummaryDto>> GetPatientConsentsAsync(string patientUserId);

    // ── Doctor: view patient data ──────────────────────────────
    /// <summary>Get list of patients who granted active consent to this doctor.</summary>
    Task<List<PatientSummaryDto>> GetMyPatientsAsync(string doctorUserId);

    /// <summary>Get scan history for a specific patient (requires active consent).</summary>
    Task<ScanHistoryDto> GetPatientScansAsync(string doctorUserId, string patientUserId,
        int page = 1, int pageSize = 10);

    /// <summary>Get a single scan for a patient (requires active consent).</summary>
    Task<ScanResultDto?> GetPatientScanAsync(string doctorUserId, string patientUserId, Guid scanId);
}
