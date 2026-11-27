// LOCKMATE Dashboard Page

import { useQuery } from '@tanstack/react-query';
import { ShieldCheck, FileText, CheckCircle, TrendingUp, Clock, Loader2, Shield, FileCheck } from 'lucide-react';
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
    <div className="flex-1 overflow-y-auto p-6 space-y-8 animate-slideUp">
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
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-accent-muted flex items-center justify-center">
                    <FileCheck className="w-5 h-5 text-accent-primary" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-primary">Latest Processing Job</h2>
                    <p className="text-xs text-muted font-mono">Job: {latestJob.job_id}</p>
                  </div>
                </div>
                <RecentRuns jobs={[latestJob]} loading={isLoading} />
              </div>
            </div>
          ) : (
            <div className="card animate-slideUp">
              <div className="flex flex-col items-center justify-center py-16 px-8">
                <div className="w-20 h-20 rounded-xl bg-accent-muted flex items-center justify-center mb-6">
                  <Shield className="w-10 h-10 text-accent-primary/50" />
                </div>
                <h2 className="text-2xl font-semibold text-primary mb-2">No Processing Runs Yet</h2>
                <p className="text-secondary mb-8 max-w-md mx-auto text-center">
                  Upload healthcare data files to begin sanitization. LOCKMATE will remove all PII while preserving clinical utility.
                </p>
                <a 
                  href="/upload" 
                  className="btn btn-primary btn-lg"
                >
                  <FileText className="w-5 h-5" />
                  Start First Sanitization
                </a>
              </div>
            </div>
          )}

          {/* System Info */}
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-primary flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-accent-primary" />
                System Constraints (Organizer Limits)
              </h3>
            </div>
            <div className="card-body">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg bg-tertiary/50 text-center border border-primary/50">
                  <p className="text-3xl font-bold text-accent-primary">2</p>
                  <p className="text-xs text-muted mt-1">CPU Cores</p>
                </div>
                <div className="p-4 rounded-lg bg-tertiary/50 text-center border border-primary/50">
                  <p className="text-3xl font-bold text-accent-primary">4 GB</p>
                  <p className="text-xs text-muted mt-1">Memory Limit</p>
                </div>
                <div className="p-4 rounded-lg bg-tertiary/50 text-center border border-primary/50">
                  <p className="text-3xl font-bold text-accent-primary">15 min</p>
                  <p className="text-xs text-muted mt-1">Time Limit</p>
                </div>
                <div className="p-4 rounded-lg bg-tertiary/50 text-center border border-primary/50">
                  <p className="text-3xl font-bold text-accent-primary">Offline</p>
                  <p className="text-xs text-muted mt-1">Network</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Quick Stats */}
        <div className="space-y-6">
          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-primary flex items-center gap-2">
                <Clock className="w-5 h-5 text-accent-primary" />
                Processing Summary
              </h3>
            </div>
            <div className="card-body space-y-4">
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
              <div className="flex justify-between text-sm border-t border-primary pt-4">
                <span className="text-secondary">Total Records</span>
                <span className="font-medium text-primary">{totalRecords.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {latestJob?.status === 'running' && (
            <div className="animate-slideUp bg-accent-muted border border-accent-primary/30 rounded-lg p-5">
              <div className="flex items-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-accent-primary" />
                <h3 className="font-semibold text-accent-primary">Job in Progress</h3>
              </div>
              <p className="text-sm text-secondary mt-2">
                Job <code className="bg-tertiary px-2 py-0.5 rounded font-mono">{latestJob.job_id}</code> is currently processing.
              </p>
              <p className="text-xs text-muted mt-3">
                Results will appear here automatically when complete.
              </p>
            </div>
          )}

          <div className="card">
            <div className="card-header">
              <h3 className="font-semibold text-primary flex items-center gap-2">
                <Shield className="w-5 h-5 text-accent-primary" />
                Supported Formats
              </h3>
            </div>
            <div className="card-body space-y-3">
              {['CSV', 'TSV', 'JSON', 'TXT', 'FHIR R4'].map(fmt => (
                <div key={fmt} className="flex items-center justify-between text-sm py-2 px-3 rounded-lg bg-tertiary/50 border border-primary/50 transition-colors hover:bg-tertiary">
                  <span className="text-secondary">{fmt}</span>
                  <span className="badge badge-success">✓ Supported</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}