import React from 'react';
import {
  LayoutDashboard,
  Users,
  CircleDot
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'students', label: 'Students', icon: Users },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-200 flex flex-col shrink-0 min-h-screen">
      {/* Brand logo area */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center font-bold">
          <CircleDot className="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <div className="font-bold tracking-tight text-white leading-tight">GitTrack</div>
          <div className="text-[11px] text-slate-400 leading-tight">GitHub Tracker</div>
        </div>
      </div>

      {/* Navigation links */}
      <nav className="p-4 space-y-1.5 flex-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
};
