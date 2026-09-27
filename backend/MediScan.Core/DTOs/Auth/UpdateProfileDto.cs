namespace MediScan.Core.DTOs.Auth;

public class UpdateProfileDto
{
    public string? FullName { get; set; }
    public string? Gender { get; set; }
    public DateTime? DateOfBirth { get; set; }
    public float? WeightKg { get; set; }
    public float? HeightCm { get; set; }
    public string? BloodGroup { get; set; }
    public string? MedicalHistory { get; set; }
}
