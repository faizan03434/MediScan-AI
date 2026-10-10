using MediScan.Core.DTOs.Auth;
using MediScan.Core.DTOs.Common;
using MediScan.Core.Interfaces;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;
using MediScan.API.Services;
using Microsoft.AspNetCore.RateLimiting;

namespace MediScan.API.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
[Produces("application/json")]
public class AuthController : ControllerBase
{
    private readonly IAuthService _authService;
    private readonly IAuditService _audit;
    private readonly AccountAccessService _access;

    public AuthController(IAuthService authService, IAuditService audit, AccountAccessService access)
    {
        _authService = authService;
        _audit = audit;
        _access = access;
    }

    /// <summary>Register a new user account</summary>
    [HttpPost("register")]
    [HttpPost("register/request")]
    [EnableRateLimiting("auth")]
    [ProducesResponseType(typeof(ApiResponse<OtpChallenge>), 200)]
    [ProducesResponseType(typeof(ApiResponse<object>), 400)]
    public async Task<IActionResult> Register([FromBody] RegisterDto dto)
    {
        try
        {
            var challenge = await _access.RequestRegistrationAsync(dto);
            return Ok(ApiResponse<OtpChallenge>.Ok(challenge, challenge.Message));
        }
        catch (ArgumentException ex)
        {
            await _audit.LogAsync("Auth.Register", "User", success: false, errorMessage: ex.Message,
                ipAddress: HttpContext.Connection.RemoteIpAddress?.ToString());
            return BadRequest(ApiResponse<object>.Fail(ex.Message));
        }
    }

    /// <summary>Login with email and password</summary>
    [HttpPost("login")]
    [EnableRateLimiting("auth")]
    [ProducesResponseType(typeof(ApiResponse<AuthResponseDto>), 200)]
    [ProducesResponseType(typeof(ApiResponse<object>), 401)]
    public async Task<IActionResult> Login([FromBody] LoginDto dto)
    {
        try
        {
            var result = await _authService.LoginAsync(dto);
            await _audit.LogAsync("Auth.Login", "User", result.User.Id,
                ipAddress: HttpContext.Connection.RemoteIpAddress?.ToString());
            return Ok(ApiResponse<AuthResponseDto>.Ok(result, "Login successful."));
        }
        catch (Exception ex)
        {
            await _audit.LogAsync("Auth.Login", "User", success: false, errorMessage: ex.Message,
                ipAddress: HttpContext.Connection.RemoteIpAddress?.ToString());
            return Unauthorized(ApiResponse<object>.Fail("Invalid email or password."));
        }
    }

    /// <summary>Refresh access token using refresh token</summary>
    [HttpPost("refresh")]
    public async Task<IActionResult> Refresh([FromBody] RefreshTokenRequest request)
    {
        try
        {
            var result = await _authService.RefreshTokenAsync(request.RefreshToken);
            return Ok(ApiResponse<AuthResponseDto>.Ok(result));
        }
        catch (Exception ex)
        {
            return Unauthorized(ApiResponse<object>.Fail(ex.Message));
        }
    }

    /// <summary>Revoke refresh token (logout)</summary>
    [HttpPost("revoke")]
    [Authorize]
    public async Task<IActionResult> Revoke([FromBody] RefreshTokenRequest request)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
        await _authService.RevokeTokenAsync(request.RefreshToken, userId!);
        await _audit.LogAsync("Auth.Logout", "User", userId, userId);
        return Ok(ApiResponse<object>.Ok(null!, "Token revoked successfully."));
    }

    /// <summary>Get current user profile</summary>
    [HttpGet("profile")]
    [Authorize]
    [ProducesResponseType(typeof(ApiResponse<UserProfileDto>), 200)]
    public async Task<IActionResult> GetProfile()
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var profile = await _authService.GetProfileAsync(userId);
        return Ok(ApiResponse<UserProfileDto>.Ok(profile));
    }

    /// <summary>Update current user profile</summary>
    [HttpPut("profile")]
    [Authorize]
    public async Task<IActionResult> UpdateProfile([FromBody] UpdateProfileDto dto)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var profile = await _authService.UpdateProfileAsync(userId, dto);
        await _audit.LogAsync("User.UpdateProfile", "User", userId, userId);
        return Ok(ApiResponse<UserProfileDto>.Ok(profile, "Profile updated successfully."));
    }

    [HttpGet("capabilities")]
    public IActionResult Capabilities([FromServices] IVerificationEmailSender email,
        [FromServices] IConfiguration config) => Ok(ApiResponse<object>.Ok(new {
            emailOtp = email.IsConfigured,
            google = (config.GetSection("Authentication:Google:ClientIds").Get<string[]>() ?? []).Any(s => !string.IsNullOrWhiteSpace(s))
        }));

    [HttpPost("register/verify"), EnableRateLimiting("auth")]
    public async Task<IActionResult> VerifyRegistration(VerifyEmailRequest dto)
    {
        var result = await _access.VerifyRegistrationAsync(dto);
        await _audit.LogAsync("Auth.EmailVerified", "User", result.User.Id);
        return Ok(ApiResponse<AuthResponseDto>.Ok(result));
    }

    [HttpPost("password/forgot"), EnableRateLimiting("auth")]
    public async Task<IActionResult> ForgotPassword(EmailCodeRequest dto) =>
        Ok(ApiResponse<OtpChallenge>.Ok(await _access.RequestResetAsync(dto.Email)));

    [HttpPost("password/reset"), EnableRateLimiting("auth")]
    public async Task<IActionResult> ResetPassword(ResetPasswordRequest dto)
    {
        await _access.ResetPasswordAsync(dto);
        await _audit.LogAsync("Auth.PasswordReset", "User");
        return Ok(ApiResponse<object>.Ok(null!, "Password updated. Sign in with your new password."));
    }

    [HttpPost("google"), EnableRateLimiting("auth")]
    public async Task<IActionResult> GoogleSignIn(GoogleSignInRequest dto)
    {
        var result = await _access.GoogleSignInAsync(dto.IdToken);
        await _audit.LogAsync("Auth.GoogleSignIn", "User", result.User.Id);
        return Ok(ApiResponse<AuthResponseDto>.Ok(result));
    }

    [HttpPost("google/link"), Authorize, EnableRateLimiting("auth")]
    public async Task<IActionResult> LinkGoogle(GoogleSignInRequest dto)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        await _access.LinkGoogleAsync(userId, dto.IdToken);
        await _audit.LogAsync("Auth.GoogleLinked", "User", userId, userId);
        return Ok(ApiResponse<object>.Ok(null!, "Google account linked."));
    }
}

public class RefreshTokenRequest
{
    public string RefreshToken { get; set; } = string.Empty;
}
