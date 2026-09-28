import { useQuery } from '@tanstack/react-query';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend,
} from 'recharts';
import adminService from '../../services/adminService';
import StatCard from '../../components/common/StatCard';
import { format, parseISO } from 'date-fns';

const SCAN_COLORS: Record<string, string> = {
  Anemia: '#ef4444', SkinDisease: '#f59e0b', Posture: '#8b5cf6',
  EyeDisease: '#3b82f6', Wound: '#10b981', TongueDiagnosis: '#ec4899',
};

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: adminService.getDashboardStats,
    refetchInterval: 60_000, // refresh every minute
  });

  // ── Loading skeleton ─────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-slate-700 rounded" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card h-24 bg-slate-800" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card h-72 bg-slate-800" />
          <div className="card h-72 bg-slate-800" />
        </div>
      </div>
    );
  }

  const lineData = stats?.scansLast7Days.map(d => ({
    date: format(parseISO(d.date), 'MMM d'),
    scans: d.count,
  })) ?? [];

  const typeData = Object.entries(stats?.scansByType ?? {}).map(([name, value]) => ({
    name: name.replace('TongueDiagnosis', 'Tongue').replace('SkinDisease', 'Skin').replace('EyeDisease', 'Eye'),
    value,
    color: SCAN_COLORS[name] ?? '#3b82f6',
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {format(new Date(), "EEEE, MMMM d yyyy")} · Real-time overview
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Live
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Users"
          value={stats?.totalUsers ?? 0}
          icon="👥"
          color="blue"
          change="+12% this month"
          changeType="positive"
        />
        <StatCard
          title="Total Scans"
          value={stats?.totalScans ?? 0}
          icon="📷"
          color="purple"
          change={`${stats?.scansToday ?? 0} today`}
          changeType="neutral"
        />
        <StatCard
          title="Active Users"
          value={stats?.activeUsers ?? 0}
          icon="🟢"
          color="green"
          change="Last 7 days"
          changeType="neutral"
        />
        <StatCard
          title="Scans Today"
          value={stats?.scansToday ?? 0}
          icon="⚡"
          color="orange"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scans over time */}
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Scans — Last 7 Days</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={lineData} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="scanGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
                itemStyle={{ color: '#60a5fa' }}
              />
              <Area
                type="monotone" dataKey="scans" stroke="#3b82f6"
                strokeWidth={2} fill="url(#scanGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Scan distribution pie */}
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Scans by Type</h3>
          {typeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={typeData} cx="50%" cy="50%"
                  innerRadius={55} outerRadius={85}
                  paddingAngle={3} dataKey="value"
                >
                  {typeData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  itemStyle={{ color: '#cbd5e1' }}
                />
                <Legend
                  iconType="circle" iconSize={8}
                  formatter={(value) => <span style={{ color: '#94a3b8', fontSize: 12 }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-500 text-sm">
              No scan data yet
            </div>
          )}
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top detections */}
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Top Detection Results</h3>
          <div className="space-y-2">
            {(stats?.topDetections ?? []).slice(0, 6).map((item, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-slate-500 text-xs w-5">{i + 1}</span>
                <div className="flex-1">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-300 truncate">{item.result}</span>
                    <span className="text-slate-400 ml-2 flex-shrink-0">{item.count}</span>
                  </div>
                  <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full"
                      style={{
                        width: `${Math.min(100, (item.count / (stats?.topDetections[0]?.count ?? 1)) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
            {!stats?.topDetections?.length && (
              <p className="text-slate-500 text-sm">No detections yet</p>
            )}
          </div>
        </div>

        {/* Model accuracy */}
        <div className="card">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Model Accuracy</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={Object.entries(stats?.modelAccuracy ?? {}).map(([name, acc]) => ({
                name: name.charAt(0).toUpperCase() + name.slice(1),
                accuracy: Math.round(acc * 100),
              }))}
              margin={{ top: 5, right: 5, bottom: 0, left: -20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                formatter={(v: number) => [`${v}%`, 'Accuracy']}
              />
              <Bar dataKey="accuracy" radius={[4, 4, 0, 0]}>
                {Object.entries(stats?.modelAccuracy ?? {}).map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {!Object.keys(stats?.modelAccuracy ?? {}).length && (
            <p className="text-slate-500 text-sm text-center -mt-36">
              Run evaluation scripts to populate model accuracy
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
