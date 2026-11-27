// LOCKMATE Header Component

import { useState, useEffect } from 'react';
import { Wifi, Cpu, HardDrive, Shield } from 'lucide-react';
import { api } from '../api/client';

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  useEffect(() => {
    checkApiHealth();
    const interval = setInterval(checkApiHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  async function checkApiHealth() {
    try {
      await api.health();
      setApiStatus('connected');
    } catch {
      setApiStatus('disconnected');
    }
  }

  return (
    <header className="h-16 bg-secondary border-b border-primary flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-lg hover:bg-tertiary text-secondary transition-colors"
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        )}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-muted flex items-center justify-center">
            <Shield className="w-5 h-5 text-accent-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-primary truncate max-w-md">LOCKMATE</h1>
            <p className="text-xs text-muted">Healthcare Privacy Dashboard</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* API Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-tertiary border border-primary">
          <span className={`w-2 h-2 rounded-full ${apiStatus === 'connected' ? 'bg-status-success' : apiStatus === 'disconnected' ? 'bg-status-error' : 'bg-status-warning animate-pulse'}`} />
          <span className="text-xs font-medium text-secondary capitalize">{apiStatus}</span>
        </div>

        {/* System Indicators */}
        <div className="hidden md:flex items-center gap-4 text-xs text-muted">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-tertiary/50">
            <Cpu className="w-3.5 h-3.5 text-accent-primary" />
            <span className="font-medium text-secondary">2 CPU</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-tertiary/50">
            <HardDrive className="w-3.5 h-3.5 text-accent-primary" />
            <span className="font-medium text-secondary">4 GB</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-tertiary/50">
            <Wifi className="w-3.5 h-3.5 text-accent-primary" />
            <span className="font-medium text-secondary">Offline</span>
          </div>
        </div>
      </div>
    </header>
  );
}