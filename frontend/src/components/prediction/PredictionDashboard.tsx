import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  AlertTriangle, 
  Calendar, 
  MinusCircle, 
  PlusCircle, 
  Zap, 
  ShieldCheck, 
  Info,
  Loader2,
  ChartNoAxesColumnIncreasing
} from 'lucide-react';
import apiClient from '../../api/client';

export interface PredictionDashboardProps {
  activeChartId: number | null;
}

export default function PredictionDashboard({ activeChartId }: PredictionDashboardProps) {
  const [predictions, setPredictions] = useState<any[]>([]);
  const [planets, setPlanets] = useState<Record<string, any>>({});
  const [grammarScores, setGrammarScores] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeChartId) return;

    setLoading(true);
    let isMounted = true;

    apiClient.get(`/lal-kitab/birth-charts/${activeChartId}`)
      .then(res => {
        if (!isMounted) return;
        
        // Ensure we handle both potential formats (the mock server might wrap things)
        const pipelineData = res.data.pipeline_output || {
          predictions: [],
          enriched_planets: {}
        };
        
        setPredictions(pipelineData.predictions || []);
        setPlanets(pipelineData.enriched_planets || {});
        setGrammarScores(pipelineData.grammar_marks || []);
      })
      .catch(err => {
        console.error("Failed to load dashboard data", err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, [activeChartId]);

  if (loading) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1.5rem', opacity: 0.8 }}>
        <div style={{ position: 'relative' }}>
          <Loader2 size={48} className="animate-spin text-gradient-violet" />
          <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap size={16} className="text-gradient-pink" />
          </div>
        </div>
        <p style={{ fontSize: '0.875rem', fontWeight: 600, letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
          ANALYZING PLANETARY STRENGTHS & GRAMMAR RULES...
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '400px 1fr', gap: '1.5rem', height: '100%', overflow: 'hidden' }}>
      
      {/* Left Column: Strengths & Grammar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', overflowY: 'auto', paddingRight: '0.5rem' }}>
        
        {/* Planetary Core Strength Panel */}
        <div className="card" style={{ background: 'var(--bg-card)', padding: '1.5rem' }}>
          <h3 style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
            <ChartNoAxesColumnIncreasing size={16} style={{ color: 'var(--accent-violet)' }} /> Planetary Core Strength
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {Object.entries(planets).sort((a,b) => b[1].strength_total - a[1].strength_total).map(([name, data]) => {
              const percentage = (data.strength_total / 6.0) * 100;
              return (
                <div key={name} style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>{name}</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{data.strength_total.toFixed(1)} / 6.0</span>
                  </div>
                  <div style={{ height: '6px', width: '100%', background: 'var(--bg-deep)', borderRadius: 'var(--radius-full)', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ 
                      height: '100%', width: `${percentage}%`, 
                      background: `linear-gradient(90deg, var(--accent-violet), ${data.strength_total > 3 ? 'var(--accent-emerald)' : 'var(--accent-pink)'})`,
                      boxShadow: '0 0 10px rgba(139, 92, 246, 0.4)'
                    }}></div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.2rem' }}>
                    {data.sleeping_status === 'Sleeping' && <span style={{ fontSize: '0.65rem', background: 'var(--bg-elevated)', padding: '1px 6px', borderRadius: '4px', border: '1px solid var(--border-normal)', color: 'var(--text-muted)' }}>Sleeping</span>}
                    {data.dharmi_status === 'Dharmi' && <span style={{ fontSize: '0.65rem', background: 'var(--accent-emerald)', backgroundOpacity: 0.1, color: 'var(--accent-emerald)', padding: '1px 6px', borderRadius: '4px', border: '1px solid var(--accent-emerald)' }}>Dharmi</span>}
                    {data.dhoka_graha && <span style={{ fontSize: '0.65rem', background: 'var(--accent-rose)', color: 'white', padding: '1px 6px', borderRadius: '4px' }}>Dhoka Graha</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Lal Kitab Grammar Marks */}
        <div className="card" style={{ background: 'var(--bg-card)', padding: '1.5rem' }}>
           <h3 style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
            <AlertTriangle size={16} style={{ color: 'var(--accent-pink)' }} /> Lal Kitab Grammar Marks
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {grammarScores.map((g, i) => (
              <div key={i} style={{ padding: '0.75rem', background: 'var(--bg-deep)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-normal)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{g.rule}</div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Impact: {g.impact}</div>
                </div>
                <div style={{ fontSize: '0.875rem', fontWeight: 800, color: g.score > 0 ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                  {g.score > 0 ? `+${g.score}` : g.score}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Column: Life Event Predictions */}
      <div style={{ overflowY: 'auto', paddingRight: '0.5rem' }}>
        <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '0.05em' }} className="text-gradient-violet">LIFE EVENT PREDICTIONS</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Chronological probabilities derived from natal and annual timing engine v2.0</p>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {predictions.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '3rem', fontStyle: 'italic', color: 'var(--text-muted)' }}>
              No definitive life events detected with high confidence at this time.
            </div>
          ) : (
            predictions.map((p, i) => (
              <div key={i} className="card animate-fade-in" style={{ display: 'grid', gridTemplateColumns: 'min-content 1fr 140px', gap: '1.5rem', alignItems: 'center' }}>
                
                {/* Age Badge */}
                <div style={{ 
                  width: '60px', height: '60px', borderRadius: 'var(--radius-md)', background: 'var(--bg-deep)', border: '1px solid var(--border-normal)', 
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' 
                }}>
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Age</span>
                  <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-violet)' }}>{p.peak_age}</span>
                </div>

                {/* Content */}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                    <span style={{ 
                      fontSize: '0.6rem', fontWeight: 800, textTransform: 'uppercase', padding: '2px 8px', borderRadius: 'var(--radius-full)',
                      background: p.polarity === 'benefic' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                      color: p.polarity === 'benefic' ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                      border: `1px solid ${p.polarity === 'benefic' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)'}`
                    }}>
                      {p.domain} • {p.event_type}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Calendar size={10} /> Window: {p.age_window[0]}-{p.age_window[1]}
                    </span>
                  </div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>{p.prediction_text}</h4>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {p.source_planets.map((pl: string) => (
                      <span key={pl} style={{ fontSize: '0.65rem', color: 'var(--text-muted)', padding: '2px 6px', background: 'var(--bg-elevated)', borderRadius: '4px' }}>{pl}</span>
                    ))}
                  </div>
                </div>

                {/* Score / Probability */}
                <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }} className="text-gradient-violet">
                    {(p.probability * 100).toFixed(0)}%
                  </div>
                  <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    {p.confidence.replace('_', ' ')}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
