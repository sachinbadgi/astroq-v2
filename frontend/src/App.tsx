import { useState, useEffect } from 'react';
import AuthPage from './components/auth/AuthPage';
import AppShell from './components/layout/AppShell';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('astroq_token');
    if (token) {
      setIsAuthenticated(true);
    }
  }, []);

  if (!isAuthenticated) {
    return <AuthPage onLogin={() => setIsAuthenticated(true)} />;
  }

  return <AppShell />;
}
