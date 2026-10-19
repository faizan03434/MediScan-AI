using System.ComponentModel.DataAnnotations;
using MediScan.Core.DTOs.Auth;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;

namespace MediScan.API.Services;

public record OtpChallenge(string ChallengeId, DateTimeOffset ExpiresAt, int ResendAfterSeconds, string Message);
public class VerifyEmailRequest
{
    [Required, EmailAddress] public string Email { get; set; } = "";
    [Required, StringLength(32, MinimumLength = 32)] public string ChallengeId { get; set; } = "";
    [Required, RegularExpression("^[0-9]{6}$")] public string Code { get; set; } = "";
}
public class EmailCodeRequest { [Required, EmailAddress] public string Email { get; set; } = ""; }
public class ResetPasswordRequest : VerifyEmailRequest
{
    [Required, StringLength(100, MinimumLength = 8)] public string Password { get; set; } = "";
    [Required, Compare("Password")] public string ConfirmPassword { get; set; } = "";
}
public class GoogleSignInRequest { [Required, StringLength(10000)] public string IdToken { get; set; } = ""; }

public sealed class AccountAccessService(UserManager<ApplicationUser> users, AppDbContext db,
    IEmailOtpStore codes, IVerificationEmailSender emailSender, IGoogleIdentityVerifier google,
    IAuthService auth)
{
    public async Task<OtpChallenge> RequestRegistrationAsync(RegisterDto dto)
    {
        EnsureEmailConfigured();
        var email = dto.Email.Trim();
        if (await users.FindByEmailAsync(email) != null) throw new ArgumentException("This email is already registered. Sign in or reset your password.");
        var user = new ApplicationUser { UserName = email, Email = email, FullName = dto.FullName.Trim(),
            Gender = dto.Gender, DateOfBirth = dto.DateOfBirth, WeightKg = dto.WeightKg,
            HeightCm = dto.HeightCm, BloodGroup = dto.BloodGroup, Role = "User", EmailConfirmed = true };
        foreach (var validator in users.PasswordValidators)
            EnsureSuccess(await validator.ValidateAsync(users, user, dto.Password));
        user.PasswordHash = users.PasswordHasher.HashPassword(user, dto.Password);
        // Pending registration holds a salted password hash, never the submitted password.
        var issued = codes.Issue(email, "registration", user);
        await DeliverAsync(email, issued, "registration");
        return Challenge(issued, "Check your inbox for the six-digit verification code.");
    }

    public async Task<AuthResponseDto> VerifyRegistrationAsync(VerifyEmailRequest dto)
    {
        var user = codes.Consume(dto.ChallengeId, dto.Email, "registration", dto.Code) as ApplicationUser
            ?? throw new ArgumentException("Invalid verification request.");
        EnsureSuccess(await users.CreateAsync(user));
        EnsureSuccess(await users.AddToRoleAsync(user, "User"));
        return await auth.IssueTokensAsync(user.Id);
    }

    public async Task<OtpChallenge> RequestResetAsync(string email)
    {
        EnsureEmailConfigured();
        var user = await users.FindByEmailAsync(email.Trim());
        var issued = codes.Issue(email, "password_reset", user?.IsActive == true ? user.Id : null);
        if (user?.IsActive == true) await DeliverAsync(email, issued, "password_reset");
        return Challenge(issued, "If this email has an account, a verification code has been sent.");
    }

    public async Task ResetPasswordAsync(ResetPasswordRequest dto)
    {
        var id = codes.Consume(dto.ChallengeId, dto.Email, "password_reset", dto.Code) as string
            ?? throw new ArgumentException("Invalid or expired code.");
        var user = await users.FindByIdAsync(id) ?? throw new ArgumentException("Invalid or expired code.");
        var resetToken = await users.GeneratePasswordResetTokenAsync(user);
        EnsureSuccess(await users.ResetPasswordAsync(user, resetToken, dto.Password));
        foreach (var token in await db.RefreshTokens.Where(t => t.UserId == id && t.RevokedAt == null).ToListAsync())
            token.RevokedAt = DateTime.UtcNow;
        await db.SaveChangesAsync();
    }

    public async Task<AuthResponseDto> GoogleSignInAsync(string idToken)
    {
        var identity = await google.VerifyAsync(idToken);
        var user = await users.FindByLoginAsync("Google", identity.Subject);
        if (user == null)
        {
            if (await users.FindByEmailAsync(identity.Email) != null)
                throw new ArgumentException("An account already uses this email. Sign in with your password, then link Google from your profile.");
            user = new ApplicationUser { UserName = identity.Email, Email = identity.Email,
                FullName = identity.Name, EmailConfirmed = true, Role = "User" };
            EnsureSuccess(await users.CreateAsync(user));
            EnsureSuccess(await users.AddToRoleAsync(user, "User"));
            EnsureSuccess(await users.AddLoginAsync(user, new UserLoginInfo("Google", identity.Subject, "Google")));
        }
        if (!user.IsActive) throw new UnauthorizedAccessException("Account is inactive.");
        return await auth.IssueTokensAsync(user.Id);
    }

    public async Task LinkGoogleAsync(string userId, string idToken)
    {
        var identity = await google.VerifyAsync(idToken);
        var user = await users.FindByIdAsync(userId) ?? throw new UnauthorizedAccessException();
        if (!string.Equals(user.Email, identity.Email, StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Use the Google account matching your profile email.");
        EnsureSuccess(await users.AddLoginAsync(user, new UserLoginInfo("Google", identity.Subject, "Google")));
    }

    private void EnsureEmailConfigured() { if (!emailSender.IsConfigured) throw new AuthConfigurationException("Email delivery is not configured. Add your SMTP app password on the server."); }
    private async Task DeliverAsync(string email, IssuedOtp issued, string purpose)
    {
        try { await emailSender.SendCodeAsync(email, issued.Code, purpose); }
        catch { codes.Cancel(issued.ChallengeId); throw new AuthConfigurationException("Email delivery failed. Check server SMTP settings and try again later."); }
    }
    private static OtpChallenge Challenge(IssuedOtp issued, string message) => new(issued.ChallengeId,
        issued.ExpiresAt, EmailOtpStore.ResendSeconds, message);
    private static void EnsureSuccess(IdentityResult result)
    { if (!result.Succeeded) throw new ArgumentException(string.Join(" ", result.Errors.Select(e => e.Description))); }
}
