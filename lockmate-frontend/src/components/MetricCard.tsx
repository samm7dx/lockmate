// LOCKMATE Metric Card Component

import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  trend?: string;
  trendUp?: boolean;
  accent?: boolean;
}

export function MetricCard({ label, value, icon: Icon, trend, trendUp, accent }: MetricCardProps) {
  return (
    <div className="bg-card border border-primary rounded-lg p-5 hover:border-secondary transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted font-medium">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${accent ? 'text-accent-primary' : 'text-primary'}`}>
            {value}
          </p>
          {trend && (
            <p className={`text-xs mt-1 flex items-center gap-1 ${trendUp ? 'text-status-success' : 'text-status-error'}`}>
              {trend}
            </p>
          )}
        </div>
        <div className={`p-2 rounded-lg ${accent ? 'bg-accent-muted' : 'bg-tertiary'}`}>
          <Icon className={`w-5 h-5 ${accent ? 'text-accent-primary' : 'text-secondary'}`} />
        </div>
      </div>
    </div>
  );
}