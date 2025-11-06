"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api import routes

# Initialize FastAPI app
app = FastAPI(
    title="Fantasy Hockey Analyzer API",
    description="Trade analyzer and league analytics for Yahoo Fantasy Hockey",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "http://localhost:3001",
        "https://localhost:3001",
        "http://localhost:5173",
        "https://localhost:5173"
    ],  # React/Vite dev server (both HTTP and HTTPS)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Fantasy Hockey Analyzer API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

