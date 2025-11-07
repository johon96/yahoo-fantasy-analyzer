# Yahoo Fantasy Hockey Trade Analyzer

A comprehensive trade analyzer and league analytics dashboard for Yahoo Fantasy Hockey leagues. This application provides insights into player performance, draft analysis, trade recommendations, and historical league data.

## Features

- **OAuth Authentication**: Secure login with Yahoo Fantasy Sports API
- **Trade Analysis**: Identify players who are over/under performing relative to projections
- **Draft Analysis**: Evaluate draft picks and identify best/worst selections with comprehensive player data
- **Historical Analysis**: View team records and performance across multiple seasons
- **Player Performance**: Compare actual stats vs. projections
- **League Dashboard**: Visualize league standings, team records, and trends
- **CSV Export**: Standalone script to export comprehensive player data to CSV for external analysis

## Tech Stack

### Backend
- Python 3.9+
- FastAPI (REST API)
- yfpy (Yahoo Fantasy Sports API wrapper)
- SQLAlchemy (ORM)
- SQLite/PostgreSQL (Database)
- OAuth2 authentication

### Frontend
- React 18+
- Node.js
- TypeScript
- Chart.js / Recharts (Visualizations)
- Axios (API client)

## Project Structure

```
fantasy-hockey-analyzer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI application
│   │   ├── config.py          # Configuration
│   │   ├── database.py        # Database setup
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── auth.py            # OAuth authentication
│   │   ├── yahoo_api.py       # Yahoo API wrapper
│   │   ├── analyzers/
│   │   │   ├── __init__.py
│   │   │   ├── trade_analyzer.py
│   │   │   ├── draft_analyzer.py
│   │   │   └── performance_analyzer.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── routes.py      # API endpoints
│   │       └── schemas.py     # Pydantic models
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
└── README.md
```

## Setup

### Prerequisites

1. Register your application on [Yahoo Developer Network](https://developer.yahoo.com/apps/)
2. Get your `client_id` and `client_secret`
3. Set up redirect URI (e.g., `http://localhost:3000/auth/callback`)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Yahoo API credentials
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

## Configuration

Create a `.env` file in the `backend` directory:

```env
YAHOO_CLIENT_ID=your_client_id
YAHOO_CLIENT_SECRET=your_client_secret
YAHOO_REDIRECT_URI=http://localhost:3000/auth/callback
DATABASE_URL=sqlite:///./fantasy_hockey.db
SECRET_KEY=your_secret_key_here

# Optional: YFPY library also looks for these (set automatically from YAHOO_CLIENT_ID/SECRET)
# YAHOO_CONSUMER_KEY=your_client_id
# YAHOO_CONSUMER_SECRET=your_client_secret
```

## Usage

1. Start the backend server (default: `http://localhost:8000`)
2. Start the frontend dev server (default: `http://localhost:3000`)
3. Navigate to the app and authenticate with Yahoo
4. Select your league and explore the analytics

## API Endpoints

- `GET /api/auth/login` - Initiate OAuth login
- `GET /api/auth/callback` - OAuth callback handler
- `GET /api/leagues` - Get user's leagues
- `GET /api/league/{league_id}` - Get league details
- `GET /api/league/{league_id}/teams` - Get league teams
- `GET /api/league/{league_id}/players` - Get league players
- `GET /api/league/{league_id}/analysis/trades` - Trade analysis
- `GET /api/league/{league_id}/analysis/draft` - Draft analysis
- `GET /api/league/{league_id}/history` - Historical data

## CSV Export Tool

Export comprehensive player data to CSV for external analysis, spreadsheets, or data science projects.

### Usage

```bash
cd backend
source venv/bin/activate
python export_players.py <league_key> --output <filename.csv>
```

### Example

```bash
python export_players.py 465.l.34948 --output draft_analysis.csv
```

### Exported Data

- Player Rank (Yahoo's draft ranking)
- Player Name, Position, NHL Team
- Fantasy Points (season total)
- Rostered Team & Owner
- Draft Round & Pick Number
- Player Stats (Goals, Assists, Points, +/-, PIM, PPG, PPP, SOG)
- Ownership Percentage

### Documentation

See [`backend/EXPORT_PLAYERS.md`](backend/EXPORT_PLAYERS.md) for detailed usage, examples, and troubleshooting.

## License

MIT

