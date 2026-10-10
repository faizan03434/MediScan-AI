namespace MediScan.Tests;

public class GoogleConfigurationTests
{
    [Fact]
    public async Task MissingClientIdsRejectBeforeAnyGoogleExchange()
    {
        var config = new Microsoft.Extensions.Configuration.ConfigurationBuilder().Build();
        var verifier = new MediScan.API.Services.GoogleIdentityVerifier(config);
        await Assert.ThrowsAsync<MediScan.API.Services.AuthConfigurationException>(() => verifier.VerifyAsync("untrusted-token"));
    }
}
