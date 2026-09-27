import api from './api';
import type { ApiResponse } from '../types';

export interface DrugInfo {
  brandName: string;
  genericName?: string;
  manufacturer?: string;
  dosageForm?: string;
  strength?: string;
  indication?: string;
  sideEffects: string[];
  warnings: string[];
  interactions: string[];
  contraindications: string[];
  storageInfo?: string;
  source?: string;
  countryOfOrigin?: string;
  aiAnalysis?: string;
  hasSafetyWarning: boolean;
  disclaimer: string;
}

export interface SaveMedicationPayload {
  drugName: string;
  genericName?: string;
  barcode?: string;
  dosageForm?: string;
  strength?: string;
  inputMethod: 'BarcodeScanner' | 'OcrScan' | 'ManualEntry';
  isPrescription?: boolean;
  prescribedBy?: string;
  prescribedDate?: string;
  prescriptionRecordId?: string;
}

export interface MedicationRecord {
  id: string;
  drugName: string;
  genericName?: string;
  manufacturer?: string;
  dosageForm?: string;
  strength?: string;
  indication?: string;
  sideEffects: string[];
  warnings: string[];
  aiAnalysis?: string;
  hasSafetyWarning: boolean;
  imageUrl?: string;
  inputMethod: string;
  isPrescription: boolean;
  prescribedBy?: string;
  prescribedDate?: string;
  createdAt: string;
}

export interface PrescriptionAnalysis {
  id: string;
  doctorName?: string;
  diagnosis?: string;
  prescribedDate?: string;
  imageUrl?: string;
  medications: ParsedDrug[];
  aiAnalysis?: string;
  hasSafetyWarnings: boolean;
  warnings: string[];
  interactions: string[];
  ocrRawText: string;
  createdAt: string;
  disclaimer: string;
}

export interface ParsedDrug {
  drugName: string;
  dosageForm?: string;
  strength?: string;
  frequency?: string;
  duration?: string;
  instructions?: string;
  isKnownDrug: boolean;
  drugInfo?: DrugInfo;
}

export interface PrescriptionSummary {
  id: string;
  doctorName?: string;
  diagnosis?: string;
  medicationCount: number;
  hasSafetyWarnings: boolean;
  imageUrl?: string;
  createdAt: string;
  status: string;
}

export interface MedicationHistory {
  items: MedicationRecord[];
  totalCount: number;
  page: number;
  pageSize: number;
}

const medicationService = {
  async searchByName(query: string, country?: string): Promise<DrugInfo> {
    const params: Record<string, string> = { q: query };
    if (country) params.country = country;
    const { data } = await api.get<ApiResponse<DrugInfo>>('/medication/search', { params });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async searchByBarcode(barcode: string): Promise<DrugInfo> {
    const { data } = await api.get<ApiResponse<DrugInfo>>(`/medication/barcode/${barcode}`);
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async saveMedication(payload: SaveMedicationPayload): Promise<MedicationRecord> {
    const { data } = await api.post<ApiResponse<MedicationRecord>>('/medication', payload);
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getHistory(page = 1, pageSize = 20): Promise<MedicationHistory> {
    const { data } = await api.get<ApiResponse<MedicationHistory>>('/medication/history', {
      params: { page, pageSize },
    });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async analyzePrescription(
    imageUri: string,
    doctorName?: string,
    notes?: string,
    prescribedDate?: string,
  ): Promise<PrescriptionAnalysis> {
    const formData = new FormData();
    const filename = imageUri.split('/').pop() ?? 'prescription.jpg';
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `image/${match[1]}` : 'image/jpeg';

    formData.append('image', { uri: imageUri, name: filename, type } as unknown as Blob);
    if (doctorName) formData.append('doctorName', doctorName);
    if (notes) formData.append('notes', notes);
    if (prescribedDate) formData.append('prescribedDate', prescribedDate);

    const { data } = await api.post<ApiResponse<PrescriptionAnalysis>>(
      '/medication/prescription', formData,
      { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60_000 },
    );
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getPrescriptions(): Promise<PrescriptionSummary[]> {
    const { data } = await api.get<ApiResponse<PrescriptionSummary[]>>('/medication/prescriptions');
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },
};

export default medicationService;
