namespace MediScan.Core.DTOs.Auth;

public class AuthResponseDto
{
    public string AccessToken { get; set; } = string.Empty;
    public string RefreshToken { get; set; } = string.Empty;
    public DateTime ExpiresAt { get; set; }
    public UserProfileDto User { get; set; } = new();
}

public class UserProfileDto
{
    public string Id { get; set; } = string.Empty;
    public string FullName { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string? Gender { get; set; }
    public DateTime? DateOfBirth { get; set; }
    public float? WeightKg { get; set; }
    public float? HeightCm { get; set; }
    public string? BloodGroup { get; set; }
    public string Role { get; set; } = "User";
    public DateTime CreatedAt { get; set; }
}
