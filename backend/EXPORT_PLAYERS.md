# Player Export Script

This standalone Python script exports comprehensive player data from Yahoo Fantasy Sports to CSV format.

## Features

Exports the following data for all players in a league:

- **Player Rank** - Yahoo's draft ranking
- **Player Name** - Full name
- **Position** - Playing position
- **NHL Team** - Current NHL team
- **Fantasy Points** - Total fantasy points
- **Rostered Team** - Fantasy team that owns the player
- **Owner** - Manager name
- **Draft Round** - Round drafted
- **Draft Pick** - Overall pick number
- **Player Stats** - Goals, Assists, Points, +/-, PIM, PPG, PPP, SOG
- **Pct Owned** - Ownership percentage across all leagues

## Requirements

- Python 3.11+
- Environment variables set in `.env`:
  - `YAHOO_CLIENT_ID` or `YAHOO_CONSUMER_KEY`
  - `YAHOO_CLIENT_SECRET` or `YAHOO_CONSUMER_SECRET`

## Installation

```bash
cd backend
source venv/bin/activate  # Activate virtual environment
pip install -r requirements.txt  # Dependencies already installed
```

## Usage

### Basic Usage

```bash
python export_players.py <league_key>
```

Example:
```bash
python export_players.py 465.l.34948
```

This will create `player_analysis.csv` in the current directory.

### Custom Output File

```bash
python export_players.py <league_key> --output <filename.csv>
```

Examples:
```bash
python export_players.py 465.l.34948 --output draft_2025.csv
python export_players.py 427.l.11181 -o season_2023.csv
```

### Make it Executable

```bash
chmod +x export_players.py
./export_players.py 465.l.34948
```

## Authentication

### Option 1: Use Existing Token (Recommended)

If you've already logged in via the web app, the script will automatically use your existing token from `data/user_tokens.json`.

### Option 2: Browser OAuth

If no token exists, the script will:
1. Open a browser window
2. Prompt you to authorize the app
3. Save the token for future use

## Output Format

The CSV file contains the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| Player Rank | Yahoo draft ranking | 1, 2, 3... |
| Player Name | Full player name | Connor McDavid |
| Position | Playing position | C, LW, RW, D, G |
| NHL Team | NHL team abbreviation | EDM, TOR, BOS |
| Fantasy Points | Total fantasy points | 145.5 |
| Rostered Team | Fantasy team name | Kiril's KaprizHog |
| Owner | Manager name | Eric |
| Draft Round | Draft round | 1, 2, 3... |
| Draft Pick | Overall pick number | 1, 2, 3... |
| Goals | Goals scored | 25 |
| Assists | Assists | 40 |
| Points | Total points | 65 |
| Plus/Minus | +/- rating | +15 |
| PIM | Penalty minutes | 20 |
| PPG | Power play goals | 10 |
| PPP | Power play points | 25 |
| SOG | Shots on goal | 200 |
| Pct Owned | Ownership % | 99.5 |

## Examples

### Export Current Season Draft Analysis

```bash
python export_players.py 465.l.34948 --output nhl_2025_draft.csv
```

### Export for Multiple Leagues

```bash
# Current season
python export_players.py 465.l.34948 --output league_2025.csv

# Previous season
python export_players.py 427.l.11181 --output league_2023.csv
```

### Quick Check

```bash
# Export and immediately view in Excel/Numbers
python export_players.py 465.l.34948 && open player_analysis.csv
```

## Troubleshooting

### "Missing Yahoo credentials"

Ensure your `.env` file has:
```
YAHOO_CLIENT_ID=your_client_id_here
YAHOO_CLIENT_SECRET=your_client_secret_here
```

### "Could not load existing token"

Run the web app first to authenticate, or let the script open a browser for OAuth.

### "Error fetching players"

The Yahoo API may rate-limit requests. The script fetches players in batches of 100. If it fails, wait a few minutes and try again.

### Stats Not Showing

Some players may not have stats if:
- They haven't played yet this season
- Stats aren't available for their position
- The season hasn't started

## Advanced Usage

### Integrate into Other Scripts

```python
from export_players import export_players_to_csv, get_yfpy_query

# Export to CSV
export_players_to_csv('465.l.34948', 'output.csv')

# Or use YFPY query directly
yfpy = get_yfpy_query('465.l.34948')
players = yfpy.get_league_players(player_count_start=0, player_count_limit=100)
```

### Scheduled Exports

Add to crontab for weekly exports:

```bash
# Export every Monday at 9 AM
0 9 * * 1 cd /path/to/backend && ./export_players.py 465.l.34948 --output weekly_$(date +\%Y\%m\%d).csv
```

## Notes

- The script fetches up to 1000 players by default
- Players are fetched in batches of 100
- All data is exported in a single CSV file
- Player stats are season-to-date
- Ownership % is league-wide across all Yahoo leagues

## Support

For issues or questions:
1. Check the `.env` file has correct credentials
2. Verify the league key format: `<game_id>.l.<league_id>`
3. Check the logs for detailed error messages
4. Ensure you have an active internet connection

