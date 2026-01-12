# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Yahoo Fantasy Hockey Analyzer - Export tool and optional web interface for analyzing Yahoo Fantasy leagues.

**Primary Use Case:** The `export_players.py` script generates comprehensive CSV files (player stats, draft data, standings) that are manually uploaded to Google Sheets for analysis.

**Secondary Use Case:** Web app provides a browser interface for viewing league data, draft analysis, and trade recommendations.

**Tech Stack:**
- Python 3.9+ with yfpy (Yahoo Fantasy Python library), FastAPI, SQLAlchemy
- React 18+ with TypeScript, Vite, Recharts (for web interface)
- Database: SQLite (minimal usage - mostly for session caching)
- Auth: Yahoo OAuth2

## Development Commands

### CSV Export (Primary Tool)

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Interactive mode - prompts you to choose from your leagues
python export_players.py

# Direct mode - specify league key
python export_players.py 465.l.34948

# Custom output filename
python export_players.py 465.l.34948 --output my_league_2025.csv
```

This generates two CSV files:
- `<league_key>_analysis.csv` - Comprehensive player data (500+ players)
- `<league_key>_standings.csv` - League standings with head-to-head category stats

### Backend Web Server (Optional)

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install

# Run development server (default: http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Configuration

Create `backend/.env` with Yahoo API credentials:

```env
YAHOO_CLIENT_ID=your_client_id
YAHOO_CLIENT_SECRET=your_client_secret
YAHOO_REDIRECT_URI=http://localhost:5173/auth/callback
DATABASE_URL=sqlite:///./fantasy_hockey.db
SECRET_KEY=your_secret_key_here
```

Register your app at [Yahoo Developer Network](https://developer.yahoo.com/apps/) to get credentials.

## Architecture

### CSV Export Script (`export_players.py`)

**This is the main tool.** It's a standalone script that:

1. **Authenticates** with Yahoo OAuth (reuses token from web app or launches browser OAuth)
2. **Fetches comprehensive data:**
   - Draft results (all picks with team/player info)
   - All teams with manager names
   - Top 500 players sorted by fantasy points via direct API calls
   - Player stats (Goals, Assists, Points, PIM, SOG, Hits, Blocks, Wins, Saves, etc.)
   - Ownership data (current team vs drafted team - tracks trades)
   - Yahoo's aggregate draft data (ADP, % drafted across all leagues)
   - League standings with category breakdowns
3. **Exports to CSV** with all enriched data ready for Google Sheets analysis
4. **Also exports standings** with head-to-head category stats to a separate CSV file

**Key patterns:**
- Fetches players in batches of 25 (Yahoo API limit) up to 1500 players
- Uses direct XML API for player data with custom stat ID parsing
- Handles bytes → string decoding (common Yahoo API issue)
- Distinguishes "current team" (after trades) from "drafted team" (original)
- Calculates derived stats (Points = G+A, Save % = SV/(SV+GA))
- Position-aware stat selection (GS for goalies, GP for skaters)
- Includes Yahoo Player ID for easy lookups and VLOOKUP operations
- Dynamically detects league stat categories from league settings
- Season detection via game ID mapping (e.g., "465" → 2025 NHL season)

**Player Analysis CSV Columns:**
Player Name, Player ID (Yahoo Player Key), Position, NHL Team, Fantasy Points, Current Team, Current Owner, Drafted Team, Drafted By, Draft Round, Draft Pick, ADP, Pct Drafted, Games Played (GP for skaters / GS for goalies), Goals, Assists, Points, PIM, SOG, Hits, Blocks, Wins, Saves, Save %, GA, Shutouts, Pct Owned

**Standings CSV Columns:**
Rank, Team Name, Manager, Wins, Losses, Ties, Win %, Points For, Points Against, Playoff Seed, G, A, PIM, SOG, HIT, BLK, W, GA, SV, SHO

Stats are ordered by position (skaters first, then goalies):
- **Skater Stats (columns 11-16):** G, A, PIM, SOG, HIT, BLK
- **Goalie Stats (columns 17-20):** W, GA, SV, SHO

You can add merged header rows in Google Sheets to group them visually.

See `backend/EXPORT_PLAYERS.md` for detailed documentation.

### Backend Web App Structure

- **`app/main.py`**: FastAPI application entry point with CORS configuration
- **`app/api/routes.py`**: API endpoints for leagues, teams, players, and analysis
- **`app/yahoo_api.py`**: Yahoo API client wrapper with hybrid approach:
  - Direct REST API calls for basic operations (leagues, standings)
  - YFPY integration for complex operations (draft results, transactions, player stats)
  - OAuth token injection to use existing authentication with YFPY
- **`app/models.py`**: SQLAlchemy ORM models (User, League, Team, Player, Draft, etc.)
- **`app/database.py`**: Database session management
- **`app/config.py`**: Pydantic settings with environment variable loading
- **`app/analyzers/`**: Analysis modules (trade, draft, performance) - mostly placeholder implementations

### Authentication Flow

1. Frontend initiates OAuth via `/api/auth/login` (gets Yahoo auth URL)
2. User authorizes at Yahoo, redirects back to `/auth/callback` with code
3. Backend exchanges code for access token at `/api/auth/callback`
4. Backend stores user data in JSON file (not database - see `app/auth.py`)
5. Frontend stores `access_token` and `user_id` (yahoo_guid) in localStorage
6. Frontend uses `Bearer <user_id>` header for API requests
7. Backend looks up user by yahoo_guid and validates/refreshes tokens as needed

**Important:** User sessions are persisted in `backend/users.json`, not the database.

### Yahoo API Integration

The codebase uses a **hybrid approach** for Yahoo API:

1. **Custom OAuth** (`app/auth.py`): Handles Yahoo OAuth2 flow independently
2. **Direct API calls**: Used for basic endpoints (leagues list, standings, league info) via `_make_request()` in `yahoo_api.py`
3. **YFPY integration**: Used for complex data (draft results, transactions, player stats) via `get_yfpy_query()` method
   - YFPY instances are created per-league with injected access tokens
   - Game code detection from league_key (e.g., "465" → "nhl", "449" → "nfl")
   - YFPY methods: `get_league_draft_results()`, `get_league_transactions()`, `get_league_players()`

**Key patterns:**
- League keys format: `<game_id>.l.<league_id>` (e.g., "465.l.34948")
- Game code mapping in `routes.py`: game_id → game_code (nhl, nfl, nba, mlb)
- Yahoo API returns JSON when `format=json` is added to URL
- API responses have deeply nested structure: `fantasy_content → users → 0 → user → [guid, {games/leagues}]`

### Frontend Structure

- **`src/pages/`**: Main page components (Dashboard, LeagueView, TradeAnalyzer, DraftAnalyzer, HistoricalView, Login)
- **`src/services/api.ts`**: Axios API client with auth header injection
- **`src/components/`**: Reusable components (Navbar)
- **React Router**: Client-side routing with protected routes checking localStorage auth
- **Vite**: Build tool and dev server (default port 5173)

### Database Models

- **User**: OAuth tokens and Yahoo GUID
- **League**: League metadata, linked to user
- **Team**: Team standings and stats within a league
- **Player**: Player info and stats within a league
- **RosterPlayer**: Junction table for team rosters
- **Draft**: Draft pick results
- **PlayerHistoricalStats**: Multi-season player data
- **AnalysisCache**: Cached analysis results

**Note:** Most data is proxied from Yahoo API rather than stored locally. Database is primarily for caching and historical tracking.

## API Endpoints

**Authentication:**
- `GET /api/auth/login` - Get Yahoo OAuth URL
- `GET /api/auth/callback` - OAuth callback handler

**Leagues & Data:**
- `GET /api/leagues?game_code=nhl` - List user's leagues (optional game filter)
- `GET /api/league/{league_key}` - League details
- `GET /api/league/{league_key}/teams` - League standings
- `GET /api/league/{league_key}/players?start=0&count=25` - League players (paginated)

**Analysis:**
- `GET /api/league/{league_key}/analysis/trades` - Trade recommendations (uses YFPY transactions)
- `GET /api/league/{league_key}/analysis/draft?page=1&page_size=100` - Draft analysis with player/team enrichment
- `GET /api/league/{league_key}/history?seasons=3` - Historical data
- `GET /api/player/{player_key}/performance?league_key={key}` - Player performance analysis

## Implementation Status

**Working:**
- Yahoo OAuth flow and token refresh
- League/team/player data retrieval via hybrid API approach
- Draft results with comprehensive player and team data enrichment
- Frontend dashboard and navigation
- CSV export tool for player data

**Placeholder/Incomplete:**
- Trade analyzer logic (only fetches transactions, no real analysis)
- Draft grading (fetches data but doesn't evaluate picks)
- Performance analyzer (basic structure only)
- Historical data across seasons (minimal implementation)
- Analysis caching

See `IMPLEMENTATION_STATUS.md` for detailed roadmap.

## Key Patterns & Gotchas

### Working with Yahoo API

- Always add `format=json` to REST endpoints for JSON responses
- League keys contain game_id which must be mapped to game_code for YFPY
- YFPY returns custom object models, not dicts - use `getattr()` to safely access attributes
- Many YFPY fields may be `bytes` - decode with `.decode('utf-8', errors='replace')`
- Player names come as `name.first` + `name.last`, not a single field
- Draft results include embedded player/team objects - extract data from both pick and lookup dicts

### API Response Parsing

Yahoo's JSON structure is heavily nested:
```python
fantasy_content → users → "0" → user → [guid_obj, {games: {...}}]
→ games → "0", "1", "2" → game → [{game_info}, {leagues: {...}}]
→ leagues → "0", "1" → league → [league_data]
```

### YFPY Integration

To use YFPY with existing OAuth:
```python
yfpy_query = client.get_yfpy_query(league_id, game_code, game_id)
draft_results = yfpy_query.get_league_draft_results()
```

YFPY expects a per-league instance. Don't reuse across leagues.

### Frontend Auth

API client in `services/api.ts` automatically adds:
```
Authorization: Bearer <yahoo_guid>
```

Backend looks up user by guid and uses their access token for Yahoo API calls.

## Common Tasks

### Exporting data for a new league

```bash
# Find your league key on Yahoo (URL: yahoo.com/.../<game_id>.l.<league_id>)
python export_players.py 465.l.34948
# Upload resulting CSVs to Google Sheets
```

### Adding custom columns to CSV export

Edit `export_players.py`:
1. Update `csv_headers` list (line ~602)
2. Extract the data from player object in the loop (line ~642)
3. Add to `writer.writerow()` dict (line ~808)

### Troubleshooting authentication issues

OAuth tokens stored in `backend/data/user_tokens.json`:
```bash
# Delete to force re-authentication
rm backend/data/user_tokens.json

# Or authenticate via web app first
cd backend && uvicorn app.main:app --reload
# Then use frontend at localhost:5173 to login
```

### Adding a new analyzer to web app

1. Create module in `backend/app/analyzers/`
2. Implement analyzer class with methods that use `YahooAPIClient`
3. Add route in `app/api/routes.py` to expose analysis
4. Add frontend page component in `frontend/src/pages/`
5. Update navigation in `Navbar.tsx`

### Debugging Yahoo API calls

Backend logs all API requests with URL and response status. Check terminal output for:
```
Making Yahoo API request to: https://...
Yahoo API response: 200
```

Use `debug_*.xml` files in backend/ directory for inspecting raw Yahoo responses.

### Understanding Yahoo API stat IDs

The export script uses direct XML API calls and parses stat IDs. Common NHL stat IDs:
- `1` = Goals (G)
- `2` = Assists (A)
- `5` = Penalty Minutes (PIM)
- `14` = Shots on Goal (SOG)
- `19` = Wins (W) - goalie
- `22` = Goals Against (GA) - goalie
- `25` = Saves (SV) - goalie
- `27` = Shutouts (SO) - goalie
- `28` = Games Started (GS) - goalie
- `29` = Games Played (GP) - skater
- `31` = Hits (HIT)
- `32` = Blocks (BLK)

**Important:** The "Games Played" column shows GP for skaters but GS (Games Started) for goalies. This is handled automatically based on player position.

See stat parsing logic in `export_players.py` around line 730.

### Working with YFPY

YFPY has extensive documentation. Key methods used:
- `get_league_draft_results()` - Draft picks with player objects
- `get_league_transactions()` - Trades, adds, drops
- `get_league_players(player_count_start, player_count_limit)` - Paginated players
- `get_league_teams()` - Teams with manager info
- `get_player_stats_by_week(player_key)` - Week-by-week stats
- `get_all_yahoo_fantasy_game_keys()` - All games user participates in
- `get_user_leagues_by_game_key(game_key)` - Leagues for specific game/season

### Running the CSV Export

**Interactive mode** (recommended for first-time use):
```bash
cd backend
python export_players.py
# Authenticates, lists all your leagues, lets you choose
```

**Direct mode** (when you know the league key):
```bash
python export_players.py 465.l.34948 --output my_analysis.csv
```

The script automatically:
- Reuses existing OAuth token from `data/user_tokens.json` (if available)
- Refreshes expired tokens
- Falls back to browser OAuth if no token exists
- Fetches 500+ players with comprehensive stats
- Exports two CSV files (player analysis + standings)

## Testing

No formal test suite currently. Manual testing via:
- FastAPI auto-generated docs: `http://localhost:8000/docs`
- Frontend dev server with browser DevTools
- `test_standings.py` - Ad-hoc script for testing standings endpoint

## Known Issues

1. **Historical leagues:** Yahoo API doesn't provide stat breakdowns (G, A, etc.) for seasons older than 1-2 years. Fantasy Points totals are still available, but individual stats may be empty.
2. **Rate limiting:** Not implemented. Yahoo API has limits - if export fails, wait a few minutes.
3. **Web app analysis modules:** Trade analyzer, draft grading, and performance analyzer are mostly placeholder implementations. The data fetching works, but analysis logic is minimal.
4. **YFPY OAuth token injection:** Fragile and may need refactoring for web app.
5. **User storage:** JSON file (`data/user_tokens.json`) instead of database.
6. **Bytes vs strings:** Yahoo API sometimes returns bytes that need decoding - export script handles this, but web app may have issues in some endpoints.
