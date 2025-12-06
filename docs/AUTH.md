# 🔐 Autenticação e Segurança

Este documento detalha a arquitetura de autenticação, o sistema multi-organização e as práticas de segurança implementadas no Backend.

## 🔑 Visão Geral da Autenticação

O sistema utiliza **JWT (JSON Web Tokens)** e **OAuth2 Password Flow**.

*   **Access Token**: Curta duração (padrão: 15 min). Usado para acesso à API.
*   **Refresh Token**: Longa duração (padrão: 7 dias). Usado apenas para obter novos Access Tokens.

### Fluxo de Login (`/api/v1/auth/token`)

1.  Usuário envia credenciais (`username`, `password`).
2.  Sistema valida credenciais.
3.  **Seleção de Organização Inteligente**:
    *   Se o usuário tem acesso a **múltiplas organizações**, o sistema verifica a **última organização acessada** (`last_organization_id`).
    *   Se `last_organization_id` for válida, o login é feito automaticamente nessa organização.
    *   Se não, login é feito na primeira organização disponível.
    *   Não há mais necessidade de um passo intermediário de "seleção de organização" obrigatório.
4.  Retorna par de tokens (`access_token`, `refresh_token`) contendo o contexto da organização (`organization_id`).

### Troca de Organização

Para mudar de organização sem relogar:
*   Endpoint: `POST /api/v1/auth/switch-organization`
*   Body: `{ "organization_id": 123 }`
*   O sistema valida se o usuário pertence à nova organização.
*   Retorna novos tokens válidos para a nova organização.
*   Atualiza `last_organization_id` no perfil do usuário.

## 🏢 Sistema Multi-Organização (Multi-Tenancy)

O isolamento de dados é lógico e reforçado em todas as camadas:

1.  **Banco de Dados**: Todas as tabelas sensíveis possuem coluna `organization_id`.
2.  **Middleware**: O token JWT decodificado injeta o `current_user` e `current_organization` no request.
3.  **API Layer**: Endpoints utilizam dependências que filtram queries automaticamente por `organization_id`.

### Permissões (RBAC)

As permissões são baseadas em **Roles** dentro de cada organização. Um usuário pode ser `ADMIN` na Organização A e `USER` na Organização B.

*   `ADMINISTRATOR` (Global): Super-usuário (apenas para equipe interna/SaaS admin).
*   `ADMIN`: Administrador do tenant (organização).
*   `MANAGER`: Gerente de processos.
*   `USER`: Usuário padrão.
*   `CONSULTANT`: Consultor externo.

## 🛡️ Segurança de Dados

### Criptografia de Arquivos (`AES-256-GCM`)
Arquivos enviados (PDFs, imagens) são criptografados antes de serem salvos no disco ou S3.
*   Cada arquivo tem um **IV (Initialization Vector)** único.
*   Usa-se uma `FILE_ENCRYPTION_KEY` (no `.env`) + `Tag` de autenticação.
*   Isso garante que, mesmo com acesso ao disco, os arquivos são ilegíveis sem a chave e o banco de dados.

### Validação de Integridade (N8N)
A comunicação com o N8N é protegida por **HMAC-SHA256**.
*   Backend -> N8N: Envia token JWT interno.
*   N8N -> Backend (Callback): Assina o payload com `N8N_SIGNING_SECRET`.
*   O Backend rejeita qualquer request que não tenha uma assinatura válida ou cujo timestamp seja antigo (prevenção contra replay attacks).
