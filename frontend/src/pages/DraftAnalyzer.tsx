import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { apiService } from '../services/api';
import '../App.css';

interface DraftPick {
  round?: number;
  pick?: number;
  team_key?: string;
  team_name?: string;
  manager?: string;
  team_id?: string;
  player_key?: string;
  player_name?: string;
  headshot_url?: string;
  position?: string;
  nhl_team?: string;
  rank?: number;
}

interface DraftAnalysis {
  draft_results: DraftPick[];
  best_picks: any[];
  worst_picks: any[];
  draft_grades: Record<string, any>;
  total_picks: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
}

const DraftAnalyzer: React.FC = () => {
  const { leagueKey } = useParams<{ leagueKey: string }>();
  const [analysis, setAnalysis] = useState<DraftAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 100;

  useEffect(() => {
    if (leagueKey) {
      const decodedKey = decodeURIComponent(leagueKey);
      loadAnalysis(decodedKey, currentPage);
    }
  }, [leagueKey, currentPage]);

  const loadAnalysis = async (key: string, page: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getDraftAnalysis(key, page, pageSize);
      setAnalysis(data);
    } catch (err: any) {
      console.error('Failed to load draft analysis:', err);
      setError(err?.message || 'Failed to load draft analysis');
    } finally {
      setLoading(false);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (analysis && currentPage < (analysis.total_pages || 1)) {
      setCurrentPage(currentPage + 1);
    }
  };

  if (loading) {
    return <div className="container"><div className="loading">Analyzing draft...</div></div>;
  }

  if (error) {
    return <div className="container"><div className="error">Error: {error}</div></div>;
  }

  if (!analysis) {
    return <div className="container"><div className="error">Failed to load analysis</div></div>;
  }

  const totalPages = analysis.total_pages || 1;

  return (
    <div className="container">
      <h1>Draft Analyzer for {leagueKey}</h1>

      <div className="card">
        <h2>Draft Results ({analysis.total_picks} total picks)</h2>
        
        {/* Pagination Controls */}
        <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <button 
              onClick={handlePrevPage} 
              disabled={currentPage === 1}
              style={{ marginRight: '10px', padding: '8px 16px' }}
            >
              ← Previous
            </button>
            <span style={{ margin: '0 10px' }}>
              Page {currentPage} of {totalPages}
            </span>
            <button 
              onClick={handleNextPage} 
              disabled={currentPage >= totalPages}
              style={{ marginLeft: '10px', padding: '8px 16px' }}
            >
              Next →
            </button>
          </div>
          <div style={{ color: '#666' }}>
            Showing picks {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, analysis.total_picks)}
          </div>
        </div>

        {analysis.draft_results.length === 0 ? (
          <p>No draft data available. This league may not have completed its draft yet.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="table" style={{ minWidth: '900px' }}>
              <thead>
                <tr>
                  <th style={{ width: '60px' }}>Pick</th>
                  <th style={{ width: '60px' }}>Rd</th>
                  <th style={{ width: '300px' }}>Player</th>
                  <th style={{ width: '100px' }}>Pos</th>
                  <th style={{ width: '80px' }}>NHL</th>
                  <th style={{ width: '80px' }}>Rank</th>
                  <th style={{ width: '200px' }}>Drafted By</th>
                </tr>
              </thead>
              <tbody>
                {analysis.draft_results.map((pick, idx) => (
                  <tr key={idx}>
                    <td><strong>{pick.pick || '-'}</strong></td>
                    <td>{pick.round || '-'}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {pick.headshot_url && (
                          <img 
                            src={pick.headshot_url} 
                            alt={pick.player_name || 'Player'} 
                            style={{ 
                              width: '40px', 
                              height: '40px', 
                              borderRadius: '50%',
                              objectFit: 'cover'
                            }}
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                        )}
                        <span>{pick.player_name || pick.player_key || '-'}</span>
                      </div>
                    </td>
                    <td>{pick.position || '-'}</td>
                    <td><strong>{pick.nhl_team || '-'}</strong></td>
                    <td>{pick.rank ? `#${pick.rank}` : '-'}</td>
                    <td>
                      <div style={{ fontSize: '0.9em' }}>
                        <div><strong>{pick.team_name || pick.team_key || '-'}</strong></div>
                        {pick.manager && (
                          <div style={{ color: '#666', fontSize: '0.9em' }}>({pick.manager})</div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls (Bottom) */}
        <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <button 
            onClick={handlePrevPage} 
            disabled={currentPage === 1}
            style={{ marginRight: '10px', padding: '8px 16px' }}
          >
            ← Previous
          </button>
          <span style={{ margin: '0 10px' }}>
            Page {currentPage} of {totalPages}
          </span>
          <button 
            onClick={handleNextPage} 
            disabled={currentPage >= totalPages}
            style={{ marginLeft: '10px', padding: '8px 16px' }}
          >
            Next →
          </button>
        </div>
      </div>

      {/* Placeholder sections for future enhancements */}
      {analysis.best_picks.length > 0 && (
        <div className="card">
          <h2>Best Value Picks</h2>
          <ul>
            {analysis.best_picks.map((player, idx) => (
              <li key={idx}>{player.name} (Drafted: {player.draft_position}, Current Rank: {player.current_rank})</li>
            ))}
          </ul>
        </div>
      )}

      {analysis.worst_picks.length > 0 && (
        <div className="card">
          <h2>Reaches / Busts</h2>
          <ul>
            {analysis.worst_picks.map((player, idx) => (
              <li key={idx}>{player.name} (Drafted: {player.draft_position}, Current Rank: {player.current_rank})</li>
            ))}
          </ul>
        </div>
      )}

      {Object.keys(analysis.draft_grades).length > 0 && (
        <div className="card">
          <h2>Team Draft Grades</h2>
          <ul>
            {Object.entries(analysis.draft_grades).map(([team, grade], idx) => (
              <li key={idx}><strong>{team}:</strong> {grade}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default DraftAnalyzer;
