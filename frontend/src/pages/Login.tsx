import React, { useEffect, useRef, useState } from 'react';
import { apiService } from '../services/api';
import './Login.css';

interface LoginProps {
  onLogin: () => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const callbackProcessed = useRef(false);
  const [debugMode, setDebugMode] = useState(false);
  const [authUrl, setAuthUrl] = useState<string>('');

  useEffect(() => {
    // Check if we're returning from OAuth callback
    // Only process once to prevent duplicate requests
    if (callbackProcessed.current) {
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const error = urlParams.get('error');
    const errorDescription = urlParams.get('error_description');
    const state = urlParams.get('state');

    if (error) {
      callbackProcessed.current = true;
      handleOAuthError(error, errorDescription);
    } else if (code) {
      callbackProcessed.current = true;
      handleCallback(code, state || undefined);
    }
  }, []);

  const handleLogin = async () => {
    console.log('=== LOGIN BUTTON CLICKED ===');
    // Store in localStorage so we can check after page reload
    localStorage.setItem('login_attempt', new Date().toISOString());
    
    try {
      console.log('Step 1: Initiating login API call...');
      const response = await apiService.login();
      console.log('Step 2: Received response:', JSON.stringify(response, null, 2));
      
      if (!response) {
        console.error('Step 2 ERROR: Response is null/undefined');
        throw new Error('No response received from server');
      }
      
      if (!response.auth_url) {
        console.error('Step 2 ERROR: No auth_url in response');
        throw new Error('No auth URL received from server');
      }
      
      console.log('Step 3: Auth URL received:', response.auth_url);
      localStorage.setItem('last_auth_url', response.auth_url);
      
      if (debugMode) {
        // Debug mode: don't redirect, just show the URL
        setAuthUrl(response.auth_url);
        alert('Debug mode: Check the auth URL on the page. Open it manually in a new tab.');
        return;
      }
      
      console.log('Step 4: About to redirect window.location.href...');
      
      // Try to redirect
      window.location.href = response.auth_url;
      
      console.log('Step 5: Redirect command executed (if you see this, redirect may have failed)');
    } catch (error) {
      console.error('=== LOGIN ERROR ===');
      console.error('Error type:', error?.constructor?.name);
      console.error('Error message:', error instanceof Error ? error.message : String(error));
      console.error('Full error:', error);
      localStorage.setItem('last_login_error', String(error));
      alert(`Failed to initiate login: ${error instanceof Error ? error.message : 'Unknown error'}. Please check the browser console for details.`);
    }
  };

  const handleOAuthError = (error: string, errorDescription: string | null) => {
    console.error('OAuth error:', error, errorDescription);
    
    let userMessage = 'Authentication failed. ';
    if (error === 'access_denied') {
      userMessage += 'You denied access to the application. Please try again and click "Allow" to continue.';
    } else {
      userMessage += `Error: ${errorDescription || error}. Please try again.`;
    }
    
    alert(userMessage);
    // Clean up URL
    window.history.replaceState({}, document.title, '/');
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
      // Clean up URL and allow retry
      window.history.replaceState({}, document.title, '/');
    }
  };

  const handleClearData = () => {
    localStorage.clear();
    alert('All stored data cleared! You can now log in fresh.');
    window.location.reload();
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Fantasy Hockey Analyzer</h1>
        <p>Analyze your Yahoo Fantasy Hockey league with advanced trading insights and historical data.</p>
        <button onClick={handleLogin} className="btn btn-primary btn-login">
          Login with Yahoo
        </button>
        <div style={{ marginTop: '20px' }}>
          <label style={{ fontSize: '14px', cursor: 'pointer' }}>
            <input 
              type="checkbox" 
              checked={debugMode}
              onChange={(e) => setDebugMode(e.target.checked)}
              style={{ marginRight: '8px' }}
            />
            Debug Mode (show URL instead of redirecting)
          </label>
        </div>
        {authUrl && (
          <div style={{ marginTop: '20px', padding: '10px', background: '#f0f0f0', borderRadius: '4px' }}>
            <strong>Auth URL:</strong>
            <div style={{ wordBreak: 'break-all', fontSize: '11px', marginTop: '5px' }}>
              <a href={authUrl} target="_blank" rel="noopener noreferrer">{authUrl}</a>
            </div>
          </div>
        )}
        <div style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
          Debug: Check browser console (F12) for detailed logs<br/>
          Last attempt: {localStorage.getItem('login_attempt')}<br/>
          {localStorage.getItem('last_login_error') && (
            <span style={{ color: 'red' }}>Last error: {localStorage.getItem('last_login_error')}</span>
          )}
        </div>
        <div style={{ marginTop: '10px' }}>
          <button 
            onClick={handleClearData}
            style={{ 
              fontSize: '12px', 
              padding: '5px 10px',
              background: '#f44336',
              color: 'white',
              border: 'none',
              borderRadius: '3px',
              cursor: 'pointer'
            }}
          >
            Clear Stored Data & Start Fresh
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;

