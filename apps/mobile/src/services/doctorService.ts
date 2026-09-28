import api from './api';
import type { ApiResponse, ScanResult, ScanHistory } from '../types';

export interface ConsentSummary {
  id: string;
  patientUserId: string;
  patientName: string;
  patientEmail: string;
  doctorUserId: string;
  doctorName: string;
  doctorEmail: string;
  status: 'Pending' | 'Granted' | 'Revoked';
  isActive: boolean;
  allowedScanTypes?: string;
  consentMessage?: string;
  requestedAt: string;
  respondedAt?: string;
  expiresAt?: string;
}

export interface PatientSummary {
  userId: string;
  fullName: string;
  email: string;
  gender?: string;
  ageYears?: number;
  bloodGroup?: string;
  totalScans: number;
  lastScanResult?: string;
  lastScanDate?: string;
  allowedScanTypes: string[];
  consentGrantedAt: string;
  consentExpiresAt?: string;
}

export interface RequestConsentPayload {
  patientEmail: string;
  message?: string;
  scanTypes?: string[];
  expiryDays?: number;
}

const doctorService = {
  // ── Doctor actions ─────────────────────────────────────────
  async requestConsent(payload: RequestConsentPayload): Promise<ConsentSummary> {
    const { data } = await api.post<ApiResponse<ConsentSummary>>(
      '/doctor/consent/request', payload,
    );
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getSentConsents(): Promise<ConsentSummary[]> {
    const { data } = await api.get<ApiResponse<ConsentSummary[]>>('/doctor/consent/sent');
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getMyPatients(): Promise<PatientSummary[]> {
    const { data } = await api.get<ApiResponse<PatientSummary[]>>('/doctor/patients');
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getPatientScans(patientId: string, page = 1): Promise<ScanHistory> {
    const { data } = await api.get<ApiResponse<ScanHistory>>(
      `/doctor/patients/${patientId}/scans`, { params: { page, pageSize: 10 } },
    );
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async getPatientScan(patientId: string, scanId: string): Promise<ScanResult> {
    const { data } = await api.get<ApiResponse<ScanResult>>(
      `/doctor/patients/${patientId}/scans/${scanId}`,
    );
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  // ── Patient actions ────────────────────────────────────────
  async getReceivedConsents(): Promise<ConsentSummary[]> {
    const { data } = await api.get<ApiResponse<ConsentSummary[]>>('/doctor/consent/received');
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async respondToConsent(consentId: string, grant: boolean, note?: string): Promise<ConsentSummary> {
    const { data } = await api.post<ApiResponse<ConsentSummary>>(
      `/doctor/consent/${consentId}/respond`, { grant, note },
    );
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async revokeConsent(consentId: string): Promise<void> {
    await api.delete(`/doctor/consent/${consentId}`);
  },
};

export default doctorService;
