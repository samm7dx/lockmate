// LOCKMATE API Client

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

export interface JobFile {
  filename: string;
  size: number;
  format: string;
}

export interface JobProgress {
  total_duration_ms: number;
  peak_memory_mb: number;
  records_processed: number;
  identifiers_detected: number;
  records_linked: number;
  records_generalized: number;
  records_suppressed: number;
  records_quarantined: number;
}

export interface Job {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  stage: string;
  progress: JobProgress;
  error: string | null;
  input_files: JobFile[];
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ReportFileEntry {
  input_sha256: string;
  output: string | null;
  status: 'sanitized' | 'quarantined' | 'suppressed';
  quarantine_reason: string | null;
  processing_duration_ms: number;
  peak_memory_mb: number;
  records_processed: number;
  identifiers_detected: number;
  records_linked: number;
  records_generalized: number;
  records_suppressed: number;
  records_quarantined: number;
}

export interface ReportCounts {
  files_total: number;
  files_sanitized: number;
  files_quarantined: number;
  records_processed: number;
  identifiers_detected: number;
  records_linked: number;
  records_generalized: number;
  records_suppressed: number;
  records_quarantined: number;
  total_processing_duration_ms: number;
  peak_memory_mb: number;
}

export interface Report {
  schema: string;
  files: ReportFileEntry[];
  counts: ReportCounts;
  entities: Record<string, number>;
  timing: { seconds: number };
  resources: { peak_rss_mb: number };
}

export interface ProcessResponse {
  job_id: string;
  status: string;
  message: string;
}

class ApiError extends Error {
  public readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || response.statusText);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  health: () => fetchApi<{ status: string; version: string; timestamp: string }>('/api/health'),

  process: (files: File[], configPath: string = 'config/policy.yaml'): Promise<ProcessResponse> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('config_path', configPath);
    
    return fetchApi<ProcessResponse>('/api/process', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type with boundary
    });
  },

  listRuns: () => fetchApi<{ jobs: Job[] }>('/api/runs'),

  getRun: (jobId: string) => fetchApi<Job>(`/api/runs/${jobId}`),

  getReport: (jobId: string) => fetchApi<{ job_id: string; report: Report }>(`/api/runs/${jobId}/report`),

  downloadRecords: (jobId: string): Promise<Blob> => 
    fetch(`${API_BASE}/api/runs/${jobId}/records`).then(res => {
      if (!res.ok) throw new ApiError(res.status, 'Failed to download records');
      return res.blob();
    }),

  downloadSanitized: (jobId: string): Promise<Blob> =>
    fetch(`${API_BASE}/api/runs/${jobId}/download`).then(res => {
      if (!res.ok) throw new ApiError(res.status, 'Failed to download sanitized files');
      return res.blob();
    }),
};

export { ApiError };

// Helper functions
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getStatusColor(status: Job['status']): string {
  switch (status) {
    case 'completed': return 'var(--status-success)';
    case 'running': return 'var(--accent-primary)';
    case 'pending': return 'var(--status-pending)';
    case 'failed': return 'var(--status-error)';
    default: return 'var(--text-muted)';
  }
}

export function getStatusLabel(status: Job['status']): string {
  switch (status) {
    case 'completed': return 'Completed';
    case 'running': return 'Processing';
    case 'pending': return 'Pending';
    case 'failed': return 'Failed';
    default: return status;
  }
}