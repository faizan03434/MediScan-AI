import api from './api';
import { appendImage } from '../utils/upload';
import type { ApiResponse, ScanType } from '../types';
export interface CaptureGuide {
  capture_eligible: boolean; guidance: string; detector: string; target_verified: boolean;
  box: { x: number; y: number; width: number; height: number } | null;
  signal: number[]; clinical_inference: false;
}
export async function getCaptureGuide(type: ScanType, uri: string, signal: AbortSignal): Promise<CaptureGuide> {
  const form = new FormData(); form.append('scanType', type); await appendImage(form, uri);
  const { data } = await api.post<ApiResponse<CaptureGuide>>('/capture/guide', form, {
    headers: { 'Content-Type': 'multipart/form-data' }, signal, timeout: 12000,
  });
  if (!data.success || !data.data) throw new Error(data.message);
  return data.data;
}
