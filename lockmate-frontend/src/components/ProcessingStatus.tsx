// LOCKMATE Processing Status Component

import { Loader2, CheckCircle, AlertCircle, Clock, RotateCcw, FileText, Shield, Link, Database } from 'lucide-react';
import type { Job } from '../api/client';
import { formatDuration } from '../api/client';

interface ProcessingStatusProps {
  job: Job | null;
  onRefresh?: () => void;
}

const stages = [
  { id: 'initializing', label: 'Initializing', icon: RotateCcw },
  { id: 'intake_and_parse', label: 'File Intake & Parsing', icon: FileText },
  { id: 'sanitize', label: 'Sanitization', icon: Shield },
  { id: 'patient_linkage', label: 'Patient Linkage', icon: Link },
  { id: 'output_and_reports', label: 'Output & Reports', icon: Database },
  { id: 'completed', label: 'Completed', icon: CheckCircle },
] as const;

function getStageProgress(job: Job): number {
  const currentStage = job.stage;
  const stageIndex = stages.findIndex(s => currentStage.includes(s.id)) ?? 
    stages.findIndex(s => s.id === currentStage) ?? -1;
  
  if (job.status === 'completed') return 100;
  if (job.status === 'failed') return stageIndex >= 0 ? (stageIndex / (stages.length - 1)) * 100 : 0;
  if (stageIndex >= 0) return (stageIndex / (stages.length - 1)) * 100;
  return 0;
}

function getCurrentStageIndex(job: Job): number {
  const currentStage = job.stage;
  return stages.findIndex(s => currentStage.includes(s.id)) ?? 
    stages.findIndex(s => s.id === currentStage) ?? 0;
}

export function ProcessingStatus({ job, onRefresh }: ProcessingStatusProps) {
  if (!job) return null;

  const currentStageIndex = getCurrentStageIndex(job);
  const progress = getStageProgress(job);

  return (
    <div className="bg-card border border-primary rounded-lg overflow-hidden animate-fadeIn">
      {/* Header */}
      <div className="px-5 py-4 border-b border-primary flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            job.status === 'completed' ? 'bg-status-success/20 text-status-success' :
            job.status === 'failed' ? 'bg-status-error/20 text-status-error' :
            'bg-accent-muted text-accent-primary'
          }`}>
            {job.status === 'completed' && <CheckCircle className="w-5 h-5" />}
            {job.status === 'failed' && <AlertCircle className="w-5 h-5" />}
            {job.status === 'running' && <Loader2 className="w-5 h-5 animate-spin" />}
            {job.status === 'pending' && <Clock className="w-5 h-5" />}
          </div>
          <div>
            <h3 className="font-semibold text-primary">Processing Job</h3>
            <p className="text-xs text-muted font-mono">{job.job_id}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {job.status === 'running' && (
            <span className="text-xs text-accent-primary flex items-center gap-1">
              <Loader2 className="w-3 h-3 animate-spin" />
              Live
            </span>
          )}
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="p-2 rounded hover:bg-tertiary text-secondary transition-colors"
              aria-label="Refresh status"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="px-5 py-3 border-b border-primary">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="text-secondary">Progress</span>
          <span className="font-mono text-accent-primary">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 bg-tertiary rounded-full overflow-hidden">
          <div 
            className="h-full bg-accent-primary rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Stage Pipeline */}
      <div className="px-5 py-4">
        <div className="space-y-4">
          {stages.map((stage, index) => {
            const isCompleted = index < currentStageIndex || (index === currentStageIndex && job.status === 'completed');
            const isCurrent = index === currentStageIndex && job.status === 'running';
            const isFailed = index === currentStageIndex && job.status === 'failed';
            
            return (
              <div 
                key={stage.id}
                className={`flex items-center gap-3 transition-colors ${
                  isCurrent ? 'opacity-100' : 'opacity-70'
                }`}
              >
                {/* Connector line */}
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 ${
                    isCompleted ? 'bg-status-success border-2 border-status-success' :
                    isCurrent ? 'bg-accent-primary border-2 border-accent-primary animate-pulse' :
                    isFailed ? 'bg-status-error border-2 border-status-error' :
                    'bg-tertiary border-2 border-primary'
                  }`}>
                    {isCompleted && <CheckCircle className="w-4 h-4 text-bg-primary" />}
                    {isCurrent && <Loader2 className="w-4 h-4 animate-spin text-bg-primary" />}
                    {isFailed && <AlertCircle className="w-4 h-4 text-bg-primary" />}
                    {!isCompleted && !isCurrent && !isFailed && <stage.icon className="w-4 h-4 text-secondary" />}
                  </div>
                  {index < stages.length - 1 && (
                    <div 
                      className="w-0.5 h-8 mt-1"
                      style={{ background: isCompleted ? 'var(--status-success)' : 'var(--border-primary)' }}
                    />
                  )}
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${
                    isCurrent ? 'text-accent-primary' :
                    isCompleted ? 'text-primary' :
                    isFailed ? 'text-status-error' :
                    'text-secondary'
                  }`}>
                    {stage.label}
                  </p>
                  {isCurrent && job.progress && (
                    <p className="text-xs text-muted mt-0.5 font-mono">
                      {job.progress.records_processed > 0 && `Records: ${job.progress.records_processed.toLocaleString()} • `}
                      {job.progress.identifiers_detected > 0 && `PII: ${job.progress.identifiers_detected.toLocaleString()} • `}
                      {job.progress.records_linked > 0 && `Linked: ${job.progress.records_linked.toLocaleString()}`}
                    </p>
                  )}
                </div>
                
                {isCompleted && job.completed_at && (
                  <span className="text-xs text-muted font-mono whitespace-nowrap">
                    {formatDuration(new Date(job.completed_at).getTime() - new Date(job.started_at || job.created_at).getTime())}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Error Display */}
      {job.status === 'failed' && job.error && (
        <div className="px-5 py-4 bg-status-error/10 border-t border-status-error/30">
          <div className="flex items-start gap-3 p-3 bg-status-error/5 rounded border border-status-error/20">
            <AlertCircle className="w-5 h-5 text-status-error flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-status-error">Processing Failed</p>
              <p className="text-xs text-muted mt-1 font-mono break-all">{job.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Completion Summary */}
      {job.status === 'completed' && job.progress && (
        <div className="px-5 py-4 bg-status-success/5 border-t border-status-success/20">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
            <div className="p-3 bg-tertiary rounded">
              <p className="text-2xl font-bold text-status-success">{job.progress.records_processed.toLocaleString()}</p>
              <p className="text-xs text-muted">Records Processed</p>
            </div>
            <div className="p-3 bg-tertiary rounded">
              <p className="text-2xl font-bold text-accent-primary">{job.progress.identifiers_detected.toLocaleString()}</p>
              <p className="text-xs text-muted">PII Detected</p>
            </div>
            <div className="p-3 bg-tertiary rounded">
              <p className="text-2xl font-bold text-status-success">{job.progress.records_linked.toLocaleString()}</p>
              <p className="text-xs text-muted">Patients Linked</p>
            </div>
            <div className="p-3 bg-tertiary rounded">
              <p className="text-2xl font-bold text-primary">{formatDuration(job.progress.total_duration_ms)}</p>
              <p className="text-xs text-muted">Total Duration</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}