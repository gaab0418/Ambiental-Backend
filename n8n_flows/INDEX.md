# 📚 Índice de Documentação - N8N Flows

## 🎯 Por Onde Começar?

### Você é...

**👨‍💼 Gestor / Tomador de Decisão?**
→ Leia primeiro: [`../RESUMO_EXECUTIVO_N8N.md`](../RESUMO_EXECUTIVO_N8N.md)
- Visão geral do projeto
- Números e métricas
- Custos estimados
- Benefícios esperados

**👨‍💻 Desenvolvedor / Técnico?**
→ Leia primeiro: [`README.md`](README.md)
- Detalhes técnicos de cada fluxo
- Payloads esperados
- Integração com backend
- Customização

**🔧 DevOps / Infraestrutura?**
→ Leia primeiro: [`SETUP_GUIDE.md`](SETUP_GUIDE.md)
- Instalação passo-a-passo
- Configuração de VPN
- Segurança e certificados
- Checklist de deploy

**🧪 QA / Testador?**
→ Comece com: [`test_payloads.json`](test_payloads.json)
- Exemplos de requisição
- Comandos curl prontos
- Respostas esperadas
- Casos de teste

---

## 📋 Documentos Disponíveis

### Documentação Executiva
- **[RESUMO_EXECUTIVO_N8N.md](../RESUMO_EXECUTIVO_N8N.md)** - Visão executiva completa
- **[N8N_IMPLEMENTATION_COMPLETE.md](../N8N_IMPLEMENTATION_COMPLETE.md)** - Documentação técnica completa do projeto

### Documentação Técnica
- **[README.md](README.md)** - Documentação técnica dos fluxos
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Guia de instalação e configuração
- **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - Diagramas visuais da arquitetura

### Recursos de Teste
- **[test_payloads.json](test_payloads.json)** - Exemplos de payloads e testes

### Workflows N8N
- **[01_chat_session_orchestrator.json](01_chat_session_orchestrator.json)** - Chat com IA
- **[02_document_intake_classification.json](02_document_intake_classification.json)** - Processamento de documentos
- **[03_timeline_checklist_updater.json](03_timeline_checklist_updater.json)** - Gestão de timeline
- **[04_in_knowledge_management.json](04_in_knowledge_management.json)** - Gestão de INs
- **[05_admin_console_apis.json](05_admin_console_apis.json)** - APIs administrativas

---

## 🗺️ Mapa de Navegação por Objetivo

### Quero entender o projeto
1. **[RESUMO_EXECUTIVO_N8N.md](../RESUMO_EXECUTIVO_N8N.md)** - Comece aqui
2. **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - Veja os diagramas
3. **[README.md](README.md)** - Detalhes técnicos

### Quero instalar o sistema
1. **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Passo-a-passo completo
2. **[README.md](README.md)** → Seção "Instalação no N8N"
3. **[N8N_IMPLEMENTATION_COMPLETE.md](../N8N_IMPLEMENTATION_COMPLETE.md)** → Seção "Como Usar"

### Quero testar os fluxos
1. **[test_payloads.json](test_payloads.json)** - Exemplos prontos
2. **[README.md](README.md)** → Seção de cada fluxo
3. **[SETUP_GUIDE.md](SETUP_GUIDE.md)** → Seção "Teste Completo do Sistema"

### Quero customizar os fluxos
1. **[README.md](README.md)** → Seção "Customização"
2. **[N8N_IMPLEMENTATION_COMPLETE.md](../N8N_IMPLEMENTATION_COMPLETE.md)** → Seção "Pontos de Extensão"
3. Abra os arquivos JSON dos workflows

### Quero integrar com o backend
1. **[README.md](README.md)** → Seção "Integração com Backend"
2. **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** → Fluxos de dados
3. **[test_payloads.json](test_payloads.json)** - Exemplos de integração

### Quero entender a arquitetura
1. **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** - Diagramas completos
2. **[README.md](README.md)** → Seção "Arquitetura Multi-Tenant"
3. **[N8N_IMPLEMENTATION_COMPLETE.md](../N8N_IMPLEMENTATION_COMPLETE.md)** → Seção "Arquitetura de Segurança"

### Quero resolver problemas
1. **[README.md](README.md)** → Seção "Troubleshooting"
2. **[SETUP_GUIDE.md](SETUP_GUIDE.md)** → Seção "Suporte"
3. **[N8N_IMPLEMENTATION_COMPLETE.md](../N8N_IMPLEMENTATION_COMPLETE.md)** → Seção "Observabilidade"

---

## 📊 Referência Rápida

### Endpoints dos Fluxos

| Fluxo | Webhook | Método | Documentação |
|-------|---------|--------|--------------|
| Chat Orchestrator | `/chat-orchestrator` | POST | [README.md](README.md#1-chat-session-orchestrator) |
| Document Intake | `/document-intake` | POST | [README.md](README.md#2-document-intake--classification) |
| Timeline Updater | `/timeline-updater` | POST | [README.md](README.md#3-timeline--checklist-updater) |
| IN Upload | `/in-upload` | POST | [README.md](README.md#4-in-knowledge-management) |
| Admin List | `/admin/list-processes` | POST | [README.md](README.md#5-admin-console-apis) |
| Admin Reprocess | `/admin/reprocess` | POST | [README.md](README.md#5-admin-console-apis) |
| Admin Health | `/admin/health` | GET | [README.md](README.md#5-admin-console-apis) |

### Credenciais Necessárias

| Nome | Tipo | Uso | Documentação |
|------|------|-----|--------------|
| `saas-postgres` | PostgreSQL | Banco SaaS | [SETUP_GUIDE.md](SETUP_GUIDE.md#postgresql-saas-database) |
| `gemini-api` | Google Gemini | IA e embeddings | [SETUP_GUIDE.md](SETUP_GUIDE.md#google-gemini-api) |

### Tabelas de Banco

| Tabela | Propósito | Migration |
|--------|-----------|-----------|
| `organizations` | Organizações (+ mode, status, key_hash) | `001_add_org_connections_table.py` |
| `org_connections` | Credenciais multi-tenant | `001_add_org_connections_table.py` |
| `municipal_instructions` | INs municipais | `001_add_org_connections_table.py` |
| `flow_metrics` | Métricas de execução | `001_add_org_connections_table.py` |
| `chat_files` | Arquivos (+ hash, category, status) | `001_add_org_connections_table.py` |

### Modelos Python

| Arquivo | Classe | Documentação |
|---------|--------|--------------|
| `org_connection.py` | `OrgConnection` | [N8N_IMPLEMENTATION_COMPLETE.md](../N8N_IMPLEMENTATION_COMPLETE.md#2-models-sqlalchemy) |
| `municipal_instruction.py` | `MunicipalInstruction` | [N8N_IMPLEMENTATION_COMPLETE.md](../N8N_IMPLEMENTATION_COMPLETE.md#2-models-sqlalchemy) |
| `flow_metric.py` | `FlowMetric` | [N8N_IMPLEMENTATION_COMPLETE.md](../N8N_IMPLEMENTATION_COMPLETE.md#2-models-sqlalchemy) |

### APIs de Ativação

| Endpoint | Método | Propósito | Documentação |
|----------|--------|-----------|--------------|
| `/api/v1/activation/generate-key` | POST | Gerar chave (admin) | [SETUP_GUIDE.md](SETUP_GUIDE.md#passo-1-gerar-chave-de-ativação) |
| `/api/v1/activation/activate` | POST | Ativar instalação | [SETUP_GUIDE.md](SETUP_GUIDE.md#passo-2-cliente-ativa-instalação) |
| `/api/v1/activation/configure-connection` | POST | Configurar DB | [SETUP_GUIDE.md](SETUP_GUIDE.md#passo-3-configurar-conexão-do-banco-on-prem) |
| `/api/v1/activation/connections/{org_id}` | GET | Listar conexões | [README.md](README.md) |

---

## 🔍 Busca Rápida por Termo

### Termos Técnicos

- **Multi-Tenant**: [`README.md`](README.md#arquitetura-multi-tenant), [`ARCHITECTURE_DIAGRAM.md`](ARCHITECTURE_DIAGRAM.md)
- **On-Prem**: [`SETUP_GUIDE.md`](SETUP_GUIDE.md#setup-de-organização-on-prem), [`ARCHITECTURE_DIAGRAM.md`](ARCHITECTURE_DIAGRAM.md#fluxo-de-ativação-on-prem)
- **Criptografia**: [`N8N_IMPLEMENTATION_COMPLETE.md`](../N8N_IMPLEMENTATION_COMPLETE.md#arquitetura-de-segurança)
- **VPN**: [`SETUP_GUIDE.md`](SETUP_GUIDE.md#passo-4-configurar-vpntúnel)
- **Credentials Resolver**: [`N8N_IMPLEMENTATION_COMPLETE.md`](../N8N_IMPLEMENTATION_COMPLETE.md#3-backend-python---sistema-de-credenciais)
- **JWT**: [`README.md`](README.md#validação-de-jwt)
- **Gemini**: [`README.md`](README.md#instalação-no-n8n)
- **Embeddings**: [`02_document_intake_classification.json`](02_document_intake_classification.json)
- **OCR**: [`02_document_intake_classification.json`](02_document_intake_classification.json)

### Tarefas Comuns

- **Adicionar categoria**: [`README.md`](README.md#ajustar-categorias-de-documentos)
- **Mudar etapas**: [`README.md`](README.md#ajustar-etapas-da-timeline)
- **Ajustar tokens**: [`README.md`](README.md#ajustar-limites-de-tokens)
- **Configurar VPN**: [`SETUP_GUIDE.md`](SETUP_GUIDE.md#opção-1-wireguard-recomendado)
- **Gerar chave de ativação**: [`SETUP_GUIDE.md`](SETUP_GUIDE.md#passo-1-gerar-chave-de-ativação)
- **Ver métricas**: [`N8N_IMPLEMENTATION_COMPLETE.md`](../N8N_IMPLEMENTATION_COMPLETE.md#consultar-métricas)
- **Troubleshooting**: [`README.md`](README.md#troubleshooting)

---

## 🎓 Tutoriais Recomendados

### Para Iniciantes
1. Leia [`RESUMO_EXECUTIVO_N8N.md`](../RESUMO_EXECUTIVO_N8N.md) para entender o contexto
2. Veja os diagramas em [`ARCHITECTURE_DIAGRAM.md`](ARCHITECTURE_DIAGRAM.md)
3. Siga o setup em [`SETUP_GUIDE.md`](SETUP_GUIDE.md)
4. Teste com exemplos de [`test_payloads.json`](test_payloads.json)

### Para Desenvolvedores Experientes
1. Clone/baixe os arquivos JSON dos workflows
2. Leia [`README.md`](README.md) seção por seção
3. Configure credenciais no N8N
4. Importe e ative os workflows
5. Teste endpoints com curl ou Postman

### Para Administradores de Sistema
1. Prepare a infraestrutura (PostgreSQL, N8N, VPN)
2. Siga [`SETUP_GUIDE.md`](SETUP_GUIDE.md) passo-a-passo
3. Configure monitoramento e logs
4. Execute checklist de segurança
5. Teste health checks

---

## 📞 Precisa de Ajuda?

### Problemas Comuns

| Problema | Onde Procurar |
|----------|---------------|
| Erro ao importar workflow | [`README.md`](README.md#instalação-no-n8n) |
| Credenciais não funcionam | [`SETUP_GUIDE.md`](SETUP_GUIDE.md#3-importar-credenciais-no-n8n) |
| Webhook não responde | [`README.md`](README.md#webhooks-não-respondem) |
| Erro de criptografia | [`README.md`](README.md#erro-failed-to-decrypt-connection-credentials) |
| VPN não conecta | [`SETUP_GUIDE.md`](SETUP_GUIDE.md#opção-1-wireguard-recomendado) |
| Organização não encontrada | [`README.md`](README.md#erro-organization-not-found-or-not-active) |

### Recursos Adicionais

- Documentação oficial do N8N: https://docs.n8n.io
- API Gemini: https://ai.google.dev/docs
- WireGuard: https://www.wireguard.com/quickstart
- PostgreSQL: https://www.postgresql.org/docs

---

## 📝 Controle de Versões

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0.0 | 2025-11-15 | Implementação inicial completa |

---

**Última atualização**: 15/11/2025  
**Mantenedor**: AI Assistant (Claude Sonnet 4.5)



