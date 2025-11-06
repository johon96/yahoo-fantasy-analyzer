"""Database models for storing league data and analysis."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model for storing OAuth tokens and user info."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    yahoo_guid = Column(String, unique=True, index=True)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    leagues = relationship("League", back_populates="user")


class League(Base):
    """League model for storing league information."""
    __tablename__ = "leagues"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    league_key = Column(String, unique=True, index=True)
    league_id = Column(String)
    season = Column(Integer)
    game_id = Column(Integer)
    game_code = Column(String)  # 'nhl' for hockey
    name = Column(String)
    league_type = Column(String)
    raw_data = Column(JSON)  # Store full API response
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="leagues")
    teams = relationship("Team", back_populates="league")
    players = relationship("Player", back_populates="league")
    drafts = relationship("Draft", back_populates="league")


class Team(Base):
    """Team model for storing team information."""
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"))
    team_key = Column(String, index=True)
    team_id = Column(Integer)
    name = Column(String)
    manager = Column(String)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    points_for = Column(Float, default=0.0)
    points_against = Column(Float, default=0.0)
    standing = Column(Integer)
    raw_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    league = relationship("League", back_populates="teams")
    roster_players = relationship("RosterPlayer", back_populates="team")


class Player(Base):
    """Player model for storing player information and stats."""
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"))
    player_key = Column(String, index=True)
    player_id = Column(Integer)
    name = Column(String)
    position = Column(String)
    team = Column(String)  # NHL team abbreviation
    status = Column(String)  # available, injured, etc.
    stats = Column(JSON)  # Current season stats
    projected_stats = Column(JSON)  # Projected stats
    raw_data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    league = relationship("League", back_populates="players")
    roster_assignments = relationship("RosterPlayer", back_populates="player")
    historical_stats = relationship("PlayerHistoricalStats", back_populates="player")


class RosterPlayer(Base):
    """Junction table for team rosters."""
    __tablename__ = "roster_players"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    week = Column(Integer)
    position = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    
    team = relationship("Team", back_populates="roster_players")
    player = relationship("Player", back_populates="roster_assignments")


class Draft(Base):
    """Draft model for storing draft results."""
    __tablename__ = "drafts"
    
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"))
    pick = Column(Integer)
    round = Column(Integer)
    team_id = Column(Integer, ForeignKey("teams.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    created_at = Column(DateTime, server_default=func.now())
    
    league = relationship("League", back_populates="drafts")


class PlayerHistoricalStats(Base):
    """Historical player statistics across seasons."""
    __tablename__ = "player_historical_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    season = Column(Integer)
    week = Column(Integer, nullable=True)  # None for season totals
    stats = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    
    player = relationship("Player", back_populates="historical_stats")


class AnalysisCache(Base):
    """Cache for analysis results to avoid repeated computations."""
    __tablename__ = "analysis_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    league_id = Column(Integer, ForeignKey("leagues.id"))
    analysis_type = Column(String)  # 'trade', 'draft', 'performance'
    data = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)

