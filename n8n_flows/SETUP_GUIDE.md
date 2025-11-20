# Guia Rápido de Setup - N8N Flows

## 🚀 Setup Inicial (15 minutos)

### 1. Preparar Banco de Dados

Execute a migration para criar as tabelas necessárias:

```bash
cd Backend
alembic upgrade head
```

Isso criará:
- Campos `mode`, `status`, `activation_key_hash` em `organizations`
- Tabela `org_connections` (credenciais multi-tenant)
- Tabela `municipal_instructions` (INs municipais)
- Tabela `flow_metrics` (métricas de execução)
- Campos adicionais em `chat_files` (hash, category, status, etc.)

### 2. Configurar N8N

#### Opção A: N8N Self-Hosted (Recomendado para Produção)

```bash
# Docker Compose
version: '3.8'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=senha-forte-aqui
      - N8N_HOST=n8n.seu-dominio.com
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://n8n.seu-dominio.com/
    volumes:
      - n8n_data:/home/node/.n8n

volumes:
  n8n_data:
```

```bash
docker-compose up -d
```

#### Opção B: N8N Cloud

1. Acesse https://n8n.io/cloud
2. Crie uma conta
3. Anote a URL do workspace (ex: `https://seu-workspace.app.n8n.cloud`)

### 3. Importar Credenciais no N8N

1. Acesse seu N8N (http://localhost:5678 ou sua URL cloud)
2. Vá em **Settings → Credentials**
3. Adicione as seguintes credenciais:

#### PostgreSQL (SaaS Database)
- **Name**: `saas-postgres`
- **Type**: Postgres
- **Host**: Seu host PostgreSQL
- **Database**: `ambiental_db`
- **User**: Seu usuário
- **Password**: Sua senha
- **Port**: 5432
- **SSL**: Recomendado ativar em produção

#### Google Gemini API
- **Name**: `gemini-api`
- **Type**: Google Gemini
- **API Key**: Sua chave da API Gemini (obtenha em https://aistudio.google.com/app/apikey)

### 4. Importar Workflows

Para cada arquivo JSON na pasta `n8n_flows`:

1. Vá em **Workflows**
2. Clique em **Import from File**
3. Selecione o arquivo:
   - `01_chat_session_orchestrator.json`
   - `02_document_intake_classification.json`
   - `03_timeline_checklist_updater.json`
   - `04_in_knowledge_management.json`
   - `05_admin_console_apis.json`
4. Clique em **Import**
5. Salve o workflow

### 5. Ativar Workflows

Para cada workflow importado:

1. Abra o workflow
2. Clique no botão **Active** (canto superior direito)
3. Anote a URL do webhook que aparece no nó "Webhook Trigger"

Exemplo de URL:
```
https://seu-n8n.com/webhook/chat-orchestrator
```

### 6. Configurar Backend Python

Edite `Backend/.env`:

```env
# N8N Integration
N8N_WEBHOOK_URL=https://seu-n8n.com/webhook
N8N_JWT_TOKEN=seu-token-opcional
N8N_SIGNING_SECRET=secret-compartilhado-para-hmac

# Deployment Mode
DEPLOYMENT_MODE=saas

# File Encryption (gere uma nova chave)
FILE_ENCRYPTION_KEY=<gere_uma_chave_forte>
```

Para gerar a chave de criptografia:

```bash
python -c "from app.core.encryption import EncryptionUtils; print(EncryptionUtils.generate_key())"
```

### 7. Testar Conexão

Inicie o backend:

```bash
cd Backend
python main.py
```

Teste o health check do n8n:

```bash
curl -X GET https://seu-n8n.com/webhook/admin/health
```

Resposta esperada:
```json
{
  "timestamp": "2025-11-15T...",
  "service": "n8n-admin-console",
  "status": "healthy",
  "database": {
    "status": "connected",
    "active_orgs": 1
  },
  "connections": {
    "total_configured": 0,
    "by_org": []
  }
}
```

## 🏢 Setup de Organização SaaS

Para cada cliente SaaS, execute:

```python
# Script: scripts/create_saas_org.py
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.organization import Organization

db = SessionLocal()

org = Organization(
    name="Nome do Cliente",
    slug="cliente-slug",
    cnpj_cpf="12345678901234",
    email="contato@cliente.com",
    mode="saas",  # Modo SaaS
    status="active",
    is_active=True
)

db.add(org)
db.commit()
db.refresh(org)

print(f"Organização criada: ID={org.id}, Mode={org.mode}")
```

## 🖥️ Setup de Organização On-Prem

### Passo 1: Gerar Chave de Ativação

Via API admin (ou script):

```bash
curl -X POST https://seu-backend.com/api/v1/activation/generate-key \
  -H "Authorization: Bearer <admin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": 2
  }'
```

Resposta:
```json
{
  "activation_key": "LbX9...muito-longa",
  "org_id": 2,
  "org_name": "Cliente On-Prem",
  "expires_at": null
}
```

**⚠️ IMPORTANTE**: Guarde essa chave com segurança e envie ao cliente. Ela será exibida apenas uma vez.

### Passo 2: Cliente Ativa Instalação

No ambiente on-prem do cliente, durante a instalação:

```bash
curl -X POST https://seu-backend-saas.com/api/v1/activation/activate \
  -H "Content-Type: application/json" \
  -d '{
    "activation_key": "LbX9...muito-longa"
  }'
```

Resposta:
```json
{
  "org_id": 2,
  "org_name": "Cliente On-Prem",
  "mode": "on_prem",
  "status": "active",
  "message": "Organization activated successfully"
}
```

### Passo 3: Configurar Conexão do Banco On-Prem

```bash
curl -X POST https://seu-backend-saas.com/api/v1/activation/configure-connection \
  -H "Content-Type: application/json" \
  -d '{
    "activation_key": "LbX9...muito-longa",
    "db_type": "app",
    "host": "192.168.1.100",
    "port": 5432,
    "database": "ambiental_cliente",
    "username": "app_user",
    "password": "senha-forte-cliente"
  }'
```

Resposta:
```json
{
  "org_id": 2,
  "db_type": "app",
  "message": "app connection configured successfully"
}
```

Repita para `db_type: "vector"` e `db_type: "logs"` se necessário.

### Passo 4: Configurar VPN/Túnel

Para segurança máxima, configure um túnel VPN entre seu servidor n8n e o servidor on-prem do cliente.

#### Opção 1: WireGuard (Recomendado)

**No servidor n8n (peer 1)**:
```bash
# Instalar WireGuard
apt update && apt install wireguard

# Gerar chaves
wg genkey | tee server_private.key | wg pubkey > server_public.key

# Configurar /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <server_private_key>
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
PublicKey = <client_public_key>
AllowedIPs = 10.0.0.2/32, 192.168.1.0/24

# Iniciar
wg-quick up wg0
systemctl enable wg-quick@wg0
```

**No servidor on-prem do cliente (peer 2)**:
```bash
# Gerar chaves
wg genkey | tee client_private.key | wg pubkey > client_public.key

# Configurar /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <client_private_key>
Address = 10.0.0.2/24

[Peer]
PublicKey = <server_public_key>
Endpoint = seu-n8n.com:51820
AllowedIPs = 10.0.0.1/32
PersistentKeepalive = 25

# Iniciar
wg-quick up wg0
```

Agora use `10.0.0.2` como host ao configurar `org_connections`.

## 🧪 Teste Completo do Sistema

### 1. Criar Thread de Teste

```bash
curl -X POST https://seu-backend.com/api/v1/chat/threads \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Processo Teste - Joinville",
    "municipality": "Joinville",
    "state": "SC"
  }'
```

### 2. Upload de Documento

```bash
curl -X POST https://seu-backend.com/api/v1/upload/chat-file \
  -H "Authorization: Bearer <jwt>" \
  -F "file=@/path/to/documento.pdf" \
  -F "thread_id=123"
```

Isso deve automaticamente:
- Chamar `/document-intake` no n8n
- Processar e classificar o arquivo
- Atualizar timeline via `/timeline-updater`

### 3. Enviar Mensagem no Chat

```bash
curl -X POST https://seu-backend.com/api/v1/chat/messages \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": 123,
    "content": "O que ainda falta para protocolar em Joinville?"
  }'
```

Isso deve chamar `/chat-orchestrator` e retornar resposta da IA.

### 4. Consultar Timeline

```bash
curl -X GET https://seu-backend.com/api/v1/chat/timeline/123 \
  -H "Authorization: Bearer <jwt>"
```

## 📊 Monitoramento

### Consultar Métricas

```sql
-- Métricas por organização (últimas 24h)
SELECT 
  org_id,
  flow_name,
  COUNT(*) as executions,
  AVG(execution_time_ms) as avg_time_ms,
  SUM(tokens_used) as total_tokens,
  COUNT(CASE WHEN status = 'error' THEN 1 END) as errors
FROM flow_metrics
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY org_id, flow_name
ORDER BY total_tokens DESC;
```

### Health Check Periódico

Configure um cron job:

```bash
*/5 * * * * curl -f https://seu-n8n.com/webhook/admin/health || echo "N8N health check failed"
```

## 🔒 Checklist de Segurança

- [ ] VPN/TLS configurado para clientes on-prem
- [ ] `FILE_ENCRYPTION_KEY` gerada e segura
- [ ] `N8N_SIGNING_SECRET` configurado
- [ ] Credenciais do n8n protegidas (Basic Auth ou OAuth)
- [ ] JWT com expiração curta (15 min)
- [ ] HTTPS habilitado em todos os endpoints
- [ ] Firewall permitindo apenas tráfego necessário
- [ ] Logs de auditoria habilitados
- [ ] Backup automático do banco de dados
- [ ] Rate limiting configurado no backend

## 🆘 Suporte

Em caso de problemas:

1. Verifique logs do n8n: `docker logs n8n_container`
2. Verifique logs do backend: `tail -f app.log`
3. Consulte métricas em `flow_metrics`
4. Teste health check: `GET /webhook/admin/health`
5. Verifique conectividade VPN (se on-prem)

## 📚 Próximos Passos

Após setup completo:

1. Cadastre INs municipais via `/in-upload`
2. Configure alertas de custo (tokens/mês)
3. Implemente dashboard de métricas
4. Configure backup automático
5. Treine equipe de suporte



