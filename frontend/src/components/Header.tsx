import React, { useState } from 'react';
import {
  LayoutDashboard,
  Users,
  Code,
  LogOut,
  Pencil,
  Check,
  X,
  Loader2,
  ChevronDown
} from 'lucide-react';
import { Teacher } from '../types';
import { api } from '../services/api';

interface HeaderProps {
  teacher: Teacher | null;
  onLogout: () => void;
  onTeacherUpdated?: (updated: Teacher) => void;
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  teacher,
  onLogout,
  onTeacherUpdated,
  currentTab,
  onSelectTab,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [nameInput, setNameInput] = useState(teacher?.full_name || '');
  const [isSaving, setIsSaving] = useState(false);

  const startEdit = () => {
    setNameInput(teacher?.full_name || '');
    setIsEditing(true);
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setNameInput(teacher?.full_name || '');
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const clean = nameInput.trim();
    if (!clean || clean === teacher?.full_name) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    try {
      const updated = await api.updateMe({ full_name: clean });
      if (onTeacherUpdated) {
        onTeacherUpdated(updated);
      }
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to update teacher name:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  const initialLetter = teacher?.full_name ? teacher.full_name.charAt(0).toUpperCase() : 'S';

  return (
    <header className="bg-[#09261a] text-white sticky top-0 z-40 border-b border-[#143d2b] shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-xl overflow-hidden border border-white/20 shadow-xs flex items-center justify-center shrink-0 bg-[#353b4e]">
            <img src="/logo.png" alt="OpenTrack Logo" className="w-full h-full object-cover" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-base font-bold text-white tracking-tight">OpenTrack</span>
          </div>
        </div>

        {/* Center: Top Navigation Pills */}
        <nav className="flex items-center gap-1.5 bg-[#061e14]/60 p-1 rounded-2xl border border-white/10">
          <button
            onClick={() => onSelectTab('overview')}
            className={`px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 transition-all ${
              currentTab === 'overview'
                ? 'bg-[#fceddb] text-[#09261a] shadow-xs'
                : 'text-white/80 hover:text-white hover:bg-white/5'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Overview</span>
          </button>

          <button
            onClick={() => onSelectTab('students')}
            className={`px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 transition-all ${
              currentTab === 'students'
                ? 'bg-[#fceddb] text-[#09261a] shadow-xs'
                : 'text-white/80 hover:text-white hover:bg-white/5'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Students</span>
          </button>
        </nav>

        {/* Right: Actions & Customizable User Profile */}
        <div className="flex items-center gap-3 shrink-0">
          {/* User Profile */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-[#fceddb] text-[#09261a] font-extrabold text-sm flex items-center justify-center shadow-xs">
              {initialLetter}
            </div>

            {isEditing ? (
              <div className="flex items-center gap-1.5 animate-in fade-in duration-150">
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  autoFocus
                  placeholder="Enter name..."
                  disabled={isSaving}
                  className="px-2.5 py-1 text-sm border border-white/30 rounded-lg focus:outline-none focus:ring-1 focus:ring-emerald-400 font-bold text-slate-900 bg-white shadow-xs w-32 sm:w-40"
                />
                <button
                  onClick={() => handleSave()}
                  disabled={isSaving}
                  className="p-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition-colors shadow-xs"
                  title="Save (Enter)"
                >
                  {isSaving ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                </button>
                <button
                  onClick={cancelEdit}
                  disabled={isSaving}
                  className="p-1.5 rounded-md bg-white/20 text-white hover:bg-white/30 transition-colors"
                  title="Cancel (Esc)"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div
                onClick={startEdit}
                className="group flex items-center gap-1 cursor-pointer py-1 px-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Click to customize professor name"
              >
                <span className="text-sm font-bold text-white tracking-tight group-hover:text-[#fceddb] transition-colors">
                  {teacher?.full_name || 'Prof. Davis'}
                </span>
                <ChevronDown className="w-4 h-4 text-white/60 group-hover:text-white transition-colors" />
              </div>
            )}
          </div>

          {/* Logout */}
          <button
            onClick={onLogout}
            className="p-1.5 text-white/60 hover:text-white hover:bg-white/10 rounded-lg transition-colors ml-1"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
