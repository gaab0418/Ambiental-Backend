"""
Database validation utilities used before starting the API server.

Ensures:
1. Database connection is alive
2. All SQLAlchemy tables exist (creates missing ones automatically)
3. Admin organization/user exist, seeding minimal data if first run
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from scripts.logger import StartupLogger

from app.config import settings
from app.database import SessionLocal
from app.models import Organization, User
from app.utils.db_validator import check_database_connection, ensure_tables_exist
from scripts.init_db import init_database


@dataclass
class ValidationReport:
    connected: bool = False
    connection_message: str = ""
    tables_ok: bool = False
    tables_message: str = ""
    missing_tables: List[str] | None = None
    created_tables: List[str] | None = None
    seeded_admin: bool = False
    ready: bool = False
    errors: List[str] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _needs_seed(session: Session) -> bool:
    admin_org = session.query(Organization).filter(Organization.slug == "org-admin").first()
    admin_user = session.query(User).filter(User.email == settings.initial_admin_email).first()
    return admin_org is None and admin_user is None


def _seed_admin_if_needed(report: ValidationReport) -> None:
    with SessionLocal() as session:
        if not _needs_seed(session):
            report.seeded_admin = False
            StartupLogger.info(
                "Organização/usuário admin já existem. Seed não necessário.",
                log_name="database",
            )
            return

    StartupLogger.info(
        "Nenhuma organização/usuário admin encontrados. Iniciando seed mínimo.",
        log_name="database",
        details={
            "admin_email": settings.initial_admin_email,
            "admin_full_name": settings.initial_admin_full_name,
        },
    )

    try:
        init_database(
            admin_email=settings.initial_admin_email,
            admin_full_name=settings.initial_admin_full_name,
            admin_password=settings.initial_admin_password,
            seed_demo=False,
        )
        
        # Aguardar um momento para garantir que o commit foi processado
        import time
        time.sleep(0.5)
        
        # Verificar se os dados foram realmente criados usando uma nova sessão
        session = SessionLocal()
        try:
            # Forçar uma nova query para garantir que estamos lendo do banco
            admin_org = session.query(Organization).filter(Organization.slug == "org-admin").first()
            admin_user = session.query(User).filter(User.email == settings.initial_admin_email).first()
            
            # Contar total de registros
            org_count = session.query(Organization).count()
            user_count = session.query(User).count()
            
            if not admin_org or not admin_user:
                error_msg = f"Seed executado mas dados não encontrados. Org: {admin_org is not None}, User: {admin_user is not None}, Total Orgs: {org_count}, Total Users: {user_count}"
                StartupLogger.error(error_msg, log_name="database")
                report.errors = (report.errors or []) + [error_msg]
                report.ready = False
                report.seeded_admin = False
                return
            
            StartupLogger.info(
                "Seed executado com sucesso. Dados validados.",
                log_name="database",
                details={
                    "org_id": admin_org.id,
                    "org_name": admin_org.name,
                    "user_id": admin_user.id,
                    "user_email": admin_user.email,
                    "total_orgs": org_count,
                    "total_users": user_count,
                },
            )
            report.seeded_admin = True
        finally:
            session.close()
            
    except Exception as exc:  # pragma: no cover - best effort
        import traceback
        error_details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
        }
        message = f"Falha ao executar seed inicial: {exc}"
        StartupLogger.error(message, log_name="database", details=error_details)
        report.errors = (report.errors or []) + [message]
        report.ready = False
        report.seeded_admin = False


def ensure_database_ready() -> Dict[str, Any]:
    report = ValidationReport(missing_tables=[], created_tables=[], errors=[])

    connected, connection_msg = check_database_connection()
    report.connected = connected
    report.connection_message = connection_msg
    if not connected:
        StartupLogger.error(connection_msg, log_name="database")
        report.errors.append(connection_msg)
        return report.to_dict()

    # PRIMEIRO: Executar migrações Alembic para garantir schema atualizado
    print("\n[0/3] Executando migrações Alembic...")
    alembic_warning = False
    try:
        from scripts.run_alembic import run_alembic_upgrade
        alembic_result = run_alembic_upgrade()
        if not alembic_result["success"]:
            error_msg = f"Aviso: Falha ao executar migrações Alembic: {alembic_result.get('stderr', 'Unknown')}"
            StartupLogger.warning(error_msg, log_name="database")
            # Não bloquear - apenas aviso, continuaremos com criação manual se necessário
            alembic_warning = True
    except Exception as e:
        error_msg = f"Aviso: Erro ao executar Alembic: {e}"
        StartupLogger.warning(error_msg, log_name="database")
        alembic_warning = True

    tables_ok, tables_msg, missing_tables, created_tables = ensure_tables_exist(auto_create=True)
    report.tables_ok = tables_ok
    report.tables_message = tables_msg
    report.missing_tables = missing_tables
    report.created_tables = created_tables
    if not tables_ok:
        StartupLogger.error(
            tables_msg,
            log_name="database",
            details={"missing_tables": missing_tables, "created_tables": created_tables},
        )
        report.errors.append(tables_msg)
        return report.to_dict()

    _seed_admin_if_needed(report)
    
    # Verificar se há erros críticos (não relacionados ao Alembic)
    critical_errors = []
    if report.errors:
        critical_errors = [e for e in report.errors if "Alembic" not in e and "Aviso" not in e and "Falha ao executar migrações Alembic" not in e]
    
    # Se houver erros críticos, bloquear
    if critical_errors:
        print(f"❌ Erros críticos encontrados: {len(critical_errors)}")
        return report.to_dict()
    
    # Se as tabelas existem e o seed foi OK (ou não era necessário), está pronto
    if tables_ok:
        if alembic_warning:
            print("⚠️  Alembic teve problemas, mas tabelas e seed estão OK. Continuando...")
        report.ready = True
    else:
        report.ready = False
    StartupLogger.info(
        "Banco validado e pronto para uso",
        log_name="database",
        details={
            "created_tables": created_tables,
            "seeded_admin": report.seeded_admin,
        },
    )
    return report.to_dict()


if __name__ == "__main__":
    status = ensure_database_ready()
    print(status)


