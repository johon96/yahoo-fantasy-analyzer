import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { apiService, TradeAnalysis } from '../services/api';
import '../App.css';

const TradeAnalyzer: React.FC = () => {
  const { leagueKey } = useParams<{ leagueKey: string }>();
  const [analysis, setAnalysis] = useState<TradeAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (leagueKey) {
      const decodedKey = decodeURIComponent(leagueKey);
      loadAnalysis(decodedKey);
    }
  }, [leagueKey]);

  const loadAnalysis = async (key: string) => {
    try {
      setLoading(true);
      const data = await apiService.getTradeAnalysis(key);
      setAnalysis(data);
    } catch (error) {
      console.error('Failed to load trade analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="container"><div className="loading">Analyzing trades...</div></div>;
  }

  if (!analysis) {
    return <div className="container"><div className="error">Failed to load analysis</div></div>;
  }

  return (
    <div className="container">
      <h1>Trade Analyzer</h1>

      <div className="card">
        <h2>Overperforming Players</h2>
        <p>Players performing better than their projections</p>
        {analysis.overperformers.length === 0 ? (
          <p>No data available</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Player</th>
                <th>Position</th>
                <th>Projected</th>
                <th>Actual</th>
                <th>Differential</th>
              </tr>
            </thead>
            <tbody>
              {analysis.overperformers.map((player, idx) => (
                <tr key={idx}>
                  <td>{player.name || 'N/A'}</td>
                  <td>{player.position || '-'}</td>
                  <td>{player.projected || '-'}</td>
                  <td>{player.actual || '-'}</td>
                  <td style={{ color: 'green' }}>+{player.differential || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2>Underperforming Players</h2>
        <p>Players performing worse than their projections</p>
        {analysis.underperformers.length === 0 ? (
          <p>No data available</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Player</th>
                <th>Position</th>
                <th>Projected</th>
                <th>Actual</th>
                <th>Differential</th>
              </tr>
            </thead>
            <tbody>
              {analysis.underperformers.map((player, idx) => (
                <tr key={idx}>
                  <td>{player.name || 'N/A'}</td>
                  <td>{player.position || '-'}</td>
                  <td>{player.projected || '-'}</td>
                  <td>{player.actual || '-'}</td>
                  <td style={{ color: 'red' }}>{player.differential || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {analysis.recommendations.length > 0 && (
        <div className="card">
          <h2>Trade Recommendations</h2>
          <ul>
            {analysis.recommendations.map((rec, idx) => (
              <li key={idx}>{JSON.stringify(rec)}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default TradeAnalyzer;

