# Teste de APIs - Sistema Ambiental

Interface web moderna e interativa para testar todas as APIs do backend do Sistema Ambiental.

## Como usar

1. **Inicie o backend** do Sistema Ambiental
2. **Abra o arquivo `index.html`** no seu navegador
3. **Faça login** usando um dos botões de login rápido:
   - **Super Admin**: `admin@ambiental.com` / `admin123`
   - **Usuário Teste**: `joao.teste@exemplo.com` / `senha123`
4. **Teste as APIs** - seu token será salvo automaticamente!

## Funcionalidades Novas

### 🔐 Autenticação Automática
- Token salvo automaticamente no localStorage
- Sessão restaurada ao reabrir a página
- Login rápido com botões pré-configurados
- Logout com confirmação

### 🎨 Interface Melhorada
- Design moderno com gradientes
- Notificações toast para feedback visual
- Status de conexão em tempo real
- Animações suaves

### 💾 Persistência
- Tokens salvos localmente
- Restauração automática de sessão
- Botão "Limpar Tudo" para reset completo

## Funcionalidades

### 🔐 Autenticação
- **Login**: Fazer login com email e senha
- **Registro**: Criar nova organização e usuário admin
- **Refresh Token**: Renovar token de acesso
- **Me**: Obter informações do usuário logado

### 🏢 Organização
- **Informações da Organização**: Obter dados da organização atual
- **Listar Usuários**: Ver todos os usuários da organização
- **Listar Roles**: Ver roles disponíveis
- **Convidar Usuário**: Adicionar novo usuário à organização
- **Remover Usuário**: Remover usuário da organização
- **Ativar Usuário**: Reativar usuário desativado

### 💳 Billing
- **Status da Assinatura**: Ver informações da assinatura atual
- **Comprar Licenças**: Adicionar mais licenças
- **Listar Planos**: Ver planos disponíveis
- **Upgrade**: Fazer upgrade do plano

### 👑 Master (Super Admin)
- **Listar Organizações**: Ver todas as organizações
- **Detalhes da Organização**: Informações específicas de uma organização
- **Assinatura da Organização**: Ver assinatura de uma organização específica
- **Atualizar Assinatura**: Modificar assinatura de uma organização
- **Usuários da Organização**: Listar usuários de uma organização
- **Ativar/Desativar Organização**: Controlar status da organização

## Estrutura dos Arquivos

```
teste_html/
├── index.html          # Interface principal
├── api-tester.js       # Lógica JavaScript para testes
└── README.md          # Este arquivo
```

## APIs Testadas

### Autenticação (`/auth`)
- `POST /token` - Login
- `POST /register` - Registro
- `POST /refresh` - Refresh token
- `GET /me` - Informações do usuário

### Organização (`/organization`)
- `GET /me` - Informações da organização
- `GET /users` - Listar usuários
- `GET /roles` - Listar roles
- `POST /users/invite` - Convidar usuário
- `DELETE /users/{user_id}` - Remover usuário
- `PUT /users/{user_id}/activate` - Ativar usuário

### Billing (`/billing`)
- `GET /subscription` - Status da assinatura
- `POST /licenses/purchase` - Comprar licenças
- `GET /plans` - Listar planos
- `POST /subscription/upgrade` - Upgrade do plano

### Master (`/master`)
- `GET /organizations` - Listar organizações
- `GET /organizations/{org_id}` - Detalhes da organização
- `GET /organizations/{org_id}/subscription` - Assinatura da organização
- `PUT /organizations/{org_id}/subscription` - Atualizar assinatura
- `GET /organizations/{org_id}/users` - Usuários da organização
- `PUT /organizations/{org_id}/activate` - Ativar organização
- `PUT /organizations/{org_id}/deactivate` - Desativar organização

## Tecnologias Utilizadas

- **HTML5**: Estrutura da página
- **Tailwind CSS**: Estilização responsiva
- **JavaScript**: Lógica de interação e requisições
- **Fetch API**: Comunicação com o backend

## Requisitos

- Navegador web moderno (Chrome, Firefox, Safari, Edge)
- Backend do Sistema Ambiental rodando
- Conexão com a internet (para carregar Tailwind CSS)

## Observações

- O token de acesso é automaticamente salvo após login/registro
- Todas as requisições autenticadas usam o token salvo
- Os resultados são exibidos em formato JSON formatado
- A interface é responsiva e funciona em dispositivos móveis
