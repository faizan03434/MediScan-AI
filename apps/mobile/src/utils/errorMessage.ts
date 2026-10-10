import { isAxiosError } from 'axios';

export function errorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    if (error.response?.status === 429) return 'Too many attempts. Please wait a few minutes and try again.';
    const data = error.response?.data;
    if (typeof data?.message === 'string') return data.message;
    if (data?.errors) return Object.values(data.errors).flat().join(' ');
    if (!error.response) return 'Cannot reach MediScan. Check your connection and try again.';
  }
  return error instanceof Error ? error.message : 'Please try again.';
}
