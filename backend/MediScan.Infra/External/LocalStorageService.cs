using MediScan.Core.Interfaces;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace MediScan.Infra.External;

/// <summary>
/// Local disk storage fallback for development.
/// Used automatically when Azure Storage connection string is empty.
/// Medical files are accessed through the authenticated owner-scoped media controller.
/// </summary>
public class LocalStorageService : IStorageService
{
    private readonly string _basePath;
    private readonly string _baseUrl;
    private readonly ILogger<LocalStorageService> _logger;

    public LocalStorageService(
        IConfiguration config,
        IWebHostEnvironment env,
        ILogger<LocalStorageService> logger)
    {
        _logger = logger;
        var configuredPath = config["Storage:LocalFallback:BasePath"] ?? "wwwroot/uploads";

        _basePath = Path.GetFullPath(Path.IsPathRooted(configuredPath)
            ? configuredPath
            : Path.Combine(env.ContentRootPath, configuredPath));

        Directory.CreateDirectory(_basePath);
        _baseUrl = "/api/v1/media";

        _logger.LogInformation("LocalStorageService: using disk storage at {Path}", _basePath);
    }

    public async Task<(string Url, string BlobName)> UploadAsync(
        Stream stream, string fileName, string contentType, string folder = "scans")
    {
        var safeName = SanitizeFileName(fileName);
        var blobName = $"{folder}/{Guid.NewGuid()}_{safeName}";
        var relativePath = blobName.Replace("/", Path.DirectorySeparatorChar.ToString());
        var fullPath = ResolveBlobPath(relativePath);

        Directory.CreateDirectory(Path.GetDirectoryName(fullPath)!);

        using var fileStream = new FileStream(fullPath, FileMode.Create, FileAccess.Write);
        await stream.CopyToAsync(fileStream);

        var url = $"{_baseUrl}/{blobName.Replace(Path.DirectorySeparatorChar, '/')}";
        _logger.LogDebug("Uploaded: {BlobName}", blobName);

        return (url, blobName);
    }

    public Task DeleteAsync(string blobName)
    {
        var relativePath = blobName.Replace("/", Path.DirectorySeparatorChar.ToString());
        var fullPath = ResolveBlobPath(relativePath);
        if (File.Exists(fullPath))
        {
            File.Delete(fullPath);
            _logger.LogDebug("Deleted: {BlobName}", blobName);
        }
        return Task.CompletedTask;
    }

    public async Task<Stream> DownloadAsync(string blobName)
    {
        var relativePath = blobName.Replace("/", Path.DirectorySeparatorChar.ToString());
        var fullPath = ResolveBlobPath(relativePath);

        if (!File.Exists(fullPath))
            throw new FileNotFoundException($"File not found: {blobName}");

        var ms = new MemoryStream();
        using var fs = new FileStream(fullPath, FileMode.Open, FileAccess.Read);
        await fs.CopyToAsync(ms);
        ms.Position = 0;
        return ms;
    }

    private static string SanitizeFileName(string fileName)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var name = string.Concat(
            Path.GetFileNameWithoutExtension(fileName)
                .Where(c => !invalid.Contains(c))
                .Take(50)
        );
        var ext = Path.GetExtension(fileName);
        return string.IsNullOrEmpty(name) ? $"file{ext}" : $"{name}{ext}";
    }

    private string ResolveBlobPath(string blobName)
    {
        var normalized = blobName.Replace('\\', '/');
        var segments = normalized.Split('/');
        if (string.IsNullOrWhiteSpace(blobName) || normalized.StartsWith('/') || Path.IsPathRooted(blobName)
            || normalized.Contains(':') || segments.Any(s => s is "" or "." or ".."))
            throw new ArgumentException("Invalid storage path.");
        var full = Path.GetFullPath(Path.Combine(_basePath, Path.Combine(segments)));
        var comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
        if (!full.StartsWith(_basePath.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, comparison))
            throw new ArgumentException("Invalid storage path.");
        // Reject links/junctions before read/write/delete. Storage root must be application controlled.
        var current = _basePath;
        foreach (var segment in new[] { "" }.Concat(segments))
        {
            if (segment != "") current = Path.Combine(current, segment);
            if ((File.Exists(current) || Directory.Exists(current)) &&
                (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                throw new ArgumentException("Storage links are not allowed.");
        }
        return full;
    }
}
