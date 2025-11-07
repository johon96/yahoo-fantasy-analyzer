import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import LeagueView from './pages/LeagueView';
import TradeAnalyzer from './pages/TradeAnalyzer';
import DraftAnalyzer from './pages/DraftAnalyzer';
import HistoricalView from './pages/HistoricalView';
import Login from './pages/Login';
import Navbar from './components/Navbar';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem('access_token');
    const userId = localStorage.getItem('user_id');
    setIsAuthenticated(!!(token && userId));
    setLoading(false);
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    // Clear all authentication data
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    
    // Clear debug data
    localStorage.removeItem('login_attempt');
    localStorage.removeItem('last_auth_url');
    localStorage.removeItem('last_login_error');
    
    setIsAuthenticated(false);
    
    // Show helpful message
    alert('Logged out successfully! If you want to switch Yahoo accounts, please also log out at login.yahoo.com');
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Router>
      <div className="App">
        {isAuthenticated && <Navbar onLogout={handleLogout} />}
        <Routes>
          <Route
            path="/auth/callback"
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard" />
              ) : (
                <Login onLogin={handleLogin} />
              )
            }
          />
          <Route
            path="/login"
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard" />
              ) : (
                <Login onLogin={handleLogin} />
              )
            }
          />
          {isAuthenticated ? (
            <>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/league/:leagueKey/trades" element={<TradeAnalyzer />} />
              <Route path="/league/:leagueKey/draft" element={<DraftAnalyzer />} />
              <Route path="/league/:leagueKey/history" element={<HistoricalView />} />
              <Route path="/league/:leagueKey" element={<LeagueView />} />
              <Route path="/" element={<Navigate to="/dashboard" />} />
            </>
          ) : (
            <Route path="*" element={<Navigate to="/login" />} />
          )}
        </Routes>
      </div>
    </Router>
  );
}

export default App;

