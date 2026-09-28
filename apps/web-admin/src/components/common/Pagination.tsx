import clsx from 'clsx';

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalCount?: number;
  pageSize?: number;
}

export default function Pagination({
  page, totalPages, onPageChange, totalCount, pageSize,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  const start = totalCount && pageSize ? (page - 1) * pageSize + 1 : null;
  const end   = totalCount && pageSize ? Math.min(page * pageSize, totalCount) : null;

  return (
    <div className="flex items-center justify-between pt-4">
      {totalCount != null && start != null && end != null ? (
        <p className="text-sm text-slate-400">
          Showing {start}–{end} of {totalCount.toLocaleString()}
        </p>
      ) : <div />}

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="btn-outline px-3 py-1.5 text-xs disabled:opacity-40 disabled:cursor-not-allowed"
        >
          ← Prev
        </button>

        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
          let p: number;
          if (totalPages <= 5) p = i + 1;
          else if (page <= 3) p = i + 1;
          else if (page >= totalPages - 2) p = totalPages - 4 + i;
          else p = page - 2 + i;

          return (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={clsx('w-8 h-8 rounded-lg text-xs font-medium transition-colors', {
                'bg-blue-600 text-white': p === page,
                'text-slate-400 hover:bg-slate-700': p !== page,
              })}
            >
              {p}
            </button>
          );
        })}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="btn-outline px-3 py-1.5 text-xs disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
