import React, { useState, useEffect } from 'react';
import { api } from './services/api';
import { Teacher } from './types';
import { Header } from './components/Header';
import { OverviewPage } from './pages/OverviewPage';
import { StudentsPage } from './pages/StudentsPage';
import { StudentDetailPage } from './pages/StudentDetailPage';
import { LoginPage } from './pages/LoginPage';

export const App: React.FC = () => {
  const [teacher, setTeacher] = useState<Teacher | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isInitializing, setIsInitializing] = useState<boolean>(true);
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);

  const checkAuth = async () => {
    try {
      const me = await api.getMe();
      setTeacher(me);
      setIsAuthenticated(true);
    } catch {
      setIsAuthenticated(false);
      setTeacher(null);
    } finally {
      setIsInitializing(false);
    }
  };

  useEffect(() => {
    checkAuth();

    const handleUnauthorized = () => {
      setIsAuthenticated(false);
      setTeacher(null);
    };

    window.addEventListener('auth-unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth-unauthorized', handleUnauthorized);
  }, []);

  const handleLogout = async () => {
    await api.logout();
    setIsAuthenticated(false);
    setTeacher(null);
  };

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-[#09261a] flex flex-col items-center justify-center px-6">
        <div className="flex flex-col items-center gap-5 w-full max-w-xs">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl overflow-hidden border border-white/20 shadow-lg bg-[#353b4e] shrink-0">
              <img src="/logo.png" alt="GitTrack Logo" className="w-full h-full object-cover" />
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-white tracking-tight leading-none">GitTrack</h1>
              <p className="text-[11px] text-[#a0b5a8] font-medium mt-1">Student Contribution Tracker</p>
            </div>
          </div>

          <div
            role="progressbar"
            aria-label="Loading GitTrack"
            className="w-full h-1.5 bg-[#143d2b] rounded-full overflow-hidden shadow-inner"
          >
            <div className="h-full w-1/2 rounded-full bg-gradient-to-r from-[#10b981] via-[#e5b263] to-[#10b981] animate-loading-bar" />
          </div>

          <span className="text-xs text-[#a0b5a8] font-medium tracking-wide">
            Preparing your workspace...
          </span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={checkAuth} />;
  }

  return (
    <div className="min-h-screen bg-[#faf6ee] text-[#11241a] flex flex-col font-sans">
      <Header
        teacher={teacher}
        onLogout={handleLogout}
        onTeacherUpdated={(updated) => setTeacher(updated)}
        currentTab={selectedStudentId ? 'students' : currentTab}
        onSelectTab={(tab) => {
          setSelectedStudentId(null);
          setCurrentTab(tab);
        }}
      />

      <main className="p-4 sm:p-6 lg:p-8 flex-1 max-w-7xl w-full mx-auto">
        {selectedStudentId ? (
          <StudentDetailPage
            studentId={selectedStudentId}
            onBack={() => setSelectedStudentId(null)}
          />
        ) : currentTab === 'overview' ? (
          <OverviewPage
            onSelectStudent={(id) => setSelectedStudentId(id)}
            onNavigateTab={(tab) => setCurrentTab(tab)}
          />
        ) : (
          <StudentsPage onSelectStudent={(id) => setSelectedStudentId(id)} />
        )}
      </main>
    </div>
  );
};

export default App;
