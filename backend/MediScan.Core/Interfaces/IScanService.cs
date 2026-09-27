using MediScan.Core.DTOs.Scan;
using MediScan.Core.Entities;

namespace MediScan.Core.Interfaces;

public interface IScanService
{
    Task<ScanResultDto> CreateScanAsync(string userId, CreateScanDto dto, Stream? imageStream, string? contentType);
    Task<ScanResultDto?> GetScanByIdAsync(Guid scanId, string userId);
    Task<ScanHistoryDto> GetScanHistoryAsync(string userId, ScanType? type, int page, int pageSize);
    Task<List<ScanResultDto>> GetRecentScansAsync(string userId, int count = 5);
    Task<ScanResultDto> CompareScanAsync(Guid scanId1, Guid scanId2, string userId);
    Task DeleteScanAsync(Guid scanId, string userId);
}
