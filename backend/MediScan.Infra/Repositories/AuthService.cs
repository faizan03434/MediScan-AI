using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using MediScan.Core.DTOs.Auth;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.IdentityModel.Tokens;

namespace MediScan.Infra.Repositories;

public class AuthService : IAuthService
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly AppDbContext _db;
    private readonly IConfiguration _config;

    public AuthService(
        UserManager<ApplicationUser> userManager,
        AppDbContext db,
        IConfiguration config)
    {
        _userManager = userManager;
        _db = db;
        _config = config;
    }

    public async Task<AuthResponseDto> RegisterAsync(RegisterDto dto)
    {
        var existingUser = await _userManager.FindByEmailAsync(dto.Email);
        if (existingUser != null)
            throw new InvalidOperationException("A user with this email already exists.");

        var user = new ApplicationUser
        {
            FullName = dto.FullName,
            Email = dto.Email,
            UserName = dto.Email,
            Gender = dto.Gender,
            DateOfBirth = dto.DateOfBirth,
            WeightKg = dto.WeightKg,
            HeightCm = dto.HeightCm,
            BloodGroup = dto.BloodGroup,
            Role = "User",
            CreatedAt = DateTime.UtcNow
        };

        var result = await _userManager.CreateAsync(user, dto.Password);
        if (!result.Succeeded)
        {
            var errors = result.Errors.Select(e => e.Description).ToList();
            throw new InvalidOperationException(string.Join("; ", errors));
        }

        await _userManager.AddToRoleAsync(user, "User");
        return await GenerateAuthResponseAsync(user);
    }

    public async Task<AuthResponseDto> LoginAsync(LoginDto dto)
    {
        var user = await _userManager.FindByEmailAsync(dto.Email)
            ?? throw new UnauthorizedAccessException("Invalid credentials.");

        if (!user.IsActive)
            throw new UnauthorizedAccessException("Account is deactivated.");
        if (await _userManager.IsLockedOutAsync(user))
            throw new UnauthorizedAccessException("Account is temporarily locked.");

        var validPassword = await _userManager.CheckPasswordAsync(user, dto.Password);
        if (!validPassword)
        {
            await _userManager.AccessFailedAsync(user);
            throw new UnauthorizedAccessException("Invalid credentials.");
        }
        await _userManager.ResetAccessFailedCountAsync(user);

        return await GenerateAuthResponseAsync(user);
    }

    public async Task<AuthResponseDto> RefreshTokenAsync(string refreshToken)
    {
        var token = await _db.RefreshTokens
            .Include(r => r.User)
            .FirstOrDefaultAsync(r => r.Token == refreshToken)
            ?? throw new UnauthorizedAccessException("Invalid refresh token.");

        if (!token.IsActive)
            throw new UnauthorizedAccessException("Refresh token is expired or revoked.");

        // Rotate token
        var newRefreshToken = GenerateRefreshToken();
        newRefreshToken.UserId = token.UserId;
        if (token.User?.IsActive != true) throw new UnauthorizedAccessException("Account is inactive.");
        token.RevokedAt = DateTime.UtcNow;
        token.ReplacedByToken = newRefreshToken.Token;

        _db.RefreshTokens.Add(newRefreshToken);
        await _db.SaveChangesAsync();

        var accessToken = GenerateJwtToken(token.User!);
        return new AuthResponseDto
        {
            AccessToken = accessToken,
            RefreshToken = newRefreshToken.Token,
            ExpiresAt = DateTime.UtcNow.AddMinutes(GetJwtExpiryMinutes()),
            User = MapToProfileDto(token.User!)
        };
    }

    public async Task RevokeTokenAsync(string refreshToken, string userId)
    {
        var token = await _db.RefreshTokens
            .FirstOrDefaultAsync(r => r.Token == refreshToken && r.UserId == userId);

        if (token != null && token.IsActive)
        {
            token.RevokedAt = DateTime.UtcNow;
            await _db.SaveChangesAsync();
        }
    }

    public async Task<UserProfileDto> GetProfileAsync(string userId)
    {
        var user = await _userManager.FindByIdAsync(userId)
            ?? throw new KeyNotFoundException("User not found.");
        return MapToProfileDto(user);
    }

    public async Task<UserProfileDto> UpdateProfileAsync(string userId, UpdateProfileDto dto)
    {
        var user = await _userManager.FindByIdAsync(userId)
            ?? throw new KeyNotFoundException("User not found.");

        if (!string.IsNullOrEmpty(dto.FullName)) user.FullName = dto.FullName;
        if (dto.Gender != null) user.Gender = dto.Gender;
        if (dto.DateOfBirth > DateTime.UtcNow) throw new ArgumentException("Date of birth cannot be in the future.");
        if (dto.DateOfBirth.HasValue) user.DateOfBirth = dto.DateOfBirth;
        if (dto.WeightKg.HasValue) user.WeightKg = dto.WeightKg;
        if (dto.HeightCm.HasValue) user.HeightCm = dto.HeightCm;
        if (dto.BloodGroup != null) user.BloodGroup = dto.BloodGroup;
        if (dto.MedicalHistory != null) user.MedicalHistory = dto.MedicalHistory;
        user.UpdatedAt = DateTime.UtcNow;

        var update = await _userManager.UpdateAsync(user);
        if (!update.Succeeded) throw new ArgumentException(string.Join(" ", update.Errors.Select(e => e.Description)));
        return MapToProfileDto(user);
    }

    // ─── Private Helpers ─────────────────────────────────

    public async Task<AuthResponseDto> IssueTokensAsync(string userId)
    {
        var user = await _userManager.FindByIdAsync(userId) ?? throw new UnauthorizedAccessException();
        if (!user.IsActive) throw new UnauthorizedAccessException();
        return await GenerateAuthResponseAsync(user);
    }

    private async Task<AuthResponseDto> GenerateAuthResponseAsync(ApplicationUser user)
    {
        var accessToken = GenerateJwtToken(user);
        var refreshToken = GenerateRefreshToken();
        refreshToken.UserId = user.Id;

        // Remove old refresh tokens for this user (keep last 5)
        var oldTokens = await _db.RefreshTokens
            .Where(r => r.UserId == user.Id)
            .OrderByDescending(r => r.CreatedAt)
            .Skip(4)
            .ToListAsync();
        _db.RefreshTokens.RemoveRange(oldTokens);

        _db.RefreshTokens.Add(refreshToken);
        await _db.SaveChangesAsync();

        return new AuthResponseDto
        {
            AccessToken = accessToken,
            RefreshToken = refreshToken.Token,
            ExpiresAt = DateTime.UtcNow.AddMinutes(GetJwtExpiryMinutes()),
            User = MapToProfileDto(user)
        };
    }

    private string GenerateJwtToken(ApplicationUser user)
    {
        var key = new SymmetricSecurityKey(
            Encoding.UTF8.GetBytes(_config["Jwt:Secret"]!));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, user.Id),
            new Claim(JwtRegisteredClaimNames.Email, user.Email!),
            new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
            new Claim(ClaimTypes.NameIdentifier, user.Id),
            new Claim(ClaimTypes.Name, user.FullName),
            new Claim(ClaimTypes.Role, user.Role),
            new Claim("sst", user.SecurityStamp ?? "")
        };

        var token = new JwtSecurityToken(
            issuer: _config["Jwt:Issuer"],
            audience: _config["Jwt:Audience"],
            claims: claims,
            expires: DateTime.UtcNow.AddMinutes(GetJwtExpiryMinutes()),
            signingCredentials: creds
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }

    private static RefreshToken GenerateRefreshToken()
    {
        var randomBytes = RandomNumberGenerator.GetBytes(64);
        return new RefreshToken
        {
            Token = Convert.ToBase64String(randomBytes),
            ExpiresAt = DateTime.UtcNow.AddDays(7),
            CreatedAt = DateTime.UtcNow
        };
    }

    private int GetJwtExpiryMinutes()
    {
        return int.TryParse(_config["Jwt:ExpiryMinutes"], out var minutes) ? minutes : 60;
    }

    private static UserProfileDto MapToProfileDto(ApplicationUser user) => new()
    {
        Id = user.Id,
        FullName = user.FullName,
        Email = user.Email!,
        Gender = user.Gender,
        DateOfBirth = user.DateOfBirth,
        WeightKg = user.WeightKg,
        HeightCm = user.HeightCm,
        BloodGroup = user.BloodGroup,
        Role = user.Role,
        CreatedAt = user.CreatedAt
    };
}
