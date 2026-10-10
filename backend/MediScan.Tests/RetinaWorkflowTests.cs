using System.Net;
using System.Text;
using MediScan.Core.Entities;
using MediScan.Infra.External;
using Microsoft.Extensions.Configuration;

namespace MediScan.Tests;

public class RetinaWorkflowTests
{
    [Fact]
    public async Task FundusUploadUsesSeparateRetinaRouteAndKeepsAbstention()
    {
        var handler = new CaptureHandler();
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        { ["AiServer:Url"] = "http://ai.invalid", ["AiServer:ApiKey"] = "test-internal-key" }).Build();
        var service = new AiInferenceService(new HttpClient(handler), config);
        using var image = new MemoryStream(new byte[] { 1, 2, 3 });
        var result = await service.RunInferenceAsync(ScanType.Retina, image, "image/png");
        Assert.Equal("/api/v1/detect/retina", handler.Path);
        Assert.Equal("Bearer test-internal-key", handler.Authorization);
        Assert.Contains("image/png", handler.Body);
        Assert.Equal(0, result.ConfidenceScore);
        Assert.Contains("Inconclusive", result.DetectionResult);
        Assert.Contains("fundus", result.DetectionDetails);
        Assert.Null(result.NextScanDays);
    }

    private sealed class CaptureHandler : HttpMessageHandler
    {
        public string? Path, Authorization, Body;
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            Path = request.RequestUri!.AbsolutePath;
            Authorization = request.Headers.Authorization?.ToString();
            Body = await request.Content!.ReadAsStringAsync(token);
            return new HttpResponseMessage(HttpStatusCode.OK)
            { Content = new StringContent("""{"result":"Inconclusive — clinical model not validated","confidence":0,"details":{"module":"retina","expected_image_modality":"fundus","clinical_inference":false},"next_scan_days":null}""", Encoding.UTF8, "application/json") };
        }
    }
}
