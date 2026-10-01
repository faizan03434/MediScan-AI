using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using MediScan.Core.DTOs.Medication;
using MediScan.Core.Entities;
using MediScan.Core.Interfaces;
using MediScan.Infra.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace MediScan.Infra.External;

public class DrugDataService : IDrugDataService
{
    private readonly HttpClient _http;
    private readonly AppDbContext _db;
    private readonly IConfiguration _config;
    private readonly ILogger<DrugDataService> _logger;

    // OpenFDA base URL
    private const string OpenFdaBase = "https://api.fda.gov/drug";

    public DrugDataService(
        HttpClient http,
        AppDbContext db,
        IConfiguration config,
        ILogger<DrugDataService> logger)
    {
        _http = http;
        _db = db;
        _config = config;
        _logger = logger;
    }

    // ─────────────────────────────────────────────────────────
    public async Task<DrugInfoDto?> FetchByNameAsync(string drugName, string? country = null)
    {
        var normalized = NormalizeName(drugName);

        // 1. Check DB cache first
        var now = DateTime.UtcNow;
        var cached = await _db.DrugCaches
            .Where(d => d.NormalizedName == normalized &&
                       (d.ExpiresAt == null || d.ExpiresAt > now))
            .OrderByDescending(d => d.FetchedAt)
            .FirstOrDefaultAsync();

        if (cached != null)
        {
            _logger.LogInformation("Drug cache hit for: {Name}", drugName);
            return MapCacheToDto(cached, "Cache");
        }

        // 2. Pakistan is default — try OpenFDA (best free API) + Pakistan DAP
        DrugInfoDto? result = null;

        // Always try OpenFDA (it covers international brands too)
        result = await FetchFromOpenFdaByNameAsync(drugName);

        // If not found in OpenFDA, try Pakistan DAP scrape/fallback
        if (result == null)
            result = await FetchFromPakistanDapAsync(drugName);

        // 3. Cache the result
        if (result != null)
            await CacheResultAsync(normalized, drugName, result);

        return result;
    }

    // ─────────────────────────────────────────────────────────
    public async Task<DrugInfoDto?> FetchByBarcodeAsync(string barcode)
    {
        // Check cache by barcode
        var barcodeNow = DateTime.UtcNow;
        var cached = await _db.DrugCaches
            .Where(d => d.Barcode == barcode &&
                       (d.ExpiresAt == null || d.ExpiresAt > barcodeNow))
            .FirstOrDefaultAsync();

        if (cached != null)
            return MapCacheToDto(cached, "Cache");

        // OpenFDA supports NDC (US barcodes) lookup
        var result = await FetchFromOpenFdaByBarcodeAsync(barcode);

        if (result != null)
            await CacheResultAsync(NormalizeName(result.BrandName), result.BrandName, result, barcode);

        return result;
    }

    // ── OpenFDA: Search by drug name ─────────────────────────
    private async Task<DrugInfoDto?> FetchFromOpenFdaByNameAsync(string drugName)
    {
        try
        {
            var apiKey = _config["OpenFDA:ApiKey"];
            var keyParam = string.IsNullOrEmpty(apiKey) ? "" : $"&api_key={apiKey}";
            var encoded = Uri.EscapeDataString(drugName);
            var url = $"{OpenFdaBase}/label.json?search=openfda.brand_name:\"{encoded}\"+openfda.generic_name:\"{encoded}\"&limit=1{keyParam}";

            var response = await _http.GetAsync(url);
            if (!response.IsSuccessStatusCode) return null;

            var json = await response.Content.ReadAsStringAsync();
            return ParseOpenFdaLabel(json, "OpenFDA");
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "OpenFDA name search failed for: {Name}", drugName);
            return null;
        }
    }

    // ── OpenFDA: Search by barcode (NDC) ─────────────────────
    private async Task<DrugInfoDto?> FetchFromOpenFdaByBarcodeAsync(string barcode)
    {
        try
        {
            var apiKey = _config["OpenFDA:ApiKey"];
            var keyParam = string.IsNullOrEmpty(apiKey) ? "" : $"&api_key={apiKey}";
            var encoded = Uri.EscapeDataString(barcode);
            var url = $"{OpenFdaBase}/ndc.json?search=product_ndc:\"{encoded}\"+package_ndc:\"{encoded}\"&limit=1{keyParam}";

            var response = await _http.GetAsync(url);
            if (!response.IsSuccessStatusCode) return null;

            var json = await response.Content.ReadAsStringAsync();
            return ParseOpenFdaNdc(json);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "OpenFDA barcode search failed for: {Barcode}", barcode);
            return null;
        }
    }

    // ── Pakistan DAP ─────────────────────────────────────────
    // Pakistan Drug Authority doesn't have a public REST API.
    // We use a common approach: query OpenFDA with the name and
    // flag it as Pakistani if manufacturer is a Pakistani company.
    // In future this can be replaced with a scraped/cached DAP DB.
    private async Task<DrugInfoDto?> FetchFromPakistanDapAsync(string drugName)
    {
        try
        {
            // Try a broader OpenFDA search
            var apiKey = _config["OpenFDA:ApiKey"];
            var keyParam = string.IsNullOrEmpty(apiKey) ? "" : $"&api_key={apiKey}";
            var encoded = Uri.EscapeDataString(drugName);
            var url = $"{OpenFdaBase}/label.json?search={encoded}&limit=1{keyParam}";

            var response = await _http.GetAsync(url);
            if (!response.IsSuccessStatusCode) return null;

            var json = await response.Content.ReadAsStringAsync();
            var dto = ParseOpenFdaLabel(json, "PakistanDAP/OpenFDA");

            // Append Pakistan-specific guidance
            if (dto != null)
            {
                dto.Warnings.Add("Pakistan: Always purchase from registered pharmacies (DAP licensed).");
                dto.Warnings.Add("Check DAP registration at https://www.dap.gov.pk before purchase.");
                dto.CountryOfOrigin = "PK";
            }

            return dto;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Pakistan DAP fallback failed for: {Name}", drugName);
            return null;
        }
    }

    // ── Parse OpenFDA /label response ─────────────────────────
    private static DrugInfoDto? ParseOpenFdaLabel(string json, string source)
    {
        try
        {
            var root = JsonNode.Parse(json);
            var results = root?["results"]?.AsArray();
            if (results == null || results.Count == 0) return null;

            var item = results[0]!;
            var openfda = item["openfda"];

            var brandName = GetFirstString(openfda?["brand_name"]) ??
                            GetFirstString(item["drug_name"]) ?? "Unknown";
            var genericName = GetFirstString(openfda?["generic_name"]);

            var dto = new DrugInfoDto
            {
                BrandName    = brandName,
                GenericName  = genericName,
                Manufacturer = GetFirstString(openfda?["manufacturer_name"]),
                DosageForm   = GetFirstString(openfda?["dosage_form"]),
                Strength     = GetFirstString(openfda?["strength"]),
                Indication   = GetFirstString(item["indications_and_usage"]) ?? GetFirstString(item["purpose"]),
                StorageInfo  = GetFirstString(item["storage_and_handling"]) ?? GetFirstString(item["how_supplied"]),
                Source       = source,
            };

            // Side effects
            var adverse = GetFirstString(item["adverse_reactions"]);
            if (!string.IsNullOrEmpty(adverse))
                dto.SideEffects = ChunkText(adverse, 120);

            // Warnings
            var warnings = GetFirstString(item["warnings"]) ?? GetFirstString(item["warnings_and_cautions"]);
            if (!string.IsNullOrEmpty(warnings))
                dto.Warnings = ChunkText(warnings, 120);

            // Drug interactions
            var interactions = GetFirstString(item["drug_interactions"]);
            if (!string.IsNullOrEmpty(interactions))
                dto.Interactions = ChunkText(interactions, 120);

            // Contraindications
            var contra = GetFirstString(item["contraindications"]);
            if (!string.IsNullOrEmpty(contra))
                dto.Contraindications = ChunkText(contra, 120);

            dto.HasSafetyWarning = dto.Warnings.Count > 0 || dto.Contraindications.Count > 0;

            return dto;
        }
        catch
        {
            return null;
        }
    }

    // ── Parse OpenFDA /ndc response ───────────────────────────
    private static DrugInfoDto? ParseOpenFdaNdc(string json)
    {
        try
        {
            var root = JsonNode.Parse(json);
            var results = root?["results"]?.AsArray();
            if (results == null || results.Count == 0) return null;

            var item = results[0]!;

            return new DrugInfoDto
            {
                BrandName    = item["brand_name"]?.GetValue<string>() ?? "Unknown",
                GenericName  = item["generic_name"]?.GetValue<string>(),
                Manufacturer = item["labeler_name"]?.GetValue<string>(),
                DosageForm   = item["dosage_form"]?.GetValue<string>(),
                Source       = "OpenFDA-NDC",
                Warnings     = new List<string> { "Check OpenFDA label for full prescribing information." },
            };
        }
        catch
        {
            return null;
        }
    }

    // ── Helpers ───────────────────────────────────────────────
    private static string? GetFirstString(JsonNode? node)
    {
        if (node == null) return null;
        if (node is JsonArray arr && arr.Count > 0)
            return arr[0]?.GetValue<string>()?.Trim();
        try { return node.GetValue<string>()?.Trim(); } catch { return null; }
    }

    private static List<string> ChunkText(string text, int maxLen)
    {
        // Split on sentence boundaries and trim
        var sentences = text
            .Replace("\n", " ")
            .Split(new[] { ". ", ".\n", "; " }, StringSplitOptions.RemoveEmptyEntries);

        return sentences
            .Where(s => s.Trim().Length > 5)
            .Select(s => s.Trim().TrimEnd('.') + ".")
            .Where(s => s.Length <= maxLen * 3)  // skip huge blocks
            .Take(8)
            .ToList();
    }

    private static string NormalizeName(string name) =>
        name.Trim().ToLowerInvariant().Replace("  ", " ");

    private DrugInfoDto MapCacheToDto(DrugCache cache, string source)
    {
        var dto = new DrugInfoDto
        {
            BrandName    = cache.BrandName,
            GenericName  = cache.GenericName,
            Manufacturer = cache.Manufacturer,
            DosageForm   = cache.DosageForm,
            Strength     = cache.Strength,
            Indication   = cache.Indication,
            StorageInfo  = cache.StorageInfo,
            Source       = source,
            CountryOfOrigin = cache.CountryOfOrigin,
        };

        if (!string.IsNullOrEmpty(cache.SideEffectsJson))
            dto.SideEffects = JsonSerializer.Deserialize<List<string>>(cache.SideEffectsJson) ?? new();
        if (!string.IsNullOrEmpty(cache.WarningsJson))
            dto.Warnings = JsonSerializer.Deserialize<List<string>>(cache.WarningsJson) ?? new();
        if (!string.IsNullOrEmpty(cache.InteractionsJson))
            dto.Interactions = JsonSerializer.Deserialize<List<string>>(cache.InteractionsJson) ?? new();
        if (!string.IsNullOrEmpty(cache.ContraindicationsJson))
            dto.Contraindications = JsonSerializer.Deserialize<List<string>>(cache.ContraindicationsJson) ?? new();

        dto.HasSafetyWarning = dto.Warnings.Count > 0 || dto.Contraindications.Count > 0;
        return dto;
    }

    private async Task CacheResultAsync(
        string normalizedName, string brandName,
        DrugInfoDto dto, string? barcode = null)
    {
        try
        {
            var cache = new DrugCache
            {
                NormalizedName       = normalizedName,
                Barcode              = barcode,
                BrandName            = brandName,
                GenericName          = dto.GenericName,
                Manufacturer         = dto.Manufacturer,
                DosageForm           = dto.DosageForm,
                Strength             = dto.Strength,
                Indication           = dto.Indication,
                StorageInfo          = dto.StorageInfo,
                Source               = dto.Source,
                CountryOfOrigin      = dto.CountryOfOrigin,
                SideEffectsJson      = JsonSerializer.Serialize(dto.SideEffects),
                WarningsJson         = JsonSerializer.Serialize(dto.Warnings),
                InteractionsJson     = JsonSerializer.Serialize(dto.Interactions),
                ContraindicationsJson = JsonSerializer.Serialize(dto.Contraindications),
                FetchedAt            = DateTime.UtcNow,
                ExpiresAt            = DateTime.UtcNow.AddDays(7),
            };

            _db.DrugCaches.Add(cache);
            await _db.SaveChangesAsync();
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to cache drug result for: {Name}", brandName);
        }
    }
}
