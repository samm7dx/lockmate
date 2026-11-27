// LOCKMATE Results Page

import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  Download, FileCheck, AlertTriangle, FileText, 
  Shield, Link as LinkIcon, Database, Clock,
  CheckCircle, XCircle, Loader2
} from 'lucide-react';
import { api } from '../api/client';
import { formatDuration, getStatusLabel } from '../api/client';
import { ProcessingStatus } from '../components/ProcessingStatus';
import { Header } from '../components/Header';

export function Results() {
  const { jobId } = useParams<{ jobId: string }>();
  
  const { data: job, isLoading: jobLoading, refetch: refetchJob } = useQuery({
    queryKey: ['run', jobId],
    queryFn: () => api.getRun(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => query.state.data?.status === 'running' ? 2000 : false,
  });

  const { data: reportData } = useQuery({
    queryKey: ['report', jobId],
    queryFn: () => api.getReport(jobId!),
    enabled: !!jobId && job?.status === 'completed',
  });

  const report = reportData?.report;
  const files = report?.files || [];

  const sanitizedFiles = files.filter(f => f.status === 'sanitized');
  const quarantinedFiles = files.filter(f => f.status === 'quarantined');

  const handleDownloadSanitized = async () => {
    if (!jobId) return;
    try {
      const blob = await api.downloadSanitized(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sanitized_${jobId}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download sanitized files');
    }
  };

  const handleDownloadRecords = async () => {
    if (!jobId) return;
    try {
      const blob = await api.downloadRecords(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `records_${jobId}.jsonl`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download records');
    }
  };

  const handleDownloadReport = async () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${jobId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!jobId) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center p-8">
          <FileText className="w-16 h-16 mx-auto text-muted mb-4" />
          <h2 className="text-xl font-semibold text-secondary mb-2">No Job Selected</h2>
          <Link to="/upload" className="text-accent-primary hover:underline">Upload files to start processing</Link>
        </div>
      </div>
    );
  }

  if (jobLoading || !job) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin text-accent-primary" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <Header />
      
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-primary mb-1">Results</h1>
            <p className="text-secondary">
              Job <code className="bg-tertiary px-2 py-0.5 rounded font-mono text-xs">{job.job_id}</code> • 
              {formatDate(job.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${
              job.status === 'completed' ? 'bg-status-success/20 text-status-success' :
              job.status === 'running' ? 'bg-accent-primary/20 text-accent-primary' :
              job.status === 'failed' ? 'bg-status-error/20 text-status-error' :
              'bg-tertiary text-secondary'
            }`}>
              {job.status === 'completed' && <CheckCircle className="w-4 h-4" />}
              {job.status === 'running' && <Loader2 className="w-4 h-4 animate-spin" />}
              {job.status === 'failed' && <XCircle className="w-4 h-4" />}
              {getStatusLabel(job.status)}
            </span>
          </div>
        </div>

        {/* Processing Status (if running) */}
        {(job.status === 'running' || job.status === 'pending') && (
          <ProcessingStatus job={job} onRefresh={() => refetchJob()} />
        )}

        {/* Error State */}
        {job.status === 'failed' && (
          <div className="bg-status-error/10 border border-status-error/30 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <AlertTriangle className="w-6 h-6 text-status-error flex-shrink-0" />
              <div>
                <h2 className="text-lg font-semibold text-status-error mb-2">Processing Failed</h2>
                <p className="text-muted font-mono text-sm break-all">{job.error || 'Unknown error'}</p>
              </div>
            </div>
          </div>
        )}

        {/* Completed Results */}
        {job.status === 'completed' && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="bg-card border border-primary rounded-lg p-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-status-success/20 rounded-lg">
                    <FileCheck className="w-5 h-5 text-status-success" />
                  </div>
                  <div>
                    <p className="text-sm text-muted">Sanitized Files</p>
                    <p className="text-2xl font-bold text-status-success">{sanitizedFiles.length}</p>
                  </div>
                </div>
              </div>
              <div className="bg-card border border-primary rounded-lg p-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-status-warning/20 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-status-warning" />
                  </div>
                  <div>
                    <p className="text-sm text-muted">Quarantined Files</p>
                    <p className="text-2xl font-bold text-status-warning">{quarantinedFiles.length}</p>
                  </div>
                </div>
              </div>
              <div className="bg-card border border-primary rounded-lg p-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-accent-muted rounded-lg">
                    <LinkIcon className="w-5 h-5 text-accent-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted">Records Processed</p>
                    <p className="text-2xl font-bold text-accent-primary">
                      {report?.counts.records_processed.toLocaleString() || '—'}
                    </p>
                  </div>
                </div>
              </div>
              <div className="bg-card border border-primary rounded-lg p-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-status-success/20 rounded-lg">
                    <Shield className="w-5 h-5 text-status-success" />
                  </div>
                  <div>
                    <p className="text-sm text-muted">PII Detected</p>
                    <p className="text-2xl font-bold text-primary">
                      {report?.counts.identifiers_detected.toLocaleString() || '—'}
                    </p>
                  </div>
                </div>
              </div>
              <div className="bg-card border border-primary rounded-lg p-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-tertiary rounded-lg">
                    <Clock className="w-5 h-5 text-secondary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted">Duration</p>
                    <p className="text-2xl font-bold text-secondary">
                      {report?.timing.seconds ? `${report.timing.seconds.toFixed(1)}s` : '—'}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Download Actions */}
            <div className="bg-card border border-primary rounded-lg p-5">
              <h3 className="font-semibold text-primary mb-4 flex items-center gap-2">
                <Download className="w-5 h-5 text-accent-primary" />
                Download Outputs
              </h3>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleDownloadSanitized}
                  disabled={sanitizedFiles.length === 0}
                  className="flex items-center gap-2 px-5 py-3 bg-accent-primary text-bg-primary rounded-lg font-medium hover:bg-accent-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Download className="w-5 h-5" />
                  <span>Sanitized Files (ZIP)</span>
                  <span className="text-xs bg-bg-primary/20 px-2 py-0.5 rounded">{sanitizedFiles.length} files</span>
                </button>
                <button
                  onClick={handleDownloadRecords}
                  className="flex items-center gap-2 px-5 py-3 bg-tertiary border border-primary text-secondary rounded-lg font-medium hover:border-accent-primary hover:text-accent-primary transition-colors"
                >
                  <FileText className="w-5 h-5" />
                  <span>Records (JSONL)</span>
                </button>
                <button
                  onClick={handleDownloadReport}
                  className="flex items-center gap-2 px-5 py-3 bg-tertiary border border-primary text-secondary rounded-lg font-medium hover:border-accent-primary hover:text-accent-primary transition-colors"
                >
                  <Database className="w-5 h-5" />
                  <span>Report (JSON)</span>
                </button>
              </div>
            </div>

            {/* File Details Tabs */}
            <div className="bg-card border border-primary rounded-lg overflow-hidden">
              <div className="border-b border-primary">
                <nav className="flex gap-1 px-4" role="tablist">
                  <button
                    role="tab"
                    aria-selected={true}
                    className="px-4 py-3 text-sm font-medium text-accent-primary border-b-2 border-accent-primary"
                  >
                    Sanitized ({sanitizedFiles.length})
                  </button>
                  <button
                    role="tab"
                    aria-selected={false}
                    className="px-4 py-3 text-sm font-medium text-secondary hover:text-primary"
                  >
                    Quarantined ({quarantinedFiles.length})
                  </button>
                  <button
                    role="tab"
                    aria-selected={false}
                    className="px-4 py-3 text-sm font-medium text-secondary hover:text-primary"
                  >
                    Report Summary
                  </button>
                </nav>
              </div>

              <div className="p-4 max-h-96 overflow-y-auto">
                {/* Sanitized Files */}
                <div role="tabpanel">
                  {sanitizedFiles.length === 0 ? (
                    <p className="text-muted text-center py-8">No sanitized files</p>
                  ) : (
                    <div className="space-y-2">
                      {sanitizedFiles.map((file, index) => (
                        <div key={`${file.input_sha256}-${index}`} className="flex items-center justify-between p-3 bg-tertiary/50 rounded border border-primary">
                          <div className="flex items-center gap-3 min-w-0">
                            <FileText className="w-5 h-5 text-accent-primary flex-shrink-0" />
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-primary truncate">{file.output || 'Unknown'}</p>
                              <p className="text-xs text-muted font-mono">
                                SHA256: {file.input_sha256.slice(0, 16)}... • {file.records_processed} records
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted">
                            <span>{formatDuration(file.processing_duration_ms)}</span>
                            <span>•</span>
                            <span>{file.peak_memory_mb.toFixed(1)} MB</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Quarantined Files */}
                <div role="tabpanel" hidden>
                  {quarantinedFiles.length === 0 ? (
                    <p className="text-muted text-center py-8">No quarantined files</p>
                  ) : (
                    <div className="space-y-2">
                      {quarantinedFiles.map((file, index) => (
                        <div key={`${file.input_sha256}-${index}`} className="flex items-center justify-between p-3 bg-status-error/5 rounded border border-status-error/20">
                          <div className="flex items-center gap-3 min-w-0">
                            <AlertTriangle className="w-5 h-5 text-status-warning flex-shrink-0" />
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-status-warning">Quarantined</p>
                              <p className="text-xs text-muted font-mono">
                                SHA256: {file.input_sha256.slice(0, 16)}... • {file.quarantine_reason || 'Unknown reason'}
                              </p>
                            </div>
                          </div>
                          <span className="text-xs text-muted">{file.quarantine_reason}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Report Summary */}
                <div role="tabpanel" hidden>
                  {report ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="p-3 bg-tertiary rounded">
                          <p className="text-xs text-muted">Total Files</p>
                          <p className="text-2xl font-bold text-primary">{report.counts.files_total}</p>
                        </div>
                        <div className="p-3 bg-tertiary rounded">
                          <p className="text-xs text-muted">Sanitized</p>
                          <p className="text-2xl font-bold text-status-success">{report.counts.files_sanitized}</p>
                        </div>
                        <div className="p-3 bg-tertiary rounded">
                          <p className="text-xs text-muted">Quarantined</p>
                          <p className="text-2xl font-bold text-status-warning">{report.counts.files_quarantined}</p>
                        </div>
                        <div className="p-3 bg-tertiary rounded">
                          <p className="text-xs text-muted">Peak Memory</p>
                          <p className="text-2xl font-bold text-secondary">{report.resources.peak_rss_mb.toFixed(1)} MB</p>
                        </div>
                      </div>
                      
                      <div className="border-t border-primary pt-4">
                        <h4 className="font-medium text-primary mb-3">PII Detection by Type</h4>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(report.entities || {}).map(([type, count]) => (
                            <span key={type} className="px-3 py-1 bg-tertiary border border-primary rounded text-sm">
                              {type}: <span className="font-medium text-accent-primary">{count}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-muted text-center py-8">Report not available</p>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Not Started Yet */}
        {job.status === 'pending' && (
          <div className="bg-card border border-primary rounded-lg p-8 text-center">
            <Clock className="w-12 h-12 mx-auto text-muted mb-4" />
            <h2 className="text-xl font-semibold text-secondary mb-2">Processing Not Started</h2>
            <p className="text-muted mb-4">Files uploaded but processing hasn't begun yet.</p>
            <button
              onClick={() => refetchJob()}
              className="px-4 py-2 bg-accent-primary text-bg-primary rounded-lg font-medium hover:bg-accent-secondary transition-colors"
            >
              <Loader2 className="w-4 h-4 inline mr-2" />
              Refresh Status
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}