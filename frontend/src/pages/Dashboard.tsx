import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiService, League } from '../services/api';
import '../App.css';

const Dashboard: React.FC = () => {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLeagues();
  }, []);

  const loadLeagues = async () => {
    try {
      setLoading(true);
      const data = await apiService.getLeagues('nhl');
      setLeagues(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load leagues');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncLeague = async (leagueKey: string) => {
    try {
      await apiService.syncLeague(leagueKey);
      alert('League synced successfully!');
      loadLeagues();
    } catch (err: any) {
      alert('Failed to sync league: ' + err.message);
    }
  };

  if (loading) {
    return <div className="container"><div className="loading">Loading leagues...</div></div>;
  }

  if (error) {
    return <div className="container"><div className="error">{error}</div></div>;
  }

  return (
    <div className="container">
      <h1>My Leagues</h1>
      {leagues.length === 0 ? (
        <div className="card">
          <p>No leagues found. Make sure you're logged in and have access to Yahoo Fantasy Hockey leagues.</p>
        </div>
      ) : (
        <div className="leagues-grid">
          {leagues.map((league) => (
            <div key={league.league_key} className="card">
              <h2>{league.name || `League ${league.league_key}`}</h2>
              <p><strong>Season:</strong> {league.season || 'N/A'}</p>
              <p><strong>Game:</strong> {league.game_code.toUpperCase()}</p>
              <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
                <Link
                  to={`/league/${encodeURIComponent(league.league_key)}`}
                  className="btn btn-primary"
                >
                  View League
                </Link>
                <button
                  onClick={() => handleSyncLeague(league.league_key)}
                  className="btn btn-secondary"
                >
                  Sync Data
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;

