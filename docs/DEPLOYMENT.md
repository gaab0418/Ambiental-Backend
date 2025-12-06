# 🚀 Deployment e Migração

Guia para implementar o sistema em produção e realizar migrações de banco de dados.

## ✅ Checklist de Deploy

### 1. Banco de Dados
- [ ] PostgreSQL 14+ rodando.
- [ ] Extensão `vector` instalada (para recursos de IA).
- [ ] Backup realizado antes de aplicar migrações.

### 2. Variáveis de Ambiente (.env)
- [ ] `DEBUG=False`
- [ ] `ENVIRONMENT=production`
- [ ] `SECRET_KEY` forte e única.
- [ ] `FILE_ENCRYPTION_KEY` definida e salva em cofre de senhas (perder isso = perder acesso a todos os arquivos!).
- [ ] `ALLOWED_ORIGINS` configurado estritamente para o domínio do Frontend.

### 3. Migrações (Alembic)
Sempre execute as migrações para garantir que o schema do banco esteja atualizado:

```bash
# Aplica todas as migrações pendentes
alembic upgrade head
```

### 4. Servidor de Aplicação
Recomendado usar **Gunicorn** com Uvicorn workers em produção Linux:

```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

## 🔄 Guia de Migração (Atualizações Recentes)

### Tabelas de Chat e Timeline
O sistema adicionou tabelas para suportar Chat com IA e Timeline de Processos.

**Novas Tabelas:**
*   `chat_threads`: Conversas.
*   `chat_messages`: Mensagens da conversa.
*   `chat_files`: Arquivos anexados (metadados + caminho criptografado).
*   `chat_timeline_events`: Eventos visuais do progresso.
*   `organizations` (update): Campos para suporte SaaS/On-Prem (`mode`, `activation_key`).

**Comandos:**
```bash
alembic upgrade head
```

Se houver erro de "relation does not exist", verifique se o Alembic está apontando para o banco correto no `.env`.

### Migração de Dados (Autenticação)
Foi adicionado o campo `last_organization_id` em `users`. A migração cuida da alteração de schema, mas o campo começará nulo para usuários existentes. Ele será preenchido automaticamente no próximo login ou troca de organização de cada usuário.
