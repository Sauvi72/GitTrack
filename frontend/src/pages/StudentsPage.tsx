import React, { useState, useEffect } from 'react';
import {
  Search,
  UserPlus,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Archive,
  CheckCircle2,
  AlertCircle,
  GitMerge,
  GitPullRequest,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { Student } from '../types';
import { AddStudentModal } from '../components/AddStudentModal';

interface StudentsPageProps {
  onSelectStudent: (id: number) => void;
}

export const StudentsPage: React.FC<StudentsPageProps> = ({ onSelectStudent }) => {
  const [students, setStudents] = useState<Student[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [syncingMap, setSyncingMap] = useState<Record<number, boolean>>({});
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const fetchStudents = async () => {
    setIsLoading(true);
    try {
      const data = await api.getStudents({ q: searchQuery || undefined });
      setStudents(data);
    } catch (err) {
      console.error('Failed to fetch students:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchStudents();
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Live polling for active sync jobs to auto-update student data
  useEffect(() => {
    let isMounted = true;
    const checkSyncStatus = async () => {
      try {
        const status = await api.getSyncStatus();
        if (!isMounted) return;
        const activeIds: number[] = status.active_students_syncing || [];
        if (activeIds.length > 0) {
          const newMap: Record<number, boolean> = {};
          activeIds.forEach((id) => {
            newMap[id] = true;
          });
          setSyncingMap((prev) => ({ ...prev, ...newMap }));
        } else {
          // Check if previously any student was syncing in syncingMap
          setSyncingMap((prev) => {
            const hadSyncing = Object.values(prev).some(Boolean);
            if (hadSyncing) {
              fetchStudents();
            }
            return {};
          });
        }
      } catch (err) {
        // Polling error silently ignored
      }
    };

    const interval = setInterval(checkSyncStatus, 2500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSyncStudent = async (e: React.MouseEvent, studentId: number) => {
    e.stopPropagation();
    setSyncingMap((prev) => ({ ...prev, [studentId]: true }));
    setStatusMessage(null);

    try {
      const res = await api.syncStudent(studentId, false);
      setStatusMessage(`Sync complete: ${res.details?.new_prs ?? 0} new PRs, ${res.details?.updated_prs ?? 0} updated.`);
      await fetchStudents();
    } catch (err: any) {
      setStatusMessage(`Sync failed: ${err.message}`);
    } finally {
      setSyncingMap((prev) => ({ ...prev, [studentId]: false }));
    }
  };

  const handleArchive = async (e: React.MouseEvent, studentId: number) => {
    e.stopPropagation();
    if (!window.confirm('Archive this student? Their historical contribution data will be preserved.')) return;

    try {
      await api.deleteStudent(studentId, false);
      fetchStudents();
    } catch (err: any) {
      alert(`Failed to archive student: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="border-l-4 border-[#0d3824] pl-3.5 py-0.5">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#09261a] tracking-tight">Student Directory</h2>
          <p className="text-xs sm:text-sm text-[#4a5a50] font-medium mt-0.5">
            Monitor students, track their open-source contributions, and run GitHub synchronizations.
          </p>
        </div>

        <button
          onClick={() => setIsAddModalOpen(true)}
          className="inline-flex items-center gap-2.5 px-4 py-2.5 bg-[#0d3824] hover:bg-[#072416] text-white text-sm font-semibold rounded-xl shadow-xs transition-colors"
        >
          <UserPlus className="w-5 h-5 sm:w-6 sm:h-6" strokeWidth={2.2} />
          <span>Add Student</span>
        </button>
      </div>

      {statusMessage && (
        <div className="p-3.5 bg-[#eaf4ed] border border-[#d6ecdc] text-[#1e613b] rounded-2xl text-xs flex items-center justify-between">
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} className="text-[#1e613b] font-bold ml-4">
            ✕
          </button>
        </div>
      )}

      {/* Search Bar with Clear Cross Button */}
      <div className="relative">
        <Search className="w-4 h-4 text-[#718076] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search students by GitHub username or display name..."
          className="w-full pl-10 pr-10 py-2.5 text-xs sm:text-sm bg-white rounded-xl border border-[#ede6db] focus:outline-none focus:ring-2 focus:ring-[#0d3824]/20 focus:border-[#0d3824] transition-colors shadow-xs text-[#11241a]"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full text-[#718076] hover:text-[#11241a] hover:bg-[#faf6ee] transition-colors"
            title="Clear search"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-[#ede6db] overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#ede6db] bg-[#faf6ee]/70 text-xs font-bold text-[#516358] uppercase tracking-wider">
                <th className="py-3.5 px-4">Student</th>
                <th className="py-3.5 px-4">GitHub Username</th>
                <th className="py-3.5 px-4 text-center">PRs Today</th>
                <th className="py-3.5 px-4 text-center">Total PRs</th>
                <th className="py-3.5 px-4 text-center">Merged</th>
                <th className="py-3.5 px-4 text-center">Open</th>
                <th className="py-3.5 px-4 text-center">Unmerged</th>
                <th className="py-3.5 px-4">Merge Ratio</th>
                <th className="py-3.5 px-4">Last Synced</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-800">
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-400">
                    Loading student directory...
                  </td>
                </tr>
              ) : students.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-400">
                    No students found. Click "Add Student" above to start tracking.
                  </td>
                </tr>
              ) : (
                students.map((student) => {
                  const isSyncing = syncingMap[student.id] || false;
                  return (
                    <tr
                      key={student.id}
                      onClick={() => onSelectStudent(student.id)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                    >
                      {/* Name / Avatar */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center border border-slate-200 text-sm">
                            {student.github_username.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900 group-hover:text-emerald-700 transition-colors text-sm">
                              {student.display_name || student.github_username}
                            </div>
                            {!student.is_active && (
                              <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded font-medium">
                                Archived
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* GitHub Link */}
                      <td className="py-3.5 px-4">
                        <a
                          href={student.profile_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 font-mono text-xs text-slate-600 hover:text-emerald-700"
                        >
                          @{student.github_username}
                          <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                        </a>
                      </td>

                      {/* PRs Today Badge */}
                      <td className="py-3.5 px-4 text-center">
                        <span
                          className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                            student.prs_today > 0
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : 'bg-slate-100 text-slate-400'
                          }`}
                        >
                          {student.prs_today}
                        </span>
                      </td>

                      {/* Counts */}
                      <td className="py-3.5 px-4 text-center font-bold text-slate-900 text-sm">
                        {student.total_prs}
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold text-emerald-700 text-sm">
                        {student.merged_prs}
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold text-blue-700 text-sm">
                        {student.open_prs}
                      </td>
                      <td className="py-3.5 px-4 text-center font-semibold text-slate-400 text-sm">
                        {student.closed_unmerged_prs}
                      </td>

                      {/* Merge Ratio */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-100 h-2 rounded-full overflow-hidden">
                            <div
                              className="bg-emerald-500 h-full rounded-full"
                              style={{ width: `${student.merge_percentage}%` }}
                            />
                          </div>
                          <span className="text-xs font-bold text-slate-800">
                            {student.merge_percentage}%
                          </span>
                        </div>
                      </td>

                      {/* Last Synced */}
                      <td className="py-3.5 px-4 text-slate-500 text-xs font-medium">
                        {isSyncing ? (
                          <span className="inline-flex items-center gap-1.5 text-emerald-600 font-semibold">
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            Syncing...
                          </span>
                        ) : student.last_synced_at ? (
                          new Date(student.last_synced_at).toLocaleString([], {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })
                        ) : (
                          'Never'
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={(e) => handleSyncStudent(e, student.id)}
                            disabled={isSyncing}
                            className={`p-1.5 rounded-lg border text-slate-600 hover:bg-slate-100 transition-colors ${
                              isSyncing ? 'animate-spin text-emerald-600 border-emerald-200' : 'border-slate-200'
                            }`}
                            title="Sync PRs now"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => handleArchive(e, student.id)}
                            className="p-1.5 rounded-lg border border-rose-200 bg-rose-50/70 text-rose-600 hover:text-rose-700 hover:bg-rose-100 hover:border-rose-300 transition-colors shadow-2xs"
                            title="Delete / Archive student"
                          >
                            <Archive className="w-3.5 h-3.5" />
                          </button>
                          <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-600 transition-colors" />
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AddStudentModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onStudentAdded={() => fetchStudents()}
      />
    </div>
  );
};
