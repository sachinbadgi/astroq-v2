import { useState, useEffect } from 'react';
import { RefreshCw, Zap, Activity } from 'lucide-react';
import apiClient from '../../api/client';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export interface RemedyPanelProps {
  chartData: any;
}

interface MatrixRow {
  aspect: string;
  baseline_health: number;
  simulated_health: number;
  delta: string;
}

export default function RemedyPanel({ chartData }: RemedyPanelProps) {
  const [activePlanet, setActivePlanet] = useState<string>('Sun');
  const [activeTab, setActiveTab] = useState<'matrix' | 'projection'>('matrix');
  const [isShifted, setIsShifted] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const [matrixData, setMatrixData] = useState<MatrixRow[]>([]);
  const [timelineData, setTimelineData] = useState<any[]>([]);
  const [commitment, setCommitment] = useState(50);

  const planets = Object.keys(chartData?.chart_0?.planets_in_houses || chartData?.planets_in_houses || { Sun: {} });

  const fetchSimulation = async () => {
    if (!isShifted) {
      setMatrixData([]);
      setTimelineData([]);
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post('/simulate-remedies', {
        chart_data: chartData,
        proposed_shifts: { [activePlanet]: -1 },
        strategic_commitment: commitment / 100
      });

      setMatrixData(res.data.simulation_matrix || []);
      setTimelineData(res.data.lifetime_timeline || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSimulation();
  }, [activePlanet, isShifted, commitment]);

  return (
    <div className="animate-fade-in" style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      
      {/* Simulation Header */}
      <div className="glass-panel" style={{ padding: '1.25rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ background: 'var(--bg-elevated)', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--accent-pink)' }}>
            <Zap size={20} style={{ color: 'var(--accent-pink)' }} />
          </div>
          <div>
            <h2 style={{ fontSize: '0.9rem', fontWeight: 800, letterSpacing: '0.1em' }} className="text-gradient-pink">REMEDY QUANTUM SIMULATOR</h2>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>PRE-DETERMINISTIC KARMIC SHIFT ANALYSIS</p>
          </div>
        </div>

        <div style={{ display: 'flex', background: 'var(--bg-deep)', padding: '0.25rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-normal)' }}>
          {['matrix', 'projection'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              style={{
                padding: '0.5rem 1.25rem', fontSize: '0.75rem', fontWeight: 700, borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer', transition: 'all 0.2s',
                background: activeTab === tab ? 'var(--bg-card)' : 'transparent',
                color: activeTab === tab ? 'var(--text-primary)' : 'var(--text-muted)',
                boxShadow: activeTab === tab ? 'var(--shadow-card)' : 'none'
              }}
            >
              {tab.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '300px 1fr', gap: '1.5rem', overflow: 'hidden' }}>
        
        {/* Sidebar Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Planet Selector */}
          <div className="card" style={{ padding: '1.25rem' }}>
            <label style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '1rem', display: 'block' }}>Target Celestial</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
              {planets.map(p => (
                <button
                  key={p}
                  onClick={() => setActivePlanet(p)}
                  style={{
                    padding: '0.5rem', fontSize: '0.7rem', fontWeight: 600, borderRadius: 'var(--radius-sm)', border: '1px solid', transition: 'all 0.2s', cursor: 'pointer',
                    background: activePlanet === p ? 'var(--accent-violet-glow)' : 'var(--bg-deep)',
                    borderColor: activePlanet === p ? 'var(--accent-violet)' : 'var(--border-normal)',
                    color: activePlanet === p ? 'var(--text-primary)' : 'var(--text-muted)'
                  }}
                >
                  {p.substring(0, 3)}
                </button>
              ))}
            </div>
          </div>

          {/* Shift Toggle */}
          <div className="card" style={{ padding: '1.25rem', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <label style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '1rem', display: 'block' }}>Reality Branch</label>
            
            <button
              onClick={() => setIsShifted(!isShifted)}
              className="btn-primary"
              style={{ 
                width: '100%', padding: '1rem', background: isShifted ? 'var(--accent-emerald)' : 'linear-gradient(135deg, var(--accent-pink), #ec4899)',
                boxShadow: isShifted ? '0 0 20px rgba(16, 185, 129, 0.3)' : '0 4px 15px rgba(244, 114, 182, 0.3)'
              }}
            >
              {loading ? <RefreshCw className="animate-spin" size={18} /> : (isShifted ? 'BRANCH ACTIVE' : 'INITIATE SHIFT')}
            </button>

            <div style={{ marginTop: '2rem', opacity: isShifted ? 1 : 0.3, transition: 'opacity 0.3s' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Commitment</span>
                <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--accent-pink)' }}>{commitment}%</span>
              </div>
              <input 
                type="range" min="0" max="100" value={commitment} 
                onChange={e => setCommitment(parseInt(e.target.value))} 
                style={{ width: '100%', accentColor: 'var(--accent-pink)', cursor: 'pointer' }}
              />
              <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '1rem', lineHeight: '1.5' }}>
                Strategic commitment scales the persistence of the remedy impact across the lifetime timeline.
              </p>
            </div>

            <div style={{ marginTop: 'auto', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-normal)', background: 'var(--bg-deep)' }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.5rem' }}>Active Logic</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)', fontStyle: 'italic' }}>
                {isShifted ? `Mitigating negative ${activePlanet} vibrations via additive baseline refinement.` : "Standing by for quantum observation."}
              </div>
            </div>
          </div>
        </div>

        {/* Main Visualization Pane */}
        <div className="glass-panel" style={{ position: 'relative', overflow: 'hidden', padding: '1.5rem' }}>
          {!isShifted ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', gap: '1.5rem' }}>
              <div style={{ padding: '2rem', background: 'rgba(255,255,255,0.02)', borderRadius: '50%', border: '1px solid var(--border-normal)' }}>
                <Activity size={48} style={{ color: 'var(--border-bright)' }} />
              </div>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, marginBottom: '0.5rem' }}>SIMULATION STANDBY</h3>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', maxWidth: '300px' }}>
                  Please initiate a shift to observe the delta between baseline and remedial realities.
                </p>
              </div>
            </div>
          ) : (
            <div className="animate-fade-in" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              {activeTab === 'matrix' ? (
                <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '1.5rem', letterSpacing: '0.05em' }}>MATRIX REALITY DELTA</h3>
                  <div style={{ flex: 1, overflowY: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border-normal)' }}>
                          <th style={{ padding: '1rem', fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Aspect</th>
                          <th style={{ padding: '1rem', fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Baseline</th>
                          <th style={{ padding: '1rem', fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: 'center' }}>Shift</th>
                          <th style={{ padding: '1rem', fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: 'right' }}>Simulated</th>
                        </tr>
                      </thead>
                      <tbody>
                        {matrixData.map((row, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            <td style={{ padding: '1rem', fontSize: '0.9rem', fontWeight: 600 }}>{row.aspect}</td>
                            <td style={{ padding: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{row.baseline_health}</td>
                            <td style={{ padding: '1rem', textAlign: 'center' }}>
                              <span style={{ 
                                fontSize: '0.75rem', fontWeight: 800, padding: '2px 8px', borderRadius: '4px',
                                background: row.delta.startsWith('+') ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                                color: row.delta.startsWith('+') ? 'var(--accent-emerald)' : 'var(--accent-rose)'
                              }}>
                                {row.delta}
                              </span>
                            </td>
                            <td style={{ padding: '1rem', textAlign: 'right', fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                              {row.simulated_health}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '2rem', letterSpacing: '0.05em' }}>LIFETIME PROBABILITY PROJECTION</h3>
                  <div style={{ flex: 1, minHeight: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={timelineData}>
                        <defs>
                          <linearGradient id="colorProb" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--accent-pink)" stopOpacity={0.5}/>
                            <stop offset="95%" stopColor="var(--accent-pink)" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="age" stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} />
                        <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-normal)', borderRadius: '12px', color: 'var(--text-primary)' }}
                          itemStyle={{ color: 'var(--accent-pink)', fontWeight: 700 }}
                        />
                        <Area type="monotone" dataKey="probability" stroke="var(--accent-pink)" strokeWidth={3} fillOpacity={1} fill="url(#colorProb)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
