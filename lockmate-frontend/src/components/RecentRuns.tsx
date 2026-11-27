// LOCKMATE Recent Runs Component

import { Link } from 'react-router-dom';
import { Clock, CheckCircle, AlertCircle, Loader2, FileText, Download, ChevronRight } from 'lucide-react';
import type { Job } from '../api/client';
import { formatDate, formatDuration, getStatusLabel } from '../api/client';

interface RecentRunsProps {
  jobs: Job[];
  onRefresh?: () => void;
  loading?: boolean;
}

export function RecentRuns({ jobs, onRefresh, loading }: RecentRunsProps) {
  if (jobs.length === 0) {
    return (
      <div className="bg-card border border-primary rounded-lg p-8 text-center">
        <FileText className="w-12 h-12 mx-auto text-muted mb-4 opacity-50" />
        <h3 className="text-lg font-medium text-secondary mb-1">No processing runs yet</h3>
        <p className="text-sm text-muted mb-4">Upload files and start sanitization to see results here</p>
        <Link to="/upload" className="inline-flex items-center gap-2 px-4 py-2 bg-accent-primary text-bg-primary rounded-lg font-medium hover:bg-accent-secondary transition-colors">
          <FileText className="w-4 h-4" />
          Start First Run
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-card border border-primary rounded-lg overflow-hidden">
      <div className="px-5 py-4 border-b border-primary flex items-center justify-between">
        <h3 className="font-semibold text-primary">Recent Runs</h3>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 rounded hover:bg-tertiary text-secondary transition-colors disabled:opacity-50"
            aria-label="Refresh runs"
          >
            <Loader2 className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full" role="table">
          <thead>
            <tr className="border-b border-primary">
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase tracking-wider">Job ID</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase tracking-wider hidden sm:table-cell">Started</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase tracking-wider hidden md:table-cell">Files</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase tracking-wider hidden lg:table-cell">Records</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted uppercase tracking-wider hidden md:table-cell">Duration</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-muted uppercase tracking-wider w-24">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-primary/50">
            {jobs.slice(0, 10).map(job => (
              <tr key={job.job_id} className="hover:bg-tertiary/50 transition-colors">
                <td className="px-4 py-3 font-mono text-sm text-primary">{job.job_id}</td>
                <td className="px-4 py-3 text-sm text-secondary hidden sm:table-cell">
                  {formatDate(job.created_at)}
                </td>
                <td className="px-4 py-3 text-sm text-secondary hidden md:table-cell">
                  {job.input_files.length}
                </td>
                <td className="px-4 py-3 text-sm text-secondary hidden lg:table-cell">
                  {job.progress.records_processed?.toLocaleString() || '—'}
                </td>
                <td className="px-4 py-3">
                  <span 
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      job.status === 'completed' ? 'bg-status-success/20 text-status-success' :
                      job.status === 'running' ? 'bg-accent-primary/20 text-accent-primary' :
                      job.status === 'failed' ? 'bg-status-error/20 text-status-error' :
                      'bg-tertiary text-secondary'
                    }`}
                  >
                    {job.status === 'completed' && <CheckCircle className="w-3 h-3" />}
                    {job.status === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
                    {job.status === 'failed' && <AlertCircle className="w-3 h-3" />}
                    {job.status === 'pending' && <Clock className="w-3 h-3" />}
                    {getStatusLabel(job.status)}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-secondary hidden md:table-cell font-mono">
                  {job.completed_at && job.started_at 
                    ? formatDuration(new Date(job.completed_at).getTime() - new Date(job.started_at).getTime())
                    : job.status === 'running' && job.started_at
                      ? formatDuration(Date.now() - new Date(job.started_at).getTime())
                      : '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    to={`/results/${job.job_id}`}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      job.status === 'completed'
                        ? 'bg-accent-primary text-bg-primary hover:bg-accent-secondary'
                        : 'bg-tertiary text-secondary hover:bg-tertiary/50 opacity-70'
                    }`}
                    aria-label={job.status === 'completed' ? `View results for ${job.job_id}` : 'Results not available'}
                  >
                    {job.status === 'completed' ? (
                      <>
                        <Download className="w-3.5 h-3.5" />
                        View Results
                      </>
                    ) : (
                      <>
                        <Clock className="w-3.5 h-3.5" />
                        Pending
                      </>
                    )}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {jobs.length > 10 && (
        <div className="px-5 py-3 border-t border-primary text-center">
          <Link to="/results" className="text-sm text-accent-primary hover:text-accent-secondary font-medium flex items-center justify-center gap-1">
            View all {jobs.length} runs
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      )}
    </div>
  );
}