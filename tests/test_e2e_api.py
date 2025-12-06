"""
Suíte única de testes automatizados:
- Fixtures de banco/cliente com isolamento completo
- Testes unitários de criptografia / storage / N8N client
- Testes end-to-end cobrindo autenticação, organização, chat, arquivos, timeline
- Testes de stress leves
"""

import os
import sys
import json
import time
import hmac
import hashlib
import secrets
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.main import app as fastapi_app
from app.database import Base, get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.chat_thread import ChatThread
from app.models.chat_file import ChatFile
from app.models.chat_timeline_event import ChatTimelineEvent
from app.core.encryption import (
    EncryptionUtils,
    encrypt_file_data,
    decrypt_file_data,
    EncryptionError,
)
from app.utils.secure_storage import secure_storage, StorageError
from app.utils.n8n_client import (
    N8NClient,
    verify_n8n_callback_signature,
    N8NClientError,
)

# ---------------------------------------------------------------------------
# FIXTURES GERAIS E INFRA
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def ensure_security_defaults():
    """Garante que as chaves sensíveis estejam configuradas durante os testes."""
    if not settings.file_encryption_key or not EncryptionUtils.validate_key(
        settings.file_encryption_key
    ):
        settings.file_encryption_key = EncryptionUtils.generate_key()
    if not settings.n8n_signing_secret:
        settings.n8n_signing_secret = "test-n8n-signing-secret"


@pytest.fixture(scope="session")
def test_db_url(tmp_path_factory) -> str:
    """Define a URL de banco exclusiva para testes.
    
    IMPORTANTE: Sempre usa um banco separado do banco de produção.
    Se DATABASE_URL_TEST não estiver configurado ou for igual ao de produção,
    usa SQLite em arquivo temporário automaticamente.
    """
    explicit = settings.database_url_test or os.getenv("DATABASE_URL_TEST")
    prod_url = settings.database_url
    
    if explicit:
        clean = explicit.strip().lstrip("=")
        if not clean:
            # Se estiver vazio, usar SQLite
            db_dir = tmp_path_factory.mktemp("db")
            return f"sqlite:///{db_dir}/test_e2e.sqlite"
        
        # Se for igual ao de produção, usar SQLite automaticamente (com aviso)
        if clean == prod_url:
            import warnings
            warnings.warn(
                f"⚠️  DATABASE_URL_TEST é igual ao DATABASE_URL de produção.\n"
                f"   Usando SQLite temporário para testes (seguro).\n"
                f"   Produção: {prod_url}\n"
                f"   Para usar um banco PostgreSQL específico para testes, configure DATABASE_URL_TEST diferente.",
                UserWarning
            )
            db_dir = tmp_path_factory.mktemp("db")
            return f"sqlite:///{db_dir}/test_e2e.sqlite"
        
        # Se for diferente, usar o banco de teste configurado
        return clean
    
    # Se não estiver configurado, usar SQLite em arquivo temporário (padrão seguro)
    db_dir = tmp_path_factory.mktemp("db")
    return f"sqlite:///{db_dir}/test_e2e.sqlite"


def _build_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, poolclass=NullPool)


def _adapt_types_for_sqlite(metadata):
    """Adapta tipos PostgreSQL-específicos para SQLite antes de criar tabelas.
    
    SQLite não suporta JSONB, então converte para JSON (que SQLite suporta nativamente).
    """
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy import JSON
    
    for table in metadata.tables.values():
        for column in table.columns:
            # Se for JSONB, converter para JSON (compatível com SQLite)
            if isinstance(column.type, JSONB):
                column.type = JSON()


@pytest.fixture(scope="session")
def test_engine(test_db_url):
    """Cria toda a estrutura do banco de testes uma única vez."""
    engine = _build_engine(test_db_url)
    
    # Se estiver usando SQLite, adaptar tipos PostgreSQL-específicos
    if test_db_url.startswith("sqlite"):
        _adapt_types_for_sqlite(Base.metadata)
    
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Abre uma sessão ligada a uma transação que é revertida ao final do teste."""
    connection = test_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection
    )

    # Salvar SessionLocal original para restaurar depois
    import app.database as app_database
    import app.dependencies.auth as auth_deps
    import app.middleware.audit as audit_mw

    original_session_local = app_database.SessionLocal
    original_auth_session = getattr(auth_deps, 'SessionLocal', None)
    original_audit_session = getattr(audit_mw, 'SessionLocal', None)

    # Garante que todas as partes do app que importam SessionLocal usem o Session de teste
    app_database.SessionLocal = TestingSessionLocal
    if hasattr(auth_deps, 'SessionLocal'):
        auth_deps.SessionLocal = TestingSessionLocal
    if hasattr(audit_mw, 'SessionLocal'):
        audit_mw.SessionLocal = TestingSessionLocal

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        
        # RESTAURAR SessionLocal original para não afetar o banco de produção
        app_database.SessionLocal = original_session_local
        if original_auth_session:
            auth_deps.SessionLocal = original_auth_session
        if original_audit_session:
            audit_mw.SessionLocal = original_audit_session


@pytest.fixture
def app_with_overrides(db_session):
    """Override do get_db para usar a sessão de teste."""
    def _get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(app_with_overrides):
    """Cliente HTTP para realizar chamadas reais nos endpoints."""
    with TestClient(app_with_overrides) as c:
        yield c


@pytest.fixture(autouse=True)
def stub_n8n_client(monkeypatch):
    """Evita chamadas HTTP externas durante os testes."""

    async def fake_start_ai_workflow(*args, **kwargs):
        return {"status": "mocked", "workflow_id": "test-workflow"}

    monkeypatch.setattr(
        "app.api.v1.chat.n8n_client.start_ai_workflow",
        fake_start_ai_workflow
    )
    
    # Define mocks globally to avoid redefinition
    import httpx
    
    class MockResponse:
        def __init__(self, status_code=200, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {"output": "Resposta mockada do endpoint"}

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("POST", "http://mock")
                response = httpx.Response(self.status_code, request=request)
                raise httpx.HTTPStatusError("Mock error", request=request, response=response)

        def json(self):
            return self._json_data

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        
        async def __aenter__(self): 
            return self
        
        async def __aexit__(self, *args): 
            pass

        async def post(self, *args, **kwargs):
            return MockResponse()

        async def get(self, *args, **kwargs):
            return MockResponse(json_data={"status": "ok"})

    # PATCH GLOBALLY on the httpx module itself
    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)
    yield


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def sign_payload(payload: Dict[str, Any]) -> Tuple[str, str, str]:
    payload_json = json.dumps(payload, ensure_ascii=False)
    timestamp = str(int(time.time()))
    signature = hmac.new(
        settings.n8n_signing_secret.encode("utf-8"),
        f"{timestamp}.{payload_json}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return payload_json, timestamp, signature


@pytest.fixture
def admin_context(client, db_session):
    """Cria uma organização + usuário admin via endpoint /api/auth/register."""
    unique = secrets.token_hex(4)
    email = f"admin_{unique}@test.com"
    org_name = f"Org Test {unique}"
    cnpj_cpf = "".join(secrets.choice("0123456789") for _ in range(14))
    password = "Test#12345"
    payload = {
        "email": email,
        "full_name": "Test Admin",
        "password": password,
        "organization_name": org_name,
        "cnpj_cpf": cnpj_cpf,
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 200, resp.text
    tokens = resp.json()

    user = db_session.query(User).filter(User.email == email).first()
    org = db_session.query(Organization).filter(Organization.name == org_name).first()
    assert user and org

    return {
        "email": email,
        "password": password,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "user_id": user.id,
        "organization_id": org.id,
    }


# ---------------------------------------------------------------------------
# TESTES DE INFRA (CRIPTOGRAFIA / STORAGE / HMAC / CLIENTE N8N)
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_roundtrip_bytes():
    key = EncryptionUtils.generate_key()
    plaintext = b"Mensagem ultra sensivel para teste de criptografia."
    ciphertext, iv, tag = EncryptionUtils.encrypt_bytes(plaintext, key)
    assert ciphertext != plaintext
    decrypted = EncryptionUtils.decrypt_bytes(ciphertext, iv, tag, key)
    assert decrypted == plaintext


def test_encrypt_decrypt_file_data_with_checksum():
    key = EncryptionUtils.generate_key()
    file_bytes = b"Conteudo de um arquivo qualquer" * 50
    ciphertext, iv_b64, tag_b64, checksum = encrypt_file_data(file_bytes, key)
    decrypted = decrypt_file_data(ciphertext, iv_b64, tag_b64, key, verify_checksum=checksum)
    assert decrypted == file_bytes


def test_decrypt_file_data_checksum_mismatch():
    key = EncryptionUtils.generate_key()
    file_bytes = b"arquivo importante"
    ciphertext, iv_b64, tag_b64, checksum = encrypt_file_data(file_bytes, key)
    wrong_checksum = "0" * 64
    with pytest.raises(EncryptionError, match="Checksum verification failed"):
        decrypt_file_data(ciphertext, iv_b64, tag_b64, key, verify_checksum=wrong_checksum)


def test_secure_storage_store_and_load_roundtrip(tmp_path, monkeypatch):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)

    if not settings.file_encryption_key or not EncryptionUtils.validate_key(
        settings.file_encryption_key
    ):
        settings.file_encryption_key = EncryptionUtils.generate_key()

    storage_path, size_bytes, checksum, iv_b64, tag_b64 = secure_storage.store_file(
        org_id=1,
        thread_id=999,
        file_bytes=b"conteudo de arquivo confidencial" * 100,
        filename="teste.pdf",
        mime_type="application/pdf",
    )

    assert size_bytes > 0
    normalized_path = storage_path.replace("\\", "/")
    assert normalized_path.startswith("chat_files/")

    loaded = secure_storage.load_file(
        storage_path=storage_path,
        iv_b64=iv_b64,
        tag_b64=tag_b64,
        checksum=checksum,
    )
    assert loaded.startswith(b"conteudo de arquivo")

    assert secure_storage.delete_file(storage_path) is True


def test_secure_storage_requires_encryption_key(monkeypatch):
    original_key = settings.file_encryption_key
    settings.file_encryption_key = ""
    try:
        with pytest.raises(StorageError, match="File encryption key not configured"):
            secure_storage.store_file(
                org_id=1,
                thread_id=1,
                file_bytes=b"test",
                filename="file.txt",
                mime_type="text/plain",
            )
    finally:
        settings.file_encryption_key = original_key


def test_verify_n8n_callback_signature_valid(monkeypatch):
    secret = "hmac-test-secret-123"
    monkeypatch.setattr(settings, "n8n_signing_secret", secret)
    payload = json.dumps({"foo": "bar", "value": 42})
    timestamp = str(int(time.time()))
    message = f"{timestamp}.{payload}"
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    assert verify_n8n_callback_signature(payload, timestamp, signature)


def test_verify_n8n_callback_signature_invalid():
    settings.n8n_signing_secret = "another-secret"
    payload = json.dumps({"foo": "bar"})
    timestamp = str(int(time.time()))
    assert not verify_n8n_callback_signature(payload, timestamp, "wrong-signature")


def test_verify_n8n_callback_signature_old_timestamp(monkeypatch):
    secret = "hmac-test-secret-old"
    monkeypatch.setattr(settings, "n8n_signing_secret", secret)
    payload = json.dumps({"foo": "bar"})
    old_timestamp = str(int(time.time()) - 600)
    message = f"{old_timestamp}.{payload}"
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    assert not verify_n8n_callback_signature(payload, old_timestamp, signature, max_age_seconds=300)


def test_verify_n8n_callback_signature_invalid_timestamp_format(monkeypatch):
    secret = "hmac-test-secret-invalid-ts"
    monkeypatch.setattr(settings, "n8n_signing_secret", secret)
    assert not verify_n8n_callback_signature(json.dumps({"foo": "bar"}), "not-a-number", "any")


@pytest.mark.asyncio
async def test_n8n_client_success(monkeypatch):
    monkeypatch.setattr(settings, "n8n_webhook_url", "https://example.com/webhook/test")
    monkeypatch.setattr(settings, "n8n_jwt_token", "test-jwt-token")
    monkeypatch.setattr(settings, "n8n_signing_secret", "test-hmac-secret")
    
    client = N8NClient()
    client.max_retries = 0

    class DummyResponse:
        status_code = 200

        def __init__(self):
            self._json = {"status": "success", "workflow_id": "abc123"}

        def raise_for_status(self):
            return None

        def json(self):
            return self._json

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, **kwargs):
            assert url == "https://example.com/webhook/test"
            content = kwargs.get("content")
            headers = kwargs.get("headers", {})
            data = json.loads(content)
            assert "thread_id" in data
            assert "organization_id" in data
            assert "user_id" in data
            assert "message" in data
            assert isinstance(data["files"], list)
            assert isinstance(data["history"], list)
            assert "metadata" in data
            assert "X-Timestamp" in headers
            assert "X-Signature" in headers
            assert headers.get("Authorization") == "Bearer test-jwt-token"
            return DummyResponse()

    monkeypatch.setattr("app.utils.n8n_client.httpx.AsyncClient", DummyAsyncClient)

    result = await client.start_ai_workflow(
        thread_id=1,
        organization_id=2,
        user_id=3,
        message_content="Teste de integração com N8N",
        files=[],
        message_history=[],
        metadata={"source": "pytest"},
    )
    assert result["status"] == "success"
    assert result["workflow_id"] == "abc123"


@pytest.mark.asyncio
async def test_n8n_client_timeout(monkeypatch):
    monkeypatch.setattr(settings, "n8n_webhook_url", "https://example.com/webhook/test-timeout")
    monkeypatch.setattr(settings, "n8n_signing_secret", "test-hmac-secret-timeout")
    
    client = N8NClient()
    client.max_retries = 0

    import httpx

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.TimeoutException("Request timeout")

    monkeypatch.setattr("app.utils.n8n_client.httpx.AsyncClient", DummyAsyncClient)

    with pytest.raises(N8NClientError):
        await client.start_ai_workflow(
            thread_id=1,
            organization_id=1,
            user_id=1,
            message_content="Teste timeout",
        )


@pytest.mark.asyncio
async def test_n8n_client_http_error(monkeypatch):
    monkeypatch.setattr(settings, "n8n_webhook_url", "https://example.com/webhook/test-error")
    monkeypatch.setattr(settings, "n8n_signing_secret", "test-hmac-secret-error")
    
    client = N8NClient()
    client.max_retries = 0

    import httpx

    class DummyResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "Server error",
                request=httpx.Request("POST", "https://example.com/webhook/test-error"),
                response=httpx.Response(self.status_code),
            )

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return DummyResponse(500)

    monkeypatch.setattr("app.utils.n8n_client.httpx.AsyncClient", DummyAsyncClient)

    with pytest.raises(N8NClientError):
        await client.start_ai_workflow(
            thread_id=1,
            organization_id=1,
            user_id=1,
            message_content="Teste erro HTTP",
        )


# ---------------------------------------------------------------------------
# TESTES END-TO-END
# ---------------------------------------------------------------------------


def test_auth_register_and_login_flow(client, admin_context):
    login_resp = client.post(
        "/api/auth/token",
        data={
            "username": admin_context["email"],
            "password": admin_context["password"],
        },
    )
    assert login_resp.status_code == 200
    login_tokens = login_resp.json()
    assert "access_token" in login_tokens

    me_resp = client.get("/api/auth/me", headers=auth_headers(login_tokens["access_token"]))
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == admin_context["email"]

    refresh_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


def test_organization_endpoints(client, admin_context):
    headers = auth_headers(admin_context["access_token"])
    org_resp = client.get("/api/organization/me", headers=headers)
    assert org_resp.status_code == 200
    users_resp = client.get("/api/organization/users", headers=headers)
    assert users_resp.status_code == 200
    assert any(user["email"] == admin_context["email"] for user in users_resp.json())


def _create_thread(client, token: str, title: str = "Thread E2E") -> int:
    resp = client.post(
        "/api/chat/threads",
        headers=auth_headers(token),
        json={"title": title},
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def _send_user_message(client, token: str, thread_id: int, content: str = "Olá, IA!"):
    resp = client.post(
        f"/api/chat/threads/{thread_id}/messages",
        headers=auth_headers(token),
        json={"content": content},
    )
    assert resp.status_code == 200
    return resp.json()


def test_chat_flow_with_n8n_callback(client, admin_context):
    headers = auth_headers(admin_context["access_token"])
    thread_id = _create_thread(client, admin_context["access_token"])

    send_resp = _send_user_message(client, admin_context["access_token"], thread_id)
    assert send_resp and send_resp[0]["role"] == "user"

    callback_payload = {
        "assistant_message": "Resposta automatizada da IA",
        "timeline_events": [
            {
                "type": "stage",
                "status": "completed",
                "title": "Análise de documentos",
                "description": "Processo finalizado",
                "order_index": 1,
                "metadata": {"tokens_used": 123},
            }
        ],
        "metadata": {"latency": 2.3},
    }
    payload_json, timestamp, signature = sign_payload(callback_payload)
    callback_resp = client.post(
        f"/api/chat/threads/{thread_id}/messages/callback",
        headers={
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Content-Type": "application/json",
        },
        data=payload_json,
    )
    assert callback_resp.status_code == 200

    timeline_resp = client.get(f"/api/chat/threads/{thread_id}/timeline", headers=headers)
    assert timeline_resp.status_code == 200
    events = timeline_resp.json()
    # Check for the timeline event created by the callback (not the auto-generated AI response event)
    assert any(event["title"] == "Análise de documentos" for event in events)


def test_chat_files_crud_flow(client, db_session, admin_context):
    headers = auth_headers(admin_context["access_token"])
    thread_id = _create_thread(client, admin_context["access_token"], title="Arquivos")

    files_payload = [
        ("files", ("doc1.txt", b"conteudo doc1", "text/plain")),
        ("files", ("doc2.txt", b"conteudo doc2", "text/plain")),
    ]
    upload_resp = client.post(
        f"/api/chat/threads/{thread_id}/files",
        headers=headers,
        files=files_payload,
    )
    assert upload_resp.status_code == 200
    uploaded = upload_resp.json()
    assert len(uploaded) == 2

    list_resp = client.get(f"/api/chat/threads/{thread_id}/files", headers=headers)
    assert list_resp.status_code == 200
    file_id = list_resp.json()[0]["id"]

    download_resp = client.get(
        f"/api/chat/threads/{thread_id}/files/{file_id}/content",
        headers=headers,
    )
    assert download_resp.status_code == 200
    assert download_resp.content.startswith(b"conteudo")

    delete_resp = client.delete(
        f"/api/chat/threads/{thread_id}/files/{file_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 200

    chat_file = db_session.query(ChatFile).filter(ChatFile.id == file_id).first()
    if chat_file:
        secure_storage.delete_file(chat_file.storage_path)


def test_timeline_endpoints(client, admin_context):
    headers = auth_headers(admin_context["access_token"])
    thread_id = _create_thread(client, admin_context["access_token"], title="Timeline Flow")

    timeline_payload = {
        "type": "system",
        "status": "pending",
        "title": "Processo iniciado",
        "description": "Evento criado via N8N",
        "order_index": 0,
        "metadata": {"step": 1},
    }
    payload_json, timestamp, signature = sign_payload(timeline_payload)
    create_resp = client.post(
        f"/api/chat/threads/{thread_id}/timeline",
        headers={
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Content-Type": "application/json",
        },
        data=payload_json,
    )
    assert create_resp.status_code == 200
    event_id = create_resp.json()["id"]

    update_payload = {"status": "completed", "metadata": {"step": 2}}
    payload_json, timestamp, signature = sign_payload(update_payload)
    patch_resp = client.patch(
        f"/api/chat/threads/{thread_id}/timeline/{event_id}",
        headers={
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Content-Type": "application/json",
        },
        data=payload_json,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "completed"

    summary_resp = client.get(
        f"/api/chat/threads/{thread_id}/timeline/summary",
        headers=headers,
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_events"] >= 1
    assert summary["status_counts"]["completed"] >= 1


@pytest.mark.stress
def test_stress_creating_multiple_threads_and_messages(client, admin_context):
    headers = auth_headers(admin_context["access_token"])
    created_thread_ids: List[int] = []
    for i in range(5):
        thread_id = _create_thread(client, admin_context["access_token"], title=f"Stress {i}")
        created_thread_ids.append(thread_id)
        for msg_idx in range(3):
            _send_user_message(
                client,
                admin_context["access_token"],
                thread_id,
                content=f"Mensagem {msg_idx} do thread {i}",
            )
    list_resp = client.get("/api/chat/threads", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= len(created_thread_ids)

