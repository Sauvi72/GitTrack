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
      <div className="min-h-screen bg-[#09261a] flex items-center justify-center text-xs text-[#a0b5a8]">
        Loading GitTrack...
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
