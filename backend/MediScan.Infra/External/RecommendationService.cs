using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace MediScan.Infra.External;

public class RecommendationService : IRecommendationService
{
    private readonly HttpClient _http;
    private readonly IConfiguration _config;
    private readonly ILogger<RecommendationService> _logger;

    public RecommendationService(
        HttpClient http,
        IConfiguration config,
        ILogger<RecommendationService> logger)
    {
        _http = http;
        _config = config;
        _logger = logger;
    }

    // ── GPT-4o: Scan advice ───────────────────────────────────
    public async Task<ScanRecommendation> GetScanAdviceAsync(
        ScanType scanType,
        string detectionResult,
        float confidence,
        Core.Interfaces.User? userContext = null)
    {
        var systemPrompt =
            "You are a compassionate medical AI assistant integrated in MediScan AI, " +
            "a HIPAA-compliant health screening app. " +
            "Provide clear, actionable, culturally appropriate health advice for Pakistani users. " +
            "Always recommend consulting a doctor. Keep responses concise and structured.";

        var userAge = userContext?.AgeYears != null ? $"Patient age: {userContext.AgeYears} years." : "";
        var userGender = userContext?.Gender != null ? $"Gender: {userContext.Gender}." : "";
        var history = userContext?.MedicalHistory != null ? $"Medical history: {userContext.MedicalHistory}." : "";

        var userPrompt = $"Scan type: {scanType}\n" +
            $"Detection result: {detectionResult}\n" +
            $"AI confidence: {confidence:P0}\n" +
            $"{userAge} {userGender} {history}\n\n" +
            "Please provide a structured health recommendation with these exact JSON keys:\n" +
            "{\n" +
            "  \"lifestyleAdvice\": \"Detailed daily lifestyle tips (sleep, water, exercise, diet)\",\n" +
            "  \"dietAdvice\": \"Specific foods to eat or avoid based on the condition\",\n" +
            "  \"whenToSeeDoctor\": \"Specific red flags that require immediate medical attention\",\n" +
            "  \"nextScanDays\": <integer: recommended days until next scan>,\n" +
            "  \"nextScanReason\": \"Why rescan is recommended in that timeframe\",\n" +
            "  \"keyPoints\": [\"point1\", \"point2\", \"point3\"]\n" +
            "}\n\n" +
            $"Be specific to {scanType} condition. Use simple language (user may not be medical professional).";

        var response = await CallGptAsync(systemPrompt, userPrompt);

        if (string.IsNullOrEmpty(response))
            return GetFallbackScanAdvice(scanType, detectionResult);

        try
        {
            // Extract JSON from response
            var jsonStart = response.IndexOf('{');
            var jsonEnd   = response.LastIndexOf('}');
            if (jsonStart >= 0 && jsonEnd > jsonStart)
            {
                var jsonStr = response[jsonStart..(jsonEnd + 1)];
                var parsed = JsonSerializer.Deserialize<ScanRecommendationRaw>(jsonStr,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                if (parsed != null)
                {
                    return new ScanRecommendation
                    {
                        LifestyleAdvice  = parsed.LifestyleAdvice ?? "",
                        DietAdvice       = parsed.DietAdvice ?? "",
                        WhenToSeeDoctor  = parsed.WhenToSeeDoctor ?? "",
                        NextScanDays     = parsed.NextScanDays > 0 ? parsed.NextScanDays : 30,
                        NextScanReason   = parsed.NextScanReason ?? "",
                        KeyPoints        = parsed.KeyPoints ?? new(),
                    };
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to parse GPT-4o scan advice response");
        }

        return GetFallbackScanAdvice(scanType, detectionResult);
    }

    // ── GPT-4o: Prescription safety analysis ─────────────────
    public async Task<DrugSafetyAnalysis> AnalyzePrescriptionSafetyAsync(
        List<string> drugNames,
        string? patientAge = null,
        string? patientConditions = null)
    {
        if (drugNames.Count == 0)
            return new DrugSafetyAnalysis { Summary = "No medications to analyze." };

        var systemPrompt =
            "You are a clinical pharmacist AI assistant. Analyze drug combinations for safety. " +
            "Always recommend consulting a real pharmacist or doctor. Be conservative in warnings. " +
            "Respond strictly in JSON format.";

        var drugs = string.Join(", ", drugNames);
        var ageInfo = patientAge != null ? $"Patient age: {patientAge}." : "";
        var condInfo = patientConditions != null ? $"Known conditions: {patientConditions}." : "";

        var userPrompt = $"Medications prescribed: {drugs}\n{ageInfo} {condInfo}\n\n" +
            "Analyze this prescription for:\n" +
            "1. Drug-drug interactions\n" +
            "2. Dosage concerns (if any strength info available)\n" +
            "3. Common side effects to watch for\n" +
            "4. Any critical safety warnings\n\n" +
            "Respond in this exact JSON format:\n" +
            "{\n" +
            "  \"summary\": \"Overall safety assessment in 1-2 sentences\",\n" +
            "  \"hasCriticalWarning\": true or false,\n" +
            "  \"warnings\": [\"warning1\", \"warning2\"],\n" +
            "  \"interactions\": [\"interaction1\", \"interaction2\"],\n" +
            "  \"recommendations\": [\"recommendation1\", \"recommendation2\"]\n" +
            "}";

        var response = await CallGptAsync(systemPrompt, userPrompt);

        if (string.IsNullOrEmpty(response))
            return new DrugSafetyAnalysis
            {
                Summary = "Unable to analyze prescription at this time. Please consult your pharmacist.",
                Recommendations = new List<string> { "Always consult a licensed pharmacist before starting any medication." }
            };

        try
        {
            var jsonStart = response.IndexOf('{');
            var jsonEnd   = response.LastIndexOf('}');
            if (jsonStart >= 0 && jsonEnd > jsonStart)
            {
                var jsonStr = response[jsonStart..(jsonEnd + 1)];
                var parsed = JsonSerializer.Deserialize<DrugSafetyAnalysis>(jsonStr,
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                if (parsed != null) return parsed;
            }
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to parse GPT-4o prescription analysis");
        }

        return new DrugSafetyAnalysis
        {
            Summary = response.Length > 200 ? response[..200] : response,
            Recommendations = new List<string> { "Consult your pharmacist for detailed advice." }
        };
    }

    // ── GPT-4o: Drug info enrichment ──────────────────────────
    public async Task<string> EnrichDrugInfoAsync(string drugName, string rawInfo)
    {
        var systemPrompt =
            "You are a medical information assistant. Summarize drug information in simple, " +
            "clear language for a general Pakistani patient. Keep it under 100 words. " +
            "Include: what it treats, important warnings, and when to see a doctor.";

        var userPrompt = $"Drug: {drugName}\nRaw information: {rawInfo}\n\nProvide a patient-friendly summary.";

        var response = await CallGptAsync(systemPrompt, userPrompt);
        return response ?? $"{drugName}: Please consult your pharmacist or doctor for complete information.";
    }

    // ── Core GPT-4o HTTP call ─────────────────────────────────
    private async Task<string?> CallGptAsync(string systemPrompt, string userPrompt)
    {
        var endpoint   = _config["Azure:OpenAI:Endpoint"];
        var apiKey     = _config["Azure:OpenAI:ApiKey"];
        var deployment = _config["Azure:OpenAI:DeploymentName"] ?? "gpt-4o";
        var apiVersion = _config["Azure:OpenAI:ApiVersion"] ?? "2024-02-01";

        // Graceful degradation — if Azure OpenAI not configured, skip
        if (string.IsNullOrEmpty(endpoint) || string.IsNullOrEmpty(apiKey))
        {
            _logger.LogWarning("Azure OpenAI not configured — skipping GPT-4o call");
            return null;
        }

        var url = $"{endpoint.TrimEnd('/')}/openai/deployments/{deployment}/chat/completions?api-version={apiVersion}";

        var requestBody = new
        {
            messages = new[]
            {
                new { role = "system", content = systemPrompt },
                new { role = "user",   content = userPrompt }
            },
            max_tokens = 800,
            temperature = 0.3,   // Low temperature for consistent medical advice
            top_p = 0.9
        };

        var json    = JsonSerializer.Serialize(requestBody);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        _http.DefaultRequestHeaders.Remove("api-key");
        _http.DefaultRequestHeaders.Add("api-key", apiKey);

        try
        {
            var response = await _http.PostAsync(url, content);

            if (!response.IsSuccessStatusCode)
            {
                var error = await response.Content.ReadAsStringAsync();
                _logger.LogWarning("Azure OpenAI error {Status}: {Error}",
                    response.StatusCode, error[..Math.Min(200, error.Length)]);
                return null;
            }

            var responseJson = await response.Content.ReadAsStringAsync();
            var parsed = JsonDocument.Parse(responseJson);
            var text = parsed
                .RootElement
                .GetProperty("choices")[0]
                .GetProperty("message")
                .GetProperty("content")
                .GetString();

            return text;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Azure OpenAI call failed");
            return null;
        }
    }

    // ── Fallback advice when GPT-4o unavailable ───────────────
    private static ScanRecommendation GetFallbackScanAdvice(ScanType scanType, string result)
    {
        var isPositive = result.ToLower().Contains("detected") || result.ToLower().Contains("likely");

        return new ScanRecommendation
        {
            LifestyleAdvice = isPositive
                ? $"Based on your {scanType} scan, please maintain a healthy lifestyle: drink 8 glasses of water daily, sleep 7-8 hours, and exercise 30 minutes daily."
                : "Great result! Maintain your healthy habits: stay hydrated, eat balanced meals, and exercise regularly.",
            DietAdvice = "Eat balanced meals with plenty of vegetables, fruits, and lean proteins. Reduce processed foods, sugar, and excessive salt.",
            WhenToSeeDoctor = "See a doctor immediately if you experience severe pain, difficulty breathing, or symptoms worsen significantly.",
            NextScanDays = isPositive ? 14 : 30,
            NextScanReason = isPositive
                ? "Follow-up scan recommended to monitor progress after lifestyle changes."
                : "Routine monitoring to track your health over time.",
            KeyPoints = new List<string>
            {
                "This is a screening tool — not a medical diagnosis.",
                "Consult a doctor before making health decisions.",
                "Stay hydrated and maintain a balanced diet."
            }
        };
    }

    // Deserialization helper
    private class ScanRecommendationRaw
    {
        public string? LifestyleAdvice { get; set; }
        public string? DietAdvice { get; set; }
        public string? WhenToSeeDoctor { get; set; }
        public int NextScanDays { get; set; }
        public string? NextScanReason { get; set; }
        public List<string>? KeyPoints { get; set; }
    }
}
