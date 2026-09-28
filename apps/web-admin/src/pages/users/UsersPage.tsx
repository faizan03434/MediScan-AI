import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import adminService from '../../services/adminService';
import DataTable, { type Column } from '../../components/common/DataTable';
import Pagination from '../../components/common/Pagination';
import type { AdminUser } from '../../types';
import { format } from 'date-fns';
import clsx from 'clsx';

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['users', page, search],
    queryFn: () => adminService.getUsers(page, 20, search || undefined),
  });

  const toggleStatus = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      adminService.updateUserStatus(id, active),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });

  const updateRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      adminService.updateUserRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });

  const columns: Column<AdminUser>[] = [
    {
      key: 'fullName',
      header: 'Name',
      render: (u) => (
        <div>
          <p className="font-medium text-white">{u.fullName}</p>
          <p className="text-xs text-slate-500">{u.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      width: '120px',
      render: (u) => (
        <select
          value={u.role}
          onChange={(e) => updateRole.mutate({ id: u.id, role: e.target.value })}
          className="bg-slate-700 border border-slate-600 rounded text-xs px-2 py-1 text-slate-200"
        >
          <option value="User">User</option>
          <option value="Doctor">Doctor</option>
          <option value="Admin">Admin</option>
        </select>
      ),
    },
    {
      key: 'isActive',
      header: 'Status',
      width: '100px',
      render: (u) => (
        <span className={clsx('badge', u.isActive ? 'badge-green' : 'badge-red')}>
          {u.isActive ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      key: 'scanCount',
      header: 'Scans',
      width: '80px',
      render: (u) => <span className="text-slate-300">{u.scanCount ?? 0}</span>,
    },
    {
      key: 'createdAt',
      header: 'Joined',
      width: '120px',
      render: (u) => (
        <span className="text-slate-400 text-xs">
          {format(new Date(u.createdAt), 'MMM d, yyyy')}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '100px',
      render: (u) => (
        <button
          onClick={() => toggleStatus.mutate({ id: u.id, active: !u.isActive })}
          className={clsx('text-xs px-3 py-1.5 rounded-lg border transition-colors', {
            'border-red-700 text-red-400 hover:bg-red-900/30':    u.isActive,
            'border-green-700 text-green-400 hover:bg-green-900/30': !u.isActive,
          })}
        >
          {u.isActive ? 'Deactivate' : 'Activate'}
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Users</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {data?.totalCount?.toLocaleString() ?? '—'} registered users
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-3">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { setSearch(searchInput); setPage(1); } }}
          placeholder="Search by name or email..."
          className="input max-w-xs"
        />
        <button
          onClick={() => { setSearch(searchInput); setPage(1); }}
          className="btn-primary"
        >
          Search
        </button>
        {search && (
          <button
            onClick={() => { setSearch(''); setSearchInput(''); setPage(1); }}
            className="btn-outline"
          >
            Clear
          </button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        keyField="id"
        isLoading={isLoading}
        emptyMessage="No users found."
      />

      <Pagination
        page={page}
        totalPages={data?.totalPages ?? 1}
        onPageChange={setPage}
        totalCount={data?.totalCount}
        pageSize={20}
      />
    </div>
  );
}
