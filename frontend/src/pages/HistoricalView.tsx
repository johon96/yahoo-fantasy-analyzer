import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { apiService } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import '../App.css';

const HistoricalView: React.FC = () => {
  const { leagueKey } = useParams<{ leagueKey: string }>();
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (leagueKey) {
      const decodedKey = decodeURIComponent(leagueKey);
      loadHistory(decodedKey);
    }
  }, [leagueKey]);

  const loadHistory = async (key: string) => {
    try {
      setLoading(true);
      const data = await apiService.getLeagueHistory(key);
      setHistory(data);
    } catch (error) {
      console.error('Failed to load historical data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="container"><div className="loading">Loading historical data...</div></div>;
  }

  return (
    <div className="container">
      <h1>Historical League Data</h1>
      
      {history.length === 0 ? (
        <div className="card">
          <p>No historical data available. Historical data will be populated as you sync league data across multiple seasons.</p>
        </div>
      ) : (
        <div className="card">
          <h2>League Performance Over Time</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="season" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="average_points" stroke="#8884d8" name="Avg Points" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="card">
        <h2>Season-by-Season Breakdown</h2>
        {history.map((season, idx) => (
          <div key={idx} style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '4px' }}>
            <h3>Season {season.season}</h3>
            <p><strong>Total Teams:</strong> {season.league_stats?.total_teams || 'N/A'}</p>
            <p><strong>Average Points:</strong> {season.league_stats?.average_team_points?.toFixed(2) || 'N/A'}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HistoricalView;

