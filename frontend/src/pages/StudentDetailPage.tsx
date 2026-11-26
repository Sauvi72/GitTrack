import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  GitPullRequest,
  GitMerge,
  AlertCircle,
  FolderGit2,
  Building,
  Calendar,
  Clock,
  Database,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Activity,
  Filter,
} from 'lucide-react';
import { api } from '../services/api';
import { StudentStatistics, PullRequest } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';

interface StudentDetailPageProps {
  studentId: number;
  onBack: () => void;
}

export const StudentDetailPage: React.FC<StudentDetailPageProps> = ({ studentId, onBack }) => {
  const [stats, setStats] = useState<StudentStatistics | null>(null);
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  
  // Date filter presets: 'today', '7d', 'this_week', 'this_month', 'this_year', '', 'custom'
  const [timeframe, setTimeframe] = useState<string>('');
  const [filterBy, setFilterBy] = useState<'created' | 'merged'>('created');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [showCustomPicker, setShowCustomPicker] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const isCustom = timeframe === 'custom';
      const rangeParam = isCustom ? undefined : timeframe || undefined;
      const fromParam = isCustom ? dateFrom || undefined : undefined;
      const toParam = isCustom ? dateTo || undefined : undefined;

      const [statsData, prsData] = await Promise.all([
        api.getStudentStatistics(studentId, {
          date_range: rangeParam,
          date_from: fromParam,
          date_to: toParam,
          filter_by: filterBy,
        }),
        api.getPullRequests({
          student_id: studentId,
          status: statusFilter || undefined,
          date_range: rangeParam,
          date_from: fromParam,
          date_to: toParam,
          filter_by: filterBy,
          limit: 100,
        }),
      ]);
      setStats(statsData);
      setPrs(prsData.items);
    } catch (err: any) {
      console.error('Failed to load student detail from local DB:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [studentId, statusFilter, timeframe, filterBy, dateFrom, dateTo]);

  const handleSync = async () => {
    setIsSyncing(true);
    setMessage(null);
    try {
      const res = await api.syncStudent(studentId, false, false);
      const newCount = res.details?.new_prs ?? 0;
      const updatedCount = res.details?.updated_prs ?? 0;
      const discovered = res.details?.discovered ?? 0;
      setMessage({
        text: `Sync completed: ${discovered} scanned, ${newCount} new saved, ${updatedCount} updated in database.`,
        type: 'success',
      });
      await loadData();
    } catch (err: any) {
      setMessage({
        text: `Sync failed: ${err.message || 'Unknown error contacting GitHub'}`,
        type: 'error',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSelectTimeframe = (preset: string) => {
    if (preset === 'custom') {
      setShowCustomPicker(true);
      setTimeframe('custom');
    } else {
      setShowCustomPicker(false);
      setTimeframe(preset);
      setDateFrom('');
      setDateTo('');
    }
  };

  const getActiveFilterLabel = () => {
    switch (timeframe) {
      case 'today':
        return 'Today';
      case '7d':
        return 'Last 7 Days';
      case 'this_week':
        return 'This Week';
      case 'this_month':
        return 'This Month';
      case 'this_year':
        return 'This Year';
      case 'custom':
        return `Custom (${dateFrom || 'start'} to ${dateTo || 'end'})`;
      default:
        return 'All Time';
    }
  };

  const syncInfo = stats?.sync_info;

  return (
    <div className="space-y-6">
      {/* Navigation & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2.5 px-4 py-2 bg-white hover:bg-[#fceddb]/60 text-[#09261a] border border-[#0d3824]/25 hover:border-[#0d3824]/50 rounded-xl text-sm font-bold shadow-sm hover:shadow transition-all group"
        >
          <div className="p-1 rounded-lg bg-[#eaf4ed] group-hover:bg-[#0d3824] text-[#0d3824] group-hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
          </div>
          <span>Back to Students Directory</span>
        </button>

        <div className="flex items-center gap-2">
          {/* Sync Button */}
          <button
            onClick={handleSync}
            disabled={isSyncing}
            title="Fetches new PRs & updates status of currently open PRs"
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#0d3824] hover:bg-[#072416] text-white text-sm font-bold rounded-xl shadow-xs transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? 'Syncing...' : 'Sync Now'}
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {message && (
        <div
          className={`p-3.5 rounded-2xl border text-xs flex items-center justify-between shadow-xs animate-in fade-in duration-200 ${
            message.type === 'success'
              ? 'bg-[#eaf4ed] border-[#d6ecdc] text-[#1e613b]'
              : message.type === 'error'
              ? 'bg-[#fef2f2] border-[#fee2e2] text-[#991b1b]'
              : 'bg-[#fdf3e5] border-[#f8e4c7] text-[#b87320]'
          }`}
        >
          <div className="flex items-center gap-2">
            {message.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-[#1e613b] shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-[#991b1b] shrink-0" />
            )}
            <span className="font-medium">{message.text}</span>
          </div>
          <button
            onClick={() => setMessage(null)}
            className="text-slate-400 hover:text-slate-700 font-bold ml-4 text-sm"
          >
            ✕
          </button>
        </div>
      )}

      {/* Student Profile & Sync Telemetry Header */}
      <div className="bg-white rounded-2xl border border-[#ede6db] p-6 shadow-xs flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-[#0d3824] text-[#fceddb] flex items-center justify-center text-xl font-extrabold shadow-sm">
            {stats?.github_username ? stats.github_username.charAt(0).toUpperCase() : 'U'}
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl sm:text-2xl font-extrabold text-[#11241a]">
                {stats?.display_name || stats?.github_username}
              </h2>
            </div>
            <a
              href={stats?.profile_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-[#516358] hover:text-[#0d3824] mt-1 font-mono transition-colors font-medium"
            >
              @{stats?.github_username}
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
          </div>
        </div>

        {/* Last Synced Info */}
        <div className="flex items-center gap-2 bg-[#faf6ee] px-4 py-2.5 rounded-2xl border border-[#ede6db] text-xs text-[#516358] font-medium shrink-0">
          <Clock className="w-4 h-4 text-[#516358]" />
          <span>Last Synced:</span>
          <span className="font-bold text-[#11241a]">
            {stats?.last_synced_at
              ? new Date(stats.last_synced_at).toLocaleString()
              : 'Never'}
          </span>
        </div>
      </div>

      {/* Date Filter Dropdown Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white px-4 py-3 rounded-2xl border border-[#ede6db] shadow-xs">
        <div className="flex items-center gap-2.5">
          <Calendar className="w-4 h-4 text-[#1e613b] shrink-0" />
          <span className="text-xs font-bold text-[#11241a]">Time Period:</span>
          <select
            value={timeframe}
            onChange={(e) => handleSelectTimeframe(e.target.value)}
            className="bg-[#faf6ee] border border-[#ede6db] text-[#11241a] font-semibold text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#0d3824] cursor-pointer"
          >
            <option value="">All Time</option>
            <option value="today">Today</option>
            <option value="this_week">This Week</option>
            <option value="this_month">This Month</option>
            <option value="this_year">This Year</option>
            <option value="custom">Custom Range</option>
          </select>
        </div>

        {timeframe === 'custom' && (
          <div className="flex items-center gap-2 text-xs animate-in fade-in duration-150">
            <span className="text-[#718076] text-xs font-medium">From:</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="px-2.5 py-1 text-xs bg-[#faf6ee] border border-[#ede6db] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#0d3824] text-[#11241a]"
            />
            <span className="text-[#718076] text-xs font-medium">To:</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="px-2.5 py-1 text-xs bg-[#faf6ee] border border-[#ede6db] rounded-xl focus:outline-none focus:ring-1 focus:ring-[#0d3824] text-[#11241a]"
            />
          </div>
        )}
      </div>

      {/* KPI Cards Grid (10 Core Requirements) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          title={filterBy === 'created' ? 'PRs Created' : 'PRs Selected'}
          value={stats?.total_prs ?? 0}
          subtitle={`Window: ${getActiveFilterLabel()}`}
          icon={<GitPullRequest className="w-4 h-4 text-slate-600" />}
        />
        <MetricCard
          title="Merged PRs"
          value={stats?.merged_prs ?? 0}
          subtitle={`${stats?.merge_percentage ?? 0}% merge rate`}
          icon={<GitMerge className="w-4 h-4 text-emerald-600" />}
          color="emerald"
        />
        <MetricCard
          title="Open in Window"
          value={stats?.open_prs ?? 0}
          subtitle={`${stats?.prs_currently_open_overall ?? 0} open total`}
          icon={<GitPullRequest className="w-4 h-4 text-blue-600" />}
          color="blue"
        />
        <MetricCard
          title="Closed Unmerged"
          value={stats?.closed_unmerged_prs ?? 0}
          subtitle="Abandoned / rejected"
          icon={<AlertCircle className="w-4 h-4 text-rose-500" />}
          color="rose"
        />
        <MetricCard
          title="Repos Active"
          value={stats?.unique_repositories ?? 0}
          subtitle="Distinct targets"
          icon={<FolderGit2 className="w-4 h-4 text-purple-600" />}
          color="purple"
        />
        <MetricCard
          title="Orgs Active"
          value={stats?.unique_organizations ?? 0}
          subtitle="External organizations"
          icon={<Building className="w-4 h-4 text-indigo-600" />}
          color="indigo"
        />
      </div>

      {/* Scope Breakdown (Repositories & Organizations for Selected Window) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Repositories */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-emerald-600" />
              Repositories Contributed To
            </h3>
            <span className="text-xs text-slate-500 font-medium">
              Respects {getActiveFilterLabel()}
            </span>
          </div>

          <div className="space-y-2 min-h-[260px] max-h-[440px] overflow-y-auto pr-1 flex-1">
            {stats?.repositories && stats.repositories.length > 0 ? (
              stats.repositories.map((r) => (
                <div
                  key={r.repository}
                  className="flex justify-between items-center text-sm p-3 rounded-xl bg-slate-50/80 border border-slate-100 hover:bg-slate-100/60 transition-colors"
                >
                  <span className="font-mono text-slate-800 font-semibold truncate max-w-[240px]" title={r.repository}>
                    {r.repository}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="font-bold text-slate-900">{r.total} PRs</span>
                    <span className="text-xs text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                      {r.merged} merged
                    </span>
                    {r.open > 0 && (
                      <span className="text-xs text-blue-700 font-bold bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">
                        {r.open} open
                      </span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-400 py-16 text-center flex items-center justify-center h-full">
                No repository contributions recorded in this time window.
              </div>
            )}
          </div>
        </div>

        {/* Organizations */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <Building className="w-4 h-4 text-blue-600" />
              Organizations Contributed To
            </h3>
            <span className="text-xs text-slate-500 font-medium">
              Respects {getActiveFilterLabel()}
            </span>
          </div>

          <div className="space-y-2 min-h-[260px] max-h-[440px] overflow-y-auto pr-1 flex-1">
            {stats?.organizations && stats.organizations.length > 0 ? (
              stats.organizations.map((o) => (
                <div
                  key={o.organization}
                  className="flex justify-between items-center text-sm p-3 rounded-xl bg-slate-50/80 border border-slate-100 hover:bg-slate-100/60 transition-colors"
                >
                  <span className="font-bold text-slate-900">{o.organization}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-slate-900 font-bold">{o.total} PRs</span>
                    <span className="text-xs text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
                      {o.merged} merged
                    </span>
                    {o.open > 0 && (
                      <span className="text-xs text-blue-700 font-bold bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">
                        {o.open} open
                      </span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-400 py-16 text-center flex items-center justify-center h-full">
                No organization contributions recorded in this time window.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pull Requests History Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
              <span>Pull Request History</span>
              <span className="text-xs font-normal text-slate-400">({prs.length} shown)</span>
            </h3>
            <p className="text-xs text-slate-400">
              Calculated strictly from local database records
            </p>
          </div>

          {/* Status Sub-filter */}
          <div className="flex items-center gap-1 text-xs bg-slate-100 p-0.5 rounded-xl">
            {['', 'MERGED', 'OPEN', 'CLOSED_UNMERGED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg transition-all ${
                  statusFilter === st
                    ? 'bg-white text-slate-900 font-semibold shadow-xs'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {st === '' ? 'All' : st === 'CLOSED_UNMERGED' ? 'Closed Unmerged' : st}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50 text-xs font-bold text-slate-600 uppercase tracking-wider">
                <th className="py-3.5 px-4">Title & Details</th>
                <th className="py-3.5 px-4">Repository</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Code Delta</th>
                <th className="py-3.5 px-4">Created (UTC/IST)</th>
                <th className="py-3.5 px-4">Merged / Closed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 text-sm">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-300" />
                    Querying local database...
                  </td>
                </tr>
              ) : prs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 text-sm">
                    No pull requests found matching the current filter window ({getActiveFilterLabel()}).
                  </td>
                </tr>
              ) : (
                prs.map((pr) => (
                  <tr key={pr.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 max-w-sm">
                      <a
                        href={pr.html_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-bold text-slate-900 hover:text-emerald-700 flex items-center gap-1.5 transition-colors text-sm"
                      >
                        <span className="truncate">{pr.title}</span>
                        <ExternalLink className="w-3.5 h-3.5 shrink-0 text-slate-400" />
                      </a>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">
                        #{pr.pr_number} • {pr.commits} {pr.commits === 1 ? 'commit' : 'commits'}
                        {pr.merged_by && ` • Merged by ${pr.merged_by}`}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-700 truncate max-w-[180px] text-xs">
                      {pr.repository_full_name}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={pr.status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs">
                      <span className="text-emerald-700 font-bold">+{pr.additions}</span>{' '}
                      <span className="text-rose-700 font-bold">-{pr.deletions}</span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 whitespace-nowrap text-xs font-medium">
                      {new Date(pr.created_at_github).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 whitespace-nowrap text-xs font-medium">
                      {pr.merged_at
                        ? new Date(pr.merged_at).toLocaleDateString()
                        : pr.closed_at
                        ? new Date(pr.closed_at).toLocaleDateString()
                        : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
