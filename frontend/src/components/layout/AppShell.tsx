import { useState, useEffect } from 'react';
import ProfileSidebar from './ProfileSidebar';
import GeneralChat from '../chat/GeneralChat';
import OracleChat from '../chat/OracleChat';
import NatalChart2D from '../chart/NatalChart2D';
import RemedyPanel from '../remedy/RemedyPanel';
import PredictionDashboard from '../prediction/PredictionDashboard';
import BenchmarkDashboard from '../benchmark/BenchmarkDashboard';
import apiClient from '../../api/client';

export default function AppShell() {
  const [activeTab, setActiveTab] = useState<'chat' | 'oracle' | '2d' | 'predict' | 'remedy' | 'benchmark'>('chat');
  const [chartData, setChartData] = useState<any>(null);
  const [activeChartId, setActiveChartId] = useState<number | null>(null);
  const currentUser = localStorage.getItem('astroq_user') || 'Guest';

  // Persistence: Load last active chart on mount
  useEffect(() => {
    const persistedId = localStorage.getItem('astroq_last_chart');
    if (persistedId) {
      handleLoadChart({ id: parseInt(persistedId, 10) } as any);
    }
  }, []);

  const handleLoadChart = async (chart: { id: number }) => {
    try {
      const res = await apiClient.get(`/lal-kitab/birth-charts/${chart.id}`);
      setChartData(res.data);
      setActiveChartId(chart.id);
      localStorage.setItem('astroq_last_chart', String(chart.id));
    } catch (err) {
      console.error("Failed to load chart", err);
    }
  };

  const logout = () => {
    localStorage.removeItem('astroq_token');
    localStorage.removeItem('astroq_user');
    window.location.reload();
  };

  return (
    <div className="app-container">
      <ProfileSidebar 
        onLoadChart={handleLoadChart} 
        onNewChart={() => setChartData(null)} 
        onLogout={logout}
        activeChartId={activeChartId}
        currentUser={currentUser}
      />

      <main className="main-stage">
        {/* Sub-navigation Header */}
        <header className="glass-panel" style={{ margin: '1rem', padding: '0.5rem', borderRadius: 'var(--radius-md)', display: 'flex', gap: '0.5rem', border: '1px solid var(--border-normal)' }}>
          {[
            { id: 'chat', label: 'General Chat' },
            { id: 'oracle', label: 'Premium Oracle' },
            { id: '2d', label: 'Natal 2D' },
            { id: 'predict', label: 'Predictions' },
            { id: 'remedy', label: 'Remedies' },
            { id: 'benchmark', label: 'Benchmark' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className="btn-tab"
              style={{
                background: activeTab === tab.id ? 'var(--bg-overlay)' : 'transparent',
                color: activeTab === tab.id ? 'var(--accent-violet)' : 'var(--text-secondary)',
                border: 'none',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {tab.label}
            </button>
          ))}
        </header>

        <div className="flex-1 overflow-auto p-6" style={{ height: 'calc(100% - 80px)' }}>
          {!chartData ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.5, fontStyle: 'italic' }}>
              Select or generate a chart in the sidebar to begin analysis.
            </div>
          ) : (
            <div className="animate-fade-in h-full">
              {activeTab === 'chat' && <GeneralChat chartData={chartData} />}
              {activeTab === 'oracle' && <OracleChat chartData={chartData} />}
              {activeTab === '2d' && <NatalChart2D chartData={chartData} />}
              {activeTab === 'predict' && <PredictionDashboard activeChartId={activeChartId} />}
              {activeTab === 'remedy' && <RemedyPanel chartData={chartData} />}
              {activeTab === 'benchmark' && <BenchmarkDashboard />}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
