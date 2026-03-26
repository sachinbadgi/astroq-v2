import React, { useEffect, useState } from 'react';
import { User, Clock, Moon, Calendar, Sparkles, LogOut, Trash2 } from 'lucide-react';
import ChartForm from '../chart/ChartForm';
import apiClient from '../../api/client';

export interface SavedChart {
  id: number;
  client_name: string;
  birth_date: string;
  birth_time: string;
  birth_place?: string;
  created_at: string;
}

interface ProfileSidebarProps {
  onLoadChart: (chart: SavedChart) => void;
  onNewChart: () => void;
  onLogout: () => void;
  activeChartId: number | null;
  currentUser: string;
}

export default function ProfileSidebar({
  onLoadChart,
  onNewChart,
  onLogout,
  activeChartId,
  currentUser
}: ProfileSidebarProps) {
  const [savedCharts, setSavedCharts] = useState<SavedChart[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSavedCharts = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/lal-kitab/birth-charts');
      setSavedCharts(res.data || []);
    } catch {
      setSavedCharts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteChart = async (e: React.MouseEvent, chartId: number) => {
    e.stopPropagation();
    console.log("handleDeleteChart triggered for ID:", chartId);
    if (!window.confirm("Are you sure you want to delete this profile?")) {
      console.log("Delete cancelled by user");
      return;
    }
    
    try {
      console.log("Sending DELETE request to /lal-kitab/birth-charts/" + chartId);
      const res = await apiClient.delete(`/lal-kitab/birth-charts/${chartId}`);
      console.log("Delete response received:", res.data);
      await fetchSavedCharts();
      if (activeChartId === chartId) {
        onNewChart();
      }
    } catch (err) {
      console.error("Failed to delete chart", err);
    }
  };

  useEffect(() => {
    fetchSavedCharts();
  }, []);

  const handleChartGenerated = async (chartId: number) => {
    await fetchSavedCharts();
    onLoadChart({ id: chartId } as any); 
  };

  return (
    <aside className="sidebar">
      <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-normal)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Moon className="text-gradient-violet" size={28} />
        <h1 style={{ fontSize: '1.5rem', fontWeight: 800, letterSpacing: '0.1em' }} className="text-gradient-violet">
          ASTROQ
        </h1>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        <ChartForm onChartGenerated={handleChartGenerated} />

        <div>
          <h2 style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Calendar size={12} style={{ color: 'var(--accent-pink)' }} /> Saved Baselines
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {loading ? (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>Loading cosmic data...</p>
            ) : savedCharts.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '1rem', background: 'rgba(255,255,255,0.02)' }}>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No profiles generated yet.</p>
              </div>
            ) : (
              savedCharts.map((chart) => (
                <div
                  key={chart.id}
                  onClick={() => onLoadChart(chart)}
                  className={`card ${activeChartId === chart.id ? 'active-profile' : ''}`}
                  style={{
                    padding: '0.75rem 1rem',
                    textAlign: 'left',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    position: 'relative',
                    borderColor: activeChartId === chart.id ? 'var(--accent-violet)' : 'var(--border-normal)',
                    background: activeChartId === chart.id ? 'var(--bg-overlay)' : 'var(--bg-card)'
                  }}
                >
                  <div style={{ background: 'var(--bg-deep)', padding: '0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-normal)' }}>
                    <User size={16} style={{ color: activeChartId === chart.id ? 'var(--accent-violet)' : 'var(--text-secondary)' }} />
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {chart.client_name}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Clock size={8} /> {chart.birth_date}
                    </div>
                  </div>
                  
                  <button
                    type="button"
                    onClick={(e) => handleDeleteChart(e, chart.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '0.4rem',
                      borderRadius: 'var(--radius-sm)',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-rose)')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div style={{ padding: '1.25rem', background: 'var(--bg-card)', borderTop: '1px solid var(--border-normal)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ padding: '0.4rem', border: '1px solid var(--accent-pink)', borderRadius: 'var(--radius-full)' }}>
            <Sparkles size={14} className="text-gradient-pink" />
          </div>
          <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>{currentUser}</span>
        </div>
        <button 
          onClick={onLogout} 
          style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-rose)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
        >
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
}
