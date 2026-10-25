using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using Microsoft.Extensions.Configuration;
using System.Net.Http.Headers;
using System.Text.Json;
using MediScan.Core.Services;

namespace MediScan.Infra.External;

public class AiInferenceService : IAiInferenceService
{
    private readonly HttpClient _httpClient;
    private readonly string _aiServerUrl;
    private readonly string _apiKey;

    private static readonly Dictionary<ScanType, string> _endpoints = new()
    {
        { ScanType.Anemia,         "/api/v1/detect/anemia" },
        { ScanType.SkinDisease,    "/api/v1/detect/skin" },
        { ScanType.Posture,        "/api/v1/detect/posture" },
        { ScanType.EyeDisease,     "/api/v1/detect/eye" },
        { ScanType.Wound,          "/api/v1/detect/wound" },
        { ScanType.TongueDiagnosis,"/api/v1/detect/tongue" },
        { ScanType.Retina,         "/api/v1/detect/retina" }
    };

    public AiInferenceService(HttpClient httpClient, IConfiguration config)
    {
        _httpClient = httpClient;
        _aiServerUrl = config["AiServer:Url"] ?? "http://localhost:8000";
        _apiKey = config["AiServer:ApiKey"] ?? string.Empty;
    }

    public async Task<AiInferenceResult> RunInferenceAsync(
        ScanType scanType, Stream imageStream, string contentType)
    {
        if (!_endpoints.TryGetValue(scanType, out var endpoint))
            throw new ArgumentException($"Unknown scan type: {scanType}");

        using var content = new MultipartFormDataContent();
        var imageContent = new StreamContent(imageStream);
        imageContent.Headers.ContentType = new MediaTypeHeaderValue(contentType);
        content.Add(imageContent, "image", "scan_image.jpg");

        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        using var request = new HttpRequestMessage(HttpMethod.Post, $"{_aiServerUrl}{endpoint}") { Content = content };
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _apiKey);
        using var response = await _httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
        response.EnsureSuccessStatusCode();
        const int maximumBytes = 64 * 1024;
        if (response.Content.Headers.ContentLength > maximumBytes)
            throw new HttpRequestException("Image service response exceeds its metadata budget.");
        await using var body = await response.Content.ReadAsStreamAsync(deadline.Token);
        using var payload = new MemoryStream();
        var buffer = new byte[8192];
        int count;
        while ((count = await body.ReadAsync(buffer.AsMemory(), deadline.Token)) != 0)
        {
            if (payload.Length + count > maximumBytes)
                throw new HttpRequestException("Image service response exceeds its metadata budget.");
            payload.Write(buffer, 0, count);
        }
        try
        {
            using var document = JsonDocument.Parse(payload.ToArray(), new JsonDocumentOptions { MaxDepth = 16 });
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("result", out var result) || result.ValueKind != JsonValueKind.String
                || string.IsNullOrWhiteSpace(result.GetString()) || result.GetString()!.Length > 256
                || !root.TryGetProperty("confidence", out var confidence) || confidence.ValueKind != JsonValueKind.Number || !confidence.TryGetSingle(out var value)
                || !float.IsFinite(value) || value < 0 || value > 1
                || !root.TryGetProperty("details", out var details) || details.ValueKind != JsonValueKind.Object)
                throw new HttpRequestException("Image service response does not match its contract.");
            if (details.TryGetProperty("module", out var module) &&
                (module.ValueKind != JsonValueKind.String || module.GetString() != ClinicalScanPolicy.Module(scanType)))
                throw new HttpRequestException("Image service response does not match the requested task.");
        }
        catch (JsonException)
        {
            throw new HttpRequestException("Image service returned invalid metadata.");
        }
        // Upstream self-declared confidence/release flags cannot override acceptance evidence.
        return ClinicalScanPolicy.ForCurrentRelease(scanType);
    }
}
