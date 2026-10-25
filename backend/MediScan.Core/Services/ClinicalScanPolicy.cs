using System.Text.Json;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;

namespace MediScan.Core.Services;

// No task in this release has independent clinical acceptance. An upstream score,
// flag or recommendation cannot authorize diagnosis, prescriptions or follow-up.
public static class ClinicalScanPolicy
{
    public static string Module(ScanType type) => type switch {
        ScanType.Anemia => "anemia", ScanType.SkinDisease => "skin", ScanType.Posture => "posture",
        ScanType.EyeDisease => "eye", ScanType.Wound => "wound", ScanType.TongueDiagnosis => "tongue",
        ScanType.Retina => "retina", _ => throw new ArgumentException("Unknown scan type.") };

    public static AiInferenceResult ForCurrentRelease(ScanType type) => new() {
        DetectionResult = "Inconclusive — clinical model not validated",
        ConfidenceScore = 0,
        DetectionDetails = JsonSerializer.Serialize(new {
            module = Module(type), status = "not_clinically_validated", clinical_inference = false,
            research_preview = true, comparison_supported = false, prescription_supported = false,
            expected_image_modality = type == ScanType.Retina ? "fundus" : "external_photo" }),
        Recommendation = "Photo saved for review. This scan cannot confirm or rule out a medical condition. Ask a clinician about symptoms and follow-up.",
        NextScanDays = null
    };
}
