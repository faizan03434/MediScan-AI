using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using MediScan.Core.Interfaces;
using Microsoft.Extensions.Configuration;

namespace MediScan.Infra.External;

public sealed class DocumentOcrService(HttpClient http, IConfiguration config) : IDocumentOcrService
{
    public async Task<DocumentOcrResult> ExtractAsync(Stream image, string contentType, CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post,
            $"{(config["AiServer:Url"] ?? "http://127.0.0.1:8001").TrimEnd('/')}/api/v1/documents/ocr");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", config["AiServer:ApiKey"]);
        using var multipart = new MultipartFormDataContent();
        var file = new StreamContent(image); file.Headers.ContentType = new MediaTypeHeaderValue(contentType);
        multipart.Add(file, "image", "document.jpg"); request.Content = multipart;
        using var response = await http.SendAsync(request, cancellationToken);
        if (response.StatusCode is HttpStatusCode.BadRequest or HttpStatusCode.UnsupportedMediaType or HttpStatusCode.UnprocessableEntity or HttpStatusCode.RequestEntityTooLarge)
            throw new ArgumentException("Image could not be read. Use a clear JPEG, PNG or WebP under 10 MB and 20 megapixels.");
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<DocumentOcrResult>(cancellationToken: cancellationToken)
            ?? throw new HttpRequestException("OCR returned no result.");
    }
}
