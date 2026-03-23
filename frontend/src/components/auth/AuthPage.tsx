import React, { useState } from 'react';
import { Moon, Sparkles, Wand2, LogIn, UserPlus, ShieldAlert } from 'lucide-react';
import apiClient from '../../api/client';

interface AuthPageProps {
  onLogin: () => void;
}

export default function AuthPage({ onLogin }: AuthPageProps) {
  const [authMode, setAuthMode] = useState<"LOGIN" | "REGISTER">("LOGIN");
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (authMode === "REGISTER") {
        await apiClient.post('/register', { username, password });
        setAuthMode("LOGIN");
        setError("Registration successful! Please login.");
        setPassword("");
      } else {
        const res = await apiClient.post('/login', { username, password });
        localStorage.setItem('astroq_token', res.data.access_token);
        localStorage.setItem('astroq_user', username);
        onLogin();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "The cosmos denies entry. Check your sign.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem',
      background: 'radial-gradient(circle at center, #1a1830 0%, #05040a 100%)',
      position: 'relative', overflow: 'hidden'
    }}>
      {/* Background Decorative Elements */}
      <div style={{ position: 'absolute', top: '10%', left: '10%', width: '300px', height: '300px', background: 'var(--accent-violet)', filter: 'blur(150px)', opacity: 0.1, zIndex: 0 }}></div>
      <div style={{ position: 'absolute', bottom: '10%', right: '10%', width: '300px', height: '300px', background: 'var(--accent-pink)', filter: 'blur(150px)', opacity: 0.1, zIndex: 0 }}></div>

      <div className="glass-panel animate-fade-in" style={{ width: '100%', maxWidth: '440px', padding: '3rem 2.5rem', zIndex: 10, border: '1px solid rgba(255,255,255,0.05)' }}>
        
        {/* Logo Section */}
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div style={{ display: 'inline-flex', padding: '1rem', background: 'var(--bg-elevated)', borderRadius: '24px', border: '1px solid var(--border-normal)', marginBottom: '1.5rem', boxShadow: 'var(--shadow-glow-violet)' }}>
            <Moon className="text-gradient-violet" size={40} />
          </div>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 900, letterSpacing: '0.15em', marginBottom: '0.5rem' }}>
            ASTRO<span className="text-gradient-pink">Q</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 500, letterSpacing: '0.05em' }}>
            ENGINEERING YOUR KARMIC BLUEPRINT
          </p>
        </div>

        {/* Form Section */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '10px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', marginLeft: '4px', marginBottom: '6px' }}>Cosmic Identifier</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text" required value={username} onChange={(e) => setUsername(e.target.value)}
                className="input-field" placeholder="e.g. Oracle_Alpha"
                style={{ paddingLeft: '1rem', height: '48px', fontSize: '1rem' }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '10px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--text-muted)', marginLeft: '4px', marginBottom: '6px' }}>Astral Key</label>
            <input
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="input-field" placeholder="••••••••"
              style={{ paddingLeft: '1rem', height: '48px', fontSize: '1rem' }}
            />
          </div>

          {error && (
            <div style={{ 
              padding: '1rem', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.75rem',
              background: error.includes('successful') ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
              color: error.includes('successful') ? 'var(--accent-emerald)' : 'var(--accent-rose)',
              border: `1px solid ${error.includes('successful') ? 'var(--accent-emerald)' : 'var(--accent-rose)'}`
            }}>
              <ShieldAlert size={16} />
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary" style={{ height: '54px', fontSize: '1rem', marginTop: '1rem', borderRadius: 'var(--radius-md)' }}>
            {loading ? <RefreshCw className="animate-spin" size={20} /> : (
              <>
                {authMode === "LOGIN" ? <LogIn size={20} /> : <UserPlus size={20} />}
                <span>{authMode === "LOGIN" ? "ACCESS PORTAL" : "MANIFEST ACCOUNT"}</span>
              </>
            )}
          </button>
        </form>

        <div style={{ marginTop: '2.5rem', textAlign: 'center' }}>
          <button
            onClick={() => { setAuthMode(authMode === "LOGIN" ? "REGISTER" : "LOGIN"); setError(""); }}
            style={{ 
              background: 'transparent', border: 'none', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer',
              color: 'var(--text-secondary)', transition: 'color 0.2s'
            }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-violet)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            {authMode === "LOGIN" ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={14} /> New to AstroQ? Manifest one.
              </span>
            ) : "Already part of the cosmos? Log in."}
          </button>
        </div>
      </div>
    </div>
  );
}
