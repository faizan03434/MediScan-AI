import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import adminService from '../../services/adminService';
import DataTable, { type Column } from '../../components/common/DataTable';
import Pagination from '../../components/common/Pagination';
import type { AuditLog } from '../../types';
import { format } from 'date-fns';
import clsx from 'clsx';

const ACTION_COLOR: Record<string, string> = {
  'Auth.Login':    'badge-green',
  'Auth.Logout':   'badge-blue',
  'Auth.Register': 'badge-blue',
  'Scan.Create':   'badge-blue',
  'Scan.Delete':   'badge-red',
  'Medication':    'badge-yellow',
  'Prescription':  'badge-yellow',
  'User':          'badge-blue',
};

function getActionBadgeClass(action: string): string {
  for (const [prefix, cls] of Object.entries(ACTION_COLOR)) {
    if (action.startsWith(prefix)) return cls;
  }
  return 'badge-blue';
}

export default function AuditPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ userId: '', action: '', from: '', to: '' });
  const [applied, setApplied] = useState(filters);

  const { data, isLoading } = useQuery({
    queryKey: ['auditLogs', page, applied],
    queryFn: () => adminService.getAuditLogs(
      page, 50,
      applied.userId || undefined,
      applied.action || undefined,
      applied.from   || undefined,
      applied.to     || undefined,
    ),
  });

  const columns: Column<AuditLog>[] = [
    {
      key: 'action',
      header: 'Action',
      width: '180px',
      render: (a) => (
        <span className={clsx('badge', getActionBadgeClass(a.action))}>
          {a.action}
        </span>
      ),
    },
    {
      key: 'entityType',
      header: 'Entity',
      width: '130px',
      render: (a) => (
        <div>
          <span className="text-slate-300 text-sm">{a.entityType}</span>
          {a.entityId && (
            <p className="text-xs text-slate-500 font-mono truncate max-w-[120px]">
              {a.entityId.slice(0, 8)}...
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'success',
      header: 'Result',
      width: '90px',
      render: (a) => (
        <span className={clsx('badge', a.success ? 'badge-green' : 'badge-red')}>
          {a.success ? 'Success' : 'Failed'}
        </span>
      ),
    },
    {
      key: 'userId',
      header: 'User ID',
      width: '140px',
      render: (a) => (
        <span className="text-slate-400 text-xs font-mono">
          {a.userId ? a.userId.slice(0, 12) + '...' : 'Anonymous'}
        </span>
      ),
    },
    {
      key: 'ipAddress',
      header: 'IP',
      width: '130px',
      render: (a) => (
        <span className="text-slate-400 text-xs">{a.ipAddress ?? '—'}</span>
      ),
    },
    {
      key: 'errorMessage',
      header: 'Error',
      render: (a) => a.errorMessage ? (
        <span className="text-red-400 text-xs truncate max-w-xs block" title={a.errorMessage}>
          {a.errorMessage.slice(0, 60)}{a.errorMessage.length > 60 ? '...' : ''}
        </span>
      ) : <span className="text-slate-600">—</span>,
    },
    {
      key: 'createdAt',
      header: 'Time',
      width: '140px',
      render: (a) => (
        <span className="text-slate-400 text-xs">
          {format(new Date(a.createdAt), 'MMM d, HH:mm:ss')}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Audit Logs</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          {data?.totalCount?.toLocaleString() ?? '—'} entries · HIPAA audit trail
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Filter Logs</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">User ID</label>
            <input
              className="input text-xs"
              placeholder="User ID..."
              value={filters.userId}
              onChange={(e) => setFilters(f => ({ ...f, userId: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Action</label>
            <input
              className="input text-xs"
              placeholder="e.g. Scan.Create"
              value={filters.action}
              onChange={(e) => setFilters(f => ({ ...f, action: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">From Date</label>
            <input
              type="date"
              className="input text-xs"
              value={filters.from}
              onChange={(e) => setFilters(f => ({ ...f, from: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">To Date</label>
            <input
              type="date"
              className="input text-xs"
              value={filters.to}
              onChange={(e) => setFilters(f => ({ ...f, to: e.target.value }))}
            />
          </div>
        </div>
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => { setApplied(filters); setPage(1); }}
            className="btn-primary text-xs"
          >
            Apply Filters
          </button>
          <button
            onClick={() => {
              const empty = { userId: '', action: '', from: '', to: '' };
              setFilters(empty);
              setApplied(empty);
              setPage(1);
            }}
            className="btn-outline text-xs"
          >
            Clear
          </button>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        keyField="id"
        isLoading={isLoading}
        emptyMessage="No audit logs found."
      />

      <Pagination
        page={page}
        totalPages={data?.totalPages ?? 1}
        onPageChange={setPage}
        totalCount={data?.totalCount}
        pageSize={50}
      />
    </div>
  );
}
