import React, { useState, useEffect } from 'react';
import VoiceAgent from './VoiceAgent';
import Login from './components/Login';

interface User {
  id: number;
  username: string;
  email: string;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  const getApiUrl = () => {
    const protocol = window.location.protocol;
    const host = window.location.host;
    return `${protocol}//${host}`;
  };

  // Check if user is already authenticated
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch(`${getApiUrl()}/auth/check`, {
          credentials: 'include', // Include cookies
        });
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          console.error('Auth check: Expected JSON but got:', contentType);
          setChecking(false);
          return;
        }
        
        const data = await response.json();
        if (data.authenticated) {
          setUser(data.user);
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        // Don't block the UI if auth check fails - just show login page
      } finally {
        setChecking(false);
      }
    };
    checkAuth();
  }, []);

  const handleLogin = (userData: User) => {
    setUser(userData);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${getApiUrl()}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (err) {
      console.error('Logout error:', err);
    }
    setUser(null);
  };

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div>Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div>
      <div className="bg-gray-800 text-white p-3 flex justify-between items-center shadow-md">
        <div className="flex items-center gap-3">
          <span className="font-medium">Logged in as: {user.email}</span>
          <span className="text-gray-400">({user.username})</span>
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm font-medium transition-colors"
        >
          Logout
        </button>
      </div>
      <VoiceAgent />
    </div>
  );
}

export default App;

