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
        const data = await response.json();
        if (data.authenticated) {
          setUser(data.user);
        }
      } catch (err) {
        console.error('Auth check failed:', err);
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
      <div className="bg-gray-800 text-white p-2 flex justify-between items-center">
        <span>Logged in as: {user.email}</span>
        <button
          onClick={handleLogout}
          className="px-4 py-1 bg-red-600 hover:bg-red-700 rounded text-sm"
        >
          Logout
        </button>
      </div>
      <VoiceAgent />
    </div>
  );
}

export default App;

