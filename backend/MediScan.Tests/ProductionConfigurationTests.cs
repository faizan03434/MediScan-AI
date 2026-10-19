using MediScan.API.Services;
using Microsoft.Extensions.Configuration;

namespace MediScan.Tests;

public class ProductionConfigurationTests
{
    private static Dictionary<string, string?> Valid() => new() {
        ["Jwt:Secret"] = new string('a', 86), ["AiServer:ApiKey"] = new string('b', 44),
        ["Jwt:Issuer"] = "MediScan", ["Jwt:Audience"] = "MediScanUsers", ["Jwt:ExpiryMinutes"] = "15",
        ["AllowedOrigins:0"] = "https://app.example.com", ["AllowedHosts"] = "api.example.com;internal.example.com" };
    private static IConfiguration Config(Dictionary<string, string?> values) => new ConfigurationBuilder().AddInMemoryCollection(values).Build();
    [Fact] public void ExplicitProductionConfigurationIsAccepted() => ProductionConfiguration.Validate(Config(Valid()));
    [Theory]
    [InlineData("Jwt:Secret", "MediScanDevSecretKey2024!ChangeInProduction32Chars")]
    [InlineData("AiServer:ApiKey", "internal-dev-key")]
    [InlineData("AllowedOrigins:0", "http://app.example.com")]
    [InlineData("AllowedOrigins:0", "https://app.example.com/private")]
    [InlineData("AllowedOrigins:0", "https://user:password@app.example.com")]
    [InlineData("AllowedHosts", "*")]
    [InlineData("Jwt:ExpiryMinutes", "1440")]
    public void UnsafeDefaultsCannotStartProduction(string key, string value)
    {
        var values = Valid(); values[key] = value;
        Assert.Throws<InvalidOperationException>(() => ProductionConfiguration.Validate(Config(values)));
    }
}
