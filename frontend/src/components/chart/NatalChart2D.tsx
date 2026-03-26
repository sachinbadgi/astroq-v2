import { useState } from 'react';
import { ChevronDown, ChevronUp, Info, Activity } from 'lucide-react';

interface NatalChart2DProps {
  chartData: any;
}

// ── Spec-exact Geometry ──────────────────────────
const S = 540; 
const C = S / 2; 

const T_: [number, number] = [C, 0];       
const R_: [number, number] = [S, C];       
const B_: [number, number] = [C, S];       
const L_: [number, number] = [0, C];       
const O: [number, number] = [C, C];        
const P_TL: [number, number] = [C / 2, C / 2];       
const P_TR: [number, number] = [S - C / 2, C / 2];   
const P_BR: [number, number] = [S - C / 2, S - C / 2]; 
const P_BL: [number, number] = [C / 2, S - C / 2];   

const HOUSE_POLYS: Record<number, [number, number][]> = {
  1: [T_, P_TR, O, P_TL], 4: [L_, P_TL, O, P_BL], 7: [B_, P_BL, O, P_BR], 10: [R_, P_TR, O, P_BR],
  2: [[0, 0], T_, P_TL], 3: [[0, 0], P_TL, L_], 5: [[0, S], L_, P_BL], 6: [[0, S], P_BL, B_],
  8: [[S, S], B_, P_BR], 9: [[S, S], P_BR, R_], 11: [[S, 0], P_TR, R_], 12: [[S, 0], T_, P_TR],
};

const PLANET_COLORS: Record<string, string> = {
  Sun: 'var(--accent-gold)', Moon: '#f1f5f9', Mars: 'var(--accent-rose)', Mercury: '#86efac',
  Jupiter: 'var(--accent-gold)', Venus: '#fef08a', Saturn: 'var(--accent-indigo)',
  Rahu: '#64748b', Ketu: '#a8a29e', Asc: 'var(--accent-pink)', ASC: 'var(--accent-pink)', Lagna: 'var(--accent-pink)'
};

const ABBREVIATIONS: Record<string, string> = {
  Sun: 'Su', Moon: 'Mo', Mars: 'Ma', Mercury: 'Me', Jupiter: 'Ju', Venus: 'Ve', Saturn: 'Sa', Rahu: 'Ra', Ketu: 'Ke',
  Asc: 'ASC', ASC: 'ASC', Lagna: 'ASC'
};

function getCentroid(house: number): [number, number] {
  const pts = HOUSE_POLYS[house];
  return [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length];
}

function getPlanetOffsets(count: number, cx: number, cy: number): [number, number][] {
  if (count === 1) return [[cx, cy]];
  const step = 28; 
  const cols = Math.ceil(Math.sqrt(count));
  return Array.from({ length: count }, (_, i) => [
    cx + (i % cols - (cols - 1) / 2) * step,
    cy + (Math.floor(i / cols) - (Math.ceil(count / cols) - 1) / 2) * step,
  ] as [number, number]);
}

function aspectColor(rel: string): string {
  const r = rel?.toLowerCase();
  return r === 'friend' ? '#86efac' : r === 'enemy' ? '#fb7185' : '#6366f1';
}

export default function NatalChart2D({ chartData }: NatalChart2DProps) {
  const [legendOpen, setLegendOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'chart' | 'details'>('chart');

  const chart = chartData?.chart_0 || chartData || {};
  const enriched = chartData?.pipeline_output?.enriched_planets || {};
  const planetsInHouses = chart?.planets_in_houses || {};

  const byHouse: Record<number, any[]> = {};
  for (let i = 1; i <= 12; i++) byHouse[i] = [];

  Object.entries(planetsInHouses).forEach(([name, data]: [string, any]) => {
    const house = typeof data === 'object' ? data.house : data;
    if (house >= 1 && house <= 12) {
      const pInfo = enriched[name] || (typeof data === 'object' ? data : {});
      const isMasnui = pInfo.is_masnui || name.toLowerCase().includes('masnui') || name.toLowerCase().includes('artificial');
      // Extract base planet (e.g., "Masnui Mars (Auspicious)" -> "Mars")
      const baseName = name.replace(/Masnui |Artificial /g, '').split(' ')[0].split('(')[0].trim();
      const abbr = isMasnui ? `m${ABBREVIATIONS[baseName] || baseName.substring(0, 2)}` : (ABBREVIATIONS[name] || name.substring(0, 2));
      
      byHouse[house].push({ 
        name, 
        house, 
        ...pInfo, 
        isMasnui,
        abbr, 
        color: PLANET_COLORS[baseName] || PLANET_COLORS[name] || 'var(--text-secondary)' 
      });
    }
  });

  return (
    <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', border: '1px solid var(--border-normal)', background: 'var(--bg-card)' }}>
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border-normal)', background: 'rgba(0,0,0,0.2)' }}>
        <button role="tab" onClick={() => setActiveTab('chart')} style={{ flex: 1, padding: '1rem', border: 'none', background: activeTab === 'chart' ? 'var(--bg-overlay)' : 'transparent', color: activeTab === 'chart' ? 'var(--accent-violet)' : 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', cursor: 'pointer', borderBottom: activeTab === 'chart' ? '2px solid var(--accent-violet)' : 'none' }}>
          <Activity size={14} style={{ marginRight: '0.5rem' }} /> 2D Cosmic Grid
        </button>
        <button role="tab" onClick={() => setActiveTab('details')} style={{ flex: 1, padding: '1rem', border: 'none', background: activeTab === 'details' ? 'var(--bg-overlay)' : 'transparent', color: activeTab === 'details' ? 'var(--accent-violet)' : 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', cursor: 'pointer', borderBottom: activeTab === 'details' ? '2px solid var(--accent-violet)' : 'none' }}>
          <Info size={14} style={{ marginRight: '0.5rem' }} /> Analysis
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
        {activeTab === 'chart' ? (
          <div style={{ padding: '2rem', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ width: 'min(500px, 90%)', aspectRatio: '1', position: 'relative' }}>
              <svg viewBox={`0 0 ${S} ${S}`} style={{ width: '100%', height: '100%', display: 'block' }}>
                <defs>
                  <filter id="planetGlow"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
                </defs>

                {/* Aspect Lines - Must be below planets */}
                {Object.values(byHouse).flat().map(p => (p.aspects || []).map((asp: any, ai: number) => {
                  const hStart = p.house;
                  const hEnd = enriched[asp.target]?.house || chart.planets_in_houses?.[asp.target]?.house;
                  if (!hStart || !hEnd) return null;
                  const s = getCentroid(hStart);
                  const e2 = getCentroid(hEnd);
                  
                  const mx = (s[0] + e2[0]) / 2, my = (s[1] + e2[1]) / 2;
                  const bx = mx + (C - mx) * 0.4, by = my + (C - my) * 0.4;
                  const col = aspectColor(asp.relationship);
                  const t = 0.85;
                  const ax = (1-t)**2*s[0] + 2*(1-t)*t*bx + t**2*e2[0];
                  const ay = (1-t)**2*s[1] + 2*(1-t)*t*by + t**2*e2[1];
                  const tx = 2*(1-t)*(bx-s[0]) + 2*t*(e2[0]-bx), ty = 2*(1-t)*(by-s[1]) + 2*t*(e2[1]-by);
                  const angle = Math.atan2(ty, tx) * 180 / Math.PI;
                  return (
                    <g key={`${p.name}-${asp.target}-${ai}`} opacity="0.6">
                      <path d={`M ${s[0]} ${s[1]} Q ${bx} ${by} ${e2[0]} ${e2[1]}`} fill="none" stroke={col} strokeWidth="1" strokeDasharray="4 3" />
                      <polygon points="0,-3 6,0 0,3" fill={col} transform={`translate(${ax},${ay}) rotate(${angle})`} />
                    </g>
                  );
                }))}

                {Array.from({ length: 12 }, (_, i) => {
                  const h = i + 1;
                  const [cx, cy] = getCentroid(h);
                  const occupants = byHouse[h];
                  const offsets = getPlanetOffsets(occupants.length, cx, cy);
                  
                  return (
                    <g key={h} data-testid={`house-${h}`}>
                      <polygon points={HOUSE_POLYS[h].map(p => p.join(',')).join(' ')} fill="rgba(139, 92, 246, 0.02)" stroke="var(--border-normal)" strokeWidth="1.2" />
                      <text x={cx} y={cy - (occupants.length > 0 ? 20 : 0)} textAnchor="middle" dominantBaseline="middle" fill="var(--text-muted)" fontSize="11" fontWeight="600" opacity="0.25" fontFamily="monospace">{h}</text>
                      
                      {occupants.map((p, idx) => {
                        const [px, py] = offsets[idx];
                        const r = 18; // Base radius for Masnui ring
                        return (
                          <g key={p.name} filter="url(#planetGlow)">
                            {p.isMasnui && (
                              <ellipse 
                                cx={px} cy={py} 
                                rx={r} ry={r * 0.4} 
                                fill="none" 
                                stroke={p.color} 
                                strokeWidth="1.2" 
                                strokeOpacity="0.8"
                                transform={`rotate(-15, ${px}, ${py})`}
                              />
                            )}
                            <text x={px} y={py + 6} textAnchor="middle" fill={p.color} fontSize={p.isMasnui ? "14" : "17"} fontWeight="800" style={{ fontFamily: 'JetBrains Mono, monospace', textShadow: `0 0 12px ${p.color}AA` }}>{p.abbr}</text>
                          </g>
                        );
                      })}
                    </g>
                  );
                })}

                <rect x="0" y="0" width={S} height={S} fill="none" stroke="var(--border-normal)" strokeWidth="1" />
              </svg>
            </div>
          </div>
        ) : (
          <div style={{ padding: '2rem', width: '100%', height: '100%', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-normal)', color: 'var(--text-muted)' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem' }}>Planet</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem' }}>House</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem' }}>Status</th>
                  <th style={{ textAlign: 'right', padding: '0.75rem' }}>Strength</th>
                </tr>
              </thead>
              <tbody>
                {Object.values(byHouse).flat().sort((a,b) => (a.house-b.house)).map(p => (
                  <tr key={p.name} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '0.75rem', color: p.color, fontWeight: 700 }}>{p.name}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'center', color: 'var(--text-primary)' }}>{p.house}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'center', color: p.isMasnui ? 'var(--accent-violet)' : (p.sleeping_status ? 'var(--accent-pink)' : 'var(--accent-emerald)') }}>
                      {p.isMasnui ? 'MASNUI' : (p.sleeping_status || 'Awake')}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: 'var(--text-primary)' }}>
                      {p.strength_total ? p.strength_total.toFixed(1) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ position: 'absolute', bottom: '1.5rem', right: '1.5rem', zIndex: 10 }}>
          <button aria-label="Toggle Legend" onClick={() => setLegendOpen(!legendOpen)} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-normal)', borderRadius: 'var(--radius-full)', padding: '0.4rem 0.8rem', color: 'var(--text-secondary)', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
            {legendOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />} Legend
          </button>
          {legendOpen && (
            <div data-testid="legend-panel" className="glass-panel animate-fade-in" style={{ position: 'absolute', bottom: '2.5rem', right: 0, width: '200px', padding: '1rem', border: '1px solid var(--border-normal)', zIndex: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                {Object.entries(ABBREVIATIONS).filter(([k]) => k !== 'Asc' && k !== 'Lagna' && k !== 'ASC').map(([name, abbr]) => (
                  <div key={name} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.7rem' }}>
                    <span style={{ color: PLANET_COLORS[name], fontWeight: 700 }}>{abbr}</span>
                    <span style={{ color: 'var(--text-muted)' }}>{name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
