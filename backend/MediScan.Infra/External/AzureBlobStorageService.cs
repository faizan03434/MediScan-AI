using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;
using MediScan.Core.Interfaces;
using Microsoft.Extensions.Configuration;

namespace MediScan.Infra.External;

public class AzureBlobStorageService : IStorageService
{
    private readonly BlobServiceClient _blobServiceClient;
    private readonly string _containerName;

    public AzureBlobStorageService(IConfiguration config)
    {
        var connectionString = config["Azure:StorageConnectionString"]
            ?? throw new InvalidOperationException("Azure:StorageConnectionString not configured.");
        _containerName = config["Azure:ContainerName"] ?? "mediscan-scans";
        _blobServiceClient = new BlobServiceClient(connectionString);
    }

    public async Task<(string Url, string BlobName)> UploadAsync(
        Stream stream, string fileName, string contentType, string folder = "scans")
    {
        var container = _blobServiceClient.GetBlobContainerClient(_containerName);
        await container.CreateIfNotExistsAsync(PublicAccessType.None);

        var blobName = $"{folder}/{Guid.NewGuid()}_{fileName}";
        var blobClient = container.GetBlobClient(blobName);

        await blobClient.UploadAsync(stream, new BlobHttpHeaders { ContentType = contentType });

        return (blobClient.Uri.ToString(), blobName);
    }

    public async Task DeleteAsync(string blobName)
    {
        var container = _blobServiceClient.GetBlobContainerClient(_containerName);
        var blobClient = container.GetBlobClient(blobName);
        await blobClient.DeleteIfExistsAsync();
    }

    public async Task<Stream> DownloadAsync(string blobName)
    {
        var container = _blobServiceClient.GetBlobContainerClient(_containerName);
        var blobClient = container.GetBlobClient(blobName);
        var response = await blobClient.DownloadAsync();
        await using var remote = response.Value.Content;
        var result = new MemoryStream();
        var buffer = new byte[81920];
        try
        {
            int count;
            while ((count = await remote.ReadAsync(buffer)) != 0)
            {
                if (result.Length + count > 16 * 1024 * 1024)
                    throw new IOException("Stored photo exceeds media size limit.");
                await result.WriteAsync(buffer.AsMemory(0, count));
            }
            result.Position = 0;
            return result;
        }
        catch { result.Dispose(); throw; }
    }
}
