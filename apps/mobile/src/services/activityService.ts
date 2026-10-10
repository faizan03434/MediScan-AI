import api from './api';
import type { ApiResponse } from '../types';

export interface AccountActivity {
  id: string;
  action: string;
  category: string;
  success: boolean;
  createdAt: string;
}

export interface ActivityPage {
  items: AccountActivity[];
  totalCount: number;
  page: number;
  hasNextPage: boolean;
}

export async function getAccountActivity(page: number): Promise<ActivityPage> {
  const { data } = await api.get<ApiResponse<ActivityPage>>('/account/activity', { params: { page, pageSize: 20 } });
  if (!data.success || !data.data) throw new Error(data.message || 'Unable to load activity');
  return data.data;
}
