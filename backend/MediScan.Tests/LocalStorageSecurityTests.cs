using MediScan.Infra.External;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Logging.Abstractions;

namespace MediScan.Tests;

public sealed class LocalStorageSecurityTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), "mediscan-storage-" + Guid.NewGuid().ToString("N"));
    private readonly LocalStorageService _storage;
    private sealed class Environment(string root) : IWebHostEnvironment
    {
        public string WebRootPath { get; set; } = root;
        public IFileProvider WebRootFileProvider { get; set; } = new NullFileProvider();
        public string ApplicationName { get; set; } = "test";
        public string EnvironmentName { get; set; } = "Testing";
        public string ContentRootPath { get; set; } = root;
        public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
    }
    public LocalStorageSecurityTests()
    {
        Directory.CreateDirectory(_root);
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        { ["Storage:LocalFallback:BasePath"] = Path.Combine(_root, "private") }).Build();
        _storage = new LocalStorageService(config, new Environment(_root), NullLogger<LocalStorageService>.Instance);
    }

    [Theory]
    [InlineData("../outside.txt")]
    [InlineData("..\\outside.txt")]
    [InlineData("/outside.txt")]
    [InlineData("C:\\outside.txt")]
    [InlineData("scans/../outside.txt")]
    [InlineData("scans/file.jpg:secret")]
    public async Task ReadsAndDeletesRejectEscapes(string path)
    {
        var outside = Path.Combine(_root, "outside.txt");
        await File.WriteAllTextAsync(outside, "keep");
        await Assert.ThrowsAsync<ArgumentException>(() => _storage.DownloadAsync(path));
        await Assert.ThrowsAsync<ArgumentException>(() => _storage.DeleteAsync(path));
        Assert.Equal("keep", await File.ReadAllTextAsync(outside));
    }

    [Fact]
    public async Task UploadRejectsUnsafeFolderBeforeWriting()
    {
        using var input = new MemoryStream([1, 2, 3]);
        await Assert.ThrowsAsync<ArgumentException>(() => _storage.UploadAsync(input, "photo.jpg", "image/jpeg", "../../outside"));
        Assert.Empty(Directory.GetFiles(Path.Combine(_root, "private"), "*", SearchOption.AllDirectories));
    }

    [Fact]
    public async Task OwnedRelativePathsStillRoundTrip()
    {
        using var input = new MemoryStream([1, 2, 3]);
        var saved = await _storage.UploadAsync(input, "photo.jpg", "image/jpeg", "scans/user-id");
        Assert.StartsWith("/api/v1/media/scans/user-id/", saved.Url);
        using var downloaded = await _storage.DownloadAsync(saved.BlobName);
        using var output = new MemoryStream();
        await downloaded.CopyToAsync(output);
        Assert.Equal(new byte[] { 1, 2, 3 }, output.ToArray());
        await _storage.DeleteAsync(saved.BlobName);
        await Assert.ThrowsAsync<FileNotFoundException>(() => _storage.DownloadAsync(saved.BlobName));
    }

    public void Dispose() => Directory.Delete(_root, recursive: true);
}
