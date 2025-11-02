# Guia Rápido - Sistema Multi-Organização

## 🚀 Começando

### 1. Aplicar a Migração

```bash
cd Backend
alembic upgrade head
```

Isso irá:
- Criar a tabela `user_organization_association`
- Migrar automaticamente todos os usuários existentes
- Remover colunas obsoletas

### 2. Verificar a Migração

```bash
python scripts/list_user_org_associations.py
```

Você deverá ver todos os usuários existentes com suas respectivas organizações.

---

## 💻 Como Usar no Código

### Extrair Organization ID do Token

**Antes:**
```python
@router.get("/my-endpoint")
async def my_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    org_id = current_user.organization_id  # ❌ NÃO FUNCIONA MAIS
```

**Depois:**
```python
from fastapi import Request
from app.dependencies.auth import get_organization_from_token

@router.get("/my-endpoint")
async def my_endpoint(
    request: Request,  # ✅ Adicionar Request
    current_user: User = Depends(get_current_active_user)
):
    org_id = get_organization_from_token(request)  # ✅ Extrair do token
    
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")
```

### Verificar Acesso a uma Organização

```python
from app.models.user_organization_association import UserOrganizationAssociation

# Verificar se usuário tem acesso
assoc = db.query(UserOrganizationAssociation).filter(
    UserOrganizationAssociation.user_id == current_user.id,
    UserOrganizationAssociation.organization_id == org_id
).first()

if not assoc:
    raise HTTPException(status_code=403, detail="Access denied")

# Obter o papel do usuário nesta organização
role = db.query(Role).filter(Role.id == assoc.role_id).first()
```

### Listar Organizações do Usuário

```python
user_orgs = db.query(UserOrganizationAssociation).filter(
    UserOrganizationAssociation.user_id == current_user.id
).all()

for assoc in user_orgs:
    org = db.query(Organization).filter(Organization.id == assoc.organization_id).first()
    role = db.query(Role).filter(Role.id == assoc.role_id).first()
    print(f"{org.name} - {role.name}")
```

---

## 🔧 Scripts Úteis

### Adicionar Usuário a uma Organização

```bash
# Sintaxe
python scripts/add_user_to_organization.py <email> <org_id> <role_name>

# Exemplo
python scripts/add_user_to_organization.py admin@empresa.com 2 CONSULTANT
```

### Listar Organizações de um Usuário

```bash
python scripts/add_user_to_organization.py list admin@empresa.com
```

### Listar Todas as Associações

```bash
python scripts/list_user_org_associations.py
```

### Listar Todas as Organizações

```bash
python scripts/list_user_org_associations.py orgs
```

---

## 📱 Frontend - Fluxo de Login

### 1. Fazer Login

```typescript
const response = await fetch('/api/auth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    username: email,
    password: password
  })
});

const data = await response.json();
```

### 2. Verificar se Precisa Selecionar Organização

```typescript
if (data.requires_org_selection) {
  // Mostrar seletor com data.available_organizations
  const selectedOrgId = await showOrgSelector(data.available_organizations);
  
  // Chamar endpoint de seleção
  const finalResponse = await fetch('/api/auth/select-organization', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${data.access_token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ organization_id: selectedOrgId })
  });
  
  const finalData = await finalResponse.json();
  saveTokens(finalData.access_token, finalData.refresh_token);
  
} else {
  // Login direto - salvar tokens
  saveTokens(data.access_token, data.refresh_token);
}
```

---

## 🎯 Placeholders de Templates

### Listar Placeholders Disponíveis

```bash
curl -X GET http://localhost:8000/api/v1/templates/placeholders \
  -H "Authorization: Bearer {token}"
```

### Usar em Templates

```html
<h1>{{ document.title }}</h1>

<p>Gerado por: {{ user.full_name }} ({{ user.email }})</p>
<p>Data: {{ current_date }} às {{ current_time }}</p>

<hr>

<h2>Informações da Empresa</h2>
<p><strong>Nome:</strong> {{ organization.name }}</p>
<p><strong>CNPJ/CPF:</strong> {{ organization.cnpj_cpf }}</p>
<p><strong>Endereço:</strong> {{ organization.address }}</p>
<p><strong>Telefone:</strong> {{ organization.phone }}</p>
```

### Adicionar Novos Placeholders

Edite `Backend/app/utils/placeholders.py`:

```python
PlaceholderInfo(
    name="meu.novo.placeholder",
    description="Descrição do que ele faz",
    example="Exemplo de valor",
    category="Nome da Categoria"
)
```

---

## 🐛 Troubleshooting

### Erro: "User is not associated with any organization"

**Causa:** Usuário não tem vínculo com nenhuma organização após a migração.

**Solução:**
```bash
python scripts/add_user_to_organization.py usuario@email.com 1 ADMIN
```

### Erro: "Could not validate credentials"

**Causa:** Token expirado ou inválido.

**Solução:** Fazer login novamente.

### Erro: "User does not have access to this organization"

**Causa:** Tentando selecionar uma organização que o usuário não tem acesso.

**Solução:** Verificar quais organizações o usuário tem acesso:
```bash
python scripts/add_user_to_organization.py list usuario@email.com
```

### Migração não Aplicada

**Verificar status:**
```bash
alembic current
```

**Aplicar migração:**
```bash
alembic upgrade head
```

**Ver histórico:**
```bash
alembic history
```

---

## 📚 Documentação Adicional

- **Sistema Completo:** `MULTI_ORGANIZATION_SYSTEM.md`
- **Resumo de Mudanças:** `CHANGES_SUMMARY.md`
- **Status de Implementação:** `IMPLEMENTATION_STATUS.md`
- **README Principal:** `README.md`

---

## ✅ Checklist Rápido

Para implementar multi-org em um endpoint existente:

- [ ] Adicionar `Request` como parâmetro da função
- [ ] Importar `get_organization_from_token`
- [ ] Substituir `current_user.organization_id` por `get_organization_from_token(request)`
- [ ] Verificar se `org_id` não é `None`
- [ ] Testar o endpoint

**Exemplo completo:**

```python
from fastapi import Request, HTTPException
from app.dependencies.auth import get_organization_from_token

@router.get("/users")
async def get_users(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Extrair org_id do token
    org_id = get_organization_from_token(request)
    
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="Organization context required"
        )
    
    # Usar org_id normalmente
    users = db.query(User).join(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.organization_id == org_id
    ).all()
    
    return users
```

---

## 🎉 Pronto!

O sistema multi-organização está configurado e pronto para uso. Se tiver dúvidas, consulte a documentação completa ou os scripts de exemplo.

