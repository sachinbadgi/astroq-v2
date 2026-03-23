import React, { useState } from 'react';
import apiClient from '../../api/client';
import { Loader2, Plus, Sparkles, MapPin } from 'lucide-react';

interface LocationChoice {
  display_name: string;
  latitude: number;
  longitude: number;
  utc_offset: string;
  timezone: string;
}

interface ChartFormProps {
  onChartGenerated: (chartId: number) => void;
}

export default function ChartForm({ onChartGenerated }: ChartFormProps) {
  const [clientData, setClientData] = useState({ name: "", dob: "", tob: "", place: "", gender: "Male", chart_system: "kp" });
  const [selectedLocation, setSelectedLocation] = useState<LocationChoice | null>(null);
  const [locationOptions, setLocationOptions] = useState<LocationChoice[]>([]);
  const [isSearchingLocation, setIsSearchingLocation] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handlePlaceBlur = async () => {
    if (!clientData.place) return;
    setIsSearchingLocation(true);
    try {
      const res = await apiClient.post('/search-location', { place_name: clientData.place });
      if (res.data.locations && res.data.locations.length > 0) {
        if (res.data.locations.length === 1) {
          setSelectedLocation(res.data.locations[0]);
          setClientData(prev => ({ ...prev, place: res.data.locations[0].display_name }));
        } else {
          setLocationOptions(res.data.locations);
        }
      }
    } catch (err) {
      console.error("Location search failed", err);
    } finally {
      setIsSearchingLocation(false);
    }
  };

  const handleGenerateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientData.name || !clientData.dob || !clientData.tob || (!selectedLocation && locationOptions.length > 0)) {
      setError("Please fill all fields and wait for location to resolve");
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const payload = {
        name: clientData.name,
        dob: clientData.dob,
        tob: clientData.tob,
        pob: clientData.place,
        lat: selectedLocation?.latitude || 0.0,
        lon: selectedLocation?.longitude || 0.0,
        gender: clientData.gender,
        chart_system: clientData.chart_system
      };

      const response = await apiClient.post('/lal-kitab/generate-birth-chart', payload);

      if (response.data && response.data.id) {
        onChartGenerated(response.data.id);
      } else {
        setError(`Error: ${response.data.message || "Unknown error occurred"}`);
      }
    } catch (err: any) {
      setError(`Error: ${err.response?.data?.detail?.[0]?.msg || err.message || String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card" style={{ padding: '1rem', background: 'var(--bg-card)', border: '1px solid var(--border-normal)' }}>
      <h2 style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Plus size={12} style={{ color: 'var(--accent-violet)' }} /> Initialize Baseline
      </h2>

      <form onSubmit={handleGenerateSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '0.5rem' }}>
           <div>
            <label style={{ fontSize: '9px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', marginLeft: '4px', marginBottom: '4px', display: 'block' }}>Name</label>
            <input type="text" placeholder="Consultant Name" required 
              className="input-field" 
              value={clientData.name} onChange={e => setClientData(prev => ({ ...prev, name: e.target.value }))} />
          </div>
          <div>
            <label style={{ fontSize: '9px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', marginLeft: '4px', marginBottom: '4px', display: 'block' }}>Gender</label>
            <select 
              value={clientData.gender} 
              onChange={e => setClientData(prev => ({ ...prev, gender: e.target.value }))}
              className="input-field"
              style={{ padding: '0.65rem 0.5rem' }}
            >
              <option value="Male">M</option>
              <option value="Female">F</option>
              <option value="Other">O</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: '9px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', marginLeft: '4px', marginBottom: '4px', display: 'block' }}>Style</label>
            <select 
              value={clientData.chart_system} 
              onChange={e => setClientData(prev => ({ ...prev, chart_system: e.target.value }))}
              className="input-field"
              style={{ padding: '0.65rem 0.5rem' }}
            >
              <option value="kp">KP</option>
              <option value="vedic">VED</option>
            </select>
          </div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
          <div>
            <label style={{ fontSize: '9px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', marginLeft: '4px', marginBottom: '4px', display: 'block' }}>Birth Date</label>
            <input type="date" required 
              className="input-field" style={{ colorScheme: 'dark' }}
              value={clientData.dob} onChange={e => setClientData(prev => ({ ...prev, dob: e.target.value }))} />
          </div>
          <div>
            <label style={{ fontSize: '9px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', marginLeft: '4px', marginBottom: '4px', display: 'block' }}>Time</label>
            <input type="time" required 
              className="input-field" style={{ colorScheme: 'dark' }}
              value={clientData.tob} onChange={e => setClientData(prev => ({ ...prev, tob: e.target.value }))} />
          </div>
        </div>

        <div style={{ position: 'relative' }}>
          <label style={{ fontSize: '9px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', marginLeft: '4px', marginBottom: '4px', display: 'block' }}>Birth Place</label>
          <div style={{ position: 'relative' }}>
            <input type="text" placeholder="City, Country" required 
              className="input-field" style={{ paddingLeft: '2.25rem' }}
              value={clientData.place} 
              onBlur={handlePlaceBlur} 
              onChange={e => { setClientData(prev => ({ ...prev, place: e.target.value })); setSelectedLocation(null); setLocationOptions([]); }} />
            <MapPin size={14} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          </div>
            
          {isSearchingLocation && (
            <div style={{ position: 'absolute', right: '0.75rem', top: '2.2rem' }}>
              <Loader2 size={12} className="animate-spin text-gradient-violet" />
            </div>
          )}
        </div>

        {locationOptions.length > 0 && !selectedLocation && (
          <div className="glass-panel" style={{ position: 'absolute', zIndex: 100, width: '100%', left: 0, marginTop: '5rem', maxHeight: '150px', overflowY: 'auto', padding: '0.5rem' }}>
            {locationOptions.map((loc, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => { setSelectedLocation(loc); setClientData(prev => ({ ...prev, place: loc.display_name })); setLocationOptions([]); }}
                style={{ width: '100%', textAlign: 'left', padding: '0.5rem', background: 'transparent', border: 'none', color: 'var(--text-primary)', fontSize: '0.75rem', cursor: 'pointer', borderBottom: '1px solid var(--border-normal)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-overlay)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {loc.display_name}
              </button>
            ))}
          </div>
        )}

        {error && <p style={{ fontSize: '0.7rem', color: 'var(--accent-rose)', fontStyle: 'italic' }}>{error}</p>}

        <button type="submit" disabled={isLoading} className="btn-primary" style={{ marginTop: '0.5rem', height: '42px' }}>
          {isLoading ? <Loader2 className="animate-spin" size={18} /> : (
            <>
              <Sparkles size={16} />
              <span>Forge Cosmic Chart</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
