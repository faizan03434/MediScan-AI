import api from './api';
import { appendImage } from '../utils/upload';
import type { ApiResponse } from '../types';

export interface DocumentOcr {
  text: string;
  lines: { text: string; confidence: number | null; needs_review: boolean }[];
  message: string;
  status: string;
}

export async function extractDocument(uri: string): Promise<DocumentOcr> {
  const form = new FormData();
  await appendImage(form, uri);
  const { data } = await api.post<ApiResponse<DocumentOcr>>('/documents/ocr', form, {
    headers: { 'Content-Type': 'multipart/form-data' }, timeout: 95_000,
  });
  if (!data.success || !data.data) throw new Error(data.message);
  return data.data;
}
