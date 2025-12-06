# 🏗️ Arquitetura do Sistema - Backend

O Backend é construído com **FastAPI**, seguindo princípios de arquitetura limpa e modular.

## Estrutura de Diretórios

```
app/
├── api/
│   └── v1/           # Endpoints da API versionados
│       ├── auth.py       # Login, refresh, perfil
│       ├── chat.py       # Chat, arquivos, timeline
│       ├── organization.py # Gestão de empresas e usuários
│       ├── templates.py  # Gestão de modelos de documentos
│       └── ...
├── core/             # Configurações globais
│   ├── config.py     # Settings via Pydantic
│   ├── security.py   # JWT, Password hash
│   └── encryption.py # Criptografia de arquivos
├── models/           # Modelos SQLAlchemy (Banco de Dados)
├── schemas/          # Schemas Pydantic (Validação e Serialização)
├── services/         # Lógica de negócio complexa (opcional, quando não cabe na rota)
├── utils/            # Utilitários (Loggers, formatadores)
└── main.py           # Entrypoint da aplicação
```

## Tecnologias Chave

*   **FastAPI**: Framework web de alta performance.
*   **SQLAlchemy (Async)**: ORM para interação com banco de dados.
*   **Alembic**: Migrações de schema.
*   **Pydantic**: Validação de dados robusta.
*   **PostgreSQL + pgvector**: Banco relacional com suporte a busca vetorial (para IA).

## Modelagem de Dados Principal

### Organização (`organizations`)
A entidade raiz. Tudo pertence a uma organização.
- `id`, `name`, `mode` (saas/onprem).

### Usuário (`users`)
Pertence a *uma ou mais* organizações (através de tabela associativa ou lógica de convites).
- `id`, `email`, `hashed_password`, `last_organization_id`.

### Chat (`chat_threads`, `chat_messages`)
Sistema de conversação associado a contextos ambientais.
- `thread`: Uma conversa sobre um processo específico.
- `files`: Arquivos criptografados vinculados à thread.
- `timeline`: Eventos gerados a partir da interação na thread.

## Fluxo de Requisição (Request Lifecycle)

1.  **Middleware**: `CORSMiddleware`, `AuditMiddleware`.
2.  **Auth Dependency**: Valida o Bearer Token. Decodifica o `organization_id`.
3.  **Router**: Direciona para a função correta em `api/v1/`.
4.  **Service/Controller**: Executa a lógica, valida permissões (RBAC).
5.  **Database**: Consulta ou persiste dados via SQLAlchemy session.
6.  **Response**: Retorna dados validados pelo Pydantic Schema.
