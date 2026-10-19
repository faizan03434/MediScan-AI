import api from './api';
import type { ApiResponse } from '../types';

const sections = ['profile', 'scans', 'medications', 'prescriptions', 'consents'] as const;
interface ExportPage { items: unknown[]; totalCount: number; hasNextPage: boolean }

export async function exportAccountData(): Promise<string> {
  const output: Record<string, unknown> = { schemaVersion: 1, exportedAt: new Date().toISOString(),
    scope: 'Account and health record text; includes retained deleted records; excludes photos and credentials.' };
  let characters = 0;
  for (const section of sections) {
    const items: unknown[] = [];
    for (let page = 1; ; page++) {
      const { data } = await api.get<ApiResponse<ExportPage>>(`/account/export/${section}`, { params: { page, pageSize: 100 } });
      if (!data.success || !data.data || !Array.isArray(data.data.items)) throw new Error('Export could not be completed. Please retry.');
      characters += JSON.stringify(data.data.items).length;
      if (characters > 1_000_000 || page > 100) throw new Error('This account exceeds the mobile export limit. A larger server export is required.');
      items.push(...data.data.items);
      if (!data.data.hasNextPage) break;
      if (!data.data.items.length) throw new Error('Export changed during download. Please retry.');
    }
    output[section] = items;
  }
  return JSON.stringify(output, null, 2);
}

export async function revokeAllSessions(): Promise<void> {
  const { data } = await api.post<ApiResponse<unknown>>('/account/sessions/revoke-all');
  if (!data.success) throw new Error(data.message || 'Sign out could not be completed.');
}
