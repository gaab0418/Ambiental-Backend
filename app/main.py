from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import auth, organization, billing, master

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
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(organization.router, prefix="/api/organization", tags=["Organization"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(master.router, prefix="/api/master", tags=["Master Admin"])


@app.get("/")
async def root():
    return {"message": "Ambiental SaaS API - Backend completo e escalável"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.environment}
