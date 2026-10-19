using System.Net;
using System.Net.Http.Headers;
using MediScan.Core.Interfaces;
using MediScan.Infra.External;
using Microsoft.Extensions.Configuration;

namespace MediScan.Tests;

public class SanitizedStorageTests
{
    private sealed class Storage : IStorageService
    {
        public byte[]? Saved; public string? Type; public string? Name;
        public async Task<(string Url, string BlobName)> UploadAsync(Stream stream, string name, string type, string folder = "scans")
        {
            using var bytes = new MemoryStream(); await stream.CopyToAsync(bytes);
            Saved = bytes.ToArray(); Name = name; Type = type;
            return ("https://private.blob/photo", folder + "/photo.png");
        }
        public Task DeleteAsync(string name) => Task.CompletedTask;
        public Task<Stream> DownloadAsync(string name) => Task.FromResult<Stream>(Stream.Null);
    }
    private sealed class Handler(HttpResponseMessage response) : HttpMessageHandler
    {
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Assert.Equal("Bearer", request.Headers.Authorization?.Scheme);
            Assert.EndsWith("/api/v1/images/normalize", request.RequestUri!.AbsoluteUri);
            await request.Content!.ReadAsByteArrayAsync(cancellationToken);
            return response;
        }
    }
    private static SanitizedImageStorageService Create(Storage storage, HttpResponseMessage response)
    {
        var config = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?> {
            ["AiServer:Url"] = "http://processor.invalid", ["AiServer:ApiKey"] = "fixture" }).Build();
        return new(storage, new HttpClient(new Handler(response)), config);
    }
    [Fact]
    public async Task OnlyProcessorOutputIsStoredAndSourceStaysOpen()
    {
        var png = Convert.FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j6ksAAAAASUVORK5CYII=");
        var response = new HttpResponseMessage(HttpStatusCode.OK) { Content = new ByteArrayContent(png) };
        response.Content.Headers.ContentType = new MediaTypeHeaderValue("image/png");
        var storage = new Storage(); var service = Create(storage, response);
        using var original = new MemoryStream("original metadata"u8.ToArray());
        var result = await service.UploadAsync(original, "eye.jpg", "image/jpeg", "scans/user");
        Assert.Equal(png, storage.Saved); Assert.Equal("image/png", storage.Type); Assert.Equal("eye.png", storage.Name);
        Assert.Equal("/api/v1/media/scans/user/photo.png", result.Url);
        Assert.True(original.CanRead); Assert.Equal(0, original.Position);
    }
    [Theory]
    [InlineData(400)] [InlineData(413)] [InlineData(415)] [InlineData(422)] [InlineData(503)]
    public async Task FailedProcessorNeverFallsBackToRawStorage(int status)
    {
        var storage = new Storage(); var service = Create(storage, new HttpResponseMessage((HttpStatusCode)status));
        await Assert.ThrowsAnyAsync<Exception>(() => service.UploadAsync(new MemoryStream([1,2,3]), "x.jpg", "image/jpeg"));
        Assert.Null(storage.Saved);
    }
    [Theory]
    [InlineData("text/html")] [InlineData("image/png")]
    public async Task InvalidProcessorPayloadIsNotStored(string contentType)
    {
        var response = new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("not a PNG") };
        response.Content.Headers.ContentType = new MediaTypeHeaderValue(contentType);
        var storage = new Storage(); var service = Create(storage, response);
        await Assert.ThrowsAsync<HttpRequestException>(() => service.UploadAsync(new MemoryStream([1,2,3]), "x.jpg", "image/jpeg"));
        Assert.Null(storage.Saved);
    }
}
