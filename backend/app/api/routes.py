"""API routes for the Fantasy Hockey Analyzer."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from app.auth import YahooOAuth, get_or_create_user, get_valid_access_token, User, _load_users
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
) -> User:
    """Get current authenticated user from JSON storage."""
    # The credentials contain the yahoo_guid (user ID)
    yahoo_guid = credentials.credentials
    users = _load_users()
    
    user = users.get(yahoo_guid)
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
    state: Optional[str] = None
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
            "user_id": user.yahoo_guid,  # Return yahoo_guid as the user identifier
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
        # Extract league_id and game_id from league_key
        parts = league_key.split('.')
        league_id = parts[-1] if len(parts) > 0 else league_key
        game_id = parts[0] if len(parts) > 0 else None
        
        # Detect game_code from game_id
        game_code_map = {
            "449": "nfl", "461": "nfl",
            "465": "nhl", "427": "nhl",
            "404": "mlb", "412": "mlb",
            "428": "nba",
        }
        game_code = game_code_map.get(game_id, "nhl")
        
        yfpy_query = client.get_yfpy_query(league_id, game_code, game_id)
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
        # Extract league_id and detect game_code from league_key
        parts = league_key.split('.')
        league_id = parts[-1] if len(parts) > 0 else league_key
        
        # Detect game_code from league_key
        game_id = parts[0] if len(parts) > 0 else None
        game_code_map = {
            "449": "nfl", "461": "nfl",  # NFL game IDs
            "465": "nhl", "427": "nhl",  # NHL game IDs  
            "404": "mlb", "412": "mlb",  # MLB game IDs
            "428": "nba",  # NBA game IDs
        }
        game_code = game_code_map.get(game_id, "nhl")  # Default to NHL
        
        print(f"Getting trade analysis for league {league_id}, game {game_code}, game_id {game_id}")
        
        yfpy_query = client.get_yfpy_query(league_id, game_code, game_id)
        if yfpy_query:
            try:
                print("Fetching transactions from YFPY...")
                # Get transactions (trades, adds, drops)
                transactions = yfpy_query.get_league_transactions()
                print(f"Transactions received: {type(transactions)}")
                
                # Get league players to analyze performance
                print("Fetching league players for performance analysis...")
                league_players = yfpy_query.get_league_players(player_count_limit=100, player_count_start=0)
                
                # Process transactions
                transaction_list = []
                if hasattr(transactions, 'transactions'):
                    for txn in transactions.transactions:
                        transaction_list.append({
                            "type": getattr(txn, 'type', None),
                            "status": getattr(txn, 'status', None),
                            "timestamp": getattr(txn, 'timestamp', None),
                        })
                
                # Analyze player performance (simplified - would need more complex logic)
                overperformers = []
                underperformers = []
                
                if hasattr(league_players, 'players'):
                    for player in league_players.players[:10]:  # Top 10 for now
                        # This is simplified - real analysis would compare projections vs actual
                        if hasattr(player, 'player'):
                            player_data = player.player
                            player_info = {
                                "name": getattr(player_data, 'name', None) if hasattr(player_data, 'name') else None,
                                "position": getattr(player_data, 'display_position', None) if hasattr(player_data, 'display_position') else None,
                            }
                            # Placeholder logic - would need actual stats comparison
                            overperformers.append(player_info)
                
                return {
                    "transactions": transaction_list,
                    "overperformers": overperformers,
                    "underperformers": underperformers,
                    "recommendations": []
                }
            except Exception as e:
                print(f"YFPY trade analysis failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback: basic response
        return {
            "transactions": [],
            "overperformers": [],
            "underperformers": [],
            "recommendations": []
        }
    except Exception as e:
        print(f"Error in trade analysis: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to analyze trades: {str(e)}")


@router.get("/league/{league_key:path}/analysis/draft")
async def get_draft_analysis(
    league_key: str,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(100, ge=10, le=250, description="Number of draft picks per page"),
    user: User = Depends(get_current_user)
):
    """Get draft analysis for a league using YFPY with comprehensive player and team data."""
    client = YahooAPIClient(user)
    
    try:
        # Extract league_id and detect game_code from league_key
        parts = league_key.split('.')
        league_id = parts[-1] if len(parts) > 0 else league_key
        
        # Detect game_code from league_key (e.g., "465" is NHL in 2025)
        game_id = parts[0] if len(parts) > 0 else None
        game_code_map = {
            "449": "nfl", "461": "nfl",  # NFL game IDs
            "465": "nhl", "427": "nhl",  # NHL game IDs  
            "404": "mlb", "412": "mlb",  # MLB game IDs
            "428": "nba",  # NBA game IDs
        }
        game_code = game_code_map.get(game_id, "nhl")  # Default to NHL
        
        print(f"Getting draft analysis for league {league_id}, game {game_code}, game_id {game_id}")
        
        yfpy_query = client.get_yfpy_query(league_id, game_code, game_id)
        if yfpy_query:
            try:
                # Fetch comprehensive data from YFPY
                print("Fetching draft results from YFPY...")
                draft_results = yfpy_query.get_league_draft_results()
                print(f"Draft results received: {type(draft_results)}, count: {len(draft_results) if isinstance(draft_results, list) else 'N/A'}")
                
                # Fetch all teams for lookup
                print("Fetching league teams...")
                teams_data = yfpy_query.get_league_teams()
                
                teams_dict = {}
                # Teams data could be a list or have a teams attribute
                teams_list = None
                if isinstance(teams_data, list):
                    teams_list = teams_data
                elif hasattr(teams_data, 'teams'):
                    teams_list = teams_data.teams
                
                if teams_list:
                    for team in teams_list:
                        team_key = getattr(team, 'team_key', None)
                        if team_key:
                            manager_name = "Unknown"
                            if hasattr(team, 'managers') and team.managers:
                                # Get first manager's nickname
                                first_manager = team.managers[0] if isinstance(team.managers, list) else team.managers
                                manager_name = getattr(first_manager, 'nickname', getattr(first_manager, 'manager_id', 'Unknown'))
                            
                            # Decode team_name if it's bytes
                            team_name = getattr(team, 'name', 'Unknown')
                            if isinstance(team_name, bytes):
                                team_name = team_name.decode('utf-8', errors='replace')
                            
                            teams_dict[team_key] = {
                                "team_name": team_name,
                                "manager": manager_name,
                                "team_id": getattr(team, 'team_id', None)
                            }
                print(f"Loaded {len(teams_dict)} teams")
                
                # Fetch all players for lookup (in batches)
                print("Fetching league players...")
                players_dict = {}
                player_count_start = 0
                player_count_limit = 100  # Fetch in batches of 100
                max_players = 1000  # Safety limit (increased to get all players)
                
                while player_count_start < max_players:
                    try:
                        players_batch = yfpy_query.get_league_players(
                            player_count_start=player_count_start,
                            player_count_limit=player_count_limit
                        )
                        
                        # Handle different return formats
                        players_list = None
                        if isinstance(players_batch, list):
                            players_list = players_batch
                        elif hasattr(players_batch, 'players') and players_batch.players:
                            players_list = players_batch.players
                        
                        if not players_list or len(players_list) == 0:
                            break
                        
                        batch_count = 0
                        for player in players_list:
                            player_key = getattr(player, 'player_key', None)
                            if player_key:
                                # Extract player name
                                player_name = "Unknown"
                                if hasattr(player, 'name') and player.name:
                                    first = getattr(player.name, 'first', '')
                                    last = getattr(player.name, 'last', '')
                                    # Decode if bytes
                                    if isinstance(first, bytes):
                                        first = first.decode('utf-8', errors='replace')
                                    if isinstance(last, bytes):
                                        last = last.decode('utf-8', errors='replace')
                                    player_name = f"{first} {last}".strip()
                                elif hasattr(player, 'full_name'):
                                    player_name = player.full_name
                                    if isinstance(player_name, bytes):
                                        player_name = player_name.decode('utf-8', errors='replace')
                                
                                # Extract headshot URL
                                headshot_url = None
                                if hasattr(player, 'headshot') and player.headshot:
                                    headshot_url = getattr(player.headshot, 'url', None)
                                    if isinstance(headshot_url, bytes):
                                        headshot_url = headshot_url.decode('utf-8', errors='replace')
                                
                                # Extract position
                                position = None
                                if hasattr(player, 'display_position'):
                                    position = player.display_position
                                elif hasattr(player, 'position_type'):
                                    position = player.position_type
                                elif hasattr(player, 'eligible_positions') and player.eligible_positions:
                                    position = ','.join(player.eligible_positions) if isinstance(player.eligible_positions, list) else player.eligible_positions
                                
                                # Decode position if bytes
                                if isinstance(position, bytes):
                                    position = position.decode('utf-8', errors='replace')
                                
                                # Extract NHL team
                                nhl_team = getattr(player, 'editorial_team_abbr', None)
                                if isinstance(nhl_team, bytes):
                                    nhl_team = nhl_team.decode('utf-8', errors='replace')
                                
                                # Extract rank from draft analysis
                                rank = None
                                if hasattr(player, 'draft_analysis') and player.draft_analysis:
                                    rank = getattr(player.draft_analysis, 'average_pick', None)
                                
                                players_dict[player_key] = {
                                    "player_name": player_name,
                                    "headshot_url": headshot_url,
                                    "position": position,
                                    "nhl_team": nhl_team,
                                    "rank": rank
                                }
                                batch_count += 1
                        
                        print(f"Loaded {batch_count} players (total: {len(players_dict)})")
                        
                        if batch_count < player_count_limit:
                            # Received fewer players than requested, we're done
                            break
                        
                        player_count_start += player_count_limit
                    except Exception as player_error:
                        print(f"Error fetching players at offset {player_count_start}: {player_error}")
                        break
                
                print(f"Total players loaded: {len(players_dict)}")
                
                # Process draft results and enrich with team/player data
                picks = []
                if isinstance(draft_results, list):
                    for pick in draft_results:
                        team_key = getattr(pick, 'team_key', None)
                        player_key = getattr(pick, 'player_key', None)
                        
                        # Build enriched pick data
                        pick_data = {
                            "round": getattr(pick, 'round', None),
                            "pick": getattr(pick, 'pick', None),
                            "team_key": team_key,
                            "player_key": player_key,
                        }
                        
                        # Add team information
                        if team_key and team_key in teams_dict:
                            pick_data.update({
                                "team_name": teams_dict[team_key]["team_name"],
                                "manager": teams_dict[team_key]["manager"],
                                "team_id": teams_dict[team_key]["team_id"]
                            })
                        
                        # Try to get player info from draft result first (most reliable)
                        player_from_pick = None
                        if hasattr(pick, 'player') and pick.player:
                            player_from_pick = pick.player
                            
                            # Extract player name
                            if hasattr(player_from_pick, 'name') and player_from_pick.name:
                                first = getattr(player_from_pick.name, 'first', '')
                                last = getattr(player_from_pick.name, 'last', '')
                                if isinstance(first, bytes):
                                    first = first.decode('utf-8', errors='replace')
                                if isinstance(last, bytes):
                                    last = last.decode('utf-8', errors='replace')
                                pick_data["player_name"] = f"{first} {last}".strip()
                            
                            # Extract headshot
                            if hasattr(player_from_pick, 'headshot') and player_from_pick.headshot:
                                headshot_url = getattr(player_from_pick.headshot, 'url', None)
                                if headshot_url:
                                    if isinstance(headshot_url, bytes):
                                        headshot_url = headshot_url.decode('utf-8', errors='replace')
                                    pick_data["headshot_url"] = headshot_url
                            
                            # Extract position
                            position = None
                            if hasattr(player_from_pick, 'display_position'):
                                position = player_from_pick.display_position
                            elif hasattr(player_from_pick, 'position_type'):
                                position = player_from_pick.position_type
                            elif hasattr(player_from_pick, 'eligible_positions') and player_from_pick.eligible_positions:
                                position = ','.join(player_from_pick.eligible_positions) if isinstance(player_from_pick.eligible_positions, list) else player_from_pick.eligible_positions
                            if position:
                                if isinstance(position, bytes):
                                    position = position.decode('utf-8', errors='replace')
                                pick_data["position"] = position
                            
                            # Extract NHL team
                            nhl_team = getattr(player_from_pick, 'editorial_team_abbr', None)
                            if nhl_team:
                                if isinstance(nhl_team, bytes):
                                    nhl_team = nhl_team.decode('utf-8', errors='replace')
                                pick_data["nhl_team"] = nhl_team
                            
                            # Extract rank
                            if hasattr(player_from_pick, 'draft_analysis') and player_from_pick.draft_analysis:
                                rank = getattr(player_from_pick.draft_analysis, 'average_pick', None)
                                if rank:
                                    pick_data["rank"] = rank
                        
                        # Fallback to players_dict if we didn't get data from pick
                        if player_key and player_key in players_dict:
                            # Only add fields that weren't already set
                            for key, value in players_dict[player_key].items():
                                if key not in pick_data:
                                    pick_data[key] = value
                        
                        picks.append(pick_data)
                
                print(f"Processed {len(picks)} enriched draft picks")
                
                # Apply pagination
                total_picks = len(picks)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_picks = picks[start_idx:end_idx]
                
                print(f"Returning page {page} ({len(paginated_picks)} picks)")
                if paginated_picks:
                    print(f"Sample enriched pick: {paginated_picks[0]}")
                
                return {
                    "draft_results": paginated_picks,
                    "best_picks": [],
                    "worst_picks": [],
                    "draft_grades": {},
                    "total_picks": total_picks,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total_picks + page_size - 1) // page_size
                }
            except Exception as e:
                print(f"YFPY draft analysis failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Fallback: basic response
        return {
            "draft_results": [],
            "best_picks": [],
            "worst_picks": [],
            "draft_grades": {},
            "total_picks": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0
        }
    except Exception as e:
        print(f"Error in draft analysis: {e}")
        import traceback
        traceback.print_exc()
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
        # Extract league_id and game_id from league_key
        parts = league_key.split('.')
        league_id = parts[-1] if len(parts) > 0 else league_key
        game_id = parts[0] if len(parts) > 0 else None
        
        # Detect game_code from game_id
        game_code_map = {
            "449": "nfl", "461": "nfl",
            "465": "nhl", "427": "nhl",
            "404": "mlb", "412": "mlb",
            "428": "nba",
        }
        game_code = game_code_map.get(game_id, "nhl")
        
        yfpy_query = client.get_yfpy_query(league_id, game_code, game_id)
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
        # Extract league_id and game_id from league_key
        parts = league_key.split('.')
        league_id = parts[-1] if len(parts) > 0 else league_key
        game_id = parts[0] if len(parts) > 0 else None
        
        # Detect game_code from game_id
        game_code_map = {
            "449": "nfl", "461": "nfl",
            "465": "nhl", "427": "nhl",
            "404": "mlb", "412": "mlb",
            "428": "nba",
        }
        game_code = game_code_map.get(game_id, "nhl")
        
        yfpy_query = client.get_yfpy_query(league_id, game_code, game_id)
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

