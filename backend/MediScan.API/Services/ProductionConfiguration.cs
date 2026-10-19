namespace MediScan.API.Services;

public static class ProductionConfiguration
{
    public static void Validate(IConfiguration configuration)
    {
        var jwt = configuration["Jwt:Secret"] ?? "";
        var ai = configuration["AiServer:ApiKey"] ?? "";
        if (jwt.Length < 64 || jwt.Contains("ChangeInProduction", StringComparison.OrdinalIgnoreCase)
            || jwt.Contains("DevSecret", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Production requires a separately generated JWT signing secret of at least 64 characters.");
        if (ai.Length < 32 || ai.Contains("internal-dev", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Production requires a separately generated internal image-service key of at least 32 characters.");
        if (string.IsNullOrWhiteSpace(configuration["Jwt:Issuer"]) || string.IsNullOrWhiteSpace(configuration["Jwt:Audience"]))
            throw new InvalidOperationException("Production token issuer and audience are required.");
        if (!int.TryParse(configuration["Jwt:ExpiryMinutes"], out var minutes) || minutes is < 1 or > 60)
            throw new InvalidOperationException("Production access-token lifetime must be between 1 and 60 minutes.");
        var origins = configuration.GetSection("AllowedOrigins").Get<string[]>() ?? [];
        if (origins.Length == 0 || origins.Any(value => !Uri.TryCreate(value, UriKind.Absolute, out var uri)
            || uri.Scheme != "https" || uri.AbsolutePath != "/" || !string.IsNullOrEmpty(uri.Query)
            || !string.IsNullOrEmpty(uri.Fragment) || !string.IsNullOrEmpty(uri.UserInfo)))
            throw new InvalidOperationException("Production requires explicit HTTPS browser origins without paths or credentials.");
        var hosts = (configuration["AllowedHosts"] ?? "").Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        if (hosts.Length == 0 || hosts.Any(host => host.Contains('*') || host.Contains('/') || host.Contains(':')))
            throw new InvalidOperationException("Production requires explicit AllowedHosts names without wildcards.");
    }
}
