// LOCKMATE Dashboard Page

import { useQuery } from '@tanstack/react-query';
import { ShieldCheck, FileText, CheckCircle, TrendingUp, Clock, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { MetricCard } from '../components/MetricCard';
import { RecentRuns } from '../components/RecentRuns';
import { Header } from '../components/Header';

export function Dashboard() {
  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: api.listRuns,
    refetchInterval: 10000,
  });

  const jobs = jobsData?.jobs || [];
  
  // Calculate metrics
  const completedJobs = jobs.filter(j => j.status === 'completed');
  const runningJobs = jobs.filter(j => j.status === 'running');
  const failedJobs = jobs.filter(j => j.status === 'failed');
  
  const totalFiles = jobs.reduce((sum, j) => sum + j.input_files.length, 0);
  const totalRecords = completedJobs.reduce((sum, j) => sum + (j.progress.records_processed || 0), 0);
  const totalQuarantined = completedJobs.reduce((sum, j) => {
    return sum + (j.progress.records_quarantined || 0);
  }, 0);

  const latestJob = jobs[0];

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <Header />
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Runs"
          value={jobs.length}
          icon={FileText}
          trend={`${completedJobs.length} completed`}
          trendUp={true}
        />
        <MetricCard
          label="Files Processed"
          value={totalFiles.toLocaleString()}
          icon={FileText}
          accent
        />
        <MetricCard
          label="Records Sanitized"
          value={totalRecords.toLocaleString()}
          icon={CheckCircle}
          trend={`${totalQuarantined} quarantined`}
          trendUp={false}
        />
        <MetricCard
          label="System Status"
          value={runningJobs.length > 0 ? 'Processing' : 'Ready'}
          icon={runningJobs.length > 0 ? Clock : ShieldCheck}
          accent={runningJobs.length > 0}
          trend={runningJobs.length > 0 ? `${runningJobs.length} active` : 'All systems operational'}
          trendUp={runningJobs.length === 0}
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Latest Run / Status */}
        <div className="lg:col-span-2 space-y-6">
          {latestJob ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-primary">Latest Processing Job</h2>
                <span className="text-xs text-muted font-mono">Job: {latestJob.job_id}</span>
              </div>
              <RecentRuns jobs={[latestJob]} loading={isLoading} />
            </div>
          ) : (
            <div className="bg-card border border-primary rounded-lg p-12 text-center">
              <ShieldCheck className="w-16 h-16 mx-auto text-muted mb-4 opacity-30" />
              <h2 className="text-xl font-semibold text-secondary mb-2">No Processing Runs Yet</h2>
              <p className="text-muted mb-6 max-w-md mx-auto">
                Upload healthcare data files to begin sanitization. LOCKMATE will remove all PII while preserving clinical utility.
              </p>
              <a 
                href="/upload" 
                className="inline-flex items-center gap-2 px-6 py-3 bg-accent-primary text-bg-primary rounded-lg font-medium hover:bg-accent-secondary transition-colors"
              >
                <FileText className="w-5 h-5" />
                Start First Sanitization
              </a>
            </div>
          )}

          {/* System Info */}
          <div className="bg-card border border-primary rounded-lg p-5">
            <h3 className="font-semibold text-primary mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-accent-primary" />
              System Constraints (Organizer Limits)
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div className="p-3 bg-tertiary rounded">
                <p className="text-2xl font-bold text-accent-primary">2</p>
                <p className="text-xs text-muted">CPU Cores</p>
              </div>
              <div className="p-3 bg-tertiary rounded">
                <p className="text-2xl font-bold text-accent-primary">4 GB</p>
                <p className="text-xs text-muted">Memory Limit</p>
              </div>
              <div className="p-3 bg-tertiary rounded">
                <p className="text-2xl font-bold text-accent-primary">15 min</p>
                <p className="text-xs text-muted">Time Limit</p>
              </div>
              <div className="p-3 bg-tertiary rounded">
                <p className="text-2xl font-bold text-accent-primary">Offline</p>
                <p className="text-xs text-muted">Network</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Quick Stats */}
        <div className="space-y-6">
          <div className="bg-card border border-primary rounded-lg p-5">
            <h3 className="font-semibold text-primary mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-accent-primary" />
              Processing Summary
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-secondary">Completed Runs</span>
                <span className="font-medium text-status-success">{completedJobs.length}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-secondary">Running</span>
                <span className="font-medium text-accent-primary">{runningJobs.length}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-secondary">Failed</span>
                <span className="font-medium text-status-error">{failedJobs.length}</span>
              </div>
              <div className="flex justify-between text-sm border-t border-primary pt-3">
                <span className="text-secondary">Total Records</span>
                <span className="font-medium text-primary">{totalRecords.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {latestJob?.status === 'running' && (
            <div className="bg-accent-muted border border-accent-primary/30 rounded-lg p-5 animate-pulse">
              <h3 className="font-semibold text-accent-primary mb-2 flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                Job in Progress
              </h3>
              <p className="text-sm text-secondary">
                Job <code className="bg-tertiary px-1.5 py-0.5 rounded font-mono">{latestJob.job_id}</code> is currently processing.
              </p>
              <p className="text-xs text-muted mt-2">
                Results will appear here automatically when complete.
              </p>
            </div>
          )}

          <div className="bg-card border border-primary rounded-lg p-5">
            <h3 className="font-semibold text-primary mb-4 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-accent-primary" />
              Supported Formats
            </h3>
            <div className="space-y-2">
              {['CSV', 'TSV', 'JSON', 'TXT', 'FHIR R4'].map(fmt => (
                <div key={fmt} className="flex items-center justify-between text-sm">
                  <span className="text-secondary">{fmt}</span>
                  <span className="text-status-success text-xs">✓ Supported</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}