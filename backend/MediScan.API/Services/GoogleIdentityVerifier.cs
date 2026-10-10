using System.IdentityModel.Tokens.Jwt;
using Microsoft.IdentityModel.Protocols;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;

namespace MediScan.API.Services;

public record GoogleIdentity(string Subject, string Email, string Name);
public interface IGoogleIdentityVerifier { Task<GoogleIdentity> VerifyAsync(string idToken); }

public sealed class GoogleIdentityVerifier(IConfiguration config) : IGoogleIdentityVerifier
{
    private readonly ConfigurationManager<OpenIdConnectConfiguration> _metadata = new(
        "https://accounts.google.com/.well-known/openid-configuration", new OpenIdConnectConfigurationRetriever());
    public async Task<GoogleIdentity> VerifyAsync(string idToken)
    {
        var audiences = config.GetSection("Authentication:Google:ClientIds").Get<string[]>() ?? [];
        audiences = audiences.Where(a => !string.IsNullOrWhiteSpace(a)).ToArray();
        if (audiences.Length == 0) throw new AuthConfigurationException("Google login is not configured. Add Google OAuth client IDs.");
        var metadata = await _metadata.GetConfigurationAsync(CancellationToken.None);
        var handler = new JwtSecurityTokenHandler { MapInboundClaims = false };
        var principal = handler.ValidateToken(idToken, new TokenValidationParameters
        {
            ValidIssuers = ["https://accounts.google.com", "accounts.google.com"],
            ValidateIssuer = true, ValidateAudience = true, ValidAudiences = audiences,
            ValidateIssuerSigningKey = true, IssuerSigningKeys = metadata.SigningKeys,
            ValidateLifetime = true, RequireSignedTokens = true, RequireExpirationTime = true,
            ValidAlgorithms = [SecurityAlgorithms.RsaSha256], ClockSkew = TimeSpan.FromSeconds(30)
        }, out _);
        if (!string.Equals(principal.FindFirst("email_verified")?.Value, "true", StringComparison.OrdinalIgnoreCase))
            throw new UnauthorizedAccessException("Google email must be verified.");
        var sub = principal.FindFirst("sub")?.Value;
        var email = principal.FindFirst("email")?.Value;
        if (string.IsNullOrEmpty(sub) || string.IsNullOrEmpty(email)) throw new UnauthorizedAccessException("Invalid Google identity.");
        return new GoogleIdentity(sub, email, principal.FindFirst("name")?.Value ?? "MediScan member");
    }
}
