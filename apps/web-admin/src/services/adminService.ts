import api from './api';
import type { ApiResponse, DashboardStats, AuditLog, AdminUser, ScanRecord, PagedResult } from '../types';

const adminService = {
  // ── Auth ────────────────────────────────────────────────────
  async login(email: string, password: string) {
    const { data } = await api.post<ApiResponse<{ accessToken: string; user: AdminUser }>>(
      '/auth/login', { email, password },
    );
    if (!data.success || !data.data) throw new Error(data.message);
    if (data.data.user.role !== 'Admin') throw new Error('Admin access required.');
    return data.data;
  },

  // ── Dashboard stats ─────────────────────────────────────────
  async getDashboardStats(): Promise<DashboardStats> {
    const { data } = await api.get<ApiResponse<DashboardStats>>('/admin/stats');
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  // ── Users ───────────────────────────────────────────────────
  async getUsers(page = 1, pageSize = 20, search?: string): Promise<PagedResult<AdminUser>> {
    const params: Record<string, unknown> = { page, pageSize };
    if (search) params.search = search;
    const { data } = await api.get<ApiResponse<PagedResult<AdminUser>>>('/admin/users', { params });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  async updateUserStatus(userId: string, isActive: boolean): Promise<void> {
    await api.patch(`/admin/users/${userId}`, { isActive });
  },

  async updateUserRole(userId: string, role: string): Promise<void> {
    await api.patch(`/admin/users/${userId}/role`, { role });
  },

  // ── Scans ───────────────────────────────────────────────────
  async getScans(page = 1, pageSize = 20, scanType?: string): Promise<PagedResult<ScanRecord>> {
    const params: Record<string, unknown> = { page, pageSize };
    if (scanType) params.scanType = scanType;
    const { data } = await api.get<ApiResponse<PagedResult<ScanRecord>>>('/admin/scans', { params });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },

  // ── Audit logs ──────────────────────────────────────────────
  async getAuditLogs(
    page = 1, pageSize = 50,
    userId?: string, action?: string,
    from?: string, to?: string,
  ): Promise<PagedResult<AuditLog>> {
    const params: Record<string, unknown> = { page, pageSize };
    if (userId) params.userId = userId;
    if (action) params.action = action;
    if (from)   params.from   = from;
    if (to)     params.to     = to;
    const { data } = await api.get<ApiResponse<PagedResult<AuditLog>>>('/admin/audit', { params });
    if (!data.success || !data.data) throw new Error(data.message);
    return data.data;
  },
};

export default adminService;
