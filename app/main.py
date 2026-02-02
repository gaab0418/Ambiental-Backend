from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1 import auth, organization, billing, master, logs, metrics, templates, upload, consultant, chat, chat_files, checklist, activation, agenda, documents, legislations, processes, api_keys
from app.middleware.audit import AuditMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.database import engine
from app.models import Base
from app.utils.n8n_client import n8n_client
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    # Validação já foi feita no main.py raiz, não precisa validar novamente aqui
    # para evitar conflitos com o seed que foi executado
    
    print("[OK] Ambiental SaaS API iniciada!")
    print("[OK] Sistema configurado e funcionando")
    
    try:
        ping_ok = await n8n_client.ping()
        if ping_ok:
            print("[OK] N8N webhook está online")
        else:
            print("[WARNING] N8N webhook não está respondendo - verifique a conectividade")
    except Exception as exc:  # pragma: no cover - startup guard
        print(f"[WARNING] Falha ao checar N8N webhook: {exc}")
    
    yield
    
    # Shutdown (if needed)
    pass


app = FastAPI(
    title="Ambiental SaaS API",
    description="Backend completo para plataforma SaaS Ambiental",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
origins = []

# Add origins from settings
if settings.allowed_origins:
    origins.extend(settings.allowed_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # TODO: SECURITY - Allow ngrok domains only in development or if explicitly allowed.
    allow_origin_regex="https://.*\\.ngrok-free\\.(app|dev)" if (settings.environment != "production" or settings.allow_ngrok_wildcard) else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware for logging API requests
app.add_middleware(
    AuditMiddleware,
    exclude_paths=["/docs", "/redoc", "/openapi.json", "/health", "/metrics"]
)

# Request Logging middleware (logs full request/response)
app.add_middleware(
    RequestLoggingMiddleware
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
app.include_router(chat_files.router, prefix="/api/chat", tags=["Chat Files"])
app.include_router(checklist.router, prefix="/api/checklist", tags=["Checklist"])
app.include_router(activation.router, prefix="/api/v1", tags=["Activation"])

# New module routers
app.include_router(agenda.router, prefix="/api/agenda", tags=["Agenda"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(legislations.router, prefix="/api/legislations", tags=["Legislations"])
app.include_router(processes.router, prefix="/api/processes", tags=["Processes"])
app.include_router(api_keys.router, prefix="/api/api-keys", tags=["API Keys"])


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
