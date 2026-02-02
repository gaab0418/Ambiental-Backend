# Contexto da Tarefa: Correção de Erros de Inicialização do Banco de Dados Backend

## Objetivo
Resolver erros que impediam a inicialização do backend (“ModuleNotFoundError” e “InvalidRequestError”) causados pela remoção incompleta dos modelos `ChatTimelineEvent` e `ProcessTimelineEntry`.

## Alterações Realizadas

### 1. Remoção de `ChatTimelineEvent`
- **Arquivos Afetados:**
  - `app/api/v1/chat.py`
  - `app/api/v1/chat_files.py`
  - `tests/test_e2e_api.py`
- **Ações:**
  - Remoção de imports de `ChatTimelineEvent`, `TimelineEventType`, `TimelineEventStatus`.
  - Remoção da lógica de criação/atualização de timeline events nos endpoints `get_chat_threads`, `send_chat_message`, `conversation_callback`, `upload_chat_files`.
  - O campo `has_timeline` nas respostas foi mantido como `False` (hardcoded) para manter compatibilidade com o frontend por enquanto, marcado como `# Deprecated`.
  - Adicionado o campo `type: str` na resposta de `get_chat_threads` que estava faltando e causando erro de validação Pydantic.

### 2. Remoção de `ProcessTimelineEntry`
- **Arquivos Afetados:**
  - `app/api/v1/processes.py`
  - `app/schemas/processes.py`
- **Ações:**
  - Remoção de imports e endpoints relacionados à timeline de processos (`get_process_timeline`, `add_timeline_entry`).
  - Remoção da criação automática de `ProcessTimelineEntry` ao criar ou atualizar status de processos.
  - Correção de imports ausentes (`ProcessListResponse`, `ProcessCreate`, etc.) em `app/api/v1/processes.py`.

### 3. Correções Diversas
- **`app/api/v1/checklist.py`:** Corrigido import de `get_current_user` (caminho incorreto `app.api.dependencies` -> `app.dependencies`).
- **`app/main.py`:** Removido import de `chat_timeline` e adicionado import de `checklist` para registrar as rotas corretamente.

## Estado Atual
- O backend inicia corretamente (`python main.py`).
- Todos os testes end-to-end (`tests/test_e2e_api.py`) passaram (18 passed, 7 warnings).
- A funcionalidade de Timeline foi efetivamente removida do código, substituída conceitualmente por Checklists (no frontend).

## Próximos Passos Sugeridos
- Validar se o Frontend não está quebrando ao receber `has_timeline: False` (parece estar ok).
- Continuar a implementação/melhoria da feature de Checklist no Frontend.
