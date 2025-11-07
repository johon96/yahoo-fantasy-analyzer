import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService, League, Team, Player } from '../services/api';
import '../App.css';

const LeagueView: React.FC = () => {
  const { leagueKey } = useParams<{ leagueKey: string }>();
  const [league, setLeague] = useState<League | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (leagueKey) {
      const decodedKey = decodeURIComponent(leagueKey);
      console.log('Loading league with key:', decodedKey);
      loadLeagueData(decodedKey);
    }
  }, [leagueKey]);

  const loadLeagueData = async (key: string) => {
    try {
      setLoading(true);
      setError(null);
      console.log('Fetching league data for:', key);
      const [leagueData, teamsData] = await Promise.all([
        apiService.getLeague(key),
        apiService.getLeagueTeams(key),
      ]);
      console.log('League data received:', leagueData);
      console.log('Teams data received:', teamsData);
      setLeague(leagueData);
      setTeams(Array.isArray(teamsData) ? teamsData : []);
    } catch (err: any) {
      console.error('Failed to load league data:', err);
      setError(err?.message || 'Failed to load league data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="container"><div className="loading">Loading league...</div></div>;
  }

  if (error) {
    return <div className="container"><div className="error">Error: {error}</div></div>;
  }

  if (!league) {
    return <div className="container"><div className="error">League not found</div></div>;
  }

  const encodedKey = leagueKey ? encodeURIComponent(leagueKey) : '';

  return (
    <div className="container">
      <h1>{league.name || `League ${league.league_key}`}</h1>
      <p>Season: {league.season || 'N/A'}</p>

      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <Link
          to={`/league/${encodedKey}/trades`}
          className="btn btn-primary"
        >
          Trade Analyzer
        </Link>
        <Link
          to={`/league/${encodedKey}/draft`}
          className="btn btn-primary"
        >
          Draft Analyzer
        </Link>
        <Link
          to={`/league/${encodedKey}/history`}
          className="btn btn-primary"
        >
          Historical Data
        </Link>
      </div>

      <div className="card">
        <h2>Standings</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Team</th>
              <th>Manager</th>
              <th>W</th>
              <th>L</th>
              <th>T</th>
              <th>Points For</th>
              <th>Points Against</th>
            </tr>
          </thead>
          <tbody>
            {teams
              .sort((a, b) => (a.standing || 999) - (b.standing || 999))
              .map((team) => (
                <tr key={team.id}>
                  <td>{team.standing || '-'}</td>
                  <td>{team.name || `Team ${team.team_key}`}</td>
                  <td>{team.manager || '-'}</td>
                  <td>{team.wins}</td>
                  <td>{team.losses}</td>
                  <td>{team.ties}</td>
                  <td>{team.points_for.toFixed(2)}</td>
                  <td>{team.points_against.toFixed(2)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LeagueView;

