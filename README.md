# Ambiental SaaS Backend

Backend completo e escalável para uma plataforma SaaS (Software as a Service) usando Python e FastAPI.

## 🚀 Características

- **FastAPI**: Framework moderno e rápido com documentação automática
- **Multi-tenancy**: Arquitetura com isolamento completo de dados por organização
- **Autenticação JWT**: Sistema seguro com OAuth2 Password Flow
- **PostgreSQL**: Banco de dados robusto com SQLAlchemy ORM
- **Alembic**: Migrações automáticas de banco de dados
- **Pydantic**: Validação robusta de dados com type hints

## 📋 Pré-requisitos

- Python 3.11+
- PostgreSQL 12+
- pip

## 🛠️ Instalação

### 🚀 Setup Rápido (Recomendado)

1. **Clone o repositório:**
```bash
git clone <repository-url>
cd Backend
```

2. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

3. **Execute o Setup Wizard:**
```bash
python setup.py
```

4. **Acesse a interface web:** http://localhost:8001

5. **Configure o sistema através da interface web**

6. **Execute a aplicação principal:**
```bash
python main.py
```

### 🔧 Setup Manual

1. **Clone o repositório:**
```bash
git clone <repository-url>
cd Backend
```

2. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

3. **Configure as variáveis de ambiente:**
```bash
cp env.example .env
# Edite o arquivo .env com suas configurações
```

4. **Configure o banco de dados:**
```bash
# Crie o banco de dados PostgreSQL
createdb ambiental_db

# Execute as migrações
alembic upgrade head
```

5. **Execute a aplicação:**
```bash
python main.py
```

## 🌱 Setup Wizard

O Setup Wizard é uma ferramenta web intuitiva para configurar o sistema de forma rápida e segura.

### ✨ Funcionalidades

- **Interface Web**: Configuração através de navegador
- **Teste de Conexão**: Validação automática do PostgreSQL
- **Importação/Exportação**: Backup e restauração de configurações
- **Inicialização Automática**: Criação de banco e dados iniciais
- **Gerenciamento Mínimo**: `.env` apenas com o essencial

### 🚀 Como Usar

```bash
# Executar o wizard
python setup.py

# Acessar interface
# http://localhost:8001

# Após configuração, executar servidor principal
python main.py
```

### 📁 Arquivos de Configuração

- `config.example.json` - Exemplo de configuração
- `config.db` - Banco SQLite para configurações
- `.env` - Variáveis mínimas necessárias

Para mais detalhes, consulte [SETUP_WIZARD.md](SETUP_WIZARD.md).

## 🔧 Configuração

### Variáveis de Ambiente

Copie o arquivo `env.example` para `.env` e configure:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/ambiental_db

# Security
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Environment
ENVIRONMENT=development
DEBUG=True

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

## 📚 Documentação da API

Após iniciar a aplicação, acesse:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏗️ Arquitetura

### Estrutura do Projeto

```
app/
├── api/v1/           # Endpoints da API
│   ├── auth.py       # Autenticação
│   ├── organization.py # Gerenciamento de organizações
│   ├── billing.py    # Assinaturas e licenças
│   └── master.py     # Admin master
├── core/             # Configurações centrais
│   └── security.py   # JWT e segurança
├── models/           # Modelos SQLAlchemy
├── schemas/          # Schemas Pydantic
├── dependencies/     # Dependências FastAPI
├── database.py       # Configuração do banco
├── config.py         # Configurações da aplicação
└── main.py          # Aplicação principal
```

### Modelos de Dados

- **Organization**: Empresas clientes
- **User**: Usuários do sistema
- **Role**: Papéis e permissões
- **Plan**: Planos de assinatura
- **Subscription**: Assinaturas ativas
- **License**: Licenças de usuário

## 🔐 Autenticação

O sistema utiliza JWT com OAuth2 Password Flow:

1. **Login**: `POST /api/auth/token`
2. **Registro**: `POST /api/auth/register`
3. **Refresh**: `POST /api/auth/refresh`

### Fluxo de Autenticação

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB

    Client->>API: POST /api/auth/token
    API->>DB: Verify credentials
    DB-->>API: User data
    API-->>Client: Access + Refresh tokens
    
    Client->>API: Protected endpoint
    Note over Client,API: Authorization: Bearer <access_token>
    API->>API: Verify JWT
    API-->>Client: Response
```

## 🏢 Multi-tenancy

Cada organização possui isolamento completo de dados através de:

- `organization_id` em todas as tabelas de dados
- Middleware de autenticação que valida organização
- Dependências que filtram dados por organização

## 📊 Endpoints Principais

### Autenticação (`/api/auth`)
- `POST /token` - Login
- `POST /register` - Registro de nova organização
- `POST /refresh` - Renovar token
- `GET /me` - Dados do usuário atual

### Organização (`/api/organization`)
- `GET /me` - Dados da organização
- `GET /users` - Listar usuários
- `POST /users/invite` - Convidar usuário
- `DELETE /users/{id}` - Remover usuário
- `GET /roles` - Listar papéis disponíveis

### Billing (`/api/billing`)
- `GET /subscription` - Status da assinatura
- `POST /licenses/purchase` - Comprar licenças
- `GET /plans` - Planos disponíveis
- `POST /subscription/upgrade` - Upgrade de plano

### Master Admin (`/api/master`)
- `GET /organizations` - Listar organizações
- `GET /organizations/{id}` - Detalhes da organização
- `PUT /organizations/{id}/subscription` - Atualizar assinatura
- `GET /organizations/{id}/users` - Usuários da organização

## 🚀 Deploy

### Desenvolvimento
```bash
python main.py
```

### Produção
```bash
python main.py
```

### Docker (Opcional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

## 🧪 Testes

```bash
# Instalar dependências de teste
pip install pytest pytest-asyncio httpx

# Executar testes
pytest
```

## 📝 Migrações

```bash
# Criar nova migração
alembic revision --autogenerate -m "Description"

# Aplicar migrações
alembic upgrade head

# Reverter migração
alembic downgrade -1
```

## 🔒 Segurança

- Senhas hasheadas com bcrypt
- JWT com expiração configurável
- CORS configurado
- Validação de dados com Pydantic
- Isolamento de dados por organização

## 📈 Próximos Passos

- [ ] Integração com gateway de pagamento
- [ ] Sistema de notificações por email
- [ ] Logs estruturados
- [ ] Métricas e monitoramento
- [ ] Testes automatizados
- [ ] CI/CD pipeline

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.
