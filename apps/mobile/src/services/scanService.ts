import api from './api';
import type { ApiResponse, ScanResult, ScanHistory, ScanType } from '../types';

const scanService = {
  /**
   * Submit a scan with image file.
   * Uses multipart/form-data.
   */
  async createScan(scanType: ScanType, imageUri: string): Promise<ScanResult> {
    const formData = new FormData();
    formData.append('scanType', scanType);

    // React Native FormData file append
    const filename = imageUri.split('/').pop() ?? 'scan.jpg';
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `image/${match[1]}` : 'image/jpeg';

    formData.append('image', {
      uri: imageUri,
      name: filename,
      type,
    } as unknown as Blob);

    const { data } = await api.post<ApiResponse<ScanResult>>('/scan', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60_000, // AI inference can take longer
    });

    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getScan(id: string): Promise<ScanResult> {
    const { data } = await api.get<ApiResponse<ScanResult>>(`/scan/${id}`);
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getHistory(
    type?: ScanType,
    page: number = 1,
    pageSize: number = 10
  ): Promise<ScanHistory> {
    const params: Record<string, unknown> = { page, pageSize };
    if (type) params.type = type;

    const { data } = await api.get<ApiResponse<ScanHistory>>('/scan/history', { params });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getRecentScans(count: number = 5): Promise<ScanResult[]> {
    const { data } = await api.get<ApiResponse<ScanResult[]>>('/scan/recent', {
      params: { count },
    });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async compareScans(scanId1: string, scanId2: string): Promise<ScanResult> {
    const { data } = await api.get<ApiResponse<ScanResult>>('/scan/compare', {
      params: { scan1Id: scanId1, scan2Id: scanId2 },
    });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async deleteScan(id: string): Promise<void> {
    await api.delete(`/scan/${id}`);
  },
};

export default scanService;
