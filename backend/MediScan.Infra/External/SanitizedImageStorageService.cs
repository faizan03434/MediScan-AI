using System.Net.Http.Headers;
using MediScan.Core.Interfaces;
using Microsoft.Extensions.Configuration;

namespace MediScan.Infra.External;

// Never store raw uploads when validation/normalization is unavailable.
public sealed class SanitizedImageStorageService(IStorageService inner, HttpClient http, IConfiguration config) : IStorageService
{
    public async Task<(string Url, string BlobName)> UploadAsync(Stream stream, string fileName, string contentType, string folder = "scans")
    {
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        if (!new[] { "image/jpeg", "image/png", "image/webp" }.Contains(contentType.ToLowerInvariant()))
            throw new ArgumentException("JPEG, PNG or WebP required.");
        var originalPosition = stream.CanSeek ? stream.Position : (long?)null;
        using var input = await ReadBounded(stream, 10 * 1024 * 1024);
        if (originalPosition.HasValue) stream.Position = originalPosition.Value;
        using var request = new HttpRequestMessage(HttpMethod.Post,
            $"{config["AiServer:Url"]?.TrimEnd('/')}/api/v1/images/normalize");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", config["AiServer:ApiKey"]);
        using var multipart = new MultipartFormDataContent();
        var content = new StreamContent(input); content.Headers.ContentType = new MediaTypeHeaderValue(contentType);
        multipart.Add(content, "image", "photo"); request.Content = multipart;
        using var response = await http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
        if ((int)response.StatusCode is 400 or 413 or 415 or 422)
            throw new ArgumentException("Photo could not be validated. Choose a smaller, clear JPEG, PNG or WebP image.");
        response.EnsureSuccessStatusCode();
        if (response.Content.Headers.ContentType?.MediaType != "image/png")
            throw new HttpRequestException("Unexpected photo processor response.");
        await using var body = await response.Content.ReadAsStreamAsync(deadline.Token);
        using var normalized = await ReadBounded(body, 15 * 1024 * 1024, deadline.Token);
        byte[] signature = [137, 80, 78, 71, 13, 10, 26, 10];
        if (normalized.Length < 8 || !normalized.GetBuffer().AsSpan(0, 8).SequenceEqual(signature))
            throw new HttpRequestException("Invalid photo processor response.");
        var stored = await inner.UploadAsync(normalized, Path.ChangeExtension(Path.GetFileName(fileName), ".png"), "image/png", folder);
        // Both local and cloud photos must pass through owner authorization.
        return ($"/api/v1/media/{stored.BlobName}", stored.BlobName);
    }

    private static async Task<MemoryStream> ReadBounded(Stream source, int limit, CancellationToken cancellationToken = default)
    {
        var result = new MemoryStream();
        var buffer = new byte[81920];
        try
        {
            int count;
            while ((count = await source.ReadAsync(buffer, cancellationToken)) != 0)
            {
                if (result.Length + count > limit) throw new ArgumentException("Photo exceeds processing size limit.");
                await result.WriteAsync(buffer.AsMemory(0, count));
            }
            if (result.Length == 0) throw new ArgumentException("Photo is empty.");
            result.Position = 0; return result;
        }
        catch { result.Dispose(); throw; }
    }

    public Task DeleteAsync(string blobName) => inner.DeleteAsync(blobName);
    public Task<Stream> DownloadAsync(string blobName) => inner.DownloadAsync(blobName);
}
