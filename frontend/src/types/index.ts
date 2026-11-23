export interface Teacher {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface Student {
  id: number;
  github_username: string;
  github_user_id: number | null;
  display_name: string | null;
  profile_url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_synced_at: string | null;
  total_prs: number;
  merged_prs: number;
  open_prs: number;
  closed_unmerged_prs: number;
  merge_percentage: number;
  prs_today: number;
  merged_today: number;
  open_today: number;
  closed_unmerged_today: number;
}

export interface PullRequest {
  id: number;
  github_id: number;
  github_node_id: string;
  student_id: number;
  repository_full_name: string;
  repository_owner: string;
  repository_name: string;
  organization_name: string | null;
  pr_number: number;
  title: string;
  html_url: string;
  state: string;
  status: 'OPEN' | 'MERGED' | 'CLOSED_UNMERGED';
  is_draft: boolean;
  author_username: string;
  created_at_github: string;
  updated_at_github: string | null;
  closed_at: string | null;
  merged_at: string | null;
  merged_by: string | null;
  base_branch: string | null;
  head_branch: string | null;
  commits: number;
  additions: number;
  deletions: number;
  changed_files: number;
  comments: number;
  review_comments: number;
  last_checked_at: string;
}

export interface TrackingScope {
  id: number;
  scope_type: 'global' | 'organization' | 'repository';
  scope_value: string;
  display_name: string | null;
  url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface SyncLog {
  id: number;
  student_id: number | null;
  scope_id: number | null;
  started_at: string;
  finished_at: string | null;
  status: string;
  discovered_count: number;
  new_pr_count: number;
  updated_pr_count: number;
  error_message: string | null;
  is_complete: boolean;
}

export interface DashboardSummary {
  total_students: number;
  total_prs: number;
  merged_prs: number;
  open_prs: number;
  closed_unmerged_prs: number;
  merge_percentage: number;
  prs_today: number;
  merged_today: number;
  open_today: number;
  closed_unmerged_today: number;
  total_repositories: number;
  total_organizations: number;
  total_additions: number;
  total_deletions: number;
  total_changed_files: number;
  last_synced_at: string | null;
}

export interface LeaderboardEntry {
  student_id: number;
  github_username: string;
  display_name: string;
  profile_url: string;
  total_prs: number;
  merged_prs: number;
  open_prs: number;
  closed_unmerged_prs: number;
  merge_percentage: number;
  prs_today: number;
  last_synced_at: string | null;
}

export interface ActivityData {
  timeline: Array<{
    date: string;
    created: number;
    merged: number;
    closed_unmerged: number;
  }>;
  top_repositories: Array<{
    repository: string;
    total_prs: number;
    merged_prs: number;
  }>;
  top_organizations: Array<{
    organization: string;
    total_prs: number;
    merged_prs: number;
  }>;
}

export interface RepositoryBreakdown {
  repository: string;
  total: number;
  merged: number;
  open: number;
  closed_unmerged: number;
}

export interface OrganizationBreakdown {
  organization: string;
  total: number;
  merged: number;
  open: number;
  closed_unmerged: number;
}

export interface SyncInfo {
  last_successful_sync: string | null;
  last_attempted_sync: string | null;
  status: string;
  total_stored: number;
  new_prs: number;
  updated_prs: number;
  is_complete: boolean;
  error_message: string | null;
}

export interface StudentStatistics {
  student_id: number;
  github_username: string;
  display_name: string | null;
  profile_url: string;
  is_active: boolean;
  last_synced_at: string | null;
  total_prs: number;
  merged_prs: number;
  open_prs: number;
  closed_unmerged_prs: number;
  merge_percentage: number;
  unique_repositories: number;
  unique_organizations: number;
  prs_merged_in_period: number;
  prs_currently_open_overall: number;
  total_additions: number;
  total_deletions: number;
  total_changed_files: number;
  filter_by: string;
  date_range?: string;
  repositories: RepositoryBreakdown[];
  organizations: OrganizationBreakdown[];
  daily_timeline: Array<{ date: string; created: number; merged: number; open: number }>;
  sync_info: SyncInfo;
}
