// LOCKMATE Upload & Sanitize Page

import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Info, Shield } from 'lucide-react';
import { api } from '../api/client';
import type { ProcessResponse } from '../api/client';
import { UploadZone } from '../components/UploadZone';
import { ProcessingStatus } from '../components/ProcessingStatus';
import { Header } from '../components/Header';
import type { Job } from '../api/client';

export function Upload() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [polling, setPolling] = useState(false);

  const addFiles = useCallback((files: File[]) => {
    setSelectedFiles(prev => [...prev, ...files]);
  }, []);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const processMutation = useMutation({
    mutationFn: (files: File[]) => api.process(files),
    onSuccess: (response: ProcessResponse) => {
      setCurrentJob(null); // Will be fetched by polling
      setPolling(true);
      // Start polling for job status
      pollJobStatus(response.job_id);
    },
    onError: (error: Error) => {
      console.error('Processing failed:', error);
      alert(`Failed to start processing: ${error.message}`);
    },
  });

  const pollJobStatus = async (jobId: string) => {
    try {
      const job = await api.getRun(jobId);
      setCurrentJob(job);
      
      if (job.status === 'running' || job.status === 'pending') {
        // Continue polling
        setTimeout(() => pollJobStatus(jobId), 2000);
      } else if (job.status === 'completed') {
        setPolling(false);
        queryClient.invalidateQueries({ queryKey: ['runs'] });
        // Navigate to results
        navigate(`/results/${jobId}`);
      } else if (job.status === 'failed') {
        setPolling(false);
      }
    } catch (error) {
      console.error('Polling error:', error);
      setPolling(false);
    }
  };

  const handleStartProcessing = () => {
    if (selectedFiles.length > 0) {
      processMutation.mutate(selectedFiles);
    }
  };

  const canProcess = selectedFiles.length > 0 && !processMutation.isPending;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <Header />
      
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-primary mb-1">Upload & Sanitize</h1>
          <p className="text-secondary">
            Drag and drop healthcare data files for PII removal and clinical preservation.
          </p>
        </div>

        {/* Upload Zone */}
        <UploadZone
          selectedFiles={selectedFiles}
          onFilesSelected={addFiles}
          onRemoveFile={removeFile}
          isProcessing={processMutation.isPending || polling}
          onStartProcessing={handleStartProcessing}
          canProcess={canProcess}
        />

        {/* Processing Status */}
        {(processMutation.isPending || polling || currentJob) && (
          <div className="animate-fadeIn">
            <h2 className="text-lg font-semibold text-primary mb-4">Processing Status</h2>
            <ProcessingStatus 
              job={currentJob} 
              onRefresh={() => currentJob && pollJobStatus(currentJob.job_id)} 
            />
          </div>
        )}

        {/* Error Display */}
        {processMutation.isError && (
          <div className="bg-status-error/10 border border-status-error/30 rounded-lg p-4 flex items-start gap-3 animate-fadeIn">
            <AlertCircle className="w-5 h-5 text-status-error flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-medium text-status-error mb-1">Upload Failed</h3>
              <p className="text-sm text-muted">
                {processMutation.error instanceof Error 
                  ? processMutation.error.message 
                  : 'An unknown error occurred'}
              </p>
            </div>
          </div>
        )}

        {/* Info Panel */}
        <div className="bg-card border border-primary rounded-lg p-5">
          <h3 className="font-semibold text-primary mb-4 flex items-center gap-2">
            <Info className="w-5 h-5 text-accent-primary" />
            How It Works
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="p-3 bg-tertiary rounded">
              <h4 className="font-medium text-primary mb-1 flex items-center gap-1">
                <Shield className="w-4 h-4 text-accent-primary" />
                1. Detect & Remove PII
              </h4>
              <p className="text-secondary">
                Names, phones, Aadhaar, ABHA, PAN, emails, addresses, dates, UHIDs
              </p>
            </div>
            <div className="p-3 bg-tertiary rounded">
              <h4 className="font-medium text-primary mb-1 flex items-center gap-1">
                <Shield className="w-4 h-4 text-accent-primary" />
                2. Preserve Clinical Data
              </h4>
              <p className="text-secondary">
                Drugs, dosages, diagnoses, labs, vitals, procedures preserved
              </p>
            </div>
            <div className="p-3 bg-tertiary rounded">
              <h4 className="font-medium text-primary mb-1 flex items-center gap-1">
                <Shield className="w-4 h-4 text-accent-primary" />
                3. Link & Pseudonymize
              </h4>
              <p className="text-secondary">
                Cross-hospital patient linkage with stable PSN-XXXX pseudonyms
              </p>
            </div>
          </div>
        </div>

        {/* Format Support */}
        <div className="bg-card border border-primary rounded-lg p-5">
          <h3 className="font-semibold text-primary mb-3">Supported File Formats</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { ext: 'CSV', desc: 'Comma-separated', icon: '📊' },
              { ext: 'TSV', desc: 'Tab-separated', icon: '📋' },
              { ext: 'JSON', desc: 'Nested objects', icon: '📄' },
              { ext: 'TXT', desc: 'Plain text notes', icon: '📝' },
            ].map(({ ext, desc, icon }) => (
              <div key={ext} className="p-3 bg-tertiary rounded border border-primary text-center">
                <span className="text-2xl">{icon}</span>
                <p className="font-medium text-primary mt-1">{ext}</p>
                <p className="text-xs text-muted">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}