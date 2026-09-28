export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data?: T;
  errors: string[];
}

export interface AdminUser {
  id: string;
  fullName: string;
  email: string;
  role: 'User' | 'Doctor' | 'Admin';
  isActive: boolean;
  createdAt: string;
  scanCount?: number;
}

export interface AuditLog {
  id: string;
  userId?: string;
  action: string;
  entityType: string;
  entityId?: string;
  success: boolean;
  errorMessage?: string;
  ipAddress?: string;
  createdAt: string;
}

export interface ScanRecord {
  id: string;
  userId: string;
  userEmail?: string;
  scanType: string;
  status: string;
  detectionResult?: string;
  confidenceScore?: number;
  createdAt: string;
  completedAt?: string;
}

export interface DashboardStats {
  totalUsers: number;
  totalScans: number;
  scansToday: number;
  activeUsers: number;
  scansByType: Record<string, number>;
  scansLast7Days: { date: string; count: number }[];
  topDetections: { result: string; count: number }[];
  modelAccuracy: Record<string, number>;
}

export interface PagedResult<T> {
  items: T[];
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
}
