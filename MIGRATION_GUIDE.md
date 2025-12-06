# Guia de Migração - Chat + Timeline + N8N

## Novas Tabelas do Banco de Dados

Esta implementação adiciona as seguintes tabelas ao banco de dados:

### 1. `chat_files`
Armazena metadados de arquivos anexados aos chats (conteúdo criptografado em disco/S3).

```sql
CREATE TABLE chat_files (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL REFERENCES chat_threads(id),
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    original_filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    encryption_iv VARCHAR(255) NOT NULL,
    encryption_tag VARCHAR(255) NOT NULL,
    encryption_algo VARCHAR(50) NOT NULL DEFAULT 'AES-256-GCM',
    key_version VARCHAR(50) NOT NULL DEFAULT 'v1',
    checksum VARCHAR(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_files_thread_id ON chat_files(thread_id);
CREATE INDEX idx_chat_files_organization_id ON chat_files(organization_id);
CREATE INDEX idx_chat_files_user_id ON chat_files(user_id);
CREATE INDEX idx_chat_files_created_at ON chat_files(created_at);
```

### 2. `chat_timeline_events`
Armazena eventos da timeline de processos.

```sql
CREATE TYPE timeline_event_type AS ENUM (
    'stage', 'system', 'file', 'decision', 'ai_processing', 'error'
);

CREATE TYPE timeline_event_status AS ENUM (
    'pending', 'in_progress', 'completed', 'error', 'cancelled'
);

CREATE TABLE chat_timeline_events (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL REFERENCES chat_threads(id),
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    type timeline_event_type NOT NULL,
    status timeline_event_status NOT NULL DEFAULT 'pending',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL DEFAULT 0,
    event_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_timeline_events_thread_id ON chat_timeline_events(thread_id);
CREATE INDEX idx_chat_timeline_events_organization_id ON chat_timeline_events(organization_id);
CREATE INDEX idx_chat_timeline_events_type ON chat_timeline_events(type);
CREATE INDEX idx_chat_timeline_events_status ON chat_timeline_events(status);
CREATE INDEX idx_chat_timeline_events_order_index ON chat_timeline_events(order_index);
CREATE INDEX idx_chat_timeline_events_created_at ON chat_timeline_events(created_at);
```

### 3. Modificações em `chat_threads`
Adiciona relacionamentos com as novas tabelas (via SQLAlchemy).

## Executar Migração

### 1. Criar Migração com Alembic

```bash
# Gerar migração automática
alembic revision --autogenerate -m "Add chat files and timeline tables"

# Verificar o arquivo de migração gerado
# Editar se necessário em: alembic/versions/XXXXX_add_chat_files_and_timeline_tables.py
```

### 2. Aplicar Migração

```bash
# Aplicar todas as migrações pendentes
alembic upgrade head

# Verificar status
alembic current
alembic history
```

### 3. Rollback (se necessário)

```bash
# Reverter última migração
alembic downgrade -1

# Reverter para versão específica
alembic downgrade <revision_id>
```

## Verificação Pós-Migração

### 1. Verificar Tabelas

```sql
-- Listar todas as tabelas
\dt

-- Verificar estrutura
\d chat_files
\d chat_timeline_events

-- Verificar tipos enum
\dT
```

### 2. Testar Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Listar threads (requer autenticação)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/chat/threads

# Swagger UI
# Abrir: http://localhost:8000/docs
```

## Preparação de Dados

### 1. Gerar Chave de Criptografia

```bash
# Gerar chave de criptografia de arquivos
python -c "from app.core.encryption import EncryptionUtils; print('FILE_ENCRYPTION_KEY=' + EncryptionUtils.generate_key())"

# Adicionar ao .env
echo "FILE_ENCRYPTION_KEY=<chave_gerada>" >> .env
```

### 2. Gerar Segredo HMAC

```bash
# Gerar segredo para validação N8N
python -c "import secrets; print('N8N_SIGNING_SECRET=' + secrets.token_hex(32))"

# Adicionar ao .env
echo "N8N_SIGNING_SECRET=<segredo_gerado>" >> .env
```

### 3. Configurar N8N

Adicionar ao `.env`:

```bash
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/your-webhook-id
N8N_JWT_TOKEN=your-jwt-token-here
N8N_SIGNING_SECRET=<segredo_gerado_acima>
```

## Deployment em Produção

### Checklist de Segurança

- [ ] `FILE_ENCRYPTION_KEY` gerada de forma segura e armazenada com backup offline
- [ ] `N8N_SIGNING_SECRET` compartilhado entre backend e N8N de forma segura
- [ ] `N8N_JWT_TOKEN` configurado e validado
- [ ] HTTPS/TLS configurado para todas as comunicações
- [ ] Backup do banco de dados antes da migração
- [ ] Backup dos arquivos em `uploads/` se existentes
- [ ] Variáveis de ambiente em produção não versionadas

### Passos de Deploy

1. **Backup**
   ```bash
   # Backup do banco
   pg_dump -U user -h host ambiental_db > backup_pre_migration.sql
   
   # Backup de arquivos
   tar -czf uploads_backup.tar.gz uploads/
   ```

2. **Aplicar Migração**
   ```bash
   # Em produção
   alembic upgrade head
   ```

3. **Verificar**
   ```bash
   # Testar health
   curl https://your-domain.com/health
   
   # Verificar logs
   tail -f logs/app.log
   ```

4. **Monitorar**
   - Verificar métricas de erro
   - Verificar logs de auditoria
   - Testar fluxo completo de chat + upload + N8N

## Rollback em Produção

Se algo der errado:

```bash
# 1. Reverter migração
alembic downgrade -1

# 2. Restaurar backup do banco (se necessário)
psql -U user -h host ambiental_db < backup_pre_migration.sql

# 3. Restaurar arquivos (se necessário)
tar -xzf uploads_backup.tar.gz

# 4. Reiniciar aplicação
systemctl restart ambiental-backend
```

## Troubleshooting

### Erro: "relation chat_files does not exist"
```bash
# Verificar se migração foi aplicada
alembic current

# Aplicar migração
alembic upgrade head
```

### Erro: "encryption key not configured"
```bash
# Gerar e configurar chave
python -c "from app.core.encryption import EncryptionUtils; print(EncryptionUtils.generate_key())"

# Adicionar ao .env
echo "FILE_ENCRYPTION_KEY=<chave>" >> .env

# Reiniciar aplicação
```

### Erro: "N8N callback signature invalid"
```bash
# Verificar se N8N_SIGNING_SECRET é igual em ambos os sistemas
# Verificar timestamp (deve estar dentro de 5 minutos)
# Verificar logs para detalhes: tail -f logs/app.log
```

## Suporte

Para problemas durante a migração:

1. Verificar logs: `tail -f logs/app.log`
2. Verificar status do Alembic: `alembic current`
3. Consultar documentação completa: [N8N_INTEGRATION_GUIDE.md](N8N_INTEGRATION_GUIDE.md)

