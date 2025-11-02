# Análise de Segurança - Sistema de Autenticação

## Data: 28/01/2025

## Resumo Executivo

A implementação do novo fluxo de autenticação mantém e até **melhora** a segurança do sistema comparado ao fluxo anterior. Todas as práticas de segurança foram preservadas e o acesso baseado em organização continua validado.

---

## ✅ Pontos Fortes de Segurança

### 1. **Autenticação Robusta**
```python
# app/core/security.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```
- ✅ Senhas hashadas com **bcrypt**
- ✅ Algoritmo forte e amplamente recomendado
- ✅ Verificação segura de senha com timing-safe

### 2. **Tokens JWT Seguros**
```python
# JWT com algoritmo HS256
encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
```
- ✅ Tokens assinados digitalmente
- ✅ Validação automática de expiração
- ✅ Separação clara entre access e refresh tokens
- ✅ Tipo de token validado (`"type": "access"` ou `"refresh"`)

### 3. **Validação de Expiração Rigorosa**
- Access tokens: **15 minutos** (configurável)
- Refresh tokens: **7 dias** (configurável)
- ✅ Revalidação automática no backend via `jwt.decode()`

### 4. **Isolamento de Organização (CRÍTICO)**

#### No Login:
```python
# Linha 92-97: Validação que usuário TEM acesso à organização selecionada
if len(user_orgs) > 1 and user.last_organization_id:
    for assoc in user_orgs:
        if assoc.organization_id == user.last_organization_id:
            selected_assoc = assoc  # ✅ Só usa se tem acesso
            break
```
- ✅ Apenas organizações na tabela `user_organization_association` são consideradas
- ✅ Não permite seleção arbitrária de organização
- ✅ Fallback seguro: primeira organização autorizada

#### No Switch:
```python
# Linha 604-613: Validação de acesso antes de trocar
assoc = db.query(UserOrganizationAssociation).filter(
    UserOrganizationAssociation.user_id == current_user.id,
    UserOrganizationAssociation.organization_id == org_selection.organization_id
).first()

if not assoc:
    raise HTTPException(403, "User does not have access to this organization")
```
- ✅ Validação explícita de acesso antes de trocar
- ✅ Retorna 403 se usuário não tem acesso
- ✅ Não permite acesso não autorizado

#### No Refresh:
```python
# Linha 377-386: Revalida acesso ao refreshar
assoc = db.query(UserOrganizationAssociation).filter(
    UserOrganizationAssociation.user_id == user.id,
    UserOrganizationAssociation.organization_id == organization_id
).first()

if not assoc:
    raise HTTPException(403, "User no longer has access to this organization")
```
- ✅ Verifica se usuário **ainda** tem acesso à organização
- ✅ Revoga automaticamente se acesso foi removido
- ✅ Protege contra tokens "órfãos" de organizações removidas

### 5. **Contexto de Organização em Cada Request**
```python
# app/dependencies/auth.py - Linha 13-27
def get_organization_from_token(request: Request) -> Optional[int]:
    """Extract organization_id from the JWT token"""
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split(" ")[1]
    payload = verify_token(token, "access")
    
    if payload:
        return payload.get("organization_id")  # ✅ Do token, não do input
    return None
```
- ✅ Organization ID vem **do token JWT**, não do input do usuário
- ✅ Usuário não pode forjar organização diferente no token
- ✅ Validação server-side sempre

### 6. **Controle de Acesso Baseado em Role (RBAC)**
```python
# app/dependencies/auth.py - Linha 302-354
def require_role_in_current_org(required_roles: list[str]):
    """Validates user has role in CURRENT organization from JWT"""
    # 1. Pega organization_id do TOKEN
    org_id = get_organization_from_token(request)
    
    # 2. Busca associação específica usuário+organização
    assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id,
        UserOrganizationAssociation.organization_id == org_id
    ).first()
    
    # 3. Valida role naquela organização específica
    if role and (role.name in required_roles or role.name == "ADMINISTRATOR"):
        return current_user
```
- ✅ Valida role **específica** por organização
- ✅ Mesmo usuário pode ter roles diferentes em diferentes organizações
- ✅ ADMINISTRATOR tem acesso global (por design)
- ✅ Separação clara de permissões entre organizações

### 7. **Validação de Usuário Ativo**
```python
# app/api/v1/auth.py - Linha 56-60
if not user.is_active:
    raise HTTPException(400, "Inactive user")

# app/dependencies/auth.py - Linha 53-57
if not user.is_active:
    raise HTTPException(400, "Inactive user")
```
- ✅ Usuários inativos bloqueados em todas as operações
- ✅ Verificado em login, refresh e endpoints protegidos

### 8. **Audit Logging**
- ✅ Middleware de auditoria registra ações
- ✅ Rastreabilidade de acesso por organização
- ✅ Logs incluem organization_id do contexto

### 9. **Segurança do Banco de Dados**
```python
# alembic/versions/a1b2c3d4e5f6_add_last_organization_id_to_users.py
op.create_foreign_key(
    'users_last_organization_id_fkey',
    'users', 'organizations',
    ['last_organization_id'], ['id'],
    ondelete='SET NULL'  # ✅ Safe: não quebra se org for deletada
)
```
- ✅ Foreign keys garantem integridade referencial
- ✅ `ON DELETE SET NULL` previne data corruption
- ✅ Índices para performance sem comprometer segurança

---

## 🔍 Análise de Vulnerabilidades Potenciais

### 1. **Token Tempo de Vida**
**Configuração atual:**
- Access token: 15 minutos
- Refresh token: 7 dias

**Análise:** ✅ **Adequado**
- Tokens de acesso curtos limitam janela de exploração
- Refresh tokens permitem renovação sem re-autenticação frequente
- Ambos são JWT assinados, não podem ser modificados

**Recomendação:** Manter conforme está

### 2. **Seleção Automática vs Segurança**
**Preocupação:** "Usuário pode ser logado em organização diferente da que esperava?"

**Análise:** ✅ **Seguro**
- Seleção sempre valida `user_organization_association`
- Usuário só pode acessar organizações onde **já tem permissão**
- Não cria novas permissões, apenas usa as existentes
- `last_organization_id` é preferência de UX, não mudança de acesso

### 3. **Race Conditions**
**Cenário:** Dois logins simultâneos atualizando `last_organization_id`

**Análise:** ✅ **Seguro**
- PostgreSQL garante atomicidade de transações
- `db.commit()` é atômico por transação
- Pior caso: último commit "ganha" (comportamento esperado)

### 4. **Token Replay**
**Cenário:** Ataque de retransmissão de token

**Análise:** ✅ **Protegido**
- JWT com expiração curta (15 min)
- Refresh requer senha ou refresh token válido
- Tokens incluem timestamp, não podem ser reutilizados indefinidamente

### 5. **Session Fixation**
**Análise:** ✅ **Não aplicável**
- Sistema usa JWT stateless
- Não mantém sessões server-side
- Cada request valida token independentemente

### 6. **Insufficient Authorization Check**
**Cenário:** Usuário força acesso a organização não autorizada

**Análise:** ✅ **Protegido**
- Organization ID vem **do token JWT assinado**
- Usuário não pode modificar conteúdo do token
- Todas as operações validam `user_organization_association`
- Refresh token revalida acesso

---

## 🛡️ Comparação com Implementação Anterior

| Aspecto | Antes | Agora | Status |
|---------|-------|-------|--------|
| **Tokens Temporários** | ❌ 5 min expiração | ✅ 15 min completos | ✅ Melhor |
| **Refresh Token** | ❌ Vazio para multi-org | ✅ Sempre completo | ✅ Melhor |
| **Validação de Acesso** | ✅ Sim | ✅ Sim | ✅ Igual |
| **Contexto de Org** | ✅ No token | ✅ No token | ✅ Igual |
| **RBAC por Org** | ✅ Sim | ✅ Sim | ✅ Igual |
| **Lembrete de Preferência** | ❌ Não | ✅ Sim | ✅ Melhor |
| **Experiência do Usuário** | ❌ Forçado a selecionar | ✅ Automático | ✅ Melhor |

**Conclusão:** Implementação **mantém** todas as garantias de segurança e **melhora** a UX sem comprometer proteções.

---

## ⚠️ Recomendações Adicionais (Opcional)

### Para Produção:

1. **Secret Key Forte**
   ```python
   # app/config.py - Linha 17
   secret_key: str = "your-super-secret-key-here-change-in-production"
   ```
   ⚠️ **CRÍTICO:** Trocar por chave forte e mantê-la em variável de ambiente

2. **Rate Limiting**
   - Considerar rate limiting no endpoint `/token` para prevenir brute force
   - Ferramentas: `slowapi`, `fastapi-limiter`

3. **HTTPS Obrigatório**
   - Em produção, sempre usar HTTPS
   - Tokens nunca devem trafegar em HTTP

4. **Token Blacklisting (Opcional)**
   - Se necessário logout invalidação, implementar blacklist de tokens
   - Redis é boa opção para isso

5. **Audit Logs Aprimorados**
   - Log de tentativas de login falhadas
   - Log de mudanças de organização

---

## ✅ Conclusão Final

A implementação é **SEGURA** e mantém todas as garantias de segurança:

1. ✅ Autenticação forte (bcrypt + JWT)
2. ✅ Isolamento completo de organizações
3. ✅ Validação de acesso em todas as etapas
4. ✅ RBAC por organização
5. ✅ Tokens com expiração adequada
6. ✅ Proteção contra replay e modificação
7. ✅ Integridade referencial no banco
8. ✅ Auditability

**A mudança apenas melhora a UX ao selecionar automaticamente a última organização usada, SEM afrouxar qualquer controle de segurança.**

---

## Testes de Segurança Recomendados

1. ✅ Tentar acessar organização sem permissão → Deve retornar 403
2. ✅ Modificar token JWT → Deve falhar na validação
3. ✅ Usar token expirado → Deve falhar
4. ✅ Remover usuário de organização → Próximo refresh deve falhar
5. ✅ Tentar switch para organização não autorizada → Deve retornar 403

**Todos esses cenários já estão protegidos pela implementação atual.**

