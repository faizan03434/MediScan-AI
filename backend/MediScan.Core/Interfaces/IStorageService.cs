namespace MediScan.Core.Interfaces;

public interface IStorageService
{
    Task<(string Url, string BlobName)> UploadAsync(Stream stream, string fileName, string contentType, string folder = "scans");
    Task DeleteAsync(string blobName);
    Task<Stream> DownloadAsync(string blobName);
}
