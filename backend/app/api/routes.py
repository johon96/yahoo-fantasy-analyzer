"""API routes for the Fantasy Hockey Analyzer."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, League, Team, Player
from app.auth import YahooOAuth, get_or_create_user, get_valid_access_token
from app.yahoo_api import YahooAPIClient
from app.analyzers.trade_analyzer import TradeAnalyzer
from app.analyzers.draft_analyzer import DraftAnalyzer
from app.analyzers.performance_analyzer import PerformanceAnalyzer
from app.api.schemas import (
    LeagueResponse, TeamResponse, PlayerResponse,
    TradeAnalysisResponse, DraftAnalysisResponse,
    PerformanceAnalysisResponse, HistoricalDataResponse,
    ErrorResponse
)
import requests

router = APIRouter(prefix="/api", tags=["api"])
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from token."""
    # In a real implementation, you'd decode a JWT token here
    # For now, we'll use a simple approach with user_id in the token
    # This is a placeholder - implement proper JWT authentication
    user_id = int(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.get("/auth/login")
async def login():
    """Initiate OAuth login flow."""
    oauth = YahooOAuth()
    auth_url, state = oauth.get_authorization_url()
    return {"auth_url": auth_url, "state": state}


@router.get("/auth/callback")
async def auth_callback(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle OAuth callback."""
    oauth = YahooOAuth()
    try:
        token_data = oauth.get_token(code)
        if not token_data or "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="Failed to obtain access token from Yahoo")
        
        user_info = oauth.get_user_info(token_data["access_token"])
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to retrieve user information")
        
        user = get_or_create_user(token_data, user_info)
        return {
            "user_id": user.id,
            "access_token": token_data["access_token"],
            "message": "Authentication successful"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Authentication failed: {str(e)}"
        print(f"OAuth callback error: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=error_detail)


@router.get("/leagues")
async def get_leagues(
    user: User = Depends(get_current_user),
    game_code: Optional[str] = Query(None, description="Game code (nhl, nfl, nba, mlb). If not specified, returns all leagues.")
):
    """Get all leagues for the authenticated user (proxied from Yahoo API)."""
    client = YahooAPIClient(user)
    
    # Get all leagues for the user across all games
    all_leagues_data = client.get_user_leagues()
    
    # Filter leagues by game_code if specified
    if game_code:
        leagues_data = [league for league in all_leagues_data if league.get("game_code") == game_code]
    else:
        leagues_data = all_leagues_data
    
    # Convert season to int for consistency
    for league in leagues_data:
        if league.get("season"):
            try:
                league["season"] = int(league["season"])
            except (ValueError, TypeError):
                pass
    
    return leagues_data


# IMPORTANT: More specific routes must come BEFORE the generic /league/{league_key:path} route
# because :path matches slashes and will catch everything

@router.get("/league/{league_key:path}/teams")
async def get_league_teams(
    league_key: str,
    user: User = Depends(get_current_user)
):
    """Get all teams in a league (proxied from Yahoo API)."""
    client = YahooAPIClient(user)
    
    try:
        # Use standings endpoint for team data
        print(f"Fetching teams for league: {league_key}")
        teams_data = client.get_league_standings(league_key)
        print(f"Teams data received: {teams_data}")
        return teams_data
    except Exception as e:
        print(f"Error fetching teams: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch teams: {str(e)}")


@router.get("/league/{league_key:path}/players")
async def get_league_players(
    league_key: str,
    start: int = Query(0, ge=0),
    count: int = Query(25, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """Get players in a league (proxied from Yahoo API)."""
    client = YahooAPIClient(user)
    
    try:
        # Use YFPY if available
        league_id = league_key.split('.')[-1]
        game_code = "nhl"  # TODO: detect from league_key
        
        yfpy_query = client.get_yfpy_query(league_id, game_code)
        if yfpy_query:
            try:
                players_data = yfpy_query.get_league_players()
                return players_data
            except Exception as e:
                print(f"YFPY failed, falling back to direct API: {e}")
        
        # Fallback to direct API
        players_data = client.get_league_players(league_key, start, count)
        return players_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch players: {str(e)}")


@router.get("/league/{league_key:path}/analysis/trades")
async def get_trade_analysis(
    league_key: str,
    user: User = Depends(get_current_user)
):
    """Get trade analysis for a league using YFPY."""
    client = YahooAPIClient(user)
    
    try:
        # Use YFPY for rich transaction data
        league_id = league_key.split('.')[-1]
        game_code = "nhl"  # TODO: detect from league_key
        
        yfpy_query = client.get_yfpy_query(league_id, game_code)
        if yfpy_query:
            try:
                # Get transactions (trades, adds, drops)
                transactions = yfpy_query.get_league_transactions()
                return {
                    "transactions": transactions,
                    "overperformers": [],
                    "underperformers": [],
                    "recommendations": []
                }
            except Exception as e:
                print(f"YFPY failed: {e}")
        
        # Fallback: basic response
        return {
            "transactions": [],
            "overperformers": [],
            "underperformers": [],
            "recommendations": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze trades: {str(e)}")


@router.get("/league/{league_key:path}/analysis/draft")
async def get_draft_analysis(
    league_key: str,
    user: User = Depends(get_current_user)
):
    """Get draft analysis for a league using YFPY."""
    client = YahooAPIClient(user)
    
    try:
        # Use YFPY for draft results
        league_id = league_key.split('.')[-1]
        game_code = "nhl"  # TODO: detect from league_key
        
        yfpy_query = client.get_yfpy_query(league_id, game_code)
        if yfpy_query:
            try:
                draft_results = yfpy_query.get_league_draft_results()
                return {
                    "draft_results": draft_results,
                    "best_picks": [],
                    "worst_picks": [],
                    "draft_grades": {},
                    "total_picks": 0
                }
            except Exception as e:
                print(f"YFPY failed: {e}")
        
        # Fallback: basic response
        return {
            "draft_results": [],
            "best_picks": [],
            "worst_picks": [],
            "draft_grades": {},
            "total_picks": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze draft: {str(e)}")


@router.get("/league/{league_key:path}/history")
async def get_league_history(
    league_key: str,
    seasons: Optional[int] = Query(None, description="Number of seasons to retrieve"),
    user: User = Depends(get_current_user)
):
    """Get historical data for a league across multiple seasons using YFPY."""
    client = YahooAPIClient(user)
    
    try:
        # Use YFPY for historical data
        league_id = league_key.split('.')[-1]
        game_code = "nhl"  # TODO: detect from league_key
        
        yfpy_query = client.get_yfpy_query(league_id, game_code)
        if yfpy_query:
            try:
                # Get league metadata that might include historical references
                metadata = yfpy_query.get_league_metadata()
                return {
                    "metadata": metadata,
                    "seasons": []
                }
            except Exception as e:
                print(f"YFPY failed: {e}")
        
        # Fallback: basic response
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


# Generic league routes - MUST come after all specific /league/{key}/... routes
@router.get("/league/{league_key:path}")
async def get_league(
    league_key: str,
    user: User = Depends(get_current_user)
):
    """Get league details by league_key (proxied from Yahoo API)."""
    client = YahooAPIClient(user)
    
    try:
        # For now, just use direct API call (YFPY is complex and requires proper setup)
        print(f"Fetching league info for: {league_key}")
        league_data = client.get_league_info(league_key)
        print(f"League data received: {league_data}")
        return league_data
    except Exception as e:
        print(f"Error fetching league: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=404, detail=f"League not found: {str(e)}")


@router.post("/league/{league_key:path}/sync")
async def sync_league(
    league_key: str,
    user: User = Depends(get_current_user)
):
    """Refresh league data from Yahoo API (no-op since we proxy everything)."""
    return {"message": "League data is always fresh (proxied from Yahoo)", "league_key": league_key}


@router.get("/player/{player_key}/performance")
async def get_player_performance(
    player_key: str,
    league_key: str = Query(..., description="League key for context"),
    user: User = Depends(get_current_user)
):
    """Get performance analysis for a specific player using YFPY."""
    client = YahooAPIClient(user)
    
    try:
        # Use YFPY for player stats
        league_id = league_key.split('.')[-1]
        game_code = "nhl"  # TODO: detect from league_key
        
        yfpy_query = client.get_yfpy_query(league_id, game_code)
        if yfpy_query:
            try:
                player_stats = yfpy_query.get_player_stats_by_week(player_key)
                return {
                    "player_key": player_key,
                    "stats": player_stats,
                    "projection": {},
                    "actual": {},
                    "comparison": {}
                }
            except Exception as e:
                print(f"YFPY failed: {e}")
        
        # Fallback: basic response
        return {
            "player_key": player_key,
            "stats": {},
            "projection": {},
            "actual": {},
            "comparison": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch player performance: {str(e)}")

