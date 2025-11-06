import React, { useEffect, useRef } from 'react';
import { apiService } from '../services/api';
import './Login.css';

interface LoginProps {
  onLogin: () => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const callbackProcessed = useRef(false);

  useEffect(() => {
    // Check if we're returning from OAuth callback
    // Only process once to prevent duplicate requests
    if (callbackProcessed.current) {
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code) {
      callbackProcessed.current = true;
      handleCallback(code, state || undefined);
    }
  }, []);

  const handleLogin = async () => {
    try {
      const { auth_url } = await apiService.login();
      window.location.href = auth_url;
    } catch (error) {
      console.error('Login failed:', error);
      alert('Failed to initiate login. Please try again.');
    }
  };

  const handleCallback = async (code: string, state?: string) => {
    try {
      await apiService.handleCallback(code, state);
      onLogin();
      window.history.replaceState({}, document.title, '/dashboard');
    } catch (error: any) {
      console.error('Callback failed:', error);
      const errorMessage = error?.message || 'Authentication failed. Please try again.';
      alert(`Authentication failed: ${errorMessage}`);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Fantasy Hockey Analyzer</h1>
        <p>Analyze your Yahoo Fantasy Hockey league with advanced trading insights and historical data.</p>
        <button onClick={handleLogin} className="btn btn-primary btn-login">
          Login with Yahoo
        </button>
      </div>
    </div>
  );
};

export default Login;

