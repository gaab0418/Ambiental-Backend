# Guia de Integração N8N - Sistema de Chat com IA

## Visão Geral

Este sistema integra o backend FastAPI com o N8N como agente de IA para processamento de mensagens, análise de arquivos e geração de timeline de processos. A comunicação é bidirecional e segura, utilizando JWT para autenticação e HMAC-SHA256 para validação de callbacks.

## Arquitetura

```
┌─────────────┐         ┌──────────┐         ┌─────────────┐
│             │  POST   │          │  Query  │             │
│  Frontend   │────────>│ Backend  │────────>│  PostgreSQL │
│             │<────────│ FastAPI  │<────────│  + pgvector │
└─────────────┘         └──────────┘         └─────────────┘
                             │ ^
                   POST (JWT)│ │ POST (HMAC)
                             v │
                        ┌──────────┐
                        │   N8N    │
                        │ AI Agent │
                        └──────────┘
```

## Fluxo de Comunicação

### 1. Usuário Envia Mensagem

1. **Frontend → Backend**: `POST /api/chat/threads/{thread_id}/messages`
   ```json
   {
     "content": "Analise este documento e me dê um resumo"
   }
   ```

2. **Backend processa**:
   - Cria registro da mensagem do usuário no banco
   - Busca arquivos anexados ao thread
   - Cria evento de timeline "Processando mensagem com IA"
   - Chama webhook do N8N

3. **Backend → N8N**: `POST https://profound-drum-faithful.ngrok-free.app/webhook/9df28051-1b03-4929-8cf0-d4de53e1ff7f`
   
   **Headers**:
   ```
   Authorization: Bearer {n8n_jwt_token}
   Content-Type: application/json
   X-Timestamp: {unix_timestamp}
   X-Signature: {hmac_sha256_signature}
   ```
   
   **Body**:
   ```json
   {
     "thread_id": 123,
     "organization_id": 45,
     "user_id": 67,
     "message": "Analise este documento e me dê um resumo",
     "files": [
       {
         "id": 1,
         "filename": "documento.pdf",
         "mime_type": "application/pdf",
         "size_bytes": 524288,
         "download_url": "https://backend.com/api/chat/threads/123/files/1/content"
       }
     ],
     "history": [
       {
         "role": "user",
         "content": "Olá, preciso de ajuda",
         "created_at": "2024-01-01T10:00:00"
       }
     ],
     "metadata": {
       "processing_event_id": 456
     },
     "timestamp": 1704110400
   }
   ```

4. **Backend → Frontend**: Retorna mensagem do usuário
   ```json
   [
     {
       "id": 789,
       "thread_id": 123,
       "role": "user",
       "content": "Analise este documento...",
       "created_at": "2024-01-01T10:00:00"
     }
   ]
   ```

### 2. N8N Processa e Responde

1. **N8N workflow**:
   - Recebe payload do backend
   - Baixa arquivos se necessário (usando `download_url` + header `X-Internal-N8N-Token`)
   - Processa com IA (OpenAI, LangChain, etc.)
   - Vetoriza documentos no pgvector
   - Gera resposta

2. **N8N → Backend**: `POST https://backend.com/api/chat/threads/{thread_id}/messages/callback`
   
   **Headers**:
   ```
   Content-Type: application/json
   X-Timestamp: {unix_timestamp}
   X-Signature: {hmac_sha256_signature}
   ```
   
   **Body**:
   ```json
   {
     "assistant_message": "Aqui está o resumo do documento: ...",
     "timeline_events": [
       {
         "type": "stage",
         "status": "completed",
         "title": "Análise documental concluída",
         "description": "Documento vetorizado com 15 chunks",
         "order_index": 1,
         "metadata": {
           "chunks_count": 15,
           "tokens_used": 1523
         }
       }
     ],
     "metadata": {
       "processing_time": 5.2,
       "model": "gpt-4"
     }
   }
   ```

3. **Backend processa callback**:
   - Valida assinatura HMAC
   - Cria mensagem do assistente no banco
   - Atualiza evento de timeline de processamento para "completed"
   - Cria novos eventos de timeline se fornecidos
   - Atualiza timestamp do thread

## Configuração

### Variáveis de Ambiente (.env)

```bash
# Banco de dados
DATABASE_URL=postgresql://user:password@localhost:5432/ambiental_db

# Segurança
SECRET_KEY=your-super-secret-jwt-key-change-in-production
FILE_ENCRYPTION_KEY=base64-encoded-256bit-key-here

# N8N Integration
N8N_WEBHOOK_URL=https://profound-drum-faithful.ngrok-free.app/webhook/9df28051-1b03-4929-8cf0-d4de53e1ff7f
N8N_JWT_TOKEN=your-n8n-jwt-token
N8N_SIGNING_SECRET=shared-secret-for-hmac-validation

# Deployment
DEPLOYMENT_MODE=saas  # ou "onprem"
FILE_STORAGE_BACKEND=local_encrypted  # ou "s3_encrypted"

# CORS
ALLOWED_ORIGINS_STR=http://localhost:3000,http://localhost:8080
```

### Geração de Chaves

#### 1. Chave de Criptografia de Arquivos

```python
from app.core.encryption import EncryptionUtils

# Gerar nova chave
encryption_key = EncryptionUtils.generate_key()
print(f"FILE_ENCRYPTION_KEY={encryption_key}")
```

#### 2. Segredo HMAC para N8N

```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

## Endpoints da API

### Chat

- `GET /api/chat/threads` - Listar threads do usuário
- `POST /api/chat/threads` - Criar novo thread
- `GET /api/chat/threads/{thread_id}/messages` - Listar mensagens
- `POST /api/chat/threads/{thread_id}/messages` - Enviar mensagem (trigger N8N)
- `DELETE /api/chat/threads/{thread_id}` - Deletar thread

### Arquivos

- `POST /api/chat/threads/{thread_id}/files` - Upload de arquivos (múltiplos)
- `GET /api/chat/threads/{thread_id}/files` - Listar arquivos do thread
- `GET /api/chat/threads/{thread_id}/files/{file_id}/content` - Download arquivo
- `DELETE /api/chat/threads/{thread_id}/files/{file_id}` - Deletar arquivo

### Timeline

- `GET /api/chat/threads/{thread_id}/timeline` - Listar eventos (usuário)
- `GET /api/chat/threads/{thread_id}/timeline/summary` - Resumo da timeline (usuário)
- `POST /api/chat/threads/{thread_id}/timeline` - Criar evento (N8N only)
- `PATCH /api/chat/threads/{thread_id}/timeline/{event_id}` - Atualizar evento (N8N only)

### Callbacks (N8N only)

- `POST /api/chat/threads/{thread_id}/messages/callback` - Entregar resposta da IA

## Segurança

### 1. Autenticação do Backend para N8N

O backend envia JWT no header `Authorization: Bearer {token}` ao chamar o webhook do N8N.

### 2. Autenticação do N8N para Backend (HMAC)

Todos os callbacks do N8N para o backend devem incluir:

**Headers obrigatórios**:
- `X-Timestamp`: Unix timestamp (segundos)
- `X-Signature`: HMAC-SHA256 do payload

**Geração da assinatura (Node.js/N8N)**:
```javascript
const crypto = require('crypto');

const timestamp = Math.floor(Date.now() / 1000).toString();
const payload = JSON.stringify(bodyData);
const message = `${timestamp}.${payload}`;

const signature = crypto
  .createHmac('sha256', process.env.N8N_SIGNING_SECRET)
  .update(message)
  .digest('hex');

// Headers
{
  'X-Timestamp': timestamp,
  'X-Signature': signature,
  'Content-Type': 'application/json'
}
```

### 3. Download de Arquivos pelo N8N

Para o N8N baixar arquivos do backend:

```
GET /api/chat/threads/{thread_id}/files/{file_id}/content
Header: X-Internal-N8N-Token: {n8n_jwt_token}
```

Usa o mesmo token JWT configurado em `N8N_JWT_TOKEN`.

### 4. Criptografia de Arquivos

Todos os arquivos são criptografados com **AES-256-GCM** antes de serem salvos:
- Cada arquivo tem IV e Tag únicos
- Checksum SHA-256 para integridade
- Metadata armazenado no banco, conteúdo criptografado em disco/S3

## Timeline Events

### Tipos de Eventos (`type`)

- `stage`: Estágio do processo (ex: "Análise iniciada")
- `system`: Evento do sistema (ex: "Arquivo anexado")
- `file`: Relacionado a arquivos (ex: "3 arquivos anexados")
- `decision`: Decisão tomada no processo
- `ai_processing`: Processamento de IA
- `error`: Erro ocorrido

### Status (`status`)

- `pending`: Aguardando
- `in_progress`: Em andamento
- `completed`: Concluído
- `error`: Erro
- `cancelled`: Cancelado

### Exemplo de Timeline Event

```json
{
  "type": "stage",
  "status": "completed",
  "title": "Documento analisado",
  "description": "O documento foi processado e vetorizado com sucesso",
  "order_index": 2,
  "metadata": {
    "chunks": 15,
    "pages": 10,
    "confidence": 0.95
  }
}
```

## Deployment

### SaaS (Nuvem)

1. Configurar `DEPLOYMENT_MODE=saas`
2. Configurar storage (`FILE_STORAGE_BACKEND=s3_encrypted` para produção)
3. Usar Secret Manager para chaves sensíveis
4. Configurar TLS/HTTPS obrigatório
5. N8N pode ser compartilhado ou multi-tenant

### On-Premise

1. Configurar `DEPLOYMENT_MODE=onprem`
2. Usar `FILE_STORAGE_BACKEND=local_encrypted`
3. Gerar chaves localmente e guardar com segurança
4. PostgreSQL local com extensão pgvector instalada
5. N8N rodando no mesmo ambiente (Docker recomendado)
6. Configurar backups regulares de:
   - Banco de dados
   - Arquivos criptografados em `uploads/chat_files/`
   - Chaves de criptografia (mantidas offline)

## Migrações de Banco

```bash
# Gerar migração
alembic revision --autogenerate -m "Add chat files and timeline tables"

# Aplicar migrações
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Testes

```bash
# Rodar todos os testes
pytest

# Testes específicos
pytest tests/test_encryption.py
pytest tests/test_n8n_client.py

# Com cobertura
pytest --cov=app --cov-report=html
```

## Troubleshooting

### N8N não recebe callbacks

1. Verificar se `N8N_WEBHOOK_URL` está correto
2. Verificar se `N8N_JWT_TOKEN` está configurado
3. Verificar logs: `docker logs backend-container`
4. Testar conexão: `curl -X POST {N8N_WEBHOOK_URL} -H "Authorization: Bearer {token}"`

### Backend rejeita callbacks do N8N

1. Verificar se `N8N_SIGNING_SECRET` é o mesmo em ambos os sistemas
2. Verificar timestamp (deve estar dentro de 5 minutos)
3. Verificar cálculo da assinatura HMAC
4. Verificar logs do backend para detalhes do erro

### Arquivos não descriptografam

1. Verificar se `FILE_ENCRYPTION_KEY` não mudou
2. Verificar integridade do arquivo (checksum)
3. Verificar se IV e Tag estão corretos no banco
4. Não misturar chaves entre ambientes (dev/prod)

## Monitoramento

Logs importantes a monitorar:

```
[INFO] N8N workflow triggered for thread {id}
[INFO] N8N callback processed for thread {id}
[ERROR] Failed to trigger N8N workflow: {error}
[WARNING] Invalid N8N callback signature for thread {id}
[INFO] Stored encrypted file for org {id}, thread {id}
```

## Suporte

Para questões e suporte:
- Documentação da API: `/docs` (Swagger UI)
- Logs de auditoria: `GET /api/logs`
- Status do sistema: `GET /health`

