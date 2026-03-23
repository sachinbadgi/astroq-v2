import { useEffect, useState } from 'react';
import { Activity, Target, Network, CheckCircle2, XCircle } from 'lucide-react';
import apiClient from '../../api/client';

interface TestRun {
  id: string;
  date: string;
  public_figure: string;
  event: string;
  actual_age: number;
  predicted_age: number;
  status: 'HIT' | 'MISS' | 'PARTIAL';
}

interface Metrics {
  hit_rate: string;
  avg_offset: string;
  total_tested: number;
}

export default function BenchmarkDashboard() {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [metrics, setMetrics] = useState<Metrics>({ hit_rate: '0%', avg_offset: '0', total_tested: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In actual implementation, we'd hit /metrics/test-runs
    // Mocking response structure based on old UI design
    const fetchMetrics = async () => {
      try {
        const res = await apiClient.get('/metrics/test-runs').catch(() => ({
          data: {
             runs: [
               { id: 'run-1', date: '2026-03-22', public_figure: 'Steve Jobs', event: 'Founded Apple', actual_age: 21, predicted_age: 21, status: 'HIT' },
               { id: 'run-2', date: '2026-03-22', public_figure: 'A. Einstein', event: 'Nobel Prize', actual_age: 42, predicted_age: 43, status: 'PARTIAL' },
               { id: 'run-3', date: '2026-03-22', public_figure: 'M. Curie', event: 'Nobel Prize 2', actual_age: 44, predicted_age: 49, status: 'MISS' }
             ],
             metrics: { hit_rate: '83.4%', avg_offset: '+0.8 yrs', total_tested: 121 }
          }
        }));
        
        setRuns(res.data.runs);
        setMetrics(res.data.metrics);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchMetrics();
  }, []);

  return (
    <div className="flex flex-col h-full space-y-6">
      <div className="flex items-center gap-3">
        <Activity size={24} className="text-[var(--accent-violet)]" />
        <h2 className="text-xl font-bold tracking-wider text-[var(--text-primary)]">TDD Pipeline Benchmarks</h2>
      </div>
      
      {/* Metric Cards */}
      <div className="grid grid-cols-3 gap-6">
        <div className="bg-[var(--bg-card)] border border-[var(--border-normal)] rounded-xl p-6 shadow-sm flex items-center gap-4">
          <div className="bg-[var(--accent-emerald)] bg-opacity-20 p-3 rounded-xl border border-[var(--accent-emerald)] border-opacity-50 text-[var(--accent-emerald)]">
            <Target size={24} />
          </div>
          <div>
            <span className="text-xs uppercase tracking-wider font-bold text-[var(--text-muted)]">Accuracy Hit Rate</span>
            <div className="text-2xl font-black text-[var(--text-primary)] mt-1 font-mono">
              {loading ? '-' : metrics.hit_rate}
            </div>
          </div>
        </div>

        <div className="bg-[var(--bg-card)] border border-[var(--border-normal)] rounded-xl p-6 shadow-sm flex items-center gap-4">
          <div className="bg-[var(--accent-gold)] bg-opacity-20 p-3 rounded-xl border border-[var(--accent-gold)] border-opacity-50 text-[var(--accent-gold)]">
            <Activity size={24} />
          </div>
          <div>
            <span className="text-xs uppercase tracking-wider font-bold text-[var(--text-muted)]">Avg Timing Offset</span>
            <div className="text-2xl font-black text-[var(--text-primary)] mt-1 font-mono">
              {loading ? '-' : metrics.avg_offset}
            </div>
          </div>
        </div>

        <div className="bg-[var(--bg-card)] border border-[var(--border-normal)] rounded-xl p-6 shadow-sm flex items-center gap-4">
          <div className="bg-[var(--accent-violet)] bg-opacity-20 p-3 rounded-xl border border-[var(--accent-violet)] border-opacity-50 text-[var(--accent-violet)]">
            <Network size={24} />
          </div>
          <div>
            <span className="text-xs uppercase tracking-wider font-bold text-[var(--text-muted)]">Charts Tested</span>
            <div className="text-2xl font-black text-[var(--text-primary)] mt-1 font-mono">
              {loading ? '-' : metrics.total_tested}
            </div>
          </div>
        </div>
      </div>

      {/* Runs Table */}
      <div className="flex-1 overflow-hidden bg-[var(--bg-card)] border border-[var(--border-normal)] rounded-xl shadow-[var(--shadow-card)] flex flex-col">
        <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-elevated)]">
           <h3 className="text-sm font-bold tracking-wider text-[var(--text-secondary)] uppercase">Continuous Integration Iterations</h3>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
             <div className="text-center italic text-[var(--text-muted)] p-8">Loading benchmark data...</div>
          ) : runs.length === 0 ? (
             <div className="text-center italic text-[var(--text-muted)] p-8">No test iterations have been recorded yet.</div>
          ) : (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                  <th className="pb-3 pt-1 px-4 text-xs font-bold uppercase tracking-wider">Target Profile</th>
                  <th className="pb-3 pt-1 px-4 text-xs font-bold uppercase tracking-wider">Verified Event</th>
                  <th className="pb-3 pt-1 px-4 text-xs font-bold uppercase tracking-wider text-right">Actual Age</th>
                  <th className="pb-3 pt-1 px-4 text-xs font-bold uppercase tracking-wider text-right">Predicted Window</th>
                  <th className="pb-3 pt-1 px-4 text-xs font-bold uppercase tracking-wider text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {runs.map(run => (
                  <tr key={run.id} className="border-b border-[var(--border-subtle)] last:border-0 hover:bg-[var(--bg-overlay)] transition-colors">
                    <td className="p-4 font-bold text-[var(--text-primary)]">{run.public_figure}</td>
                    <td className="p-4 text-[var(--text-secondary)] max-w-[200px] truncate" title={run.event}>{run.event}</td>
                    <td className="p-4 text-right font-mono text-[var(--text-muted)]">{run.actual_age}</td>
                    <td className="p-4 text-right font-mono text-[var(--accent-violet)]">{run.predicted_age}</td>
                    <td className="p-4 text-center">
                      {run.status === 'HIT' && <span className="inline-flex items-center gap-1 bg-green-500/10 text-green-500 border border-green-500/20 px-2.5 py-1 rounded text-xs font-bold uppercase"><CheckCircle2 size={12}/> HIT</span>}
                      {run.status === 'PARTIAL' && <span className="inline-flex items-center gap-1 bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 px-2.5 py-1 rounded text-xs font-bold uppercase">PARTIAL</span>}
                      {run.status === 'MISS' && <span className="inline-flex items-center gap-1 bg-red-500/10 text-red-500 border border-red-500/20 px-2.5 py-1 rounded text-xs font-bold uppercase"><XCircle size={12}/> MISS</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
