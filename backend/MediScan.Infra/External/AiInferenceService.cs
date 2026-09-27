using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using Microsoft.Extensions.Configuration;
using System.Net.Http.Headers;
using System.Text.Json;

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
        { ScanType.TongueDiagnosis,"/api/v1/detect/tongue" }
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

        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", _apiKey);

        var response = await _httpClient.PostAsync($"{_aiServerUrl}{endpoint}", content);
        response.EnsureSuccessStatusCode();

        var json = await response.Content.ReadAsStringAsync();
        var result = JsonSerializer.Deserialize<AiServerResponse>(json,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true })
            ?? throw new Exception("Invalid AI server response");

        return new AiInferenceResult
        {
            DetectionResult = result.Result,
            ConfidenceScore = result.Confidence,
            DetectionDetails = JsonSerializer.Serialize(result.Details),
            Recommendation = result.Recommendation,
            NextScanDays = result.NextScanDays
        };
    }

    private class AiServerResponse
    {
        public string Result { get; set; } = string.Empty;
        public float Confidence { get; set; }
        public object? Details { get; set; }
        public string? Recommendation { get; set; }
        public int? NextScanDays { get; set; }
    }
}
