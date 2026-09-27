using MediScan.Core.Entities;

namespace MediScan.Core.Interfaces;

public class ScanRecommendation
{
    public string LifestyleAdvice { get; set; } = string.Empty;
    public string DietAdvice { get; set; } = string.Empty;
    public string WhenToSeeDoctor { get; set; } = string.Empty;
    public int NextScanDays { get; set; } = 30;
    public string NextScanReason { get; set; } = string.Empty;
    public List<string> KeyPoints { get; set; } = new();
}

public class DrugSafetyAnalysis
{
    public string Summary { get; set; } = string.Empty;
    public bool HasCriticalWarning { get; set; }
    public List<string> Warnings { get; set; } = new();
    public List<string> Interactions { get; set; } = new();
    public List<string> Recommendations { get; set; } = new();
}

public interface IRecommendationService
{
    /// <summary>Generate lifestyle + follow-up advice for a completed scan using GPT-4o.</summary>
    Task<ScanRecommendation> GetScanAdviceAsync(
        ScanType scanType,
        string detectionResult,
        float confidence,
        User? userContext = null);

    /// <summary>Analyze prescription safety using GPT-4o — drug interactions, warnings.</summary>
    Task<DrugSafetyAnalysis> AnalyzePrescriptionSafetyAsync(
        List<string> drugNames,
        string? patientAge = null,
        string? patientConditions = null);

    /// <summary>Simple drug info enrichment prompt.</summary>
    Task<string> EnrichDrugInfoAsync(string drugName, string rawInfo);
}

/// <summary>Lightweight user context for personalized recommendations.</summary>
public class User
{
    public int? AgeYears { get; set; }
    public string? Gender { get; set; }
    public string? BloodGroup { get; set; }
    public string? MedicalHistory { get; set; }
}
