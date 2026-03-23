import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, BrainCircuit, Terminal, CheckCircle2, Loader2, Send } from 'lucide-react';
import { useSSE } from '../../hooks/useSSE';

export default function OracleChat({ chartData }: { chartData: any }) {
  const [input, setInput] = useState('');
  const [hasQueried, setHasQueried] = useState(false);
  const { data: streamEvents, error, isStreaming, startStream } = useSSE();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [streamEvents]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    setHasQueried(true);
    startStream('/ask-chart-premium/stream', {
      question: input,
      chart_data: chartData
    });
  };

  const getStepIcon = (step: string) => {
    switch (step) {
      case 'ANALYZE': return <Terminal size={14} className="text-gradient-pink" />;
      case 'REASON': return <BrainCircuit size={14} style={{ color: 'var(--accent-indigo)' }} />;
      default: return <CheckCircle2 size={14} style={{ color: 'var(--accent-emerald)' }} />;
    }
  };

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <header style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-normal)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ background: 'var(--bg-elevated)', padding: '0.6rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--accent-violet)' }}>
            <BrainCircuit size={20} className="text-gradient-violet" />
          </div>
          <div>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 800, letterSpacing: '0.1em' }}>PREMIUM ORACLE ANALYSIS</h2>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500 }}>REINFORCEMENT LEARNING REASONING ENGINE</p>
          </div>
        </div>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {!hasQueried ? (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', maxWidth: '400px', margin: '0 auto', gap: '1.5rem' }}>
             <div style={{ width: '80px', height: '80px', borderRadius: '50%', border: '2px dashed var(--accent-violet)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <BrainCircuit size={40} className="text-gradient-violet" />
            </div>
            <p style={{ fontSize: '1rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              The Oracle uses <strong className="text-gradient-violet">multi-step reasoning</strong> to break down complex life questions. It examines planetary strengths, grammar rules, and transits before determining the final answer.
            </p>
            <div style={{ width: '100%', display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
              <input
                className="input-field"
                placeholder="Consult the Oracle (Deep Analysis)..."
                value={input}
                onChange={e => setInput(e.target.value)}
                style={{ borderRadius: 'var(--radius-md)', height: '52px' }}
              />
              <button 
                onClick={handleSend}
                disabled={!input.trim()}
                className="btn-primary"
                style={{ width: '52px', height: '52px', padding: 0, borderRadius: 'var(--radius-md)', flexShrink: 0 }}
                title="Consult Oracle"
              >
                <Send size={20} />
              </button>
            </div>
          </div>
        ) : (
          <div ref={scrollRef} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="card" style={{ borderStyle: 'dashed', borderOpacity: 0.5, marginBottom: '1rem' }}>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Query:</span> {input}
              </p>
            </div>

            {streamEvents.map((evt, idx) => (
              <div 
                key={idx} 
                className="animate-fade-in card" 
                style={{ 
                  display: 'flex', gap: '1rem', 
                  borderLeft: evt.step === 'CONCLUDE' ? '4px solid var(--accent-emerald)' : '1px solid var(--border-normal)',
                  background: evt.step === 'CONCLUDE' ? 'rgba(16, 185, 129, 0.05)' : 'var(--bg-card)'
                }}
              >
                <div style={{ marginTop: '0.2rem' }}>{getStepIcon(evt.step)}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.65rem', fontWeight: 800, color: 'var(--text-muted)', marginBottom: '0.25rem', letterSpacing: '0.1em' }}>
                    {evt.step}
                  </div>
                  <div style={{ fontSize: '0.9rem', color: evt.step === 'CONCLUDE' ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: evt.step === 'CONCLUDE' ? 600 : 400 }}>
                    {evt.content}
                  </div>
                </div>
              </div>
            ))}

            {isStreaming && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                <Loader2 size={16} className="animate-spin" />
                <span>Oracle is meditating on your chart...</span>
              </div>
            )}

            {error && (
              <div className="card" style={{ color: 'var(--accent-rose)', borderColor: 'var(--accent-rose)', opacity: 0.8 }}>
                {error}
              </div>
            )}
            
            {!isStreaming && streamEvents.some(e => e.step === 'CONCLUDE') && (
              <button 
                onClick={() => { setHasQueried(false); setInput(''); }}
                style={{ alignSelf: 'center', marginTop: '2rem', background: 'transparent', border: 'none', color: 'var(--accent-violet)', fontSize: '0.875rem', cursor: 'pointer', fontWeight: 600 }}
              >
                + New Consultation
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
