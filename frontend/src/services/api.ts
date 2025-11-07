import axios from 'axios';

// Use relative path to go through Vite proxy (works for both HTTP and HTTPS)
const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  const userId = localStorage.getItem('user_id');
  if (token && userId) {
    config.headers.Authorization = `Bearer ${userId}`;
  }
  return config;
});

// Add error interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.detail || error.response.data?.message || error.message;
      console.error('API Error:', message, error.response.status);
      return Promise.reject(new Error(message));
    } else if (error.request) {
      // Request was made but no response received
      console.error('Network Error:', 'No response from server');
      return Promise.reject(new Error('Network error: Could not reach server'));
    } else {
      // Something else happened
      console.error('Error:', error.message);
      return Promise.reject(error);
    }
  }
);

export interface League {
  id: number;
  league_key: string;
  name?: string;
  season?: number;
  game_code: string;
  league_type?: string;
}

export interface Team {
  id: number;
  team_key: string;
  name?: string;
  manager?: string;
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  points_against: number;
  standing?: number;
}

export interface Player {
  id: number;
  player_key: string;
  name?: string;
  position?: string;
  team?: string;
  status?: string;
  stats?: Record<string, any>;
}

export interface TradeAnalysis {
  overperformers: any[];
  underperformers: any[];
  recommendations: any[];
}

export interface DraftAnalysis {
  draft_results: any[];
  best_picks: any[];
  worst_picks: any[];
  draft_grades: Record<string, any>;
  total_picks: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
}

export const apiService = {
  // Auth
  async login() {
    const response = await api.get('/auth/login');
    return response.data;
  },

  async handleCallback(code: string, state?: string) {
    const response = await api.get('/auth/callback', {
      params: { code, state },
    });
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user_id', response.data.user_id.toString());
    }
    return response.data;
  },

  // Leagues
  async getLeagues(gameCode: string = 'nhl') {
    const response = await api.get('/leagues', {
      params: { game_code: gameCode },
    });
    return response.data;
  },

  async getLeague(leagueKey: string) {
    const response = await api.get(`/league/${leagueKey}`);
    return response.data;
  },

  async syncLeague(leagueKey: string) {
    const response = await api.post(`/league/${leagueKey}/sync`);
    return response.data;
  },

  // Teams
  async getLeagueTeams(leagueKey: string) {
    const response = await api.get(`/league/${leagueKey}/teams`);
    return response.data;
  },

  // Players
  async getLeaguePlayers(leagueKey: string, start: number = 0, count: number = 25) {
    const response = await api.get(`/league/${leagueKey}/players`, {
      params: { start, count },
    });
    return response.data;
  },

  // Analysis
  async getTradeAnalysis(leagueKey: string): Promise<TradeAnalysis> {
    const response = await api.get(`/league/${leagueKey}/analysis/trades`);
    return response.data;
  },

  async getDraftAnalysis(leagueKey: string, page: number = 1, pageSize: number = 100): Promise<DraftAnalysis> {
    const response = await api.get(`/league/${leagueKey}/analysis/draft`, {
      params: { page, page_size: pageSize }
    });
    return response.data;
  },

  async getLeagueHistory(leagueKey: string, seasons?: number) {
    const response = await api.get(`/league/${leagueKey}/history`, {
      params: { seasons },
    });
    return response.data;
  },

  async getPlayerPerformance(playerKey: string, leagueKey: string) {
    const response = await api.get(`/player/${playerKey}/performance`, {
      params: { league_key: leagueKey },
    });
    return response.data;
  },
};

export default api;

