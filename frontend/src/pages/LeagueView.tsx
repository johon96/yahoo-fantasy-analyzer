import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService, League, Team, Player } from '../services/api';
import '../App.css';

const LeagueView: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const [league, setLeague] = useState<League | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (leagueId) {
      loadLeagueData(parseInt(leagueId));
    }
  }, [leagueId]);

  const loadLeagueData = async (id: number) => {
    try {
      setLoading(true);
      const [leagueData, teamsData] = await Promise.all([
        apiService.getLeague(id),
        apiService.getLeagueTeams(id),
      ]);
      setLeague(leagueData);
      setTeams(teamsData);
    } catch (error) {
      console.error('Failed to load league data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="container"><div className="loading">Loading league...</div></div>;
  }

  if (!league) {
    return <div className="container"><div className="error">League not found</div></div>;
  }

  return (
    <div className="container">
      <h1>{league.name || `League ${league.league_id}`}</h1>
      <p>Season: {league.season || 'N/A'}</p>

      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <Link
          to={`/league/${leagueId}/trades`}
          className="btn btn-primary"
        >
          Trade Analyzer
        </Link>
        <Link
          to={`/league/${leagueId}/history`}
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

