#!/usr/bin/env python3
"""
Upload CSV files to Google Sheets with automatic formatting and merged headers.

This script:
1. Automatically detects season from league key
2. Uploads player analysis CSV to "<SEASON> Players" sheet
3. Uploads standings CSV to "<SEASON> Standings" sheet with merged headers
4. Applies formatting (frozen headers, bold, colors, etc.)

Setup:
1. Create a Google Cloud project: https://console.cloud.google.com/
2. Enable Google Sheets API
3. Create a Service Account and download credentials JSON
4. Save credentials to: backend/data/google_sheets_credentials.json
5. Share your Google Sheet with the service account email

Usage:
    python upload_to_sheets.py <league_key> <spreadsheet_id>

    Example:
    python upload_to_sheets.py 465.l.34948 15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg

    This will upload to sheets named "2025 Players" and "2025 Standings"
"""

import sys
import csv
import os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Google Sheets API scopes
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Path to service account credentials
CREDENTIALS_FILE = Path(__file__).parent / "data" / "google_sheets_credentials.json"

# Yahoo game ID to season mapping
GAME_SEASON_MAP = {
    "331": 2014, "346": 2015, "348": 2015, "352": 2015, "353": 2015,
    "357": 2016, "359": 2016, "363": 2016, "364": 2016,
    "370": 2017, "371": 2017, "375": 2017, "376": 2017,
    "378": 2018, "380": 2018, "383": 2018, "385": 2018, "386": 2018,
    "388": 2019, "390": 2019, "391": 2019, "395": 2019, "396": 2019,
    "398": 2020, "399": 2020, "402": 2020, "403": 2020,
    "404": 2021, "406": 2021, "410": 2021, "411": 2021,
    "412": 2022, "414": 2022, "418": 2022, "419": 2022,
    "422": 2023, "423": 2023, "427": 2023, "428": 2023,
    "431": 2024, "449": 2024, "453": 2024, "454": 2024,
    "458": 2025, "461": 2025, "465": 2025,  # 465 is NHL 2025
}


def get_season_from_league_key(league_key):
    """Extract game ID from league key and map to season year."""
    # League key format: "465.l.34948" where 465 is the game_id
    game_id = league_key.split('.')[0]
    season = GAME_SEASON_MAP.get(game_id, 2025)
    return season, game_id


def get_sheets_service():
    """Create and return Google Sheets API service."""
    if not CREDENTIALS_FILE.exists():
        print(f"❌ Credentials file not found: {CREDENTIALS_FILE}")
        print("\nSetup instructions:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a project and enable Google Sheets API")
        print("3. Create a Service Account")
        print("4. Download the JSON key file")
        print(f"5. Save it to: {CREDENTIALS_FILE}")
        sys.exit(1)

    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    return service


def read_csv_data(csv_file):
    """Read CSV file and return as list of rows."""
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        return list(reader)


def sheet_exists(service, spreadsheet_id, sheet_name):
    """Check if a sheet with the given name exists."""
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return True
        return False
    except HttpError:
        return False


def upload_player_analysis(service, spreadsheet_id, csv_file, sheet_name="Player Analysis"):
    """Upload player analysis CSV to Google Sheets."""
    print(f"\n📊 Uploading {csv_file} to '{sheet_name}' sheet...")

    data = read_csv_data(csv_file)

    try:
        # Check if sheet exists
        if sheet_exists(service, spreadsheet_id, sheet_name):
            # Clear existing sheet
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A:ZZ"
            ).execute()
            print(f"  Cleared existing '{sheet_name}' sheet")
        else:
            # Create new sheet
            body = {'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body).execute()
            print(f"  Created new '{sheet_name}' sheet")

        # Upload data
        body = {'values': data}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A1",
            valueInputOption='RAW',
            body=body
        ).execute()

        # Get sheet ID for formatting (now that we know the sheet exists)
        sheet_id = get_sheet_id(service, spreadsheet_id, sheet_name)
        if sheet_id is None:
            print(f"  ⚠️  Could not find sheet ID for '{sheet_name}', skipping formatting")
            return

        # Apply formatting (no auto-resize - preserve manual column widths)
        requests = [
            # Freeze header row
            {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {'frozenRowCount': 1}
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            },
            # Bold header row without wrapping
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'wrapStrategy': 'OVERFLOW_CELL',
                            'verticalAlignment': 'MIDDLE',
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,wrapStrategy,verticalAlignment,horizontalAlignment)'
                }
            }
        ]

        body = {'requests': requests}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body).execute()

        print(f"✅ Uploaded {len(data)-1} players to '{sheet_name}'")

    except HttpError as e:
        print(f"❌ Error uploading: {e}")
        raise


def upload_standings(service, spreadsheet_id, csv_file, sheet_name="Standings"):
    """Upload standings CSV with 3-row header structure and merged cells."""
    print(f"\n📊 Uploading {csv_file} to '{sheet_name}' sheet...")

    data = read_csv_data(csv_file)

    # CSV now has 3 header rows built-in:
    # Row 1: Category headers (Skaters, Goalies)
    # Row 2: Sub-headers (Records, Totals)
    # Row 3: Column names
    # Data rows follow

    # Column structure (0-indexed):
    # 0-9: Team info (10 columns)
    # 10-15: Skater Records (6 columns) - empty
    # 16-21: Skater Totals (6 columns) - data
    # 22-25: Goalie Records (4 columns) - empty
    # 26-29: Goalie Totals (4 columns) - data

    try:
        # Check if sheet exists
        if sheet_exists(service, spreadsheet_id, sheet_name):
            # Clear existing sheet
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A:ZZ"
            ).execute()
            print(f"  Cleared existing '{sheet_name}' sheet")
        else:
            # Create new sheet
            body = {'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body).execute()
            print(f"  Created new '{sheet_name}' sheet")

        # Upload data as-is (already has 3 header rows)
        body = {'values': data}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A1",
            valueInputOption='RAW',
            body=body
        ).execute()

        # Get sheet ID for formatting (now that we know the sheet exists)
        sheet_id = get_sheet_id(service, spreadsheet_id, sheet_name)
        if sheet_id is None:
            print(f"  ⚠️  Could not find sheet ID for '{sheet_name}', skipping formatting")
            return

        requests = [
            # Freeze top 3 rows (all headers)
            {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sheet_id,
                        'gridProperties': {'frozenRowCount': 3}
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            },
            # Bold all 3 header rows without wrapping (preserve manual column widths)
            {
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 3
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                            'wrapStrategy': 'OVERFLOW_CELL',
                            'verticalAlignment': 'MIDDLE',
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor,wrapStrategy,verticalAlignment,horizontalAlignment)'
                }
            },
            # ROW 1: Merge "Skaters" across Records + Totals (columns 10-21, 12 columns)
            {
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 10,
                        'endColumnIndex': 22
                    },
                    'mergeType': 'MERGE_ALL'
                }
            },
            # ROW 1: Merge "Goalies" across Records + Totals (columns 22-29, 8 columns)
            {
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 22,
                        'endColumnIndex': 30
                    },
                    'mergeType': 'MERGE_ALL'
                }
            },
            # ROW 2: Merge "Records" for Skaters (columns 10-15, 6 columns)
            {
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': 2,
                        'startColumnIndex': 10,
                        'endColumnIndex': 16
                    },
                    'mergeType': 'MERGE_ALL'
                }
            },
            # ROW 2: Merge "Totals" for Skaters (columns 16-21, 6 columns)
            {
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': 2,
                        'startColumnIndex': 16,
                        'endColumnIndex': 22
                    },
                    'mergeType': 'MERGE_ALL'
                }
            },
            # ROW 2: Merge "Records" for Goalies (columns 22-25, 4 columns)
            {
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': 2,
                        'startColumnIndex': 22,
                        'endColumnIndex': 26
                    },
                    'mergeType': 'MERGE_ALL'
                }
            },
            # ROW 2: Merge "Totals" for Goalies (columns 26-29, 4 columns)
            {
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,
                        'endRowIndex': 2,
                        'startColumnIndex': 26,
                        'endColumnIndex': 30
                    },
                    'mergeType': 'MERGE_ALL'
                }
            },
        ]

        body = {'requests': requests}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body).execute()

        print(f"✅ Uploaded {len(data)-3} teams to '{sheet_name}' with 3-row merged headers")

    except HttpError as e:
        print(f"❌ Error uploading: {e}")
        raise


def get_sheet_id(service, spreadsheet_id, sheet_name):
    """Get the sheet ID for a given sheet name. Returns None if not found."""
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        return None
    except HttpError:
        return None


def main():
    if len(sys.argv) < 3:
        print("Usage: python upload_to_sheets.py <league_key> <spreadsheet_id>")
        print("\nExample:")
        print("  python upload_to_sheets.py 465.l.34948 15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg")
        print("\nTo find your spreadsheet ID:")
        print("  Open your Google Sheet and look at the URL:")
        print("  https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit")
        sys.exit(1)

    league_key = sys.argv[1]
    spreadsheet_id = sys.argv[2]

    # Detect season from league key
    season, game_id = get_season_from_league_key(league_key)

    # Generate CSV file names
    safe_league_key = league_key.replace('.', '_')
    analysis_csv = f"{safe_league_key}_analysis.csv"
    standings_csv = f"{safe_league_key}_standings.csv"

    # Generate sheet names based on season
    players_sheet_name = f"{season} Players"
    standings_sheet_name = f"{season} Standings"

    # Check if CSV files exist
    if not os.path.exists(analysis_csv):
        print(f"❌ File not found: {analysis_csv}")
        print("Run export_players.py first to generate the CSV files")
        sys.exit(1)

    if not os.path.exists(standings_csv):
        print(f"❌ File not found: {standings_csv}")
        print("Run export_players.py first to generate the CSV files")
        sys.exit(1)

    print("="*60)
    print("Google Sheets Upload Tool")
    print("="*60)
    print(f"League: {league_key}")
    print(f"Game ID: {game_id} → Season: {season}")
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(f"Target sheets: '{players_sheet_name}' and '{standings_sheet_name}'")

    # Get Google Sheets service
    service = get_sheets_service()

    # Upload both sheets
    upload_player_analysis(service, spreadsheet_id, analysis_csv, sheet_name=players_sheet_name)
    upload_standings(service, spreadsheet_id, standings_csv, sheet_name=standings_sheet_name)

    print(f"\n✅ Upload complete!")
    print(f"View your spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")


if __name__ == "__main__":
    main()
