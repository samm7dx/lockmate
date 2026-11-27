// LOCKMATE Upload Zone Component

import { useCallback, useState } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { Upload, X, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { formatBytes } from '../api/client';

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  selectedFiles: File[];
  onRemoveFile: (index: number) => void;
  isProcessing: boolean;
  onStartProcessing: () => void;
  canProcess: boolean;
  uploadProgress?: number; // 0-100
}

const SUPPORTED_FORMATS = [
  { ext: 'csv', label: 'CSV', desc: 'Comma-separated values' },
  { ext: 'tsv', label: 'TSV', desc: 'Tab-separated values' },
  { ext: 'json', label: 'JSON', desc: 'JavaScript Object Notation' },
  { ext: 'txt', label: 'TXT', desc: 'Plain text files' },
];

export function UploadZone({ 
  onFilesSelected, 
  selectedFiles, 
  onRemoveFile, 
  isProcessing, 
  onStartProcessing,
  canProcess,
  uploadProgress 
}: UploadZoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const validateFiles = useCallback((files: FileList): File[] => {
    const validFiles: File[] = [];
    const newErrors: string[] = [];
    const supportedExts = new Set(SUPPORTED_FORMATS.map(f => f.ext));
    const maxSize = 100 * 1024 * 1024; // 100 MB
    const maxTotalSize = 2 * 1024 * 1024 * 1024; // 2 GB
    let totalSize = selectedFiles.reduce((sum, f) => sum + f.size, 0);

    Array.from(files).forEach(file => {
      const ext = file.name.split('.').pop()?.toLowerCase();
      
      if (!ext || !supportedExts.has(ext)) {
        newErrors.push(`${file.name}: Unsupported format. Supported: ${SUPPORTED_FORMATS.map(f => f.ext).join(', ')}`);
        return;
      }

      if (file.size > maxSize) {
        newErrors.push(`${file.name}: File exceeds 100 MB limit`);
        return;
      }

      if (totalSize + file.size > maxTotalSize) {
        newErrors.push(`Total upload size would exceed 2 GB limit`);
        return;
      }

      // Check for duplicates
      if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
        newErrors.push(`${file.name}: Duplicate file`);
        return;
      }

      totalSize += file.size;
      validFiles.push(file);
    });

    setErrors(newErrors);
    return validFiles;
  }, [selectedFiles]);

  const handleDrag = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const validFiles = validateFiles(e.dataTransfer.files);
      if (validFiles.length > 0) {
        onFilesSelected(validFiles);
      }
    }
  }, [validateFiles, onFilesSelected]);

  const handleFileSelect = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const validFiles = validateFiles(e.target.files);
      if (validFiles.length > 0) {
        onFilesSelected(validFiles);
      }
      e.target.value = ''; // Reset input
    }
  }, [validateFiles, onFilesSelected]);

  const getFormatInfo = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    return SUPPORTED_FORMATS.find(f => f.ext === ext) || { label: ext.toUpperCase(), desc: 'Unknown format' };
  };

  return (
    <div className="bg-card border border-primary rounded-lg overflow-hidden">
      {/* Drop Zone */}
      <div
        className={`relative p-8 text-center transition-all duration-200 ${
          dragActive 
            ? 'border-accent-primary bg-accent-muted' 
            : 'border-dashed border-secondary hover:border-accent-primary/50'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          multiple
          accept=".csv,.tsv,.json,.txt"
          onChange={handleFileSelect}
          className="sr-only"
          disabled={isProcessing}
        />
        
        <Upload className={`w-12 h-12 mx-auto mb-4 transition-colors ${
          dragActive ? 'text-accent-primary' : 'text-secondary'
        }`} />
        
        <h3 className="text-lg font-medium text-primary mb-1">
          {dragActive ? 'Drop files here' : 'Drag & drop files here'}
        </h3>
        <p className="text-sm text-muted mb-4">
          or click to browse • Supports: CSV, TSV, JSON, TXT • Max 100 MB/file, 2 GB total
        </p>

        {/* Supported Formats */}
        <div className="flex flex-wrap justify-center gap-2 mb-4">
          {SUPPORTED_FORMATS.map(({ ext, label, desc }) => (
            <span
              key={ext}
              className="px-2.5 py-1 text-xs bg-tertiary border border-primary rounded text-secondary"
              title={desc}
            >
              {label}
            </span>
          ))}
        </div>

        {errors.length > 0 && (
          <div className="mt-4 p-3 bg-status-error/10 border border-status-error/30 rounded text-sm text-status-error text-left">
            {errors.map((err, i) => (
              <div key={i} className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {err}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="border-t border-primary">
          <div className="px-4 py-3 flex items-center justify-between">
            <h4 className="text-sm font-medium text-secondary">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
            </h4>
            <span className="text-xs text-muted">
              Total: {formatBytes(selectedFiles.reduce((sum, f) => sum + f.size, 0))}
            </span>
          </div>
          
          <div className="divide-y divide-primary max-h-60 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <div key={`${file.name}-${file.size}-${index}`} className="px-4 py-3 flex items-center gap-3 hover:bg-tertiary/50 transition-colors">
                <div className="p-2 bg-tertiary rounded">
                  <FileText className="w-5 h-5 text-secondary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-primary truncate">{file.name}</p>
                  <p className="text-xs text-muted flex items-center gap-2">
                    <span>{formatBytes(file.size)}</span>
                    <span>•</span>
                    <span className="px-1.5 py-0.5 bg-tertiary rounded text-xs">{getFormatInfo(file.name).label}</span>
                  </p>
                </div>
                <button
                  onClick={() => onRemoveFile(index)}
                  disabled={isProcessing}
                  className="p-2 rounded hover:bg-status-error/10 text-secondary hover:text-status-error transition-colors disabled:opacity-50"
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          {/* Progress Bar (when uploading/processing) */}
          {(uploadProgress !== undefined && uploadProgress > 0) && (
            <div className="px-4 py-3 bg-tertiary/30 border-t border-primary">
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-tertiary rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-accent-primary rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${Math.min(uploadProgress, 100)}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-primary w-12 text-right">
                  {Math.min(uploadProgress, 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-xs text-muted mt-1 text-center">
                {uploadProgress < 100 ? 'Uploading files...' : 'Upload complete, starting processing...'}
              </p>
            </div>
          )}

          {/* Start Processing Button */}
          <div className="px-4 py-4 bg-tertiary/30">
            <button
              onClick={onStartProcessing}
              disabled={!canProcess || isProcessing || selectedFiles.length === 0}
              className="w-full py-3 px-6 rounded-lg font-medium text-base transition-all duration-200 flex items-center justify-center gap-2
                bg-accent-primary text-bg-primary hover:bg-accent-secondary
                disabled:opacity-50 disabled:cursor-not-allowed
                focus:outline-none focus:ring-2 focus:ring-accent-primary focus:ring-offset-2 focus:ring-offset-bg-primary"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  Start Sanitization
                </>
              )}
            </button>
            {!canProcess && selectedFiles.length > 0 && !isProcessing && (
              <p className="text-xs text-muted text-center mt-2">
                Upload files to enable processing
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}