#!/usr/bin/env python3
"""
Export comprehensive player data from Yahoo Fantasy Sports to CSV.

Usage:
    python export_players.py <league_key> [--output <filename.csv>]

Example:
    python export_players.py 465.l.34948 --output draft_analysis.csv
"""

# Standard library imports
import argparse
import csv
import json
import logging
import os
import sys
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

# Third-party imports
from dotenv import load_dotenv
from yfpy.query import YahooFantasySportsQuery
from yfpy.models import Player
from yfpy.data import Data
from yahoo_fantasy_api import league as yahoo_league
from yahoo_oauth import OAuth2
import requests

# Load environment variables
load_dotenv()


def decode_if_bytes(value):
    """
    Decode bytes to string if needed, handling various encoding issues.
    Fixes common UTF-8 mojibake (garbled text) issues.
    """
    if isinstance(value, bytes):
        try:
            # Try UTF-8 first
            decoded = value.decode('utf-8')
            return decoded
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            return value.decode('latin-1', errors='replace')
    
    # If it's already a string but looks garbled (mojibake), try to fix it
    if isinstance(value, str):
        # Common mojibake: UTF-8 bytes interpreted as Windows-1252/Latin-1
        # Example: "Kiril窶冱" should be "Kiril's"
        try:
            # Try to encode as latin-1 then decode as utf-8 to fix mojibake
            fixed = value.encode('latin-1').decode('utf-8')
            return fixed
        except (UnicodeDecodeError, UnicodeEncodeError):
            # If that doesn't work, return original
            return value
    
    return value


def get_yfpy_query(league_key, use_existing_token=True):
    """
    Initialize YFPY query for a league.
    
    Args:
        league_key: Yahoo league key (e.g., "465.l.34948")
        use_existing_token: If True, try to use existing token from user_tokens.json
    
    Returns:
        YahooFantasySportsQuery instance
    """
    # Parse league key
    parts = league_key.split('.')
    game_id = parts[0] if len(parts) > 0 else None
    league_id = parts[-1] if len(parts) > 0 else league_key
    
    # Map game_id to game_code
    game_code_map = {
        "449": "nfl", "461": "nfl",
        "465": "nhl", "427": "nhl",
        "404": "mlb", "412": "mlb",
        "428": "nba",
    }
    game_code = game_code_map.get(game_id, "nhl")
    
    print(f"Initializing YFPY for league {league_id}, game {game_code}, game_id {game_id}")
    
    # Get credentials from settings
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
    from config import settings
    
    consumer_key = settings.yahoo_client_id
    consumer_secret = settings.yahoo_client_secret
    
    if not consumer_key or not consumer_secret:
        raise ValueError(
            "Missing Yahoo credentials. Please check your .env file."
        )
    
    # Try to load existing access token and refresh if needed
    access_token_json = None
    if use_existing_token:
        token_file = Path(__file__).parent / "data" / "user_tokens.json"
        if token_file.exists():
            try:
                from app.auth import User, get_valid_access_token, _load_users, _save_users
                
                # Load users from JSON
                users = _load_users()
                if users:
                    # Get the first user (assumes single user)
                    first_guid = list(users.keys())[0]
                    user = users[first_guid]
                    
                    print(f"Using existing access token for user: {user.yahoo_guid}")
                    
                    # Get valid token (will refresh if expired)
                    try:
                        valid_token = get_valid_access_token(user)
                        print("Token validated/refreshed successfully")
                        
                        # Reload user data after potential refresh
                        users = _load_users()
                        user = users[first_guid]
                        
                        access_token_json = {
                            "access_token": user.access_token,
                            "refresh_token": user.refresh_token,
                            "consumer_key": consumer_key,
                            "consumer_secret": consumer_secret,
                            "guid": user.yahoo_guid,
                            "token_type": "Bearer",
                            "token_time": user.token_expires_at.timestamp() if user.token_expires_at else datetime.now().timestamp()
                        }
                    except Exception as token_error:
                        print(f"Token refresh failed: {token_error}")
                        print("Will attempt browser OAuth flow...")
                        access_token_json = None
            except Exception as e:
                print(f"Could not load existing token: {e}")
    
    # Initialize YFPY
    yahoo_query = YahooFantasySportsQuery(
        league_id=league_id,
        game_id=game_id,
        game_code=game_code,
        offline=False,
        yahoo_consumer_key=consumer_key,
        yahoo_consumer_secret=consumer_secret,
        yahoo_access_token_json=access_token_json,
        browser_callback=True  # Enable browser OAuth if no token
    )
    
    print("YFPY initialized successfully!")
    return yahoo_query


def get_user_leagues(yfpy_query):
    """Fetch all leagues for the authenticated user."""
    print("\n" + "="*60)
    print("Fetching your leagues...")
    print("="*60)
    
    # Temporarily suppress YFPY error logging for games without leagues
    yfpy_logger = logging.getLogger('yfpy.query')
    original_level = yfpy_logger.level
    yfpy_logger.setLevel(logging.CRITICAL)  # Only show critical errors
    
    try:
        # Get user's games
        games = yfpy_query.get_all_yahoo_fantasy_game_keys()
        
        all_leagues = []
        for game in games:
            try:
                # Extract game_key string from Game object
                if hasattr(game, 'game_key'):
                    game_key = game.game_key
                elif isinstance(game, str):
                    game_key = game
                else:
                    continue  # Skip silently
                
                # Get leagues for this game
                leagues = yfpy_query.get_user_leagues_by_game_key(game_key)
                if leagues:
                    leagues_list = leagues if isinstance(leagues, list) else [leagues]
                    all_leagues.extend(leagues_list)
            except Exception:
                # Silently skip games where user has no leagues
                pass
        
        return all_leagues
    except Exception as e:
        print(f"Error fetching user leagues: {e}")
        return []
    finally:
        # Restore original logging level
        yfpy_logger.setLevel(original_level)


def export_standings_to_csv(league_key, output_file):
    """Export league standings with head-to-head category stats to CSV."""
    print(f"\n{'='*60}")
    print(f"Exporting standings for league: {league_key}")
    print(f"Output file: {output_file}")
    print(f"{'='*60}\n")

    try:
        # Get credentials from settings
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        from config import settings
        from auth import get_valid_access_token, _load_users

        # Load user from storage
        users = _load_users()
        if not users:
            print("❌ No authenticated users found. Please run the main app first to authenticate.")
            sys.exit(1)

        # Get the first user (assumes single user)
        first_guid = list(users.keys())[0]
        user = users[first_guid]

        # Get valid access token (will refresh if needed)
        access_token = get_valid_access_token(user)

        # Reload user after potential refresh
        users = _load_users()
        user = users[first_guid]

        # Use direct API for better control over stat fetching
        headers = {'Authorization': f'Bearer {access_token}'}

        # Fetch league settings to get stat categories
        print("  Fetching league settings...")
        league_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/settings"
        league_response = requests.get(league_url, headers=headers)

        # Define namespace for XML parsing
        ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}

        # Parse league settings to get stat categories
        league_root = ET.fromstring(league_response.content)
        stat_categories = {}

        # Try both paths - stat_categories and stat_modifiers
        stat_modifiers = league_root.find('.//fantasy:stat_categories', ns)
        if stat_modifiers is None or len(list(stat_modifiers)) == 0:
            stat_modifiers = league_root.find('.//fantasy:stat_modifiers', ns)

        if stat_modifiers is not None:
            for stat in stat_modifiers.findall('fantasy:stats/fantasy:stat', ns):
                stat_id = stat.find('fantasy:stat_id', ns)
                display_name = stat.find('fantasy:display_name', ns)
                enabled = stat.find('fantasy:enabled', ns)
                if stat_id is not None and display_name is not None and enabled is not None:
                    if enabled.text == '1':
                        stat_categories[stat_id.text] = decode_if_bytes(display_name.text)

            # If that didn't work, try direct stat children
            if len(stat_categories) == 0:
                for stat in stat_modifiers.findall('fantasy:stat', ns):
                    stat_id = stat.find('fantasy:stat_id', ns)
                    display_name = stat.find('fantasy:display_name', ns)
                    enabled = stat.find('fantasy:enabled', ns)
                    if stat_id is not None and display_name is not None and enabled is not None:
                        if enabled.text == '1':
                            stat_categories[stat_id.text] = decode_if_bytes(display_name.text)

        print(f"  Found {len(stat_categories)} active stat categories")

        # Fetch standings with team stats
        print("  Fetching standings with category stats...")
        standings_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/standings"
        standings_response = requests.get(standings_url, headers=headers)
        standings_root = ET.fromstring(standings_response.content)

        # Parse teams and their stats
        teams_data = []
        teams_elem = standings_root.find('.//fantasy:teams', ns)
        if teams_elem is not None:
            for team_elem in teams_elem.findall('fantasy:team', ns):
                team_data = {}

                # Extract team key
                team_key_elem = team_elem.find('fantasy:team_key', ns)
                if team_key_elem is not None:
                    team_data['team_key'] = team_key_elem.text

                # Extract team name
                name_elem = team_elem.find('fantasy:name', ns)
                if name_elem is not None:
                    team_data['name'] = decode_if_bytes(name_elem.text)

                # Extract manager name
                managers_elem = team_elem.find('fantasy:managers', ns)
                if managers_elem is not None:
                    manager = managers_elem.find('fantasy:manager', ns)
                    if manager is not None:
                        nickname = manager.find('fantasy:nickname', ns)
                        if nickname is not None:
                            team_data['manager'] = decode_if_bytes(nickname.text)

                # Extract team standings
                team_standings_elem = team_elem.find('.//fantasy:team_standings', ns)
                if team_standings_elem is not None:
                    rank_elem = team_standings_elem.find('fantasy:rank', ns)
                    if rank_elem is not None:
                        team_data['rank'] = rank_elem.text

                    playoff_seed_elem = team_standings_elem.find('fantasy:playoff_seed', ns)
                    if playoff_seed_elem is not None:
                        team_data['playoff_seed'] = playoff_seed_elem.text

                    outcome_totals = team_standings_elem.find('fantasy:outcome_totals', ns)
                    if outcome_totals is not None:
                        wins = outcome_totals.find('fantasy:wins', ns)
                        losses = outcome_totals.find('fantasy:losses', ns)
                        ties = outcome_totals.find('fantasy:ties', ns)
                        percentage = outcome_totals.find('fantasy:percentage', ns)

                        if wins is not None:
                            team_data['wins'] = wins.text
                        if losses is not None:
                            team_data['losses'] = losses.text
                        if ties is not None:
                            team_data['ties'] = ties.text
                        if percentage is not None:
                            team_data['win_pct'] = percentage.text

                    points_for = team_standings_elem.find('fantasy:points_for', ns)
                    points_against = team_standings_elem.find('fantasy:points_against', ns)
                    if points_for is not None:
                        team_data['points_for'] = points_for.text
                    if points_against is not None:
                        team_data['points_against'] = points_against.text

                # Extract team stats (category totals)
                team_stats_elem = team_elem.find('.//fantasy:team_stats', ns)
                if team_stats_elem is not None:
                    stats_elem = team_stats_elem.find('fantasy:stats', ns)
                    if stats_elem is not None:
                        for stat in stats_elem.findall('fantasy:stat', ns):
                            stat_id = stat.find('fantasy:stat_id', ns)
                            value = stat.find('fantasy:value', ns)
                            if stat_id is not None and value is not None:
                                stat_name = stat_categories.get(stat_id.text, f"Stat_{stat_id.text}")
                                team_data[f"{stat_name}"] = value.text

                teams_data.append(team_data)

        # Build CSV with 3-row header structure matching Google Sheets format
        # Row 1: Empty cells, then "Skaters", then "Goalies"
        # Row 2: Empty cells, then "Records"/"Totals" for Skaters, then "Records"/"Totals" for Goalies
        # Row 3: Actual column names

        skater_stats = ['G', 'A', 'PIM', 'SOG', 'HIT', 'BLK']
        goalie_stats = ['W', 'GA', 'SV', 'SHO']

        # Write to CSV with manual header rows
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)

            # ROW 1: Category headers (Skaters, Goalies)
            row1 = ['', '', '', '', '', '', '', '', '', '']  # 10 empty cells for team info
            row1.extend(['', '', '', '', '', ''])  # 6 empty for Skater Records
            row1.append('Skaters')  # First Skater Total column
            row1.extend(['', '', '', '', ''])  # Remaining 5 Skater Totals
            row1.extend(['', '', '', ''])  # 4 empty for Goalie Records
            row1.append('Goalies')  # First Goalie Total column
            row1.extend(['', '', ''])  # Remaining 3 Goalie Totals
            writer.writerow(row1)

            # ROW 2: Sub-headers (Records, Totals)
            row2 = ['', '', '', '', '', '', '', '', '', '']  # 10 empty cells for team info
            row2.append('Records')  # Skater Records
            row2.extend(['', '', '', '', ''])  # Remaining 5 Skater Records
            row2.append('Totals')  # Skater Totals
            row2.extend(['', '', '', '', ''])  # Remaining 5 Skater Totals
            row2.append('Records')  # Goalie Records
            row2.extend(['', '', ''])  # Remaining 3 Goalie Records
            row2.append('Totals')  # Goalie Totals
            row2.extend(['', '', ''])  # Remaining 3 Goalie Totals
            writer.writerow(row2)

            # ROW 3: Column names
            row3 = [
                'Rank', 'Team Name', 'Manager', 'Wins', 'Losses', 'Ties',
                'Win %', 'Points For', 'Points Against', 'Playoff Seed'
            ]
            # Skater Records columns (6)
            row3.extend(skater_stats)
            # Skater Totals columns (6)
            row3.extend(skater_stats)
            # Goalie Records columns (4)
            row3.extend(goalie_stats)
            # Goalie Totals columns (4)
            row3.extend(goalie_stats)
            writer.writerow(row3)

            # Helper function to convert to int if value exists
            def to_int(value):
                """Convert to int if not empty, otherwise return empty string."""
                if value and value != '':
                    try:
                        return int(float(value))
                    except (ValueError, TypeError):
                        return value
                return ''

            # Helper function to format decimals
            def to_decimal(value, decimals=2):
                """Format as decimal if not empty, otherwise return empty string."""
                if value and value != '':
                    try:
                        return f"{float(value):.{decimals}f}"
                    except (ValueError, TypeError):
                        return value
                return ''

            # DATA ROWS
            for team in teams_data:
                row = [
                    to_int(team.get('rank', '')),
                    team.get('name', ''),
                    team.get('manager', ''),
                    to_int(team.get('wins', '')),
                    to_int(team.get('losses', '')),
                    to_int(team.get('ties', '')),
                    to_decimal(team.get('win_pct', ''), 3),
                    to_decimal(team.get('points_for', ''), 1),
                    to_decimal(team.get('points_against', ''), 1),
                    to_int(team.get('playoff_seed', ''))
                ]

                # Skater Records (empty - 6 columns)
                row.extend(['', '', '', '', '', ''])

                # Skater Totals (actual data - 6 columns) - all integers
                for stat in skater_stats:
                    row.append(to_int(team.get(stat, '')))

                # Goalie Records (empty - 4 columns)
                row.extend(['', '', '', ''])

                # Goalie Totals (actual data - 4 columns) - all integers
                for stat in goalie_stats:
                    row.append(to_int(team.get(stat, '')))

                writer.writerow(row)

        print(f"✅ Successfully exported standings with category stats to {output_file}\n")

    except Exception as e:
        print(f"❌ Error exporting standings: {e}")
        traceback.print_exc()


def export_players_to_csv(league_key, output_file=None):
    """
    Export comprehensive player data to CSV.
    
    Args:
        league_key: Yahoo league key (e.g., "465.l.34948")
        output_file: Output CSV filename (default: <league_key>_analysis.csv)
    """
    # Generate default filename from league key
    if output_file is None:
        # Replace dots with underscores for filename
        safe_league_key = league_key.replace('.', '_')
        output_file = f"{safe_league_key}_analysis.csv"
    
    print(f"\n{'='*60}")
    print(f"Exporting player data for league: {league_key}")
    print(f"Output file: {output_file}")
    print(f"{'='*60}\n")
    
    # Initialize YFPY
    yfpy_query = get_yfpy_query(league_key)
    
    # Fetch league data
    print("Fetching league information...")
    league_info = yfpy_query.get_league_key()
    print(f"League: {league_info}")
    
    # Fetch draft results
    print("\nFetching draft results...")
    draft_results = yfpy_query.get_league_draft_results()
    draft_dict = {}
    if isinstance(draft_results, list):
        for pick in draft_results:
            player_key = getattr(pick, 'player_key', None)
            if player_key:
                draft_dict[player_key] = {
                    'round': getattr(pick, 'round', None),
                    'pick': getattr(pick, 'pick', None),
                    'team_key': getattr(pick, 'team_key', None)
                }
        print(f"Loaded {len(draft_dict)} draft picks")
    
    # Fetch teams
    print("\nFetching league teams...")
    teams_data = yfpy_query.get_league_teams()
    teams_dict = {}
    teams_list = teams_data if isinstance(teams_data, list) else getattr(teams_data, 'teams', [])
    if teams_list:
        for team in teams_list:
            team_key = getattr(team, 'team_key', None)
            if team_key:
                manager_name = "Unknown"
                if hasattr(team, 'managers') and team.managers:
                    first_manager = team.managers[0] if isinstance(team.managers, list) else team.managers
                    manager_name = decode_if_bytes(getattr(first_manager, 'nickname', 'Unknown'))
                
                team_name = decode_if_bytes(getattr(team, 'name', 'Unknown'))
                teams_dict[team_key] = {
                    'name': team_name,
                    'manager': manager_name
                }
        print(f"Loaded {len(teams_dict)} teams")
    
    # Extract season from league_key (first part is game_key which contains season)
    game_id = league_key.split('.')[0]
    
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
        "458": 2025, "461": 2025, "465": 2025,  # 465 is NHL 2025 (season starts in 2024)
    }
    
    # Determine season from game_id
    season = GAME_SEASON_MAP.get(game_id, 2024)
    print(f"  Game ID: {game_id} → Season: {season}")
    
    # Warn about historical league limitations
    current_year = datetime.now().year
    if season < current_year - 1:
        print(f"\n  ⚠️  WARNING: This is a historical league from {season}")
        print(f"  Yahoo's API has limited data for past seasons:")
        print(f"    ✅ Fantasy Points totals are available")
        print(f"    ✅ Ownership and draft data are available")
        print(f"    ❌ Individual stat breakdowns (G, A, etc.) may show as empty")
        print(f"  This is a Yahoo API limitation, not a bug in this script.\n")
    
    # Note: We don't need to build a rostered_players map anymore
    # Current ownership comes from the 'ownership' field in player XML (reflects trades/waivers)
    # Drafted team comes from draft_dict
    
    # Fetch ALL players (top 1500 by fantasy points) using direct API call
    print("\nFetching player data (up to 1500 players, in batches of 25)...")
    all_players = []  # Build player list

    # Get access token
    access_token = None
    if hasattr(yfpy_query, 'oauth') and hasattr(yfpy_query.oauth, 'access_token'):
        access_token = yfpy_query.oauth.access_token

    if not access_token:
        print("  ⚠️  No access token found, trying to use auth module...")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        from auth import get_valid_access_token
        access_token = get_valid_access_token()

    headers = {'Authorization': f'Bearer {access_token}'}

    # Yahoo API returns max 25 players per call, so we need to paginate
    # Fetch 60 batches of 25 to get 1500 total (top players sorted by fantasy points)
    
    try:
        added_count = 0
        for batch_num in range(60):  # 60 batches = 1500 players
            start = batch_num * 25
            
            # API endpoint: includes ownership, draft_analysis, season stats
            # Note: NOT sorting by PTS because it might exclude players with 0 points
            # This will get ALL players in the league (rostered + free agents)
            api_url = (
                f"https://fantasysports.yahooapis.com/fantasy/v2/"
                f"leagues;league_keys={league_key}/players;start={start};count=25;sort=PTS;sort_type=season;"
                f"out=ownership,info,starting_status,percent_started,percent_owned,draft_analysis/"
                f"stats;type=season;season={season};extra_stat_ids=18,19,22,23,25,26,27,29,30,31,32,34"
            )
            
            print(f"  Fetching players {start}-{start+24}... (batch {batch_num + 1}/60)")
            response = requests.get(api_url, headers=headers)
            
            if response.status_code != 200:
                print(f"    ❌ API call failed with status {response.status_code}")
                continue
            
            # Parse XML response using same logic as before
            # Define namespace
            ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
            
            root = ET.fromstring(response.content)
            
            # Find the players element with namespace
            # Navigate: fantasy_content -> leagues -> league -> players -> player
            batch_added = 0
            leagues_elem = root.find('fantasy:leagues', ns)
            
            if leagues_elem is not None:
                for league in leagues_elem.findall('fantasy:league', ns):
                    players_elem = league.find('fantasy:players', ns)
                    if players_elem is not None:
                        player_elems = players_elem.findall('fantasy:player', ns)
                        print(f"    Found {len(player_elems)} player elements in this batch")
                        
                        # If we got 0 players in this batch, the API has no more players
                        if len(player_elems) == 0:
                            print(f"  API returned 0 players - no more players available")
                            batch_added = 0  # Signal to break outer loop
                            break
                        
                        for player_elem in player_elems:
                            try:
                                # Convert XML to dict for YFPY parsing
                                player_dict = {}
                                
                                # Helper function to strip namespace from tag
                                def strip_ns_local(tag):
                                    return tag.split('}')[-1] if '}' in tag else tag
                                
                                # Parse all player fields from XML
                                for child in player_elem:
                                    tag = strip_ns_local(child.tag)
                                    if tag in ['player_key', 'player_id', 'status', 'editorial_player_key', 'editorial_team_key',
                                               'editorial_team_full_name', 'editorial_team_abbr', 'display_position',
                                               'position_type', 'primary_position', 'uniform_number', 'is_undroppable', 'image_url']:
                                        player_dict[tag] = child.text
                                    elif tag == 'name':
                                        player_dict['name'] = {strip_ns_local(sc.tag): sc.text for sc in child}
                                    elif tag == 'headshot':
                                        player_dict['headshot'] = {strip_ns_local(sc.tag): sc.text for sc in child}
                                    elif tag == 'percent_owned':
                                        if child.text and child.text.strip():
                                            player_dict['percent_owned'] = {'value': child.text.strip()}
                                        else:
                                            player_dict['percent_owned'] = {strip_ns_local(sc.tag): sc.text for sc in child}
                                    elif tag == 'ownership':
                                        # Parse current ownership (team that currently owns the player)
                                        player_dict['ownership'] = {strip_ns_local(sc.tag): sc.text for sc in child}
                                    elif tag == 'draft_analysis':
                                        player_dict['draft_analysis'] = {strip_ns_local(sc.tag): sc.text for sc in child}
                                    elif tag == 'player_stats':
                                        stats_dict = {'coverage_type': 'season', 'stats': []}
                                        for sc in child:
                                            if strip_ns_local(sc.tag) == 'stats':
                                                for stat in sc:
                                                    if strip_ns_local(stat.tag) == 'stat':
                                                        stat_data = {strip_ns_local(sf.tag): sf.text for sf in stat}
                                                        stats_dict['stats'].append({'stat': stat_data})
                                        player_dict['player_stats'] = stats_dict
                                    elif tag == 'player_points':
                                        player_dict['player_points'] = {strip_ns_local(sc.tag): sc.text for sc in child}
                                
                                # Convert to Player object
                                try:
                                    player = Data(player_dict, None).to_model(Player)
                                except Exception:
                                    # Fallback: create simple object
                                    class SimpleObject:
                                        def __init__(self, data):
                                            if isinstance(data, dict):
                                                for key, value in data.items():
                                                    if isinstance(value, dict):
                                                        setattr(self, key, SimpleObject(value))
                                                    elif isinstance(value, list):
                                                        setattr(self, key, [SimpleObject(item) if isinstance(item, dict) else item for item in value])
                                                    else:
                                                        setattr(self, key, value)
                                            else:
                                                self.value = data
                                    player = SimpleObject(player_dict)
                                
                                player_key = getattr(player, 'player_key', None)
                                if player_key:
                                    all_players.append(player)
                                    added_count += 1
                                    batch_added += 1
                            
                            except Exception as parse_error:
                                print(f"      Error parsing player: {parse_error}")
                                continue
                        
                        print(f"    Added {batch_added} players from this batch")
                        
                        # If we got 0 players, we've reached the end - no need to continue
                        if batch_added == 0:
                            print(f"  Reached end of available players at batch {batch_num + 1}")
                            break
            
            # If we got 0 players in this batch, stop fetching more batches
            if batch_added == 0:
                break
        
        print(f"  ✅ Fetched {added_count} total players!")
    
    except Exception as e:
        print(f"  ❌ API call failed: {e}")
        traceback.print_exc()
    
    print(f"\nTotal players loaded: {len(all_players)}")
    
    # Now process the CSV writing section below
    
    if len(all_players) == 0:
        print("❌ No players found! Check your league key or try again.")
        return

    # Sort players by Fantasy Points (descending)
    print(f"\nSorting {len(all_players)} players by Fantasy Points...")
    def get_fantasy_points(player):
        try:
            if hasattr(player, 'player_points') and player.player_points:
                total = getattr(player.player_points, 'total', None)
                if total:
                    return float(total)
        except (ValueError, TypeError, AttributeError):
            pass
        return 0.0

    all_players.sort(key=get_fantasy_points, reverse=True)

    # Process players and write to CSV
    print(f"Writing to CSV: {output_file}")
    print(f"  Note: Free agents won't have Draft Round/Pick data (not drafted in your league)")
    print(f"        Games Played = GP for skaters, GS (Games Started) for goalies")
    print(f"        Points = Goals + Assists (calculated)")
    print(f"        Save % = Saves / (Saves + GA) (calculated)")
    print(f"        Fan Pts/GP = Fantasy Points / GP (or GS for goalies) (calculated)")
    
    csv_headers = [
        'Player',
        'Pos',
        'Team',
        'Rank',
        'Fan Pts',  # Fantasy Points
        'Cur Team',  # Current Team (trades/waivers)
        'Owner',
        'Draft Team',
        'Draft Owner',
        'Rd',  # Draft Round
        'Pick',  # Draft Pick
        # Draft Analysis (Yahoo aggregate across all leagues)
        'ADP',
        '% Draft',  # Percent Drafted
        # Skater stats
        'GP',  # GP for skaters, GS for goalies
        'G',
        'A',
        'P',  # Points
        'PIM',
        'SOG',
        'HIT',
        'BLK',
        # Goalie stats
        'W',
        'SV',
        'SV%',
        'GA',
        'SO',
        # Ownership
        '% Own',
        # Performance
        'Fan Pts/GP',  # Fantasy Points per Game
        'ID'  # Yahoo Player Key
    ]
    
    players_with_stats = 0
    players_without_stats = 0
    
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        writer.writeheader()
        
        for idx, player in enumerate(all_players, 1):
            # Extract player key (Yahoo Player ID)
            player_key = getattr(player, 'player_key', '')

            # Extract player name
            player_name = "Unknown"
            if hasattr(player, 'name'):
                name = player.name
                if isinstance(name, dict):
                    player_name = decode_if_bytes(name.get('full', 'Unknown'))
                else:
                    player_name = decode_if_bytes(getattr(name, 'full', 'Unknown'))

            # Extract position
            position = decode_if_bytes(getattr(player, 'display_position',
                       getattr(player, 'primary_position',
                       getattr(player, 'position_type', '-'))))

            # Check if player is a goalie
            is_goalie = 'G' in str(position).upper()

            # Extract NHL team
            nhl_team = decode_if_bytes(getattr(player, 'editorial_team_abbr', '-'))
            
            # Extract draft_analysis - Yahoo's aggregate data across all leagues
            adp = pct_drafted = None
            if hasattr(player, 'draft_analysis') and player.draft_analysis:
                try:
                    avg_pick_val = getattr(player.draft_analysis, 'average_pick', None)
                    if avg_pick_val and avg_pick_val != '-':
                        adp = float(avg_pick_val)
                except (ValueError, TypeError, AttributeError):
                    pass
                
                try:
                    pct_drafted_val = getattr(player.draft_analysis, 'percent_drafted', None)
                    if pct_drafted_val and pct_drafted_val != '-':
                        pct_drafted = float(pct_drafted_val)
                except (ValueError, TypeError, AttributeError):
                    pass
            
            # Extract fantasy points
            fantasy_points = None
            if hasattr(player, 'player_points') and player.player_points:
                try:
                    total = getattr(player.player_points, 'total', None)
                    if total:
                        fantasy_points = float(total)
                except (ValueError, TypeError, AttributeError):
                    pass
            
            # Extract ownership percentage
            # Free agents will have this from the XML API call
            # Rostered players from get_team_roster_player_stats won't have it
            pct_owned = None
            if hasattr(player, 'percent_owned') and player.percent_owned:
                try:
                    # percent_owned might be a dict or object with 'value' key/attr
                    if isinstance(player.percent_owned, dict):
                        owned_val = player.percent_owned.get('value')
                    else:
                        owned_val = getattr(player.percent_owned, 'value', None)
                    if owned_val and owned_val != '-':
                        pct_owned = float(owned_val)
                except (ValueError, TypeError, AttributeError):
                    pass
            
            # Extract stats (try multiple sources)
            # Skater stats
            goals = assists = points = pim = sog = hits = blocks = None
            # Goalie stats
            wins = saves = save_pct = ga = shutouts = games_played = games_started = None
            
            # Try to get stats from player_stats (season stats)
            if hasattr(player, 'player_stats') and player.player_stats:
                stats = player.player_stats
                if hasattr(stats, 'stats') and stats.stats:
                    stat_list = stats.stats if isinstance(stats.stats, list) else [stats.stats]
                    for stat_obj in stat_list:
                        # Check if there's a nested 'stat' object
                        if hasattr(stat_obj, 'stat'):
                            stat = stat_obj.stat
                        else:
                            stat = stat_obj

                        stat_id = str(getattr(stat, 'stat_id', ''))
                        value = getattr(stat, 'value', None)

                        # Try to convert value to number
                        try:
                            value = float(value) if value and value != '-' else None
                        except (ValueError, TypeError):
                            value = None
                        
                        # Common NHL stat IDs (may vary by league settings)
                        # Skater stats
                        if stat_id in ['1', 'G']:  # Goals
                            goals = value
                        elif stat_id in ['2', 'A']:  # Assists
                            assists = value
                        elif stat_id in ['3', 'P', 'PTS']:  # Points
                            points = value
                        elif stat_id in ['5', 'PIM']:  # Penalty Minutes
                            pim = value
                        elif stat_id in ['14', 'SOG', 'SHT']:  # Shots on Goal
                            sog = value
                        elif stat_id in ['31', 'HIT']:  # Hits
                            hits = value
                        elif stat_id in ['32', 'BLK']:  # Blocks
                            blocks = value
                        elif stat_id in ['29', 'GP']:  # Games Played (skaters)
                            games_played = value
                        # Goalie stats
                        elif stat_id in ['18', '30', 'GS']:  # Games Started (goalies) - stat_id 18 or 30
                            games_started = value
                        elif stat_id in ['19', 'W']:  # Wins
                            wins = value
                        elif stat_id in ['25', 'SV']:  # Saves
                            saves = value
                        elif stat_id in ['22', 'GA']:  # Goals Against
                            ga = value
                        elif stat_id in ['27', 'SO']:  # Shutouts
                            shutouts = value
            
            # Derive calculated stats
            # Points = Goals + Assists (for skaters)
            if goals is not None and assists is not None:
                points = goals + assists
            elif goals is not None and assists is None:
                points = goals
            elif assists is not None and goals is None:
                points = assists
            # If both are None, points stays None
            
            # Save % = Saves / (Saves + GA) for goalies
            if saves is not None and ga is not None and (saves + ga) > 0:
                save_pct = saves / (saves + ga)
            # If we don't have both stats, save_pct stays None

            # For GP column: use Games Started for goalies, Games Played for skaters
            gp_value = games_started if is_goalie and games_started is not None else games_played

            # Calculate Fantasy Points per Game (or per GS for goalies)
            fan_pts_per_gp = None
            if fantasy_points is not None and gp_value is not None and gp_value > 0:
                fan_pts_per_gp = fantasy_points / gp_value

            # Extract CURRENT ownership (from XML - reflects trades/waivers)
            current_team = '-'
            current_owner = '-'
            if hasattr(player, 'ownership') and player.ownership:
                ownership = player.ownership
                if isinstance(ownership, dict):
                    current_team = decode_if_bytes(ownership.get('owner_team_name', '-'))
                    # Try to match team key to get manager name
                    owner_team_key = ownership.get('owner_team_key')
                    if owner_team_key and owner_team_key in teams_dict:
                        current_owner = teams_dict[owner_team_key]['manager']
                else:
                    current_team = decode_if_bytes(getattr(ownership, 'owner_team_name', '-'))
                    owner_team_key = getattr(ownership, 'owner_team_key', None)
                    if owner_team_key and owner_team_key in teams_dict:
                        current_owner = teams_dict[owner_team_key]['manager']
            
            # Get DRAFTED team info from YOUR league (original draft)
            draft_info = draft_dict.get(player_key, {})
            draft_round = draft_info.get('round', '-')
            draft_pick = draft_info.get('pick', '-')
            drafted_team = '-'
            drafted_by = '-'
            draft_team_key = draft_info.get('team_key')
            if draft_team_key and draft_team_key in teams_dict:
                drafted_team = teams_dict[draft_team_key]['name']
                drafted_by = teams_dict[draft_team_key]['manager']
            
            # Track stats availability
            if any([goals, assists, points, pim, sog, hits, blocks, wins, saves, save_pct, ga, shutouts]):
                players_with_stats += 1
            else:
                players_without_stats += 1
            
            # Helper function to format integer stats (no decimal points)
            def int_or_empty(value):
                """Convert to int if not None, otherwise return empty string."""
                return int(value) if value is not None else ''

            # Helper function to format decimal stats
            def decimal_or_empty(value, decimals=2):
                """Format as decimal if not None, otherwise return empty string."""
                return f"{float(value):.{decimals}f}" if value is not None else ''

            # Write row (use empty string instead of '-' for missing values)
            writer.writerow({
                'Player': player_name,
                'ID': player_key,
                'Pos': position,
                'Team': nhl_team,
                'Rank': idx,
                'Fan Pts': decimal_or_empty(fantasy_points),
                'Cur Team': current_team if current_team != '-' else '',
                'Owner': current_owner if current_owner != '-' else '',
                'Draft Team': drafted_team if drafted_team != '-' else '',
                'Draft Owner': drafted_by if drafted_by != '-' else '',
                'Rd': int_or_empty(draft_round) if draft_round != '-' else '',
                'Pick': int_or_empty(draft_pick) if draft_pick != '-' else '',
                'ADP': decimal_or_empty(adp, 1),
                '% Draft': decimal_or_empty(pct_drafted, 1),
                'GP': int_or_empty(gp_value),
                'G': int_or_empty(goals),
                'A': int_or_empty(assists),
                'P': int_or_empty(points),
                'PIM': int_or_empty(pim),
                'SOG': int_or_empty(sog),
                'HIT': int_or_empty(hits),
                'BLK': int_or_empty(blocks),
                'W': int_or_empty(wins),
                'SV': int_or_empty(saves),
                'SV%': decimal_or_empty(save_pct, 3),
                'GA': int_or_empty(ga),
                'SO': int_or_empty(shutouts),
                '% Own': decimal_or_empty(pct_owned, 1),
                'Fan Pts/GP': decimal_or_empty(fan_pts_per_gp, 2)
            })
    
    print(f"\n✅ Successfully exported {len(all_players)} players to {output_file}")
    print(f"  Players with stats: {players_with_stats}")
    print(f"  Players without stats: {players_without_stats}")
    
    # Export standings to separate CSV
    safe_league_key = league_key.replace('.', '_')
    standings_file = f"{safe_league_key}_standings.csv"
    export_standings_to_csv(league_key, standings_file)


def upload_to_google_sheets(league_key, spreadsheet_id):
    """Upload exported CSVs to Google Sheets."""
    try:
        # Import upload functions
        from upload_to_sheets import (
            get_sheets_service,
            upload_player_analysis,
            upload_standings,
            get_season_from_league_key
        )

        # Detect season from league key
        season, game_id = get_season_from_league_key(league_key)

        # Generate CSV file names
        safe_league_key = league_key.replace('.', '_')
        analysis_csv = f"{safe_league_key}_analysis.csv"
        standings_csv = f"{safe_league_key}_standings.csv"

        # Generate sheet names based on season
        players_sheet_name = f"{season} Players"
        standings_sheet_name = f"{season} Standings"

        print(f"\n{'='*60}")
        print("Uploading to Google Sheets")
        print(f"{'='*60}")
        print(f"Season: {season} (Game ID: {game_id})")
        print(f"Spreadsheet ID: {spreadsheet_id}")
        print(f"Target sheets: '{players_sheet_name}' and '{standings_sheet_name}'")

        # Get Google Sheets service
        service = get_sheets_service()

        # Upload both sheets
        upload_player_analysis(service, spreadsheet_id, analysis_csv, sheet_name=players_sheet_name)
        upload_standings(service, spreadsheet_id, standings_csv, sheet_name=standings_sheet_name)

        print(f"\n✅ Upload complete!")
        print(f"View your spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    except ImportError as e:
        print(f"\n⚠️  Google Sheets upload failed: Missing dependencies")
        print(f"    Run: pip install google-auth google-api-python-client")
    except FileNotFoundError as e:
        print(f"\n⚠️  Google Sheets upload failed: {e}")
        print(f"    Make sure credentials are set up at: backend/data/google_sheets_credentials.json")
        print(f"    See GOOGLE_SHEETS_SETUP.md for instructions")
    except Exception as e:
        print(f"\n⚠️  Google Sheets upload failed: {e}")
        print(f"    See GOOGLE_SHEETS_SETUP.md for troubleshooting")


if __name__ == "__main__":
    import argparse

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Export Yahoo Fantasy league data to CSV (and optionally upload to Google Sheets)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (choose from your leagues)
  python export_players.py

  # Direct mode with league key
  python export_players.py 465.l.34948

  # Export and upload to Google Sheets
  python export_players.py 465.l.34948 --spreadsheet-id 15eH6iapchiEcYtvU8nK8rFA6pC7SixYU5RnM1NtTLLg

  # Export only (skip upload even if spreadsheet-id is set)
  python export_players.py 465.l.34948 --no-upload
        """
    )
    parser.add_argument('league_key', nargs='?', help='Yahoo league key (e.g., 465.l.34948)')
    parser.add_argument('--output', help='Custom output filename for player analysis CSV')
    parser.add_argument('--spreadsheet-id', help='Google Sheets spreadsheet ID for automatic upload')
    parser.add_argument('--no-upload', action='store_true', help='Skip Google Sheets upload (even if spreadsheet-id is provided)')

    args = parser.parse_args()

    # Determine which league to export
    league_key = None

    if args.league_key:
        # Direct mode: use provided league key
        league_key = args.league_key
        export_players_to_csv(league_key, output_file=args.output)
    else:
        # Interactive mode: let user choose from their leagues
        print("\n" + "="*60)
        print("Yahoo Fantasy Player & Standings Export Tool")
        print("="*60)

        # Initialize YFPY with a temporary league to get user's leagues
        # We'll use a dummy league key just to authenticate
        print("\nAuthenticating with Yahoo...")

        # Import settings and auth
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
        from config import settings
        from auth import get_authenticated_user

        # Get authenticated user (handles first-time OAuth if needed)
        try:
            user = get_authenticated_user()
            access_token = user.access_token
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            sys.exit(1)

        if not access_token:
            print("❌ Failed to authenticate. Please check your credentials.")
            sys.exit(1)

        print("✅ Authenticated successfully!\n")

        # Initialize YFPY with NHL game (465) to fetch user's leagues
        # Set required environment variables for YFPY
        os.environ['YAHOO_CONSUMER_KEY'] = settings.yahoo_client_id
        os.environ['YAHOO_CONSUMER_SECRET'] = settings.yahoo_client_secret

        # Create YFPY query object (no specific league needed for fetching user leagues)
        # Use minimal parameters - we just need to authenticate to fetch leagues
        yfpy_query = YahooFantasySportsQuery(
            league_id="1",  # Dummy league ID
            game_id="465",  # NHL 2025
            game_code="nhl",
            offline=False,
            yahoo_consumer_key=settings.yahoo_client_id,
            yahoo_consumer_secret=settings.yahoo_client_secret,
            yahoo_access_token_json={
                "access_token": access_token,
                "refresh_token": user.refresh_token,
                "consumer_key": settings.yahoo_client_id,
                "consumer_secret": settings.yahoo_client_secret,
                "guid": user.yahoo_guid,
                "token_type": "Bearer",
                "token_time": user.token_expires_at.timestamp() if user.token_expires_at else datetime.now().timestamp()
            },
            browser_callback=False
        )

        # Fetch user's leagues
        leagues = get_user_leagues(yfpy_query)

        if not leagues:
            print("❌ No leagues found. Please check your account.")
            sys.exit(1)

        # Display leagues
        print(f"\nFound {len(leagues)} leagues:\n")
        for idx, league in enumerate(leagues, 1):
            league_name = decode_if_bytes(getattr(league, 'name', 'Unknown'))
            league_key_temp = getattr(league, 'league_key', 'Unknown')
            game_code = getattr(league, 'game_code', 'Unknown').upper()
            season = getattr(league, 'season', 'Unknown')

            print(f"  {idx}. [{game_code} {season}] {league_name}")
            print(f"     League Key: {league_key_temp}")

        # Let user choose
        print()
        try:
            choice = input("Enter the number of the league to export (or 'q' to quit): ").strip()

            if choice.lower() == 'q':
                print("Exiting...")
                sys.exit(0)

            choice_num = int(choice)
            if 1 <= choice_num <= len(leagues):
                selected_league = leagues[choice_num - 1]
                league_key = getattr(selected_league, 'league_key')
                league_name = decode_if_bytes(getattr(selected_league, 'name', 'Unknown'))

                print(f"\n{'='*60}")
                print(f"Selected: {league_name}")
                print(f"League Key: {league_key}")
                print(f"{'='*60}\n")

                # Export the selected league
                export_players_to_csv(league_key, output_file=args.output)
            else:
                print(f"❌ Invalid choice. Please enter a number between 1 and {len(leagues)}.")
                sys.exit(1)
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\nExiting...")
            sys.exit(0)

    # After export, check if we should upload to Google Sheets
    if league_key and not args.no_upload:
        spreadsheet_id = args.spreadsheet_id

        # If no spreadsheet ID provided, ask user
        if not spreadsheet_id:
            print(f"\n{'='*60}")
            print("Google Sheets Upload")
            print(f"{'='*60}")

            try:
                upload_choice = input("\nWould you like to upload to Google Sheets? (y/n): ").strip().lower()

                if upload_choice in ['y', 'yes']:
                    spreadsheet_id = input("Enter your Google Sheets spreadsheet ID: ").strip()

                    if not spreadsheet_id:
                        print("⚠️  No spreadsheet ID provided. Skipping upload.")
                    else:
                        upload_to_google_sheets(league_key, spreadsheet_id)
                else:
                    print("Skipping Google Sheets upload.")
            except KeyboardInterrupt:
                print("\n\nSkipping Google Sheets upload.")
        else:
            # Spreadsheet ID was provided via command line
            upload_to_google_sheets(league_key, spreadsheet_id)
