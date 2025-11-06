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


@router.get("/leagues", response_model=List[LeagueResponse])
async def get_leagues(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    game_code: str = Query("nhl", description="Game code (nhl, nfl, nba, mlb)")
):
    """Get all leagues for the authenticated user."""
    client = YahooAPIClient(user)
    
    # Get game key for the sport
    games = client.get_user_games()
    # Find the current game for the sport
    game_keys = []
    for game in games:
        if game.get("code") == game_code:
            if "game_keys" not in locals():
                game_keys = []
            game_keys.append(game.get("game_key"))
            break
    
    # Get leagues for this game
    leagues_data = client.get_user_leagues(game_keys)
    leagues = []
    for league in leagues_data:
        league_key = league.get("league_key")
        league_data = client.get_league_info(league_key)
        league = League(
            user_id=user.id,
            league_key=league_key,
            league_id=league_data.get("league_id"),
        )
        db.add(league)
        db.commit()
        db.refresh(league)
        leagues.append(league)

    return [LeagueResponse.model_validate(league) for league in leagues]


@router.get("/league/{league_id}", response_model=LeagueResponse)
async def get_league(
    league_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get league details."""
    league = db.query(League).filter(
        League.id == league_id,
        League.user_id == user.id
    ).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    return LeagueResponse.model_validate(league)


@router.post("/league/{league_key}/sync")
async def sync_league(
    league_key: str,
    user: User = Depends(get_current_user)
):
    """Sync league data from Yahoo API to database."""
    client = YahooAPIClient(user)
    try:
        league = client.sync_league_to_db(league_key)
        return {"message": "League synced successfully", "league_id": league.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sync failed: {str(e)}")


@router.get("/league/{league_id}/teams", response_model=List[TeamResponse])
async def get_league_teams(
    league_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all teams in a league."""
    league = db.query(League).filter(
        League.id == league_id,
        League.user_id == user.id
    ).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    teams = db.query(Team).filter(Team.league_id == league_id).all()
    return [TeamResponse.model_validate(team) for team in teams]


@router.get("/league/{league_id}/players", response_model=List[PlayerResponse])
async def get_league_players(
    league_id: int,
    start: int = Query(0, ge=0),
    count: int = Query(25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get players in a league."""
    league = db.query(League).filter(
        League.id == league_id,
        League.user_id == user.id
    ).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    players = db.query(Player).filter(
        Player.league_id == league_id
    ).offset(start).limit(count).all()
    
    return [PlayerResponse.model_validate(player) for player in players]


@router.get("/league/{league_id}/analysis/trades", response_model=TradeAnalysisResponse)
async def get_trade_analysis(
    league_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get trade analysis for a league."""
    league = db.query(League).filter(
        League.id == league_id,
        League.user_id == user.id
    ).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    client = YahooAPIClient(user)
    analyzer = TradeAnalyzer(client, league)
    
    overperformers = analyzer.get_overperformers()
    underperformers = analyzer.get_underperformers()
    
    return TradeAnalysisResponse(
        overperformers=overperformers,
        underperformers=underperformers,
        recommendations=[]
    )


@router.get("/league/{league_id}/analysis/draft", response_model=DraftAnalysisResponse)
async def get_draft_analysis(
    league_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get draft analysis for a league."""
    league = db.query(League).filter(
        League.id == league_id,
        League.user_id == user.id
    ).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    client = YahooAPIClient(user)
    analyzer = DraftAnalyzer(client, league)
    analysis = analyzer.analyze_draft()
    
    return DraftAnalysisResponse(
        best_picks=analysis.get("best_picks", []),
        worst_picks=analysis.get("worst_picks", []),
        draft_grades=analysis.get("draft_grades", {}),
        total_picks=analysis.get("total_picks", 0)
    )


@router.get("/league/{league_id}/history", response_model=List[HistoricalDataResponse])
async def get_league_history(
    league_id: int,
    seasons: Optional[int] = Query(None, description="Number of seasons to retrieve"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get historical data for a league across multiple seasons."""
    league = db.query(League).filter(
        League.id == league_id,
        League.user_id == user.id
    ).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # This would fetch historical data from database or API
    # Placeholder implementation
    return []


@router.get("/player/{player_key}/performance", response_model=PerformanceAnalysisResponse)
async def get_player_performance(
    player_key: str,
    league_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get performance analysis for a specific player."""
    league = db.query(League).filter(
        League.id == league_id,
        League.user_id == user.id
    ).first()
    
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    client = YahooAPIClient(user)
    analyzer = PerformanceAnalyzer(client, league)
    analysis = analyzer.compare_projection_to_actual(player_key)
    
    return PerformanceAnalysisResponse(**analysis)

