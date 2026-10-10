using System.ComponentModel.DataAnnotations;

namespace MediScan.Core.DTOs.Auth;

public class UpdateProfileDto
{
    [StringLength(100, MinimumLength = 2)] public string? FullName { get; set; }
    [StringLength(20)] public string? Gender { get; set; }
    public DateTime? DateOfBirth { get; set; }
    [Range(1, 500)] public float? WeightKg { get; set; }
    [Range(20, 300)] public float? HeightCm { get; set; }
    [RegularExpression("^(A|B|AB|O)[+-]$")] public string? BloodGroup { get; set; }
    public string? MedicalHistory { get; set; }
}
