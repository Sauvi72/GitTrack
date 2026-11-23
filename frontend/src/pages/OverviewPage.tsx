import React, { useEffect, useState } from 'react';
import {
  Users,
  GitPullRequest,
  GitMerge,
  Percent,
  Code2,
  Trophy,
  BarChart2,
  PieChart as PieIcon,
  ExternalLink,
  ArrowRight,
  User,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { api } from '../services/api';
import { DashboardSummary, LeaderboardEntry, ActivityData } from '../types';
import { MetricCard } from '../components/MetricCard';

interface OverviewPageProps {
  onSelectStudent: (id: number) => void;
  onNavigateTab: (tab: string) => void;
}

// Crisp, high-contrast custom tooltips ensuring all text is perfectly readable
const CustomAreaTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-white border border-[#ede6db] rounded-xl p-3 shadow-lg text-xs min-w-[140px] pointer-events-none">
      <p className="font-bold text-[#11241a] text-xs pb-1 mb-1.5 border-b border-[#f0ebe1]">{label}</p>
      <div className="space-y-1.5">
        {payload.map((entry: any, index: number) => (
          <div key={`area-tip-${index}`} className="flex items-center justify-between gap-3 text-xs">
            <span className="flex items-center gap-1.5 font-semibold text-[#516358]">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: entry.stroke || entry.color }}
              />
              {entry.name}:
            </span>
            <span className="font-extrabold text-[#11241a]">{entry.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const CustomPieTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;
  const item = payload[0];
  return (
    <div className="bg-white border border-[#ede6db] rounded-xl px-3 py-1.5 shadow-xl text-xs pointer-events-none z-50 whitespace-nowrap">
      <div className="flex items-center gap-2">
        <span
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: item.payload?.color || item.color }}
        />
        <span className="font-semibold text-[#516358]">{item.name}:</span>
        <span className="font-extrabold text-[#11241a]">{item.value}</span>
      </div>
    </div>
  );
};

export const OverviewPage: React.FC<OverviewPageProps> = ({ onSelectStudent, onNavigateTab }) => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [activity, setActivity] = useState<ActivityData | null>(null);
  const [dateRange, setDateRange] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      const [sumData, leadData, actData] = await Promise.all([
        api.getDashboardSummary(dateRange || undefined),
        api.getLeaderboard(6, 'merged', dateRange || undefined),
        api.getActivity(undefined, dateRange || undefined),
      ]);
      setSummary(sumData);
      setLeaderboard(leadData);
      setActivity(actData);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [dateRange]);

  const rangeLabel =
    dateRange === 'today'
      ? 'Today'
      : dateRange === 'this_week'
      ? 'This Week'
      : dateRange === 'this_month'
      ? 'This Month'
      : dateRange === 'this_year'
      ? 'This Year'
      : 'All Time';

  const pieData = summary
    ? [
        { name: 'Merged', value: summary.merged_prs, color: '#10b981' },
        { name: 'Open', value: summary.open_prs, color: '#0d3824' },
        { name: 'Closed Unmerged', value: summary.closed_unmerged_prs, color: '#cbd5e1' },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="space-y-6">
      {/* Top Banner & Date Filter */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="border-l-4 border-[#0d3824] pl-3.5 py-0.5">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#09261a] tracking-tight">Teacher Overview</h2>
          <p className="text-xs sm:text-sm text-[#4a5a50] font-medium mt-0.5">
            Real-time contribution analytics calculated from GitHub pull requests.
          </p>
        </div>

        {/* Date Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-white p-1 rounded-2xl border border-[#ede6db] shadow-xs text-sm font-semibold text-[#516358]">
          {[
            { id: 'today', label: 'Today' },
            { id: 'this_week', label: 'This Week' },
            { id: 'this_month', label: 'This Month' },
            { id: 'this_year', label: 'This Year' },
            { id: '', label: 'All Time' },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setDateRange(pill.id)}
              className={`px-3.5 py-1.5 rounded-xl transition-all ${
                dateRange === pill.id
                  ? 'bg-[#fceddb] text-[#11241a] font-bold shadow-xs'
                  : 'hover:text-[#11241a] hover:bg-[#faf6ee]'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards Row (5 Cards exactly as in sample) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <MetricCard
          title="TOTAL STUDENTS"
          value={summary?.total_students ?? 0}
          icon={<Users className="w-5 h-5 text-[#1e613b]" />}
          subtitle="Monitored in class"
          color="slate"
        />
        <MetricCard
          title="TOTAL PRS"
          value={summary?.total_prs ?? 0}
          icon={<GitPullRequest className="w-5 h-5 text-[#b87320]" />}
          subtitle="Authored across scopes"
          color="blue"
        />
        <MetricCard
          title="MERGED PRS"
          value={summary?.merged_prs ?? 0}
          icon={<GitMerge className="w-5 h-5 text-[#1e613b]" />}
          subtitle="Accepted into upstream"
          color="emerald"
        />
        <MetricCard
          title="OPEN PRS"
          value={summary?.open_prs ?? 0}
          icon={<Code2 className="w-5 h-5 text-[#b87320]" />}
          subtitle="Pending maintainer review"
          color="amber"
        />
        <MetricCard
          title="MERGE RATIO"
          value={`${summary?.merge_percentage ?? 0}%`}
          icon={<Percent className="w-5 h-5 text-[#1e613b]" />}
          subtitle="Outcome distribution"
          color="purple"
        />
      </div>

      {/* Middle Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Timeline Area Chart */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-[#ede6db] p-6 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-xl bg-[#eaf4ed] text-[#1e613b]">
                <BarChart2 className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-[#11241a] text-base leading-tight">PR Activity ({rangeLabel})</h3>
                <p className="text-xs text-[#516358] font-medium leading-tight mt-0.5">Creation vs. upstream merge dates</p>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm font-semibold text-[#516358]">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#0d3824]" />
                Created
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#e5b263]" />
                Merged
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            {activity?.timeline && activity.timeline.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={activity.timeline} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCreatedForest" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0d3824" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#0d3824" stopOpacity={0.01} />
                    </linearGradient>
                    <linearGradient id="colorMergedGold" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#e5b263" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#e5b263" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f4ede4" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(val: string) => {
                      if (!val) return '';
                      if (val.length === 10 && val.includes('-')) {
                        return val.slice(5);
                      }
                      return val;
                    }}
                    stroke="#718076"
                    fontSize={11}
                    tickLine={false}
                  />
                  <YAxis stroke="#718076" fontSize={11} allowDecimals={false} tickLine={false} />
                  <Tooltip content={<CustomAreaTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="created"
                    name="Created PRs"
                    stroke="#0d3824"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCreatedForest)"
                  />
                  <Area
                    type="monotone"
                    dataKey="merged"
                    name="Merged PRs"
                    stroke="#e5b263"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorMergedGold)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-[#718076]">
                No activity records in this time window.
              </div>
            )}
          </div>
        </div>

        {/* Status Distribution Donut Chart */}
        <div className="bg-white rounded-2xl border border-[#ede6db] p-6 shadow-xs flex flex-col justify-between">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="p-1.5 rounded-xl bg-[#eaf4ed] text-[#1e613b]">
              <PieIcon className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-[#11241a] text-base leading-tight">Status Distribution</h3>
              <p className="text-xs text-[#516358] font-medium leading-tight mt-0.5">Breakdown of student PR outcomes</p>
            </div>
          </div>

          <div className="flex items-center justify-between gap-4 py-2">
            {/* Donut Chart with Centered Metric */}
            <div className="w-44 h-44 relative flex items-center justify-center shrink-0">
              {/* Centered Total / Open Count placed at base layer (z-0) */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-0">
                <span className="text-2xl font-extrabold text-[#11241a] leading-tight">
                  {summary?.total_prs ?? 0}
                </span>
                <span className="text-xs text-[#516358] font-bold leading-tight">
                  {summary?.open_prs ? 'Open PRs' : 'Total PRs'}
                </span>
              </div>

              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%" className="relative z-10">
                  <PieChart>
                    <Pie
                      data={pieData}
                      innerRadius={48}
                      outerRadius={70}
                      paddingAngle={3}
                      dataKey="value"
                      stroke="none"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      content={<CustomPieTooltip />}
                      wrapperStyle={{ zIndex: 50, pointerEvents: 'none' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="w-32 h-32 rounded-full border-8 border-[#0d3824] flex items-center justify-center" />
              )}
            </div>

            {/* Right Legend */}
            <div className="space-y-2.5 text-sm font-semibold text-[#516358] flex-1">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#10b981]" />
                  <span className="font-semibold text-[#11241a]">Merged</span>
                </span>
                <span className="font-extrabold text-[#11241a]">{summary?.merged_prs ?? 0}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#0d3824]" />
                  <span className="font-semibold text-[#11241a]">Open</span>
                </span>
                <span className="font-extrabold text-[#11241a]">{summary?.open_prs ?? 0}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#cbd5e1]" />
                  <span className="font-semibold text-[#11241a]">Closed Unmerged</span>
                </span>
                <span className="font-extrabold text-[#11241a]">{summary?.closed_unmerged_prs ?? 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Grid: Leaderboard & Top Repositories */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Top Contributing Students */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-[#ede6db] p-6 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-xl bg-[#fdf3e5] text-[#b87320]">
                <Trophy className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-[#11241a] text-base leading-tight">Top Contributing Students</h3>
                <p className="text-xs text-[#516358] font-medium leading-tight mt-0.5">Ranked by verified merged pull requests ({rangeLabel})</p>
              </div>
            </div>
            <button
              onClick={() => onNavigateTab('students')}
              className="text-sm font-bold text-[#11241a] hover:text-[#0d3824] flex items-center gap-1 transition-colors"
            >
              View all <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-3">
            {leaderboard.length === 0 ? (
              <div className="py-8 text-center text-sm text-[#718076]">
                No students recorded yet. Add students in the Students tab to track contributions.
              </div>
            ) : (
              leaderboard.slice(0, 4).map((student, idx) => {
                // Ratio of merged PRs to total PRs raised by this student
                const mergeRatio =
                  student.total_prs > 0
                    ? Math.min(100, Math.round((student.merged_prs / student.total_prs) * 100))
                    : 0;
                return (
                  <div
                    key={student.student_id}
                    onClick={() => onSelectStudent(student.student_id)}
                    className="flex items-center justify-between gap-4 p-2.5 rounded-xl hover:bg-[#faf6ee] cursor-pointer transition-colors"
                  >
                    {/* Rank & Student Info */}
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-7 h-7 rounded-full bg-[#fceddb] text-[#b87320] font-extrabold text-sm flex items-center justify-center shrink-0">
                        {idx + 1}
                      </div>
                      <div className="w-9 h-9 rounded-full bg-slate-100 border border-slate-200 text-slate-800 font-bold text-sm flex items-center justify-center shrink-0">
                        {student.github_username.charAt(0).toUpperCase()}
                      </div>
                      <div className="truncate">
                        <div className="font-bold text-sm text-[#11241a] truncate">
                          {student.display_name || student.github_username}
                        </div>
                        <div className="text-xs text-[#516358] font-mono flex items-center gap-1">
                          @{student.github_username}
                          <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                        </div>
                      </div>
                    </div>

                    {/* Progress Bar & Merged Count */}
                    <div className="flex items-center gap-4 shrink-0">
                      <div
                        className="w-24 sm:w-44 bg-[#ede6db] h-2.5 rounded-full overflow-hidden hidden sm:block"
                        title={`${student.merged_prs} of ${student.total_prs} PRs merged (${mergeRatio}%)`}
                      >
                        <div
                          className="bg-[#0d3824] h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${student.merged_prs > 0 ? Math.max(mergeRatio, 5) : 0}%`,
                          }}
                        />
                      </div>
                      <div
                        className="font-extrabold text-sm text-[#11241a] min-w-[75px] text-right"
                        title={`${student.merged_prs} merged out of ${student.total_prs} total PRs (${mergeRatio}%)`}
                      >
                        {student.merged_prs} merged
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Top Repositories */}
        <div className="bg-white rounded-2xl border border-[#ede6db] p-6 shadow-xs">
          <div className="flex items-center gap-2.5 mb-4">
            <div className="p-1.5 rounded-xl bg-[#fdf3e5] text-[#b87320]">
              <Code2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-[#11241a] text-base leading-tight">Top Repositories</h3>
              <p className="text-xs text-[#516358] font-medium leading-tight mt-0.5">Where students contributed code ({rangeLabel})</p>
            </div>
          </div>

          <div className="space-y-3">
            {activity?.top_repositories && activity.top_repositories.length > 0 ? (
              activity.top_repositories.slice(0, 5).map((repo) => (
                <div key={repo.repository} className="flex items-center justify-between text-sm py-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <User className="w-4 h-4 text-[#718076] shrink-0" />
                    <span className="font-semibold text-[#11241a] truncate font-mono max-w-[190px]">
                      {repo.repository}
                    </span>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  </div>
                  <span className="text-[#11241a] font-extrabold shrink-0">{repo.total_prs} PRs</span>
                </div>
              ))
            ) : (
              <div className="text-sm text-[#718076] py-6 text-center">
                No repositories recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
