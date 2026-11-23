import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: string;
  color?: 'emerald' | 'blue' | 'amber' | 'slate' | 'purple' | 'rose' | 'indigo';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color = 'slate',
}) => {
  // Soft pastel warm palettes matching the design
  const badgeStyles: Record<string, string> = {
    emerald: 'bg-[#eaf4ed] text-[#1e613b] border-[#d6ecdc]',
    blue: 'bg-[#fdf3e5] text-[#b87320] border-[#f8e4c7]',
    amber: 'bg-[#fdf3e5] text-[#b87320] border-[#f8e4c7]',
    slate: 'bg-[#eaf4ed] text-[#1e613b] border-[#d6ecdc]',
    purple: 'bg-[#eaf4ed] text-[#1e613b] border-[#d6ecdc]',
    rose: 'bg-[#fef2f2] text-[#991b1b] border-[#fee2e2]',
    indigo: 'bg-[#eaf4ed] text-[#1e613b] border-[#d6ecdc]',
  };

  return (
    <div className="bg-white rounded-2xl border border-[#ede6db] p-4 shadow-xs flex items-start justify-between gap-3 hover:shadow-sm transition-all min-h-[96px]">
      <div className="space-y-1 min-w-0 flex-1">
        <span className="text-xs font-bold text-[#516358] uppercase tracking-wider block leading-tight">
          {title}
        </span>
        <div className="text-2xl font-extrabold text-[#11241a] tracking-tight">{value}</div>
        {subtitle && (
          <div className="text-xs text-[#516358] font-medium leading-tight">{subtitle}</div>
        )}
      </div>
      <div className={`p-2.5 rounded-xl border shrink-0 ${badgeStyles[color] || badgeStyles.slate}`}>
        {icon}
      </div>
    </div>
  );
};
