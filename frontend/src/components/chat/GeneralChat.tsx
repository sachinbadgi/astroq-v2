import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Sparkles, MessageSquare, Bot } from 'lucide-react';
import apiClient from '../../api/client';

export default function GeneralChat({ chartData }: { chartData: any }) {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await apiClient.post('/ask-chart', {
        question: input,
        chart_data: chartData
      });
      setMessages(prev => [...prev, { role: 'bot', content: res.data.answer }]);
    } catch {
      setMessages(prev => [...prev, { role: 'bot', content: "The cosmos is clouded. Please try again later." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <header style={{ padding: '1rem 1.5rem', borderBottom: '1px solid var(--border-normal)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <MessageSquare size={20} style={{ color: 'var(--accent-indigo)' }} />
          <div>
            <h2 style={{ fontSize: '0.9rem', fontWeight: 700, letterSpacing: '0.05em' }}>COSMIC CONSULTATION</h2>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Interactive Natural Language Analysis</p>
          </div>
        </div>
        <div style={{ padding: '0.4rem 0.8rem', background: 'var(--bg-overlay)', borderRadius: 'var(--radius-full)', border: '1px solid var(--border-subtle)', fontSize: '0.7rem', fontWeight: 600 }}>
          <span className="text-gradient-violet">AI Engine v2.0 Active</span>
        </div>
      </header>

      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {messages.length === 0 ? (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '2rem' }}>
            <div style={{ background: 'var(--bg-elevated)', padding: '1.5rem', borderRadius: 'var(--radius-full)', marginBottom: '1.5rem', border: '1px solid var(--border-normal)' }}>
              <Sparkles size={40} className="text-gradient-violet" />
            </div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>The Stars are Listening</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', maxWidth: '300px' }}>
              Chart loaded successfully. What would you like to know about your destiny?
            </p>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%', display: 'flex', gap: '0.75rem', flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
              <div style={{ 
                width: '32px', height: '32px', borderRadius: 'var(--radius-sm)', backgroundColor: m.role === 'user' ? 'var(--accent-indigo)' : 'var(--bg-elevated)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--border-normal)', flexShrink: 0 
              }}>
                {m.role === 'user' ? <User size={16} color="white" /> : <Bot size={16} className="text-gradient-violet" />}
              </div>
              <div style={{ 
                padding: '1rem', borderRadius: 'var(--radius-md)', 
                background: m.role === 'user' ? 'var(--accent-violet-glow)' : 'var(--bg-card)',
                border: '1px solid',
                borderColor: m.role === 'user' ? 'var(--accent-violet)' : 'var(--border-normal)',
                color: 'var(--text-primary)', fontSize: '0.875rem', lineHeight: '1.6'
              }}>
                {m.content}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bot size={16} className="text-gradient-violet" />
            </div>
            <div style={{ background: 'var(--bg-card)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-normal)' }}>
              <div style={{ display: 'flex', gap: '4px' }}>
                <div style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%' }}></div>
                <div style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%' }}></div>
                <div style={{ width: '6px', height: '6px', background: 'var(--text-muted)', borderRadius: '50%' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={{ padding: '1.5rem', background: 'rgba(0,0,0,0.2)', borderTop: '1px solid var(--border-normal)' }}>
        <div style={{ position: 'relative', display: 'flex', gap: '0.75rem' }}>
          <input
            className="input-field"
            style={{ paddingRight: '3.5rem', borderRadius: 'var(--radius-md)' }}
            placeholder="Ask the cosmos about career, health, or karma..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSend()}
          />
          <button 
            onClick={handleSend} 
            disabled={!input.trim() || loading}
            className="btn-primary"
            style={{ width: '48px', height: '48px', padding: 0, borderRadius: 'var(--radius-md)', flexShrink: 0 }}
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}
