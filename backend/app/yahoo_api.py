"""Yahoo Fantasy Sports API wrapper with optional yfpy support."""
import json
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from pathlib import Path
from app.models import User, League, Team, Player
from app.database import SessionLocal
from app.auth import get_valid_access_token
import os

# YFPY imports are optional (commented out for now)
# from yfpy.query import YahooFantasySportsQuery
# from yfpy.data import Data


class YahooAPIClient:
    """Wrapper around yfpy for Yahoo Fantasy Sports API interactions."""
    
    def __init__(self, user: User, data_dir: Optional[Path] = None):
        """Initialize Yahoo API client with user authentication."""
        self.user = user
        self.access_token = get_valid_access_token(user)
        
        # Set up data directory for yfpy
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
        
        # Store data directory for later YFPY initialization
        self.data_dir = data_dir
        self.yahoo_query = None  # Will be initialized per-league as needed
        
        # Also keep direct API access for custom endpoints
        self.base_url = "https://fantasysports.yahooapis.com/fantasy/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"  # Request JSON response
        }
    
    def get_yfpy_query(self, league_id: str, game_code: str = "nhl"):
        """Get or create YFPY query instance for a specific league."""
        try:
            from yfpy.query import YahooFantasySportsQuery
            
            # Create YFPY instance for this specific league
            yahoo_query = YahooFantasySportsQuery(
                league_id=league_id,
                game_code=game_code,
                offline=False,
                all_output_as_json=True,
                consumer_key=os.getenv("YAHOO_CLIENT_ID"),
                consumer_secret=os.getenv("YAHOO_CLIENT_SECRET"),
                browser_callback=False
            )
            
            # Inject our access token
            if hasattr(yahoo_query, 'oauth'):
                yahoo_query.oauth.access_token = self.access_token
                yahoo_query.oauth.token_time = 9999999999  # Prevent refresh attempts
            
            return yahoo_query
        except Exception as e:
            print(f"Could not initialize YFPY for league {league_id}: {e}")
            return None
    
    def _make_request(self, endpoint: str) -> dict:
        """Make API request to Yahoo Fantasy Sports API."""
        import requests
        
        # Add format=json to the endpoint
        separator = '&' if '?' in endpoint else '?'
        url = f"{self.base_url}/{endpoint}{separator}format=json"
        
        # Log request for debugging
        print(f"Making Yahoo API request to: {url}")
        print(f"Using access token: {self.access_token[:20]}..." if self.access_token else "No access token!")
        
        response = requests.get(url, headers=self.headers)
        
        # Log response status
        print(f"Yahoo API response: {response.status_code}")
        
        # Check for authentication errors
        if response.status_code == 401:
            error_msg = f"Unauthorized: {response.text[:200]}"
            print(f"Yahoo API authentication error: {error_msg}")
            raise requests.exceptions.HTTPError(f"401 Unauthorized: {error_msg}")
        
        response.raise_for_status()
        
        # With format=json, Yahoo returns proper JSON
        return response.json()
    
    def _parse_xml_response(self, xml_text: str) -> dict:
        """Parse XML response from Yahoo API into a dictionary."""
        try:
            root = ET.fromstring(xml_text)
            return self._xml_to_dict(root)
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            print(f"Response text: {xml_text[:500]}")
            return {"error": "Failed to parse XML response", "raw": xml_text}
    
    def _xml_to_dict(self, element: ET.Element) -> dict:
        """Recursively convert XML element to dictionary."""
        result = {}
        
        # Add attributes
        if element.attrib:
            result.update(element.attrib)
        
        # Add text content if present
        if element.text and element.text.strip():
            # If element has no children, use text as value
            if len(element) == 0:
                return element.text.strip()
            else:
                result["_text"] = element.text.strip()
        
        # Process children
        for child in element:
            child_dict = self._xml_to_dict(child)
            # Strip namespace from tag name
            child_tag = child.tag
            if '}' in child_tag:
                child_tag = child_tag.split('}', 1)[1]  # Remove namespace
            
            # If multiple children with same tag, make it a list
            if child_tag in result:
                if not isinstance(result[child_tag], list):
                    result[child_tag] = [result[child_tag]]
                result[child_tag].append(child_dict)
            else:
                result[child_tag] = child_dict
        
        return result
    
    def get_user_games(self) -> List[dict]:
        """Get all games for the authenticated user."""
        endpoint = "users;use_login=1/games"
        response = self._make_request(endpoint)
        
        # Parse Yahoo's JSON structure:
        # fantasy_content -> users -> "0" -> user (array) -> games object -> numbered keys -> game
        try:
            fantasy_content = response.get('fantasy_content', {})
            users = fantasy_content.get('users', {})
            user_data = users.get('0', {})
            user_array = user_data.get('user', [])
            
            # The user array has guid as first element, games as second element
            if len(user_array) < 2:
                print("DEBUG: user array too short")
                return []
            
            games_obj = user_array[1].get('games', {})
            
            # games_obj is a dict with numbered keys "0", "1", "2", etc.
            # Each contains a "game" key with either a dict or list
            game_list = []
            for key in games_obj:
                if key == 'count':
                    continue
                game_entry = games_obj[key].get('game')
                if game_entry:
                    # game_entry can be a dict or a list
                    if isinstance(game_entry, list):
                        game_list.extend(game_entry)
                    else:
                        game_list.append(game_entry)
            
            return game_list
        except Exception as e:
            print(f"Error parsing games response: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_user_leagues(self, game_key: Optional[str] = None) -> List[dict]:
        """Get all leagues for a specific game, or all leagues if game_key is None."""
        if game_key:
            endpoint = f"users;use_login=1/games;game_keys={game_key}/leagues"
        else:
            endpoint = "users;use_login=1/games/leagues"
        
        response = self._make_request(endpoint)
        
        # Parse Yahoo's JSON structure
        try:
            fantasy_content = response.get('fantasy_content', {})
            users = fantasy_content.get('users', {})
            user_data = users.get('0', {})
            user_array = user_data.get('user', [])
            
            if len(user_array) < 2:
                return []
            
            games_obj = user_array[1].get('games', {})
            
            league_list = []
            # Iterate through all games
            for key in games_obj:
                if key == 'count':
                    continue
                
                game_data = games_obj[key]
                game = game_data.get('game')
                
                if not game:
                    continue
                
                # If game is a list, the leagues are in the second element
                leagues_obj = {}
                if isinstance(game, list):
                    # Yahoo returns [game_info, {leagues: {...}}]
                    if len(game) > 1 and isinstance(game[1], dict):
                        leagues_obj = game[1].get('leagues', {})
                    else:
                        # Fallback: check first element
                        leagues_obj = game[0].get('leagues', {}) if game else {}
                else:
                    leagues_obj = game.get('leagues', {})
                
                # Extract leagues from leagues_obj
                for league_key in leagues_obj:
                    if league_key == 'count':
                        continue
                    league_entry = leagues_obj[league_key].get('league')
                    if league_entry:
                        if isinstance(league_entry, list):
                            league_list.extend(league_entry)
                        else:
                            league_list.append(league_entry)
            
            return league_list
        except Exception as e:
            print(f"Error parsing leagues response: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_league_info(self, league_key: str) -> dict:
        """Get league information."""
        endpoint = f"league/{league_key}"
        response = self._make_request(endpoint)
        
        # Extract league data from nested JSON structure
        try:
            fantasy_content = response.get('fantasy_content', {})
            league_data = fantasy_content.get('league', [])
            
            # Yahoo returns league as an array of objects
            if isinstance(league_data, list) and len(league_data) > 0:
                # The first element usually contains the core league info
                league_info = league_data[0]
                
                # Extract useful fields
                result = {
                    'league_key': league_info.get('league_key'),
                    'league_id': league_info.get('league_id'),
                    'name': league_info.get('name'),
                    'season': league_info.get('season'),
                    'game_code': league_info.get('game_code'),
                    'league_type': league_info.get('league_type'),
                    'url': league_info.get('url'),
                    'num_teams': league_info.get('num_teams'),
                    'scoring_type': league_info.get('scoring_type'),
                    'current_week': league_info.get('current_week'),
                    'start_week': league_info.get('start_week'),
                    'end_week': league_info.get('end_week'),
                }
                
                return result
            
            # Fallback: return raw response if structure is unexpected
            return response
        except Exception as e:
            print(f"Error parsing league info: {e}")
            print(f"Raw response: {response}")
            return response
    
    def get_league_teams(self, league_key: str) -> List[dict]:
        """Get all teams in a league."""
        endpoint = f"league/{league_key}/teams"
        return self._make_request(endpoint)
    
    def get_league_standings(self, league_key: str) -> List[dict]:
        """Get league standings - using direct API for reliability."""
        print(f"Getting standings for league: {league_key}")
        
        # Just use direct API - it's more reliable than trying to wrap yahoo-fantasy-api
        return self._get_standings_direct_api(league_key)
    
    def _get_standings_direct_api(self, league_key: str) -> List[dict]:
        """Direct API fallback for getting standings."""
        endpoint = f"league/{league_key}/standings"
        response = self._make_request(endpoint)
        
        # Try to parse the response
        try:
            fantasy_content = response.get('fantasy_content', {})
            league_data = fantasy_content.get('league', [])
            
            print(f"Parsing standings - league_data type: {type(league_data)}")
            
            # league_data is a list: [league_info_dict, standings_dict]
            standings_obj = None
            if isinstance(league_data, list) and len(league_data) > 1:
                # Second element usually contains standings
                standings_obj = league_data[1]
                print(f"Found standings object: {standings_obj.keys() if isinstance(standings_obj, dict) else type(standings_obj)}")
            
            if not standings_obj or not isinstance(standings_obj, dict):
                print("No standings object found")
                return []
            
            # Extract standings list
            standings_list = standings_obj.get('standings', [])
            if not standings_list or not isinstance(standings_list, list):
                print("No standings list found")
                return []
            
            # First element of standings list contains teams
            teams_container = standings_list[0] if len(standings_list) > 0 else {}
            teams_data = teams_container.get('teams', {}) if isinstance(teams_container, dict) else {}
            
            if not isinstance(teams_data, dict):
                print(f"Teams data is not a dict: {type(teams_data)}")
                return []
            
            print(f"Found {len(teams_data)} team entries")
            
            # teams_data is a dict with numbered keys ('0', '1', '2'..., 'count')
            teams = []
            for key, value in teams_data.items():
                if key == 'count':
                    continue
                    
                if not isinstance(value, dict) or 'team' not in value:
                    continue
                
                team_info = value['team']
                
                # team_info is a list: [[team_attrs], {team_stats}, {team_standings}]
                if not isinstance(team_info, list) or len(team_info) < 3:
                    print(f"Unexpected team_info structure for key {key}: {type(team_info)}")
                    continue
                
                # First element is a list of team attribute objects
                team_attrs_list = team_info[0] if len(team_info) > 0 else []
                team_standings_obj = team_info[2] if len(team_info) > 2 else {}
                
                # Parse team attributes from the list
                team_key = None
                team_id = None
                name = None
                manager_nickname = None
                
                if isinstance(team_attrs_list, list):
                    for attr in team_attrs_list:
                        if isinstance(attr, dict):
                            if 'team_key' in attr:
                                team_key = attr['team_key']
                            elif 'team_id' in attr:
                                team_id = attr['team_id']
                            elif 'name' in attr:
                                name = attr['name']
                            elif 'managers' in attr:
                                managers = attr['managers']
                                if isinstance(managers, list) and len(managers) > 0:
                                    manager_data = managers[0].get('manager', {})
                                    manager_nickname = manager_data.get('nickname')
                
                # Extract standings data
                team_standings = team_standings_obj.get('team_standings', {}) if isinstance(team_standings_obj, dict) else {}
                outcome_totals = team_standings.get('outcome_totals', {})
                
                teams.append({
                    'team_key': team_key,
                    'team_id': team_id,
                    'name': name,
                    'manager': manager_nickname,
                    'wins': int(outcome_totals.get('wins', 0)),
                    'losses': int(outcome_totals.get('losses', 0)),
                    'ties': int(outcome_totals.get('ties', 0)),
                    'points_for': float(team_standings.get('points_for', 0)),
                    'points_against': float(team_standings.get('points_against', 0)),
                    'standing': int(team_standings.get('rank', 0)),
                })
            
            print(f"Successfully parsed {len(teams)} teams")
            return teams
        except Exception as e:
            print(f"Error parsing direct API standings: {e}")
            return []
    
    def get_league_players(self, league_key: str, start: int = 0, count: int = 25) -> List[dict]:
        """Get players in a league."""
        endpoint = f"league/{league_key}/players;start={start};count={count}"
        return self._make_request(endpoint)
    
    def get_team_roster(self, team_key: str, week: Optional[int] = None) -> List[dict]:
        """Get team roster."""
        if week:
            endpoint = f"team/{team_key}/roster;week={week}"
        else:
            endpoint = f"team/{team_key}/roster"
        return self._make_request(endpoint)
    
    def get_player_stats(self, player_key: str, week: Optional[int] = None) -> dict:
        """Get player statistics."""
        if week:
            endpoint = f"player/{player_key}/stats;week={week}"
        else:
            endpoint = f"player/{player_key}/stats"
        return self._make_request(endpoint)
    
    def get_league_draft_results(self, league_key: str) -> List[dict]:
        """Get draft results for a league."""
        endpoint = f"league/{league_key}/draftresults"
        return self._make_request(endpoint)
    
    def get_league_transactions(self, league_key: str, transaction_type: Optional[str] = None) -> List[dict]:
        """Get league transactions (trades, adds, drops, etc.)."""
        if transaction_type:
            endpoint = f"league/{league_key}/transactions;types={transaction_type}"
        else:
            endpoint = f"league/{league_key}/transactions"
        return self._make_request(endpoint)
    
    def get_league_matchups(self, league_key: str, week: int) -> List[dict]:
        """Get league matchups for a specific week."""
        endpoint = f"league/{league_key}/scoreboard;week={week}"
        return self._make_request(endpoint)
    
    def get_game_info(self, game_key: str) -> dict:
        """Get game information."""
        endpoint = f"game/{game_key}"
        return self._make_request(endpoint)
    
    def get_all_games(self, game_code: str = "nhl") -> List[dict]:
        """Get all games for a sport."""
        endpoint = f"games;game_keys={game_code}"
        return self._make_request(endpoint)
    
    def sync_league_to_db(self, league_key: str) -> League:
        """Sync league data from Yahoo API to database."""
        db = SessionLocal()
        try:
            # Get league info from API
            league_data = self.get_league_info(league_key)
            
            # Extract league details (simplified - actual parsing depends on Yahoo API response structure)
            # This is a placeholder - actual implementation will parse the Yahoo API XML/JSON response
            league_info = self._parse_league_data(league_data)
            
            # Check if league exists
            league = db.query(League).filter(League.league_key == league_key).first()
            
            if not league:
                league = League(
                    user_id=self.user.id,
                    league_key=league_key,
                    league_id=league_info.get("league_id"),
                    season=league_info.get("season"),
                    game_id=league_info.get("game_id"),
                    game_code=league_info.get("game_code", "nhl"),
                    name=league_info.get("name"),
                    league_type=league_info.get("league_type"),
                    raw_data=league_data
                )
                db.add(league)
            else:
                league.raw_data = league_data
                league.name = league_info.get("name", league.name)
                league.season = league_info.get("season", league.season)
            
            db.commit()
            db.refresh(league)
            return league
        finally:
            db.close()
    
    def _parse_league_data(self, league_data: dict) -> dict:
        """Parse Yahoo API response to extract league information."""
        # This is a simplified parser - actual implementation depends on Yahoo's response format
        # Yahoo API typically returns XML, so we may need XML parsing
        # For now, return a basic structure
        return {
            "league_id": league_data.get("league_id"),
            "season": league_data.get("season"),
            "game_id": league_data.get("game_id"),
            "game_code": league_data.get("game_code", "nhl"),
            "name": league_data.get("name"),
            "league_type": league_data.get("league_type")
        }
    
    # YFPY-powered convenience methods
    # Note: get_league_standings is now defined earlier in the file (line ~287)
    
    def get_league_draft_results_yfpy(self, league_key: str) -> Any:
        """Get draft results using YFPY."""
        try:
            return self.yahoo_query.get_league_draft_results(league_key)
        except Exception as e:
            print(f"Error getting draft results with YFPY: {e}")
            return []
    
    def get_league_players_stats(self, league_key: str, player_keys: List[str] = None) -> List[Any]:
        """Get player stats using YFPY."""
        try:
            # YFPY can fetch all league players with stats
            return self.yahoo_query.get_league_players(league_key)
        except Exception as e:
            print(f"Error getting player stats with YFPY: {e}")
            return []
    
    def get_team_stats(self, team_key: str) -> Any:
        """Get team stats using YFPY."""
        try:
            return self.yahoo_query.get_team_stats(team_key)
        except Exception as e:
            print(f"Error getting team stats with YFPY: {e}")
            return None
    
    def get_league_transactions_yfpy(self, league_key: str) -> List[Any]:
        """Get league transactions (trades, adds, drops) using YFPY."""
        try:
            return self.yahoo_query.get_league_transactions(league_key)
        except Exception as e:
            print(f"Error getting transactions with YFPY: {e}")
            return []

