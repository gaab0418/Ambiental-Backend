from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api.v1 import auth, organization, billing, master, logs, metrics, templates, upload, consultant, chat
from app.middleware.audit import AuditMiddleware
from app.database import engine
from app.models import Base
import os

app = FastAPI(
    title="Ambiental SaaS API",
    description="Backend completo para plataforma SaaS Ambiental",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware for logging API requests
app.add_middleware(
    AuditMiddleware,
    exclude_paths=["/docs", "/redoc", "/openapi.json", "/health", "/metrics"]
)

# Create uploads directory if it doesn't exist
uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "profiles"), exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "logos"), exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(organization.router, prefix="/api/organization", tags=["Organization"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(master.router, prefix="/api/master", tags=["Master Admin"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs & Audit"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(consultant.router, prefix="/api/consultant", tags=["Consultant"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])


@app.on_event("startup")
async def startup_event():
    """Validate database before starting API"""
    from app.utils.db_validator import validate_database_or_exit
    
    # Validate database connection and tables, exit if not ready
    validate_database_or_exit()
    
    print("[OK] Ambiental SaaS API iniciada!")
    print("[OK] Sistema configurado e funcionando")


@app.get("/")
async def root():
    return {"message": "Ambiental SaaS API - Backend completo e escalável"}


@app.get("/health")
async def health_check():
    from app.utils.db_validator import get_database_status
    
    status = get_database_status()
    
    return {
        "status": "healthy" if status["ready"] else "unhealthy",
        "message": "Sistema funcionando corretamente" if status["ready"] else "Erro no banco de dados",
        "environment": settings.environment,
        "database": "connected" if status["connected"] else "disconnected",
        "tables_initialized": status["tables_exist"],
        "details": {
            "connection": status["connection_message"],
            "tables": status["tables_message"]
        }
    }


@app.get("/status")
async def status():
    from app.utils.db_validator import get_database_status
    
    db_status = get_database_status()
    
    return {
        "message": "Sistema funcionando corretamente" if db_status["ready"] else "Erro no sistema",
        "version": "1.0.0",
        "environment": settings.environment,
        "database": {
            "status": "connected" if db_status["connected"] else "disconnected",
            "tables_exist": db_status["tables_exist"]
        }
    }
