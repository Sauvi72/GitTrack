import {
  Teacher,
  Student,
  PullRequest,
  TrackingScope,
  SyncLog,
  DashboardSummary,
  LeaderboardEntry,
  ActivityData,
  StudentStatistics,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, '')}/api`
  : '/api';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('opentrack_token');
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If unauthorized, clear token and notify
    localStorage.removeItem('opentrack_token');
    window.dispatchEvent(new Event('auth-unauthorized'));
  }

  if (!response.ok) {
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      const errData = await response.json();
      if (errData && errData.detail) {
        errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    throw new ApiError(errorMsg, response.status);
  }

  return response.json();
}

export const api = {
  // Auth
  login: async (email: string, password: string) => {
    const data = await request<{ access_token: string; expires_in: number }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('opentrack_token', data.access_token);
    return data;
  },
  logout: async () => {
    try {
      await request('/auth/logout', { method: 'POST' });
    } finally {
      localStorage.removeItem('opentrack_token');
    }
  },
  getMe: () => request<Teacher>('/auth/me'),
  updateMe: (data: { full_name: string }) =>
    request<Teacher>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  // Students
  getStudents: (params?: {
    q?: string;
    is_active?: boolean;
    date_range?: string;
    date_from?: string;
    date_to?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.q) query.set('q', params.q);
    if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));
    if (params?.date_range) query.set('date_range', params.date_range);
    if (params?.date_from) query.set('date_from', params.date_from);
    if (params?.date_to) query.set('date_to', params.date_to);
    return request<Student[]>(`/students?${query.toString()}`);
  },
  getStudent: (id: number) => request<Student>(`/students/${id}`),
  createStudent: (github_username: string, display_name?: string, sync_now = true) =>
    request<Student>(`/students?sync_now=${sync_now}`, {
      method: 'POST',
      body: JSON.stringify({ github_username, display_name }),
    }),
  updateStudent: (id: number, data: { display_name?: string; is_active?: boolean }) =>
    request<Student>(`/students/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteStudent: (id: number, hardDelete = true) =>
    request<{ message: string }>(`/students/${id}?hard_delete=${hardDelete}`, {
      method: 'DELETE',
    }),
  getStudentStatistics: (
    id: number,
    params?: {
      date_range?: string;
      date_from?: string;
      date_to?: string;
      filter_by?: string;
      tz?: string;
    } | string
  ) => {
    let query = new URLSearchParams();
    if (typeof params === 'string') {
      if (params) query.set('date_range', params);
    } else if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') query.set(k, String(v));
      });
    }
    const qStr = query.toString();
    return request<StudentStatistics>(`/students/${id}/statistics${qStr ? `?${qStr}` : ''}`);
  },

  // Scopes
  getScopes: () => request<TrackingScope[]>('/scopes'),
  createScope: (data: { scope_type: string; scope_value: string; display_name?: string }) =>
    request<TrackingScope>('/scopes', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateScope: (id: number, data: { is_active?: boolean; display_name?: string }) =>
    request<TrackingScope>(`/scopes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteScope: (id: number) => request<{ message: string }>(`/scopes/${id}`, { method: 'DELETE' }),

  // Pull Requests
  getPullRequests: (params?: {
    student_id?: number;
    status?: string;
    organization?: string;
    repository?: string;
    date_from?: string;
    date_to?: string;
    date_range?: string;
    filter_by?: string;
    tz?: string;
    sort_by?: string;
    order?: string;
    page?: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') query.set(k, String(v));
      });
    }
    return request<{
      items: PullRequest[];
      total: number;
      page: number;
      limit: number;
      total_pages: number;
    }>(`/pull-requests?${query.toString()}`);
  },

  // Sync
  syncStudent: (id: number, force_full = false, background = false) =>
    request<{ message: string; status: string; details?: any }>(
      `/students/${id}/sync?force_full=${force_full}&background=${background}`,
      { method: 'POST' }
    ),
  syncAll: (background = true) =>
    request<{ message: string; status: string }>(`/sync-all?background=${background}`, {
      method: 'POST',
    }),
  getSyncLogs: (limit = 30) => request<SyncLog[]>(`/sync-logs?limit=${limit}`),
  getSyncStatus: () =>
    request<{
      is_syncing: boolean;
      active_students_syncing: number[];
      last_sync: any;
    }>('/sync-status'),

  // Dashboard
  getDashboardSummary: (date_range?: string, date_from?: string, date_to?: string) => {
    const query = new URLSearchParams();
    if (date_range) query.set('date_range', date_range);
    if (date_from) query.set('date_from', date_from);
    if (date_to) query.set('date_to', date_to);
    return request<DashboardSummary>(`/dashboard/summary?${query.toString()}`);
  },
  getLeaderboard: (limit = 10, sort_by = 'merged') =>
    request<LeaderboardEntry[]>(`/dashboard/leaderboard?limit=${limit}&sort_by=${sort_by}`),
  getActivity: (days = 30) => request<ActivityData>(`/dashboard/activity?days=${days}`),

  // Reports
  getCsvDownloadUrl: (params?: { student_id?: number; status?: string; date_from?: string; date_to?: string }) => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') query.set(k, String(v));
      });
    }
    return `/api/reports/csv?${query.toString()}`;
  },
};
