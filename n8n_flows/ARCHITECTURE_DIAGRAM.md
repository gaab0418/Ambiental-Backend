# Diagrama de Arquitetura - Sistema N8N Multi-Tenant

## 🏗️ Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React/Next.js)                          │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Chat UI      │  │ Upload UI    │  │ Timeline UI  │  │ Admin Panel  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │                 │           │
└─────────┼─────────────────┼─────────────────┼─────────────────┼───────────┘
          │                 │                 │                 │
          │  JWT            │  JWT            │  JWT            │  JWT
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND PYTHON (FastAPI)                            │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │ Chat API        │  │ Upload API      │  │ Activation API  │           │
│  │ /api/chat       │  │ /api/upload     │  │ /api/v1/        │           │
│  │                 │  │                 │  │ activation/...  │           │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘           │
│           │                    │                    │                      │
│           │    ┌───────────────┴────────────────────┴───────────┐         │
│           │    │      N8N Client (app/utils/n8n_client.py)      │         │
│           │    │  - JWT signing                                 │         │
│           │    │  - HMAC signatures                             │         │
│           │    │  - Retry logic                                 │         │
│           │    └───────────────┬────────────────────────────────┘         │
│           │                    │                                           │
│  ┌────────┴────────────────────┴────────┐                                 │
│  │  OrgCredentialsResolver              │  Encryption Utils               │
│  │  - resolve_credentials(org_id)       │  - encrypt()                    │
│  │  - add_onprem_connection()           │  - decrypt()                    │
│  └────────┬─────────────────────────────┘                                 │
│           │                                                                 │
│  ┌────────▼─────────────────────────────────────────────────────────────┐ │
│  │                    PostgreSQL (SaaS Database)                        │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │ │
│  │  │organizations │  │org_connections│ │municipal_ins │             │ │
│  │  │- id          │  │- org_id       │ │- municipality│             │ │
│  │  │- mode        │  │- db_type      │ │- version     │             │ │
│  │  │- status      │  │- host_enc     │ │- is_current  │             │ │
│  │  │- key_hash    │  │- password_enc │ │- content     │             │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │ │
│  │  │chat_threads  │  │chat_messages │  │chat_files    │             │ │
│  │  │chat_timeline │  │flow_metrics  │  │audit_logs    │             │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │ │
│  └──────────────────────────────────────────────────────────────────── │ │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                    HTTPS/TLS     │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              N8N (Cloud/Self-Hosted)                        │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ 01. Chat Session Orchestrator                                         │ │
│  │                                                                       │ │
│  │  Webhook → Validate JWT → Resolve Credentials → Load Context →      │ │
│  │  Build Prompt → Call Gemini AI → Save Response → Metrics             │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ 02. Document Intake & Classification                                  │ │
│  │                                                                       │ │
│  │  Webhook → Validate → Check Hash → Detect Type → Extract Metadata → │ │
│  │  OCR (if image) → Generate Embedding → Update DB → Trigger Timeline  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ 03. Timeline & Checklist Updater                                      │ │
│  │                                                                       │ │
│  │  Webhook → Load Thread → Load Files → Load IN → Evaluate Checklist → │ │
│  │  Calculate Progress → Detect Changes → Update Timeline                │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ 04. IN Knowledge Management                                           │ │
│  │                                                                       │ │
│  │  Webhook → Validate IN → Check Existing → Deactivate Old →           │ │
│  │  Insert New → Find Impacted Processes → Notify Timeline               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ 05. Admin Console APIs                                                │ │
│  │                                                                       │ │
│  │  /admin/list-processes → Query & Filter                               │ │
│  │  /admin/reprocess → Reset & Trigger                                   │ │
│  │  /admin/health → Check DB & Connections                               │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────┐                                          │
│  │ Credentials                 │                                          │
│  │ - saas-postgres (SaaS DB)   │                                          │
│  │ - gemini-api (Google AI)    │                                          │
│  └─────────────────────────────┘                                          │
└─────────────────┬────────────────────────────────────┬────────────────────┘
                  │                                    │
                  │ Gemini API                         │ DB Queries
                  ▼                                    ▼
        ┌──────────────────┐              ┌──────────────────────┐
        │ Google Gemini AI │              │ SaaS PostgreSQL      │
        │ - gemini-1.5-flash│             │ (for SaaS orgs)      │
        │ - text-embedding  │             └──────────────────────┘
        │ - vision (OCR)    │
        └──────────────────┘
                                           
                                           VPN/TLS Tunnel
                                                  │
                                                  ▼
                                    ┌──────────────────────────┐
                                    │ Cliente On-Prem          │
                                    │                          │
                                    │  ┌────────────────────┐ │
                                    │  │ PostgreSQL Local   │ │
                                    │  │ (org_id = X)       │ │
                                    │  │ - app database     │ │
                                    │  │ - vector database  │ │
                                    │  │ - logs database    │ │
                                    │  └────────────────────┘ │
                                    └──────────────────────────┘
```

## 🔄 Fluxo de Dados Detalhado

### Cenário 1: Usuário Envia Mensagem no Chat (SaaS)

```
┌─────────┐  1. POST /api/chat/messages           ┌─────────┐
│ Frontend├──────────────────────────────────────>│ Backend │
│         │  { thread_id, message, JWT }          │ Python  │
└─────────┘                                        └────┬────┘
                                                        │
                                                        │ 2. Validate JWT
                                                        │    Extract org_id
                                                        │
                                                   ┌────▼────┐
                                                   │ Check   │
                                                   │ org_id  │
                                                   │ mode    │
                                                   └────┬────┘
                                                        │
                              ┌─────────────────────────┴─────────────────────────┐
                              │ mode = "saas"                                     │
                              │                                                   │
                         ┌────▼────┐                                              │
                         │ Save    │  3. Save user message                        │
                         │ message │     to chat_messages                         │
                         │ to DB   │                                              │
                         └────┬────┘                                              │
                              │                                                   │
                              │ 4. Call n8n_client.start_ai_workflow()            │
                              │                                                   │
                         ┌────▼────────────────────────────────┐                 │
                         │ POST /webhook/chat-orchestrator     │                 │
                         │ Headers: Authorization: Bearer JWT  │                 │
                         │ Body: {                             │                 │
                         │   org_id, thread_id, user_id,       │                 │
                         │   message, files, history           │                 │
                         │ }                                   │                 │
                         └────┬────────────────────────────────┘                 │
                              │                                                   │
                              ▼                                                   │
                    ┌──────────────────┐                                         │
                    │ N8N Workflow     │                                         │
                    │                  │                                         │
                    │ 5. Validate JWT  │                                         │
                    │ 6. Check org     │                                         │
                    │ 7. Resolve creds │─────> mode=saas → use saas-postgres    │
                    │ 8. Load history  │                                         │
                    │ 9. Load files    │                                         │
                    │ 10. Load timeline│                                         │
                    │ 11. Build prompt │                                         │
                    │ 12. Call Gemini  │───────> Google Gemini API               │
                    │ 13. Format resp  │                                         │
                    │ 14. Save to DB   │                                         │
                    │ 15. Save metrics │                                         │
                    └────┬─────────────┘                                         │
                         │                                                       │
                         │ 16. Return AI response                                │
                         │                                                       │
                    ┌────▼────┐                                                  │
                    │ Backend │  17. Receive response                            │
                    │ receives│      from n8n                                    │
                    └────┬────┘                                                  │
                         │                                                       │
                         │ 18. Return to frontend                                │
                         │                                                       │
                    ┌────▼────┐                                                  │
                    │Frontend │  19. Display AI message                          │
                    │displays │      in chat UI                                  │
                    └─────────┘                                                  │
                                                                                 │
```

### Cenário 2: Upload de Documento (On-Prem)

```
┌─────────┐  1. POST /api/upload/chat-file        ┌─────────┐
│ Frontend├──────────────────────────────────────>│ Backend │
│         │  FormData: file, thread_id, JWT       │ Python  │
└─────────┘                                        └────┬────┘
                                                        │
                                                        │ 2. Validate JWT
                                                        │    Extract org_id = 5
                                                        │
                                                   ┌────▼────┐
                                                   │ Check   │
                                                   │ org_id  │
                                                   │ mode    │
                                                   └────┬────┘
                                                        │
                              ┌─────────────────────────┴─────────────────────────┐
                              │ mode = "on_prem"                                  │
                              │                                                   │
                         ┌────▼────┐                                              │
                         │ Save    │  3. Save file to disk                        │
                         │ file    │     /uploads/chat_files/...                  │
                         │         │  4. Create record in chat_files              │
                         └────┬────┘                                              │
                              │                                                   │
                              │ 5. Call n8n /document-intake                      │
                              │                                                   │
                         ┌────▼────────────────────────────────┐                 │
                         │ POST /webhook/document-intake       │                 │
                         │ Body: {                             │                 │
                         │   file_id, org_id, thread_id,       │                 │
                         │   filename, file_path, mime_type    │                 │
                         │ }                                   │                 │
                         └────┬────────────────────────────────┘                 │
                              │                                                   │
                              ▼                                                   │
                    ┌──────────────────┐                                         │
                    │ N8N Workflow     │                                         │
                    │                  │                                         │
                    │ 6. Validate      │                                         │
                    │ 7. Check hash    │──> Query SaaS DB for existing hash      │
                    │ 8. Resolve creds │──> mode=on_prem                         │
                    │                  │    → Query org_connections (org_id=5)   │
                    │                  │    → Get encrypted creds                │
                    │                  │    → Connect via VPN to 10.0.0.5:5432   │
                    │ 9. Detect type   │                                         │
                    │ 10. Extract meta │                                         │
                    │ 11. OCR (if img) │───────> Gemini Vision API               │
                    │ 12. Gen embedding│───────> Gemini Embedding API            │
                    │ 13. Save to DB   │──> Save to ON-PREM DB (via VPN)        │
                    │ 14. Update file  │                                         │
                    │ 15. Trigger TL   │──> Call /timeline-updater               │
                    │ 16. Save metrics │──> Save to SaaS DB (flow_metrics)      │
                    └────┬─────────────┘                                         │
                         │                                                       │
                         │ 17. Return success                                    │
                         │                                                       │
                    ┌────▼────┐                                                  │
                    │ Backend │  18. Receive response                            │
                    └────┬────┘                                                  │
                         │                                                       │
                         │ 19. Return to frontend                                │
                         │                                                       │
                    ┌────▼────┐                                                  │
                    │Frontend │  20. Show success, refresh UI                    │
                    └─────────┘                                                  │
```

### Cenário 3: Admin Reprocessa Processo

```
┌─────────┐  1. POST /admin/reprocess via Frontend
│ Admin   ├────────────────────────────────────────┐
│ Panel   │  { thread_id, org_id, force: true }   │
└─────────┘                                        │
                                                   ▼
                                            ┌─────────────┐
                                            │ Backend API │
                                            └──────┬──────┘
                                                   │
                                                   │ 2. Validate admin JWT
                                                   │    Check role
                                                   │
                                              ┌────▼────┐
                                              │ Call N8N│
                                              │ /admin/ │
                                              │reprocess│
                                              └────┬────┘
                                                   │
                                                   ▼
                                        ┌──────────────────┐
                                        │ N8N Admin API    │
                                        │                  │
                                        │ 3. Get all files │
                                        │    for thread_id │
                                        │ 4. Reset status  │
                                        │    to 'pending'  │
                                        │ 5. Clear hashes  │
                                        │ 6. Trigger       │
                                        │    /timeline-    │
                                        │    updater       │
                                        └────┬─────────────┘
                                             │
                                             │ 7. Each file is re-queued
                                             │
                            ┌────────────────┴────────────────┐
                            │                                 │
                            ▼                                 ▼
                  ┌──────────────────┐            ┌──────────────────┐
                  │ Document Intake  │            │ Document Intake  │
                  │ (file 1)         │            │ (file 2)         │
                  │ - Reprocess all  │            │ - Reprocess all  │
                  └────────┬─────────┘            └────────┬─────────┘
                           │                               │
                           └───────────┬───────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │ Timeline Updater │
                              │ - Recalculate    │
                              │ - Update progress│
                              └────────┬─────────┘
                                       │
                                       │ 8. Return completion
                                       │
                                  ┌────▼────┐
                                  │ Admin   │
                                  │ Panel   │
                                  │ shows   │
                                  │ success │
                                  └─────────┘
```

## 🔐 Fluxo de Ativação On-Prem

```
┌──────────────┐                                      ┌──────────────┐
│ Admin Master │                                      │ Cliente      │
│ (sua empresa)│                                      │ On-Prem      │
└──────┬───────┘                                      └──────────────┘
       │
       │ 1. Criar organização com mode="on_prem"
       │
  ┌────▼────────────────────────────────┐
  │ INSERT INTO organizations           │
  │ (name, mode, status)                │
  │ VALUES ('Cliente X', 'on_prem',     │
  │         'pending')                  │
  └────┬────────────────────────────────┘
       │
       │ 2. Gerar chave de ativação
       │
  ┌────▼────────────────────────────────┐
  │ POST /api/v1/activation/generate-key│
  │ Authorization: Bearer <admin_jwt>   │
  │ { org_id: 5 }                       │
  └────┬────────────────────────────────┘
       │
       │ Response: {
       │   activation_key: "LbX9a4f...muito-longa",
       │   org_id: 5
       │ }
       │
       │ 3. Hash stored in DB
       │    UPDATE organizations
       │    SET activation_key_hash = SHA256('LbX9a4f...')
       │
       │ 4. Enviar chave ao cliente
       │    (email seguro, instalador, etc.)
       │
       ├──────────────────────────────────────────────>│
       │          activation_key                       │
       │                                               │
       │                                               │ 5. Instalar sistema
       │                                               │    on-prem
       │                                               │
       │                                          ┌────▼────┐
       │                                          │ Setup   │
       │                                          │ Wizard  │
       │                                          └────┬────┘
       │                                               │
       │                                               │ 6. Ativar
       │                                               │
       │       POST /api/v1/activation/activate        │
       │ <─────────────────────────────────────────────┤
       │       { activation_key: "LbX9a4f..." }        │
       │                                               │
       │ 7. Validate key hash                          │
       │    UPDATE status = 'active'                   │
       │                                               │
       │       Response: { status: "active" }          │
       │ ──────────────────────────────────────────────>│
       │                                               │
       │                                               │ 8. Configurar DB
       │                                               │
       │  POST /api/v1/activation/configure-connection │
       │ <─────────────────────────────────────────────┤
       │  {                                            │
       │    activation_key: "LbX9a4f...",              │
       │    db_type: "app",                            │
       │    host: "192.168.1.100",                     │
       │    port: 5432,                                │
       │    database: "ambiental_cliente",             │
       │    username: "app_user",                      │
       │    password: "senha-forte"                    │
       │  }                                            │
       │                                               │
       │ 9. Encrypt & save to org_connections          │
       │                                               │
       │       Response: { status: "configured" }      │
       │ ──────────────────────────────────────────────>│
       │                                               │
       │                                               │ 10. Setup VPN
       │                                               │     (WireGuard)
       │                                               │
       │ 11. VPN tunnel established                    │
       │     10.0.0.1 (N8N) <─────VPN─────> 10.0.0.5  │
       │                                               │
       │                                               │ 12. Teste de conexão
       │                                               │
       │ 13. N8N resolve_credentials(org_id=5)         │
       │     → Retorna: host=10.0.0.5, port=5432, ...  │
       │                                               │
       │ ✅ Sistema pronto para uso                    │
       │                                               │
```

## 📦 Stack Tecnológico

```
┌──────────────────────────────────────────────────────────┐
│ FRONTEND                                                 │
│ - React / Next.js                                        │
│ - TypeScript                                             │
│ - Tailwind CSS                                           │
│ - Axios (HTTP client)                                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ BACKEND                                                  │
│ - Python 3.11+                                           │
│ - FastAPI                                                │
│ - SQLAlchemy (ORM)                                       │
│ - Alembic (migrations)                                   │
│ - Pydantic (validation)                                  │
│ - cryptography (encryption)                              │
│ - httpx (async HTTP)                                     │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ AUTOMATION                                               │
│ - N8N (workflow automation)                              │
│ - Gemini AI (Google)                                     │
│   - gemini-1.5-flash (chat)                              │
│   - text-embedding-004 (embeddings)                      │
│   - gemini-vision (OCR)                                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ DATABASE                                                 │
│ - PostgreSQL 14+                                         │
│ - pgvector (optional, for embeddings)                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE                                           │
│ - WireGuard (VPN)                                        │
│ - Docker / Docker Compose                                │
│ - Nginx (reverse proxy)                                  │
│ - Let's Encrypt (SSL)                                    │
└──────────────────────────────────────────────────────────┘
```

---

**Diagrama criado em**: 15/11/2025  
**Versão**: 1.0.0



