import clsx from 'clsx';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  color?: 'blue' | 'green' | 'purple' | 'orange';
}

const colorMap = {
  blue:   'bg-blue-900/30 border-blue-700/50 text-blue-400',
  green:  'bg-emerald-900/30 border-emerald-700/50 text-emerald-400',
  purple: 'bg-purple-900/30 border-purple-700/50 text-purple-400',
  orange: 'bg-orange-900/30 border-orange-700/50 text-orange-400',
};

export default function StatCard({
  title, value, icon, change, changeType = 'neutral', color = 'blue',
}: StatCardProps) {
  return (
    <div className="card flex items-start gap-4">
      <div className={clsx('w-12 h-12 rounded-xl flex items-center justify-center text-2xl border', colorMap[color])}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-slate-400">{title}</p>
        <p className="text-2xl font-bold text-white mt-0.5">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </p>
        {change && (
          <p className={clsx('text-xs mt-1', {
            'text-emerald-400': changeType === 'positive',
            'text-red-400':    changeType === 'negative',
            'text-slate-500':  changeType === 'neutral',
          })}>
            {change}
          </p>
        )}
      </div>
    </div>
  );
}
