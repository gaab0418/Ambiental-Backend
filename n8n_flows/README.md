# N8N Flows - Sistema Ambiental

Este diretório contém todos os fluxos n8n necessários para o sistema de gestão de processos ambientais com IA.

## 📋 Visão Geral

O sistema é composto por 5 fluxos principais que trabalham juntos para fornecer:
- Chat inteligente com IA (Gemini)
- Processamento e classificação automática de documentos
- Gestão de timeline e checklist de processos
- Gerenciamento de Instruções Normativas municipais
- APIs administrativas para gestão e monitoramento

## 🏗️ Arquitetura Multi-Tenant

O sistema suporta dois modos de operação:
- **SaaS**: Banco de dados centralizado na cloud
- **On-Prem**: Banco de dados no ambiente do cliente (via VPN/TLS)

Cada organização é automaticamente roteada para suas credenciais corretas através do helper "Resolve Org Credentials".

## 📦 Fluxos Incluídos

### 1. Chat Session Orchestrator (`01_chat_session_orchestrator.json`)
**Webhook**: `/chat-orchestrator`

Orquestra conversas com IA, incluindo:
- Validação de JWT e org_id
- Resolução automática de credenciais (SaaS/On-Prem)
- Carregamento de histórico, arquivos e timeline
- Construção de prompt contextualizado
- Chamada ao Gemini AI com limites de tokens
- Salvamento de resposta e métricas

**Payload esperado**:
```json
{
  "org_id": 1,
  "thread_id": 123,
  "user_id": 456,
  "message": "O que ainda falta para protocolar?",
  "files": [],
  "metadata": {}
}
```

**Headers**:
```
Authorization: Bearer <JWT_TOKEN>
```

### 2. Document Intake & Classification (`02_document_intake_classification.json`)
**Webhook**: `/document-intake`

Processa uploads de documentos:
- Validação e cálculo de hash (evita reprocessamento)
- Detecção de tipo (PDF, imagem, documento)
- Classificação automática em categorias (Boletos, Projetos, Licenças, etc.)
- Extração de metadados
- OCR com Gemini Vision (para imagens)
- Geração de embeddings
- Atualização de timeline

**Payload esperado**:
```json
{
  "file_id": 789,
  "org_id": 1,
  "thread_id": 123,
  "filename": "projeto_arquitetonico.pdf",
  "file_path": "/uploads/chat_files/4/2/file.pdf",
  "mime_type": "application/pdf",
  "file_size": 1024000
}
```

### 3. Timeline & Checklist Updater (`03_timeline_checklist_updater.json`)
**Webhook**: `/timeline-updater`

Atualiza timeline e checklist de processos:
- Carrega informações do thread e arquivos
- Consulta IN vigente do município
- Avalia checklist por categoria de documentos
- Calcula progresso e estágios
- Detecta mudanças e atualiza eventos
- Retorna checklist e percentual completo

**Payload esperado**:
```json
{
  "thread_id": 123,
  "org_id": 1,
  "event_type": "document_added",
  "file_id": 789
}
```

### 4. IN Knowledge Management (`04_in_knowledge_management.json`)
**Webhook**: `/in-upload`

Gerencia Instruções Normativas municipais:
- Validação de nova IN
- Comparação com versões anteriores
- Desativação de versão antiga
- Inserção de nova versão
- Notificação de processos impactados
- Criação de alertas na timeline

**Payload esperado**:
```json
{
  "municipality": "Joinville",
  "state": "SC",
  "instruction_number": "IN-2024-001",
  "version": "2.0",
  "valid_from": "2024-01-01",
  "valid_until": null,
  "content_text": "...",
  "content_url": "https://...",
  "metadata": {}
}
```

### 5. Admin Console APIs (`05_admin_console_apis.json`)
**Webhooks**: 
- `/admin/list-processes` (POST)
- `/admin/reprocess` (POST)
- `/admin/health` (GET)

APIs administrativas para:
- Listar processos com filtros (org, município, status)
- Forçar reprocessamento de threads
- Health check do sistema

**List Processes Payload**:
```json
{
  "org_id": 1,
  "municipality": "Joinville",
  "state": "SC",
  "status": null,
  "limit": 50,
  "offset": 0
}
```

**Reprocess Payload**:
```json
{
  "thread_id": 123,
  "org_id": 1,
  "force": true
}
```

## 🔧 Instalação no N8N

### Pré-requisitos

1. **N8N instalado** (self-hosted ou cloud)
2. **Credenciais configuradas**:
   - **PostgreSQL** (SaaS): credencial nomeada `saas-postgres`
   - **Google Gemini API**: credencial nomeada `gemini-api`
3. **Variáveis de ambiente**:
   ```
   N8N_WEBHOOK_URL=https://seu-n8n.com/webhook
   ```

### Passo a Passo

1. **Importar Credenciais**:
   - Vá em Settings → Credentials
   - Adicione PostgreSQL com nome `saas-postgres` (aponta para seu DB principal)
   - Adicione Google Gemini API com nome `gemini-api`

2. **Importar Fluxos**:
   - Para cada arquivo JSON nesta pasta:
     - Vá em Workflows → Import from File
     - Selecione o arquivo JSON
     - Clique em Save

3. **Ativar Fluxos**:
   - Para cada fluxo importado:
     - Abra o workflow
     - Clique em "Active" no topo direito
     - Verifique que os webhooks estão ativos

4. **Testar Webhooks**:
   - Cada webhook terá uma URL única gerada pelo n8n
   - Anote essas URLs para configurar no backend

## 🔐 Segurança

### Validação de JWT
Todos os fluxos validam o header `Authorization: Bearer <token>` e extraem claims:
- `org_id`: ID da organização
- `user_id`: ID do usuário
- `role`: Papel do usuário

### Resolução de Credenciais
O nó "Resolve Org Credentials" em cada fluxo:
1. Consulta tabela `organizations` com `org_id`
2. Se `mode = 'saas'`: usa credencial `saas-postgres`
3. Se `mode = 'on_prem'`: busca em `org_connections` e usa credenciais específicas (criptografadas)

### Criptografia
- Credenciais on-prem são armazenadas criptografadas em `org_connections`
- O backend Python usa `EncryptionUtils` para decrypt antes de usar
- N8N recebe credenciais já descriptografadas (ou aliases)

## 📊 Métricas e Observabilidade

Todos os fluxos salvam métricas em `flow_metrics`:
- `org_id`: Organização
- `flow_name`: Nome do fluxo
- `tokens_used`: Tokens consumidos (quando aplicável)
- `execution_time_ms`: Tempo de execução
- `status`: success/error
- `metadata`: Detalhes adicionais

Use o endpoint `/admin/health` para verificar conectividade e status geral.

## 🔄 Fluxo de Trabalho Típico

1. **Upload de Documento**:
   - Backend chama `/document-intake`
   - Documento é processado, classificado e vetorizado
   - Timeline é atualizada automaticamente

2. **Usuário Faz Pergunta**:
   - Backend chama `/chat-orchestrator`
   - IA recebe contexto completo (histórico + arquivos + timeline)
   - Resposta é salva e retornada

3. **Admin Consulta Processos**:
   - Frontend admin chama `/admin/list-processes`
   - Lista processos com filtros
   - Pode forçar reprocessamento via `/admin/reprocess`

4. **Atualização de IN**:
   - Admin faz upload de nova IN via `/in-upload`
   - Sistema notifica processos impactados
   - Alertas aparecem na timeline de cada processo

## 🛠️ Customização

### Ajustar Categorias de Documentos
Edite o nó "Detect Document Type" em `02_document_intake_classification.json`:
```javascript
// Adicione novas categorias
if (filename.includes('sua_palavra_chave')) {
  category = 'Sua Nova Categoria';
}
```

### Ajustar Etapas da Timeline
Edite o nó "Evaluate Checklist" em `03_timeline_checklist_updater.json`:
```javascript
const stages = [
  { name: 'Sua Nova Etapa', status: 'pending', progress: 0 },
  // ...
];
```

### Ajustar Limites de Tokens
Edite o nó "Build LLM Prompt" em `01_chat_session_orchestrator.json`:
```javascript
return {
  json: {
    messages: messages,
    max_tokens: 1500,  // Aumente ou diminua
    temperature: 0.7
  }
};
```

## 🐛 Troubleshooting

### Erro: "Organization not found or not active"
- Verifique se `org_id` existe em `organizations`
- Verifique se `status = 'active'`

### Erro: "On-prem credentials not configured"
- Verifique se existe registro em `org_connections` para aquele `org_id`
- Verifique se `is_active = true`
- Verifique se credenciais estão corretamente criptografadas

### Erro: "Failed to decrypt connection credentials"
- Verifique se `FILE_ENCRYPTION_KEY` no backend está correta
- Verifique se credenciais foram criptografadas com a mesma chave

### Webhooks não respondem
- Verifique se fluxos estão ativos
- Verifique URLs dos webhooks no backend
- Consulte logs do n8n

## 📞 Integração com Backend

No backend Python, configure:

```python
# app/config.py
N8N_WEBHOOK_URL = "https://seu-n8n.com/webhook"
N8N_JWT_TOKEN = "seu-token-n8n"  # Opcional
N8N_SIGNING_SECRET = "secret-compartilhado"  # Para HMAC
```

Use o client existente:

```python
from app.utils.n8n_client import n8n_client

# Chamar chat
response = await n8n_client.start_ai_workflow(
    thread_id=123,
    organization_id=1,
    user_id=456,
    message_content="Minha pergunta",
    files=[...],
    message_history=[...]
)
```

## 📝 Próximos Passos

- [ ] Implementar retry automático em caso de falha
- [ ] Adicionar cache de embeddings para reduzir custos
- [ ] Implementar rate limiting por organização
- [ ] Adicionar dashboard de métricas em tempo real
- [ ] Suportar múltiplos modelos de IA (fallback)

## 📄 Licença

Interno - Sistema Ambiental © 2025



