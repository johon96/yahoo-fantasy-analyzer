"""Yahoo Fantasy Sports API wrapper using yfpy."""
import json
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from pathlib import Path
from yfpy.query import YahooFantasySportsQuery
from yfpy.data import Data
from app.models import User, League, Team, Player
from app.database import SessionLocal
from app.auth import get_valid_access_token


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
        
        self.data = Data(data_dir)
        
        # Initialize yfpy query object
        # Note: yfpy requires OAuth setup, we'll need to configure it with our token
        # For now, we'll use requests directly with the access token
        self.base_url = "https://fantasysports.yahooapis.com/fantasy/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"  # Request JSON response
        }
    
    def _make_request(self, endpoint: str) -> dict:
        """Make API request to Yahoo Fantasy Sports API."""
        import requests
        url = f"{self.base_url}/{endpoint}"
        
        # Log request for debugging
        print(f"Making Yahoo API request to: {url}")
        print(f"Using access token: {self.access_token}..." if self.access_token else "No access token!")
        
        response = requests.get(url, headers=self.headers)
        
        # Log response status
        print(f"Yahoo API response: {response.status_code}")
        
        # Check for authentication errors
        if response.status_code == 401:
            error_msg = f"Unauthorized: {response.text[:200]}"
            print(f"Yahoo API authentication error: {error_msg}")
            raise requests.exceptions.HTTPError(f"401 Unauthorized: {error_msg}")
        
        response.raise_for_status()
        
        # Yahoo API typically returns XML, not JSON
        # Try to parse as JSON first, fall back to XML parsing
        content_type = response.headers.get("Content-Type", "").lower()
        
        try:
            if "application/json" in content_type or response.text.strip().startswith("{"):
                return response.json()
            else:
                # Parse XML response (Yahoo's default format)
                return self._parse_xml_response(response.text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try XML
            return self._parse_xml_response(response.text)
    
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
            child_tag = child.tag
            
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
        return self._make_request(endpoint)
    
    def get_user_leagues(self, game_key: str) -> List[dict]:
        """Get all leagues for a specific game."""
        endpoint = f"users;use_login=1/games;game_keys={game_key}/leagues"
        return self._make_request(endpoint)
    
    def get_league_info(self, league_key: str) -> dict:
        """Get league information."""
        endpoint = f"league/{league_key}"
        return self._make_request(endpoint)
    
    def get_league_teams(self, league_key: str) -> List[dict]:
        """Get all teams in a league."""
        endpoint = f"league/{league_key}/teams"
        return self._make_request(endpoint)
    
    def get_league_standings(self, league_key: str) -> List[dict]:
        """Get league standings."""
        endpoint = f"league/{league_key}/standings"
        return self._make_request(endpoint)
    
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

