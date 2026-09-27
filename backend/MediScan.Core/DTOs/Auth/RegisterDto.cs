using System.ComponentModel.DataAnnotations;

namespace MediScan.Core.DTOs.Auth;

public class RegisterDto
{
    [Required]
    [StringLength(100, MinimumLength = 2)]
    public string FullName { get; set; } = string.Empty;

    [Required]
    [EmailAddress]
    public string Email { get; set; } = string.Empty;

    [Required]
    [StringLength(100, MinimumLength = 8)]
    public string Password { get; set; } = string.Empty;

    [Required]
    [Compare("Password", ErrorMessage = "Passwords do not match.")]
    public string ConfirmPassword { get; set; } = string.Empty;

    public string? Gender { get; set; }
    public DateTime? DateOfBirth { get; set; }
    public float? WeightKg { get; set; }
    public float? HeightCm { get; set; }
    public string? BloodGroup { get; set; }
}
