// LOCKMATE Metric Card Component

import type { LucideIcon } from 'lucide-react';
import { TrendingUp } from 'lucide-react';

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
    <div className="card animate-slideUp">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted font-medium">{label}</p>
          <p className={`text-3xl font-bold mt-1 ${accent ? 'text-accent-primary' : 'text-primary'}`}>
            {value}
          </p>
          {trend && (
            <p className={`text-xs mt-2 flex items-center gap-1 ${trendUp ? 'text-status-success' : 'text-status-warning'}`}>
              <TrendingUp className={`w-3 h-3 ${trendUp ? 'text-status-success' : 'text-status-warning'}`} />
              {trend}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-xl ${accent ? 'bg-accent-muted' : 'bg-tertiary/50'}`}>
          <Icon className={`w-6 h-6 ${accent ? 'text-accent-primary' : 'text-secondary'}`} />
        </div>
      </div>
    </div>
  );
}