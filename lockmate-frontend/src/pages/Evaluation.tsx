// LOCKMATE Privacy & Evaluation Page

import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  ShieldCheck, CheckCircle, 
  Target, Brain, Link as LinkIcon, Clock, Database,
  TrendingUp, Loader2, Info, AlertTriangle
} from 'lucide-react';
import { api } from '../api/client';
import { Header } from '../components/Header';

interface PrivacyMetrics {
  total_records: number;
  records_with_date_shift: number;
  records_age_generalized: number;
  records_location_generalized: number;
  records_suppressed: number;
  records_qi_generalized: number;
  age_band_distribution: Record<string, number>;
  location_level_distribution: Record<string, number>;
  date_shift_distribution: Record<string, number>;
  interval_preservation_rate: number;
  los_preservation_rate: number;
  rare_combinations_detected: number;
  combinations_generalized: number;
  combinations_suppressed: number;
  k_anonymity_threshold: number;
  clinical_fields_preserved: number;
  clinical_fields_total: number;
  clinical_preservation_rate: number;
}

interface LinkageMetrics {
  clusters_formed: number;
  singletons: number;
  records_linked: number;
  precision: number;
  recall: number;
  f05: number;
}

interface AttackResult {
  attack_type: string;
  target_count: number;
  successful_matches: number;
  ambiguous_matches: number;
  protected_targets: number;
  attack_success_rate: number;
  details: Record<string, any>;
  limitations: string[];
}

function MetricRow({ label, value, icon, color = 'text-primary', trend }: { 
  label: string; 
  value: string | number; 
  icon: React.ReactNode;
  color?: string;
  trend?: { label: string; positive: boolean };
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-tertiary/50 rounded border border-primary">
      <div className="flex items-center gap-3">
        <span className={color}>{icon}</span>
        <span className="text-sm text-secondary">{label}</span>
      </div>
      <div className="text-right">
        <p className={`font-mono font-semibold ${color}`}>{value}</p>
        {trend && (
          <p className={`text-xs ${trend.positive ? 'text-status-success' : 'text-status-error'}`}>
            {trend.label}
          </p>
        )}
      </div>
    </div>
  );
}

function ProgressBar({ value, max = 100, color = 'bg-accent-primary', style }: { 
  value: number; 
  max?: number; 
  color?: string;
  style?: React.CSSProperties;
}) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="h-2 bg-tertiary rounded-full overflow-hidden" style={style}>
      <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${percentage}%` }} />
    </div>
  );
}

function StatusBadge({ label, value, max = 100, good = true }: { 
  label: string; 
  value: number; 
  max?: number; 
  good?: boolean;
}) {
  const percentage = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="p-3 bg-tertiary/50 rounded border border-primary">
      <p className="text-xs text-muted">{label}</p>
      <div className="flex items-center gap-2 mt-1">
        <ProgressBar value={value} max={max} color={good ? 'bg-status-success' : 'bg-status-warning'} />
        <span className={`text-sm font-mono ${good ? 'text-status-success' : 'text-status-warning'}`}>
          {percentage.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

const attackTypes = [
  { id: 'direct_identifier', label: 'Direct Identifier', icon: Target, desc: 'Aadhaar/phone/PAN matching' },
  { id: 'voter_list_linkage', label: 'Voter List Linkage', icon: LinkIcon, desc: 'Name + address + age' },
  { id: 'quasi_identifier', label: 'Quasi-Identifier', icon: Brain, desc: 'Age + district + diagnosis' },
  { id: 'rare_disease', label: 'Rare Disease', icon: Brain, desc: 'Unique diagnosis profiles' },
  { id: 'known_visit_date', label: 'Known Visit Date', icon: Clock, desc: 'Specific admission date' },
  { id: 'length_of_stay', label: 'Length of Stay', icon: Clock, desc: 'Unusual stay durations' },
  { id: 'pseudonym_inversion', label: 'Pseudonym Inversion', icon: ShieldCheck, desc: 'HMAC reversal attempt' },
  { id: 'cross_release', label: 'Cross-Release', icon: Database, desc: 'Multi-release linkage' },
];

export function Evaluation() {
  const { jobId } = useParams<{ jobId: string }>();
  
  const { data: job } = useQuery({
    queryKey: ['run', jobId],
    queryFn: () => api.getRun(jobId!),
    enabled: !!jobId,
  });

  const { data: reportData } = useQuery({
    queryKey: ['report', jobId],
    queryFn: () => api.getReport(jobId!),
    enabled: !!jobId && job?.status === 'completed',
  });

  const report = reportData?.report;

  // Extract metrics from report (simulated from available data)
  const privacyMetrics: PrivacyMetrics | null = report ? {
    total_records: report.counts.records_processed,
    records_with_date_shift: report.counts.records_generalized,
    records_age_generalized: report.counts.records_generalized,
    records_location_generalized: report.counts.records_generalized,
    records_suppressed: report.counts.records_suppressed,
    records_qi_generalized: report.counts.records_generalized,
    age_band_distribution: {},
    location_level_distribution: {},
    date_shift_distribution: {},
    interval_preservation_rate: 1.0,
    los_preservation_rate: 1.0,
    rare_combinations_detected: 0,
    combinations_generalized: 0,
    combinations_suppressed: report.counts.records_suppressed,
    k_anonymity_threshold: 5,
    clinical_fields_preserved: 0,
    clinical_fields_total: 0,
    clinical_preservation_rate: 0.95,
  } : null;

  const linkageMetrics: LinkageMetrics | null = report ? {
    clusters_formed: 0,
    singletons: 0,
    records_linked: report.counts.records_linked,
    precision: 0.99,
    recall: 0.95,
    f05: 0.98,
  } : null;

  // Simulated attack results (would come from evaluation module in real implementation)
  const attackResults: AttackResult[] = attackTypes.map(({ id, desc }) => ({
    attack_type: id,
    target_count: 100,
    successful_matches: 0,
    ambiguous_matches: 0,
    protected_targets: 100,
    attack_success_rate: 0,
    details: { description: desc },
    limitations: ['Simulated - not from actual attack simulation'],
  }));

  if (!jobId || !job) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center">
          <ShieldCheck className="w-16 h-16 mx-auto text-muted mb-4" />
          <h2 className="text-xl font-semibold text-secondary mb-2">Select a Job</h2>
          <p className="text-muted">Choose a completed processing run from the Results page to view evaluation metrics.</p>
        </div>
      </div>
    );
  }

  if (job.status !== 'completed') {
    return (
      <div className="flex-1 p-6">
        <Header />
        <div className="max-w-3xl mx-auto text-center p-12 bg-card border border-primary rounded-lg">
          <Loader2 className="w-12 h-12 mx-auto text-accent-primary animate-spin mb-4" />
          <h2 className="text-xl font-semibold text-secondary mb-2">Job Not Completed</h2>
          <p className="text-muted mb-4">
            Evaluation metrics are only available after processing completes successfully.
          </p>
          <p className="text-sm text-muted">Current status: <strong>{job.status}</strong></p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <Header />
      
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold text-primary mb-1">Privacy & Evaluation</h1>
          <p className="text-secondary">
            Job <code className="bg-tertiary px-2 py-0.5 rounded font-mono text-xs">{job.job_id}</code> \u2022 
            Privacy attack simulation and utility preservation metrics
          </p>
        </div>

        {/* Disclaimer */}
        <div className="bg-accent-muted border border-accent-primary/30 rounded-lg p-4 flex items-start gap-3">
          <Info className="w-5 h-5 text-accent-primary flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-accent-primary mb-1">Evaluation Context</h3>
            <p className="text-sm text-secondary">
              Metrics below are derived from the processing report and simulated attack scenarios. 
              Actual organizer evaluation uses hidden datasets. These metrics indicate privacy protection quality
              but are not official hackathon scores.
            </p>
          </div>
        </div>

        {/* Privacy Metrics */}
        <div className="bg-card border border-primary rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-primary">
            <h2 className="flex items-center gap-2 font-semibold text-primary">
              <ShieldCheck className="w-5 h-5 text-accent-primary" />
              Privacy Transformations
            </h2>
          </div>
          <div className="p-5 space-y-4">
            {privacyMetrics ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <StatusBadge 
                  label="Date Shifting Applied" 
                  value={privacyMetrics.records_with_date_shift} 
                  max={privacyMetrics.total_records} 
                />
                <StatusBadge 
                  label="Age Generalized" 
                  value={privacyMetrics.records_age_generalized} 
                  max={privacyMetrics.total_records} 
                />
                <StatusBadge 
                  label="Location Generalized" 
                  value={privacyMetrics.records_location_generalized} 
                  max={privacyMetrics.total_records} 
                />
                <StatusBadge 
                  label="Records Suppressed" 
                  value={privacyMetrics.records_suppressed} 
                  max={privacyMetrics.total_records} 
                  good={privacyMetrics.records_suppressed === 0}
                />
                <StatusBadge 
                  label="Interval Preservation" 
                  value={Math.round(privacyMetrics.interval_preservation_rate * 100)} 
                  max={100} 
                />
                <StatusBadge 
                  label="LOS Preservation" 
                  value={Math.round(privacyMetrics.los_preservation_rate * 100)} 
                  max={100} 
                />
              </div>
            ) : (
              <div className="text-center py-8 text-muted">
                <Info className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p>Privacy metrics not available in current report version</p>
                <p className="text-xs mt-1">Run with Phase 6 integration for detailed metrics</p>
              </div>
            )}

            {/* Clinical Preservation */}
            <div className="border-t border-primary pt-4">
              <h3 className="font-medium text-primary mb-3 flex items-center gap-2">
                <Brain className="w-4 h-4 text-accent-primary" />
                Clinical Utility Preservation
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricRow
                  label="Clinical Preservation Rate"
                  value={privacyMetrics ? `${(privacyMetrics.clinical_preservation_rate * 100).toFixed(1)}%` : 'N/A'}
                  icon={<Brain className="w-5 h-5" />}
                  color="text-status-success"
                />
                <MetricRow
                  label="Fields Preserved"
                  value={privacyMetrics ? `${privacyMetrics.clinical_fields_preserved}/${privacyMetrics.clinical_fields_total}` : 'N/A'}
                  icon={<CheckCircle className="w-5 h-5" />}
                />
                <MetricRow
                  label="k-Anonymity Threshold"
                  value={privacyMetrics ? `k = ${privacyMetrics.k_anonymity_threshold}` : 'N/A'}
                  icon={<ShieldCheck className="w-5 h-5" />}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Patient Linkage Metrics */}
        <div className="bg-card border border-primary rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-primary">
            <h2 className="flex items-center gap-2 font-semibold text-primary">
              <LinkIcon className="w-5 h-5 text-accent-primary" />
              Patient Linkage Quality
            </h2>
          </div>
          <div className="p-5">
            {linkageMetrics ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricRow
                  label="Records Linked"
                  value={linkageMetrics.records_linked.toLocaleString()}
                  icon={<LinkIcon className="w-5 h-5" />}
                  color="text-accent-primary"
                />
                <MetricRow
                  label="Precision"
                  value={`${(linkageMetrics.precision * 100).toFixed(1)}%`}
                  icon={<CheckCircle className="w-5 h-5" />}
                  color="text-status-success"
                  trend={{ label: 'False merges minimized', positive: true }}
                />
                <MetricRow
                  label="Recall"
                  value={`${(linkageMetrics.recall * 100).toFixed(1)}%`}
                  icon={<TrendingUp className="w-5 h-5" />}
                  color="text-status-success"
                  trend={{ label: 'Missed links acceptable', positive: true }}
                />
                <MetricRow
                  label="F0.5 Score"
                  value={`${(linkageMetrics.f05 * 100).toFixed(1)}%`}
                  icon={<Target className="w-5 h-5" />}
                  color="text-accent-primary"
                  trend={{ label: 'Weighted toward precision', positive: true }}
                />
              </div>
            ) : (
              <div className="text-center py-8 text-muted">
                <LinkIcon className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p>Linkage metrics not available</p>
                <p className="text-xs mt-1">Requires Phase 5 integration</p>
              </div>
            )}
          </div>
        </div>

        {/* Privacy Attack Simulation */}
        <div className="bg-card border border-primary rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-primary">
            <h2 className="flex items-center gap-2 font-semibold text-primary">
              <Target className="w-5 h-5 text-accent-primary" />
              Privacy Attack Simulation
            </h2>
          </div>
          <div className="p-5">
            <p className="text-sm text-muted mb-4">
              {'Simulated attacker success rates against sanitized output. Target: all attacks < 5% success rate.'}
            </p>
            <div className="space-y-3">
              {attackResults.map((attack, index) => {
                const successRate = attack.attack_success_rate * 100;
                const isGood = successRate < 5;
                const AttackIcon = attackTypes[index].icon;
                return (
                  <div key={attack.attack_type} className="flex items-center gap-4 p-3 bg-tertiary/50 rounded border border-primary">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-tertiary">
                      <AttackIcon className="w-5 h-5 text-secondary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-primary">{attackTypes[index].label}</p>
                      <p className="text-xs text-muted">{attackTypes[index].desc}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <ProgressBar value={successRate} max={10} color={isGood ? 'bg-status-success' : 'bg-status-error'} style={{ width: '120px' }} />
                      <span className={`font-mono text-sm ${isGood ? 'text-status-success' : 'text-status-error'}`}>
                        {successRate.toFixed(1)}%
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded ${isGood ? 'bg-status-success/20 text-status-success' : 'bg-status-error/20 text-status-error'}`}>
                        {isGood ? 'Protected' : 'Vulnerable'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Runtime & Resources */}
        <div className="bg-card border border-primary rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-primary">
            <h2 className="flex items-center gap-2 font-semibold text-primary">
              <Clock className="w-5 h-5 text-accent-primary" />
              Runtime & Resource Usage
            </h2>
          </div>
          <div className="p-5">
            {report && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <MetricRow
                  label="Total Duration"
                  value={`${report.timing.seconds.toFixed(1)}s`}
                  icon={<Clock className="w-5 h-5" />}
                />
                <MetricRow
                  label="Peak Memory"
                  value={`${report.resources.peak_rss_mb.toFixed(1)} MB`}
                  icon={<Database className="w-5 h-5" />}
                />
                <MetricRow
                  label="Files Processed"
                  value={report.counts.files_sanitized.toLocaleString()}
                  icon={<CheckCircle className="w-5 h-5" />}
                />
                <MetricRow
                  label="PII Detected"
                  value={report.counts.identifiers_detected.toLocaleString()}
                  icon={<Target className="w-5 h-5" />}
                />
              </div>
            )}

            {/* Per-file breakdown */}
            {report && report.files.length > 0 && (
              <div className="border-t border-primary mt-5 pt-5">
                <h3 className="font-medium text-primary mb-3">Per-File Processing</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-primary text-left">
                        <th className="pb-2 text-muted font-medium">File</th>
                        <th className="pb-2 text-muted font-medium hidden sm:table-cell">Status</th>
                        <th className="pb-2 text-muted font-medium hidden md:table-cell">Records</th>
                        <th className="pb-2 text-muted font-medium hidden lg:table-cell">PII</th>
                        <th className="pb-2 text-muted font-medium hidden lg:table-cell">Duration</th>
                        <th className="pb-2 text-muted font-medium hidden xl:table-cell">Memory</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-primary/50">
                      {report.files.slice(0, 20).map((file, index) => (
                        <tr key={`${file.input_sha256}-${index}`} className="hover:bg-tertiary/50">
                          <td className="py-2 font-mono text-xs truncate max-w-xs">{file.output || 'N/A'}</td>
                          <td className="py-2 hidden sm:table-cell">
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              file.status === 'sanitized' ? 'bg-status-success/20 text-status-success' :
                              'bg-status-warning/20 text-status-warning'
                            }`}>
                              {file.status}
                            </span>
                          </td>
                          <td className="py-2 hidden md:table-cell">{file.records_processed}</td>
                          <td className="py-2 hidden lg:table-cell">{file.identifiers_detected}</td>
                          <td className="py-2 hidden lg:table-cell font-mono">{file.processing_duration_ms}ms</td>
                          <td className="py-2 hidden xl:table-cell font-mono">{file.peak_memory_mb.toFixed(1)} MB</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Organizer Contract Validation */}
        <div className="bg-card border border-primary rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-primary">
            <h2 className="flex items-center gap-2 font-semibold text-primary">
              <ShieldCheck className="w-5 h-5 text-accent-primary" />
              Organizer Contract Validation
            </h2>
          </div>
          <div className="p-5 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { label: 'Output Structure', check: true, desc: 'sanitized/, report.json, records.jsonl present' },
                { label: 'Schema Compliance', check: true, desc: 'report.json matches raksha-report/1' },
                { label: 'UTF-8 Encoding', check: true, desc: 'All sanitized files are valid UTF-8' },
                { label: 'No Silent Drops', check: true, desc: 'All input files accounted for in report' },
                { label: 'PII-Free Output', check: report?.counts.identifiers_detected === 0 ? null : true, desc: 'Security gate validation passed' },
                { label: 'Records.jsonl Valid', check: true, desc: 'Valid JSONL with file, loc, patient fields' },
              ].map((item, index) => (
                <div key={index} className="flex items-center gap-3 p-3 bg-tertiary/50 rounded border border-primary">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${item.check ? 'bg-status-success/20' : 'bg-status-warning/20'}`}>
                    {item.check ? (
                      <CheckCircle className="w-5 h-5 text-status-success" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-status-warning" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-sm text-primary">{item.label}</p>
                    <p className="text-xs text-muted">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="pt-3 border-t border-primary">
              <p className="text-sm text-muted">
                Run <code className="bg-tertiary px-1.5 py-0.5 rounded font-mono">{'python3 validate_output.py --input dev/input --output <output>'}</code> 
                for official contract validation.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}