import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import adminService from '../../services/adminService';
import DataTable, { type Column } from '../../components/common/DataTable';
import Pagination from '../../components/common/Pagination';
import type { ScanRecord } from '../../types';
import { format } from 'date-fns';
import clsx from 'clsx';

const SCAN_TYPES = ['All', 'Anemia', 'SkinDisease', 'Posture', 'EyeDisease', 'Wound', 'TongueDiagnosis'];

const TYPE_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  Anemia:          { label: 'Anemia',   icon: '🩸', color: 'badge-red' },
  SkinDisease:     { label: 'Skin',     icon: '🦠', color: 'badge-yellow' },
  Posture:         { label: 'Posture',  icon: '🦴', color: 'badge-blue' },
  EyeDisease:      { label: 'Eye',      icon: '👁️', color: 'badge-blue' },
  Wound:           { label: 'Wound',    icon: '🩹', color: 'badge-green' },
  TongueDiagnosis: { label: 'Tongue',   icon: '👅', color: 'badge-blue' },
};

const STATUS_BADGE: Record<string, string> = {
  Completed: 'badge-green',
  Processing: 'badge-yellow',
  Failed: 'badge-red',
  Pending: 'badge-yellow',
};

export default function ScansPage() {
  const [page, setPage] = useState(1);
  const [selectedType, setSelectedType] = useState('All');

  const { data, isLoading } = useQuery({
    queryKey: ['adminScans', page, selectedType],
    queryFn: () => adminService.getScans(page, 25, selectedType === 'All' ? undefined : selectedType),
  });

  const columns: Column<ScanRecord>[] = [
    {
      key: 'scanType',
      header: 'Type',
      width: '130px',
      render: (s) => {
        const t = TYPE_LABELS[s.scanType];
        return t ? (
          <span className={clsx('badge', t.color)}>
            {t.icon} {t.label}
          </span>
        ) : <span className="text-slate-400 text-xs">{s.scanType}</span>;
      },
    },
    {
      key: 'detectionResult',
      header: 'Result',
      render: (s) => (
        <span className="text-slate-300 text-sm truncate max-w-xs block">
          {s.detectionResult ?? '—'}
        </span>
      ),
    },
    {
      key: 'confidenceScore',
      header: 'Confidence',
      width: '110px',
      render: (s) => s.confidenceScore != null ? (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className={clsx('h-full rounded-full', {
                'bg-emerald-500': s.confidenceScore >= 0.7,
                'bg-yellow-500':  s.confidenceScore >= 0.5,
                'bg-red-500':     s.confidenceScore < 0.5,
              })}
              style={{ width: `${s.confidenceScore * 100}%` }}
            />
          </div>
          <span className="text-xs text-slate-400">{(s.confidenceScore * 100).toFixed(0)}%</span>
        </div>
      ) : <span className="text-slate-500 text-xs">—</span>,
    },
    {
      key: 'status',
      header: 'Status',
      width: '110px',
      render: (s) => (
        <span className={clsx('badge', STATUS_BADGE[s.status] ?? 'badge-blue')}>
          {s.status}
        </span>
      ),
    },
    {
      key: 'userEmail',
      header: 'User',
      width: '180px',
      render: (s) => (
        <span className="text-slate-400 text-xs truncate">{s.userEmail ?? s.userId.slice(0, 8) + '...'}</span>
      ),
    },
    {
      key: 'createdAt',
      header: 'Date',
      width: '130px',
      render: (s) => (
        <span className="text-slate-400 text-xs">
          {format(new Date(s.createdAt), 'MMM d, HH:mm')}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Scan Records</h1>
        <p className="text-slate-400 text-sm mt-0.5">
          {data?.totalCount?.toLocaleString() ?? '—'} total scans
        </p>
      </div>

      {/* Type filter */}
      <div className="flex flex-wrap gap-2">
        {SCAN_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => { setSelectedType(t); setPage(1); }}
            className={clsx('px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors', {
              'bg-blue-600 border-blue-500 text-white':                  t === selectedType,
              'border-slate-600 text-slate-400 hover:border-slate-500': t !== selectedType,
            })}
          >
            {TYPE_LABELS[t]?.icon ?? ''} {TYPE_LABELS[t]?.label ?? t}
          </button>
        ))}
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        keyField="id"
        isLoading={isLoading}
        emptyMessage="No scans found."
      />

      <Pagination
        page={page}
        totalPages={data?.totalPages ?? 1}
        onPageChange={setPage}
        totalCount={data?.totalCount}
        pageSize={25}
      />
    </div>
  );
}
