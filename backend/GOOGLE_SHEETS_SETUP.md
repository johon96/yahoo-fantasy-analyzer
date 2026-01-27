# Google Sheets Integration Setup

This guide explains how to automatically upload your Yahoo Fantasy CSV exports to Google Sheets with formatted headers.

## Features

- Automatic upload of player analysis and standings CSVs
- Merged header rows for "Skaters" and "Goalies" sections in standings
- Frozen header rows for easy scrolling
- Bold headers with background color
- Auto-resized columns

## Setup Instructions

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Click "Enable APIs and Services"
4. Search for "Google Sheets API" and enable it

### 2. Create Service Account

1. In Google Cloud Console, go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name it (e.g., "yahoo-fantasy-uploader")
4. Click "Create and Continue"
5. Skip optional steps and click "Done"

### 3. Download Credentials

1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Choose "JSON" format
5. Click "Create" - the JSON file will download

### 4. Save Credentials

Save the downloaded JSON file to:
```
backend/data/google_sheets_credentials.json
```

### 5. Create Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Name it (e.g., "Yahoo Fantasy 2025")
4. Copy the Spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```

### 6. Share Sheet with Service Account

1. In your Google Sheet, click "Share"
2. Paste the service account email (from the JSON file, looks like: `xxx@xxx.iam.gserviceaccount.com`)
3. Give it "Editor" permissions
4. Uncheck "Notify people"
5. Click "Share"

## Usage

### Interactive Workflow (Recommended)

Simply run the export script and it will prompt you whether to upload:

```bash
cd backend
python export_players.py 465.l.34948

# After export completes, you'll see:
# ============================================================
# Google Sheets Upload
# ============================================================
#
# Would you like to upload to Google Sheets? (y/n): y
# Enter your Google Sheets spreadsheet ID: 15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg
```

This workflow:
1. Exports player analysis and standings CSVs from Yahoo
2. Asks if you want to upload to Google Sheets
3. If yes, prompts for spreadsheet ID
4. Automatically detects the season (e.g., 465 → 2025)
5. Uploads to sheets named "2025 Players" and "2025 Standings"
6. Applies all formatting and merged headers

### One-Command Upload (No Prompts)

If you already know your spreadsheet ID, skip the prompts:

```bash
python export_players.py 465.l.34948 --spreadsheet-id 15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg
```

### Export Only (No Upload)

```bash
# Skip upload prompt entirely
python export_players.py 465.l.34948 --no-upload
```

### Manual Upload (Two-Step)

If you prefer to export and upload separately:

```bash
# 1. Export CSVs from Yahoo
python export_players.py 465.l.34948 --no-upload

# 2. Upload to Google Sheets manually
python upload_to_sheets.py 465.l.34948 15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg
```

### Example Output

When using the one-step workflow:

```bash
$ python export_players.py 465.l.34948 --spreadsheet-id 15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg

============================================================
Exporting player data for league: 465.l.34948
Output file: 465_l_34948_analysis.csv
============================================================

Fetching league information...
Game ID: 465 → Season: 2025

Fetching draft results...
Loaded 180 draft picks

Fetching league teams...
Loaded 14 teams

Fetching player data (up to 1500 players, in batches of 25)...
  Fetching players 0-24... (batch 1/60)
  [...]
  Fetching players 1475-1499... (batch 60/60)

✅ Successfully exported 1500 players to 465_l_34948_analysis.csv
  Players with stats: 1450
  Players without stats: 50

============================================================
Exporting standings for league: 465.l.34948
Output file: 465_l_34948_standings.csv
============================================================

✅ Successfully exported standings with category stats to 465_l_34948_standings.csv

============================================================
Uploading to Google Sheets
============================================================
Season: 2025 (Game ID: 465)
Spreadsheet ID: 15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg
Target sheets: '2025 Players' and '2025 Standings'

📊 Uploading 465_l_34948_analysis.csv to '2025 Players' sheet...
  Created new '2025 Players' sheet
✅ Uploaded 1500 players to '2025 Players'

📊 Uploading 465_l_34948_standings.csv to '2025 Standings' sheet...
  Created new '2025 Standings' sheet
✅ Uploaded 14 teams to '2025 Standings' with 3-row merged headers

✅ Upload complete!
View your spreadsheet: https://docs.google.com/spreadsheets/d/15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg/
```

## Sheet Formatting

### Player Analysis Sheet
- **Row 1:** Bold headers with gray background
- **Frozen:** First row stays visible while scrolling
- **Auto-sized:** Columns adjust to content width
- **Sorted:** Players ranked by Fantasy Points (descending)

### Standings Sheet
- **Row 1:** Merged headers for "Skaters" and "Goalies" (spans both Records and Totals)
- **Row 2:** Sub-headers "Records" and "Totals" for each category
- **Row 3:** Individual stat column names (G, A, PIM, etc.)
- **Frozen:** Top 3 rows stay visible
- **Bold:** All 3 header rows with gray background
- **Centered:** Header text alignment
- **Structure:**
  - Skaters: 6 empty Records columns + 6 Totals columns (G, A, PIM, SOG, HIT, BLK)
  - Goalies: 4 empty Records columns + 4 Totals columns (W, GA, SV, SHO)

## Troubleshooting

### "Credentials file not found"
- Make sure you saved the JSON file to `backend/data/google_sheets_credentials.json`
- Check file permissions

### "The caller does not have permission"
- Ensure you shared the Google Sheet with the service account email
- Give the service account "Editor" permissions

### "Invalid spreadsheet ID"
- Double-check the spreadsheet ID from the URL
- Make sure you're using the ID, not the entire URL

### "Module not found: google"
- Install dependencies: `pip install -r requirements.txt`
- Or manually: `pip install google-auth google-api-python-client`

## Advanced Usage

### Update Existing Sheets

The script automatically clears and updates existing sheets if they already exist. Just run it again with the same spreadsheet ID:

```bash
python upload_to_sheets.py 465.l.34948 YOUR_SPREADSHEET_ID
```

### Multiple Seasons/Leagues

You can upload multiple seasons to the same spreadsheet. Each season will have its own sheets:

```bash
# Upload 2025 season data
python upload_to_sheets.py 465.l.34948 SPREADSHEET_ID  # Creates "2025 Players" and "2025 Standings"

# Upload 2024 season data
python upload_to_sheets.py 449.l.12345 SPREADSHEET_ID  # Creates "2024 Players" and "2024 Standings"

# Upload 2023 season data
python upload_to_sheets.py 428.l.67890 SPREADSHEET_ID  # Creates "2023 Players" and "2023 Standings"
```

Each season maintains separate sheets, allowing you to compare year-over-year data in the same spreadsheet.

## Security Notes

- **Never commit** `google_sheets_credentials.json` to git
- The `data/` directory is already in `.gitignore`
- Service accounts have limited access (only to sheets you explicitly share)
- You can revoke access anytime by unsharing the sheet or deleting the service account
