# ✅ Checklist de Deploy - Sistema N8N Multi-Tenant

## 📋 Pré-Requisitos

### Infraestrutura
- [ ] Servidor PostgreSQL 14+ disponível
- [ ] N8N instalado (self-hosted ou cloud)
- [ ] Backend Python (FastAPI) configurado
- [ ] Chave de API do Google Gemini obtida
- [ ] Domínio configurado com SSL (Let's Encrypt ou similar)
- [ ] VPN preparada (para clientes on-prem)

### Acesso e Permissões
- [ ] Acesso admin ao N8N
- [ ] Acesso admin ao PostgreSQL
- [ ] Permissões para criar/modificar tabelas no banco
- [ ] Chave SSH para servidor (se aplicável)

---

## 🗄️ Banco de Dados

### Backup
- [ ] Fazer backup completo do banco antes de qualquer mudança
- [ ] Testar restore do backup
- [ ] Guardar backup em local seguro

### Migration
```bash
cd Backend
alembic upgrade head
```

- [ ] Migration executada sem erros
- [ ] Verificar que todas as tabelas foram criadas:
  ```sql
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public' 
  AND table_name IN (
    'org_connections', 
    'municipal_instructions', 
    'flow_metrics'
  );
  ```
- [ ] Verificar que campos foram adicionados em `organizations`:
  ```sql
  SELECT column_name FROM information_schema.columns 
  WHERE table_name = 'organizations' 
  AND column_name IN ('mode', 'status', 'activation_key_hash');
  ```
- [ ] Verificar que campos foram adicionados em `chat_files`:
  ```sql
  SELECT column_name FROM information_schema.columns 
  WHERE table_name = 'chat_files' 
  AND column_name IN ('file_hash', 'category', 'status', 'vectorized_at');
  ```

---

## 🔐 Segurança

### Chaves e Secrets
- [ ] Gerar `FILE_ENCRYPTION_KEY`:
  ```bash
  python -c "from app.core.encryption import EncryptionUtils; print(EncryptionUtils.generate_key())"
  ```
- [ ] Gerar `N8N_SIGNING_SECRET` (senha forte aleatória)
- [ ] Guardar todas as chaves em vault/gerenciador de senhas
- [ ] **NUNCA** commitar chaves no Git

### Configuração `.env`
```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/db

# Security
SECRET_KEY=<seu-secret-key>
FILE_ENCRYPTION_KEY=<chave-gerada-acima>

# N8N Integration
N8N_WEBHOOK_URL=https://seu-n8n.com/webhook
N8N_JWT_TOKEN=<token-opcional>
N8N_SIGNING_SECRET=<secret-compartilhado>

# Environment
ENVIRONMENT=production
DEBUG=False

# CORS (ajustar para produção)
ALLOWED_ORIGINS_STR=https://seu-frontend.com
```

- [ ] Arquivo `.env` configurado
- [ ] Verificar que não há valores de exemplo/desenvolvimento
- [ ] Testar que backend inicia sem erros:
  ```bash
  python main.py
  ```

---

## 🤖 N8N

### Credenciais
- [ ] Criar credencial `saas-postgres`:
  - Host: seu-postgres.com
  - Database: ambiental_db
  - User: app_user
  - Password: ***
  - Port: 5432
  - SSL: ✅ Habilitado

- [ ] Criar credencial `gemini-api`:
  - API Key: (da Google AI Studio)
  - Testar chamada básica

### Importação de Workflows
- [ ] Importar `01_chat_session_orchestrator.json`
- [ ] Importar `02_document_intake_classification.json`
- [ ] Importar `03_timeline_checklist_updater.json`
- [ ] Importar `04_in_knowledge_management.json`
- [ ] Importar `05_admin_console_apis.json`

### Ativação e Teste
Para cada workflow:
- [ ] Abrir workflow
- [ ] Verificar que credenciais estão vinculadas corretamente
- [ ] Clicar em "Active" (ativar)
- [ ] Anotar URL do webhook
- [ ] Testar webhook com curl:
  ```bash
  curl -X GET https://seu-n8n.com/webhook/admin/health
  ```

---

## 🔌 Integração Backend → N8N

### Atualizar URLs dos Webhooks
No código do backend, se necessário, atualizar URLs:
- `app/config.py`: Verificar `N8N_WEBHOOK_URL`
- Verificar que `n8n_client.py` está usando a URL correta

### Testar Integração
```bash
# Testar health check
curl -X GET https://seu-n8n.com/webhook/admin/health

# Deve retornar:
# {
#   "timestamp": "...",
#   "service": "n8n-admin-console",
#   "status": "healthy",
#   "database": { "status": "connected", "active_orgs": 0 }
# }
```

- [ ] Health check retorna sucesso
- [ ] Database mostra "connected"

---

## 👥 Organizações

### Criar Primeira Organização (SaaS)
```python
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.organization import Organization

db = SessionLocal()

org = Organization(
    name="Organização de Teste",
    slug="org-teste",
    cnpj_cpf="12345678901234",
    email="contato@teste.com",
    mode="saas",
    status="active",
    is_active=True
)

db.add(org)
db.commit()
db.refresh(org)

print(f"Organização criada: ID={org.id}")
```

- [ ] Organização criada com sucesso
- [ ] `mode = 'saas'`
- [ ] `status = 'active'`

### Testar Resolução de Credenciais
```python
from app.utils.org_credentials_resolver import resolve_org_credentials
from app.database import SessionLocal

db = SessionLocal()
creds = resolve_org_credentials(db, org_id=1, db_type="app")

print(creds)
# Deve mostrar credenciais do banco SaaS
```

- [ ] Credenciais resolvidas corretamente
- [ ] Mode = 'saas'
- [ ] Connection string presente

---

## 🧪 Testes End-to-End

### 1. Criar Thread de Teste
```bash
curl -X POST https://seu-backend.com/api/chat/threads \
  -H "Authorization: Bearer <jwt-valido>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Processo Teste - Joinville",
    "municipality": "Joinville",
    "state": "SC"
  }'
```

- [ ] Thread criado com sucesso
- [ ] Anotar `thread_id` retornado

### 2. Testar Upload de Documento
```bash
curl -X POST https://seu-backend.com/api/upload/chat-file \
  -H "Authorization: Bearer <jwt-valido>" \
  -F "file=@/path/to/test.pdf" \
  -F "thread_id=<thread-id>"
```

- [ ] Upload bem-sucedido
- [ ] Arquivo aparece em `chat_files`
- [ ] N8N processou documento (verificar `flow_metrics`)
- [ ] Categoria foi atribuída
- [ ] Timeline foi atualizada

### 3. Testar Chat
```bash
curl -X POST https://seu-backend.com/api/chat/messages \
  -H "Authorization: Bearer <jwt-valido>" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": <thread-id>,
    "content": "O que ainda falta para protocolar?"
  }'
```

- [ ] Mensagem enviada
- [ ] IA respondeu
- [ ] Resposta salva em `chat_messages`
- [ ] Métricas registradas em `flow_metrics`

### 4. Testar Timeline
```bash
curl -X GET https://seu-backend.com/api/chat/timeline/<thread-id> \
  -H "Authorization: Bearer <jwt-valido>"
```

- [ ] Timeline retornada
- [ ] Eventos presentes
- [ ] Progresso calculado

### 5. Testar Admin APIs
```bash
# List processes
curl -X POST https://seu-n8n.com/webhook/admin/list-processes \
  -H "Authorization: Bearer <admin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{ "limit": 10 }'

# Health check
curl -X GET https://seu-n8n.com/webhook/admin/health
```

- [ ] Listagem funciona
- [ ] Health check retorna status
- [ ] Sem erros 500

---

## 🏢 Setup On-Prem (Opcional)

### Criar Organização On-Prem
```python
org_onprem = Organization(
    name="Cliente On-Prem",
    slug="cliente-onprem",
    cnpj_cpf="98765432109876",
    email="contato@cliente-onprem.com",
    mode="on_prem",
    status="pending",
    is_active=True
)
db.add(org_onprem)
db.commit()
```

- [ ] Organização criada
- [ ] `mode = 'on_prem'`

### Gerar Chave de Ativação
```bash
curl -X POST https://seu-backend.com/api/v1/activation/generate-key \
  -H "Authorization: Bearer <admin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{ "org_id": <org-onprem-id> }'
```

- [ ] Chave gerada
- [ ] **GUARDAR CHAVE COM SEGURANÇA** (só mostra uma vez)

### Testar Ativação
```bash
curl -X POST https://seu-backend.com/api/v1/activation/activate \
  -H "Content-Type: application/json" \
  -d '{ "activation_key": "<chave-gerada>" }'
```

- [ ] Ativação bem-sucedida
- [ ] Status mudou para "active"

### Configurar Conexão
```bash
curl -X POST https://seu-backend.com/api/v1/activation/configure-connection \
  -H "Content-Type: application/json" \
  -d '{
    "activation_key": "<chave>",
    "db_type": "app",
    "host": "10.0.0.5",
    "port": 5432,
    "database": "ambiental_cliente",
    "username": "app_user",
    "password": "senha-forte"
  }'
```

- [ ] Conexão configurada
- [ ] Credenciais criptografadas em `org_connections`

### Configurar VPN
- [ ] WireGuard instalado em ambos os lados
- [ ] Chaves geradas
- [ ] Configuração aplicada
- [ ] Túnel ativo:
  ```bash
  wg show
  ```
- [ ] Ping funciona:
  ```bash
  ping 10.0.0.5
  ```

### Testar Acesso On-Prem
```python
creds = resolve_org_credentials(db, org_id=<org-onprem-id>, db_type="app")
print(creds)
# Deve mostrar credenciais on-prem com host=10.0.0.5
```

- [ ] Credenciais resolvidas
- [ ] Mode = 'on_prem'
- [ ] Host correto (via VPN)

---

## 📊 Monitoramento

### Métricas
- [ ] Verificar que `flow_metrics` está sendo populado:
  ```sql
  SELECT flow_name, COUNT(*) as executions, AVG(execution_time_ms) as avg_ms
  FROM flow_metrics
  WHERE created_at >= NOW() - INTERVAL '1 hour'
  GROUP BY flow_name;
  ```

### Logs
- [ ] Logs do backend funcionando
- [ ] Logs do N8N acessíveis
- [ ] Logs de auditoria em `audit_logs`

### Alertas
- [ ] Configurar alerta para erros em `flow_metrics`
- [ ] Configurar alerta para custo (tokens usados)
- [ ] Configurar health check periódico (cron)

---

## 🔒 Checklist de Segurança

### Network
- [ ] HTTPS habilitado (certificado válido)
- [ ] Firewall configurado (apenas portas necessárias)
- [ ] VPN funcionando para clientes on-prem
- [ ] CORS configurado corretamente (não usar `*` em produção)

### Autenticação
- [ ] JWT com expiração curta (15 min)
- [ ] Refresh token implementado
- [ ] Rate limiting configurado
- [ ] Endpoints admin protegidos por role

### Dados
- [ ] FILE_ENCRYPTION_KEY forte e única
- [ ] Backup automático configurado
- [ ] Retenção de logs definida
- [ ] LGPD/GDPR considerado

### Auditoria
- [ ] Logs de acesso habilitados
- [ ] Logs de alterações críticas
- [ ] Auditoria de ativações on-prem

---

## 📚 Documentação

### Entrega ao Time
- [ ] Documentação técnica entregue
- [ ] Guia de setup compartilhado
- [ ] Exemplos de teste disponíveis
- [ ] Diagramas de arquitetura explicados

### Treinamento
- [ ] Time de desenvolvimento treinado
- [ ] Time de suporte treinado
- [ ] Administradores treinados
- [ ] Runbook de operações criado

---

## 🚀 Go-Live

### Pré-Go-Live
- [ ] Todos os testes passaram
- [ ] Métricas e logs funcionando
- [ ] Backup recente disponível
- [ ] Time de suporte alertado
- [ ] Plano de rollback preparado

### Go-Live
- [ ] Deploy em produção executado
- [ ] Smoke tests executados
- [ ] Monitoramento ativo
- [ ] Primeiros usuários testando

### Pós-Go-Live
- [ ] Monitorar por 24h-48h
- [ ] Verificar métricas de uso
- [ ] Coletar feedback inicial
- [ ] Ajustes finos se necessário

---

## 📞 Contatos de Emergência

### Suporte Técnico
- Desenvolvedor responsável: _____________
- DevOps: _____________
- DBA: _____________

### Serviços Externos
- Google Cloud (Gemini): https://console.cloud.google.com
- N8N Cloud: https://app.n8n.cloud (se aplicável)

### Escalation
1. Desenvolvedor on-call
2. Tech Lead
3. CTO/Diretor de Tecnologia

---

## ✅ Aprovações

- [ ] Desenvolvedor: _____________ Data: _____
- [ ] DevOps: _____________ Data: _____
- [ ] QA: _____________ Data: _____
- [ ] Tech Lead: _____________ Data: _____

---

**Status Final**: ⬜ Pendente | ⬜ Em Progresso | ⬜ **PRONTO PARA PRODUÇÃO**

**Data de Deploy**: _____ / _____ / _____

**Notas**:
_____________________________________________________________________________
_____________________________________________________________________________
_____________________________________________________________________________



