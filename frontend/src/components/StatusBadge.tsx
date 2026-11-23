import React from 'react';
import { GitPullRequest, GitMerge, AlertCircle } from 'lucide-react';

interface StatusBadgeProps {
  status: 'OPEN' | 'MERGED' | 'CLOSED_UNMERGED' | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normStatus = (status || '').toUpperCase();
  const px = size === 'sm' ? 'px-2.5 py-0.5 text-xs font-bold' : 'px-3 py-1 text-sm font-bold';

  if (normStatus === 'MERGED') {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/70 ${px}`}>
        <GitMerge className="w-3.5 h-3.5 text-emerald-600" />
        Merged
      </span>
    );
  }

  if (normStatus === 'OPEN') {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/70 ${px}`}>
        <GitPullRequest className="w-3.5 h-3.5 text-blue-600" />
        Open
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 ${px}`}>
      <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
      Closed Unmerged
    </span>
  );
};
