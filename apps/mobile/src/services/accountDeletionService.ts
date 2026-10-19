import axios from 'axios';
import api, { BASE_URL } from './api';
import * as storage from '../utils/secureStorage';
import type { ApiResponse } from '../types';

export interface DeletionProof { confirmation: string; password?: string; challengeId?: string; code?: string }
export interface DeletionStatus { status: 'pending' | 'completed'; requestedAt: string; completedAt: string | null }
interface Receipt { receipt: string; status: 'pending'; requestedAt: string }
interface Challenge { challengeId: string; expiresAt: string; resendAfterSeconds: number }
const key = 'mediscan_deletion_receipt';
let memoryReceipt: string | null = null;

export async function sendDeletionCode(): Promise<Challenge> {
  const { data } = await api.post<ApiResponse<Challenge>>('/account/deletion/code');
  if (!data.success || !data.data) throw new Error(data.message || 'Could not send verification code.');
  return data.data;
}
export async function requestAccountDeletion(proof: DeletionProof): Promise<Receipt> {
  const { data } = await api.post<ApiResponse<Receipt>>('/account/deletion', proof);
  if (!data.success || !data.data || !/^[A-Za-z0-9_-]{43}$/.test(data.data.receipt))
    throw new Error('Deletion could not be confirmed.');
  memoryReceipt = data.data.receipt;
  // The request has already been accepted. A local storage failure must not imply server rollback.
  await storage.setItemAsync(key, memoryReceipt).catch(() => {});
  return data.data;
}
export async function getDeletionStatus(): Promise<DeletionStatus | null> {
  const receipt = memoryReceipt ?? await storage.getItemAsync(key);
  if (!receipt) return null;
  const { data } = await axios.post<ApiResponse<DeletionStatus>>(`${BASE_URL}/account/deletion/status`, { receipt }, { timeout: 12000 });
  if (!data.success || !data.data) throw new Error('Deletion status is unavailable.');
  return data.data;
}
