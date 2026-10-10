using MediScan.API.Services;
using Microsoft.Extensions.Configuration;

namespace MediScan.Tests;

public class EnvFileConfigurationTests
{
    private static Dictionary<string, string?> Parse(string content)
    {
        var path = Path.GetTempFileName();
        try { File.WriteAllText(path, content); return EnvFileConfiguration.Read(path); }
        finally { File.Delete(path); }
    }

    [Fact]
    public void ServerKeysAndQuotedSecretsAreLiteral()
    {
        var values = Parse("# SMTP\nEmail__Smtp__Password='a#b=$x'\nEmail__Smtp__Port=587\n");
        Assert.Equal("a#b=$x", values["Email:Smtp:Password"]);
        var config = new ConfigurationBuilder().AddInMemoryCollection(values)
            .AddInMemoryCollection(new Dictionary<string, string?> { ["Email:Smtp:Password"] = "override" }).Build();
        Assert.Equal("override", config["Email:Smtp:Password"]);
    }

    [Theory]
    [InlineData("BAD KEY=secret")]
    [InlineData("PASSWORD='secret")]
    [InlineData("PASSWORD=secret\npassword=another")]
    public void InvalidFilesFailWithoutRevealingValues(string content)
    {
        var error = Assert.Throws<InvalidOperationException>(() => Parse(content));
        Assert.DoesNotContain("secret", error.Message);
    }

    [Fact]
    public void MissingFileIsOptional() => Assert.Empty(EnvFileConfiguration.Read(Path.Combine(Path.GetTempPath(), Guid.NewGuid() + ".env")));
}
