import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.seed_data import seed_database
from app.api import endpoints, chat

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and seed data
    logger.info("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    
    logger.info("Checking and seeding hospital data...")
    db = SessionLocal()
    try:
        seed_database(db)
        logger.info("Database seeding complete.")
    finally:
        db.close()
        
    yield
    # Shutdown
    logger.info("Shutting down AarogyaConnect AI backend...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Action-Oriented AI Customer Operations Agent for Aarogya Multispeciality Hospital",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(endpoints.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.HOSPITAL_NAME} Operations API",
        "service": settings.APP_NAME,
        "docs_url": "/docs",
        "health_url": "/api/health"
    }
