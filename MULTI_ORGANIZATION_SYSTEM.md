# Sistema Multi-Organização

## Visão Geral

O sistema foi reestruturado para permitir que um usuário (identificado pelo e-mail) possa fazer parte de múltiplas organizações. Isso é especialmente útil para:

- **Administradores**: que precisam acessar o painel de múltiplos clientes
- **Consultores**: que trabalham com várias empresas
- **Usuários multi-empresa**: que atuam em mais de uma organização

## Mudanças no Banco de Dados

### Antes (Relação Um-para-Muitos)
- Um usuário pertencia a uma única organização
- `users.organization_id` era uma chave estrangeira direta
- `users.role_id` definia o papel do usuário

### Depois (Relação Muitos-para-Muitos)
- Um usuário pode pertencer a múltiplas organizações
- Nova tabela: `user_organization_association`
- O papel (role) do usuário agora é específico por organização
- `users.organization_id` e `users.role_id` foram removidos

### Tabela de Associação

```sql
CREATE TABLE user_organization_association (
    user_id INTEGER NOT NULL,
    organization_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (user_id, organization_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
```

## Fluxo de Login

### 1. Login Inicial
```http
POST /api/auth/token
Content-Type: application/x-www-form-urlencoded

username=usuario@exemplo.com&password=senha123
```

**Resposta - Usuário com uma organização:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "requires_org_selection": false,
  "available_organizations": []
}
```

**Resposta - Usuário com múltiplas organizações:**
```json
{
  "access_token": "eyJ..._temp",
  "refresh_token": "",
  "token_type": "bearer",
  "requires_org_selection": true,
  "available_organizations": [
    {
      "id": 1,
      "name": "Empresa A Ltda",
      "cnpj_cpf": "12.345.678/0001-90",
      "role_name": "ADMIN"
    },
    {
      "id": 2,
      "name": "Empresa B SA",
      "cnpj_cpf": "98.765.432/0001-10",
      "role_name": "CONSULTANT"
    }
  ]
}
```

### 2. Seleção de Organização (se necessário)

Se `requires_org_selection` for `true`, o frontend deve chamar:

```http
POST /api/auth/select-organization
Authorization: Bearer eyJ..._temp
Content-Type: application/json

{
  "organization_id": 1
}
```

**Resposta:**
```json
{
  "access_token": "eyJ..._full",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "requires_org_selection": false,
  "available_organizations": []
}
```

## Estrutura do Token JWT

### Token Temporário (para seleção de organização)
```json
{
  "sub": "123",
  "temp": true,
  "exp": 1730000000
}
```

### Token Completo (com organização)
```json
{
  "sub": "123",
  "organization_id": 1,
  "role": "ADMIN",
  "type": "access",
  "exp": 1730000000
}
```

## Endpoint `/me`

O endpoint `/api/auth/me` agora retorna:

```json
{
  "id": 123,
  "email": "usuario@exemplo.com",
  "full_name": "Nome do Usuário",
  "is_active": true,
  "is_verified": true,
  "profile_image_url": null,
  "phone": null,
  "bio": null,
  "created_at": "2025-10-26T10:00:00Z",
  "last_login_at": "2025-10-26T14:30:00Z",
  "current_organization_id": 1,
  "current_role_name": "ADMIN",
  "current_organization_name": "Empresa A Ltda",
  "organizations": [
    {
      "id": 1,
      "name": "Empresa A Ltda",
      "cnpj_cpf": "12.345.678/0001-90",
      "role_name": "ADMIN"
    },
    {
      "id": 2,
      "name": "Empresa B SA",
      "cnpj_cpf": "98.765.432/0001-10",
      "role_name": "CONSULTANT"
    }
  ]
}
```

## Como Adicionar um Usuário a uma Nova Organização

```python
from app.models.user_organization_association import UserOrganizationAssociation

# Adicionar usuário existente a uma organização
assoc = UserOrganizationAssociation(
    user_id=user.id,
    organization_id=organization.id,
    role_id=role.id
)
db.add(assoc)
db.commit()
```

## Migração de Dados

A migração `bbbb58c5cb60_add_user_organization_many_to_many.py` automaticamente:

1. Cria a tabela `user_organization_association`
2. Migra todos os dados existentes de `users.organization_id` e `users.role_id`
3. Remove as colunas antigas

Para aplicar a migração:

```bash
alembic upgrade head
```

Para reverter (se necessário):

```bash
alembic downgrade -1
```

## Considerações de Segurança

1. **Tokens Temporários**: Expiram em 5 minutos e só permitem seleção de organização
2. **Verificação de Acesso**: Ao selecionar uma organização, o sistema verifica se o usuário realmente tem acesso
3. **Contexto por Sessão**: Cada token carrega o `organization_id`, garantindo que as operações sejam feitas no contexto correto
4. **Refresh Token**: Também vinculado à organização selecionada

## Impactos nas APIs Existentes

Todas as APIs que anteriormente usavam `current_user.organization_id` precisam ser atualizadas para extrair o `organization_id` do token JWT.

### Exemplo de Adaptação

**Antes:**
```python
@router.get("/resource")
async def get_resource(current_user: User = Depends(get_current_active_user)):
    org_id = current_user.organization_id
    # ...
```

**Depois:**
```python
from app.dependencies.auth import get_organization_from_token

@router.get("/resource")
async def get_resource(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    org_id = get_organization_from_token(request)
    # ...
```

Ou usando o helper combinado:

```python
from app.dependencies.auth import get_current_user_with_org

@router.get("/resource")
async def get_resource(
    user_org: Tuple[User, Optional[int]] = Depends(get_current_user_with_org)
):
    current_user, org_id = user_org
    # ...
```

## Frontend - Exemplo de Implementação

```typescript
// 1. Login inicial
const loginResponse = await authClient.login(email, password);

if (loginResponse.requires_org_selection) {
  // 2. Mostrar seletor de organização
  const selectedOrg = await showOrganizationSelector(
    loginResponse.available_organizations
  );
  
  // 3. Selecionar organização
  const finalTokens = await authClient.selectOrganization(
    loginResponse.access_token,
    selectedOrg.id
  );
  
  // 4. Salvar tokens finais
  saveTokens(finalTokens);
} else {
  // Login direto - apenas uma organização
  saveTokens(loginResponse);
}
```

## Placeholders para Templates

Um novo endpoint foi adicionado para listar os placeholders disponíveis para templates:

```http
GET /api/v1/templates/placeholders
Authorization: Bearer {token}
```

**Resposta:**
```json
[
  {
    "name": "Usuário Atual",
    "description": "Informações sobre o usuário logado...",
    "placeholders": [
      {
        "name": "user.full_name",
        "description": "Nome completo do usuário",
        "example": "João da Silva",
        "category": "Usuário Atual"
      }
    ]
  }
]
```

Para usar em um template:
```html
<p>Documento gerado por {{ user.full_name }} em {{ current_date }}</p>
<p>Empresa: {{ organization.name }} - CNPJ: {{ organization.cnpj_cpf }}</p>
```

