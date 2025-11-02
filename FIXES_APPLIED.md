# Correções Aplicadas

## Erro Corrigido: NameError em dependencies/auth.py

### Problema
```
NameError: name 'get_current_active_user' is not defined
```

A função `get_current_user_with_org` estava sendo definida **antes** de `get_current_active_user`, causando um erro de referência.

### Solução Aplicada

1. **Reordenação de Funções:**
   - Movida `get_current_user_with_org` para o **final** do arquivo
   - Agora ela é definida após todas as outras funções

2. **Atualização das Funções `require_*`:**
   - Todas as funções `require_role`, `require_admin_role`, `require_manager_or_admin`, etc. foram atualizadas
   - Agora verificam roles através de `UserOrganizationAssociation`
   - Verificam se o usuário tem o role necessário em **pelo menos uma** organização

### Mudanças nas Funções de Autorização

#### Antes:
```python
def require_admin_role(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role."""
    if current_user.role.name not in ["ADMIN", "ADMINISTRATOR", "MANAGER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user
```

#### Depois:
```python
def require_admin_role(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role.
    
    NOTE: This function checks if user has admin role in ANY organization.
    For organization-specific role checks, verify role through UserOrganizationAssociation
    in the endpoint itself using get_organization_from_token().
    """
    from app.models.user_organization_association import UserOrganizationAssociation
    from app.models.role import Role
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        user_orgs = db.query(UserOrganizationAssociation).filter(
            UserOrganizationAssociation.user_id == current_user.id
        ).all()
        
        for assoc in user_orgs:
            role = db.query(Role).filter(Role.id == assoc.role_id).first()
            if role and role.name in ["ADMIN", "ADMINISTRATOR", "MANAGER"]:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    finally:
        db.close()
```

### Funções Atualizadas

1. ✅ `require_role()` - Verifica roles em qualquer organização
2. ✅ `require_admin_role()` - Verifica ADMIN em qualquer organização
3. ✅ `require_manager_or_admin()` - Verifica MANAGER/ADMIN em qualquer organização
4. ✅ `require_super_admin()` - Verifica ADMINISTRATOR em qualquer organização
5. ✅ `require_consultant()` - Verifica CONSULTANT em qualquer organização
6. ✅ `require_manager_or_consultant()` - Verifica MANAGER/CONSULTANT em qualquer organização
7. ✅ `require_administrator()` - Verifica ADMINISTRATOR em qualquer organização
8. ✅ `get_current_user_with_org()` - Movida para o final do arquivo

### Comportamento das Funções `require_*`

**Importante:** Estas funções agora verificam se o usuário tem o role necessário em **QUALQUER** organização. 

Para verificações **específicas por organização**, use este padrão no endpoint:

```python
@router.get("/endpoint")
async def my_endpoint(
    request: Request,
    current_user: User = Depends(require_admin_role),  # Verifica se é admin em ALGUMA org
    db: Session = Depends(get_db)
):
    # Obter organização atual da sessão
    current_user_org_id = get_organization_from_token(request)
    
    # Verificar role NESTA organização específica
    assoc = db.query(UserOrganizationAssociation).filter(
        UserOrganizationAssociation.user_id == current_user.id,
        UserOrganizationAssociation.organization_id == current_user_org_id
    ).first()
    
    if not assoc:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    
    role = db.query(Role).filter(Role.id == assoc.role_id).first()
    if not role or role.name not in ["ADMIN", "MANAGER"]:
        raise HTTPException(status_code=403, detail="Admin role required in this organization")
    
    # Código do endpoint...
```

### Por Que Essa Abordagem?

1. **Compatibilidade:** Mantém as funções `require_*` funcionando sem quebrar código existente
2. **Flexibilidade:** Usuários com roles administrativos em alguma organização podem acessar endpoints gerais
3. **Segurança:** Endpoints específicos ainda podem verificar roles por organização usando `get_organization_from_token()`
4. **Progressividade:** Permite migração gradual - endpoints críticos podem adicionar verificações específicas

### Testando o Servidor

Agora o servidor deve iniciar sem erros:

```bash
cd Backend
uvicorn app.main:app --reload
```

### Erros de Linting

✅ **0 erros** - Arquivo passou no linter com sucesso

### Próximas Ações Recomendadas

1. **Testar o servidor:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Verificar logs de inicialização:**
   - Procurar por avisos ou erros
   - Confirmar que todas as rotas foram registradas

3. **Testar endpoints básicos:**
   ```bash
   curl http://localhost:8000/docs
   ```

4. **Fazer login e testar multi-organização:**
   - Login com usuário existente
   - Verificar se o sistema detecta corretamente as organizações

### Arquivos Modificados Nesta Correção

- ✅ `Backend/app/dependencies/auth.py` - Reordenação e atualização de funções

### Status Final

✅ **CORREÇÃO COMPLETA**
- Servidor deve iniciar sem erros
- Todas as funções de autorização atualizadas
- Linting limpo
- Documentação adicionada

---

**Data:** 26 de Outubro de 2025  
**Erro Corrigido:** NameError em dependencies/auth.py  
**Status:** ✅ RESOLVIDO

