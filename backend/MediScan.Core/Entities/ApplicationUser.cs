using Microsoft.AspNetCore.Identity;

namespace MediScan.Core.Entities;

public class ApplicationUser : IdentityUser
{
    public string FullName { get; set; } = string.Empty;
    public string? Gender { get; set; }
    public DateTime? DateOfBirth { get; set; }
    public float? WeightKg { get; set; }
    public float? HeightCm { get; set; }
    public string? BloodGroup { get; set; }
    public string? MedicalHistory { get; set; }  // JSON string
    public string Role { get; set; } = "User";   // User | Doctor | Admin
    public bool IsActive { get; set; } = true;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? UpdatedAt { get; set; }

    // Navigation
    public ICollection<ScanRecord> ScanRecords { get; set; } = new List<ScanRecord>();
    public ICollection<MedicationRecord> MedicationRecords { get; set; } = new List<MedicationRecord>();
    public ICollection<PrescriptionRecord> PrescriptionRecords { get; set; } = new List<PrescriptionRecord>();
}
