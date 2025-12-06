# 🛠️ Instalação e Configuração - Ambiental SaaS

Este guia descreve como configurar o ambiente de desenvolvimento e produção para o Backend do projeto Ambiental SaaS.

## 📋 Pré-requisitos

- **Python**: 3.11 ou superior
- **PostgreSQL**: 14+ (com extensão `vector`)
- **Gestor de Pacotes**: `pip`

## 🚀 Setup Rápido (Wizard)

A maneira mais fácil de configurar o projeto é utilizando o **Setup Wizard**.

1. **Clone o repositório:**
   ```bash
   git clone <repository-url>
   cd Backend
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Execute o Wizard:**
   ```bash
   python setup.py
   ```

4. **Acesse a interface de configuração:**
   Abra `http://localhost:8001` no seu navegador e siga as instruções para conectar ao banco de dados e gerar as configurações iniciais.

5. **Inicie o servidor:**
   ```bash
   python main.py
   ```

## 🔧 Setup Manual

Se preferir configurar manualmente sem o Wizard:

1. **Variáveis de Ambiente:**
   Copie o exemplo e configure o `.env`:
   ```bash
   cp env.example .env
   ```

   Edite o `.env` com suas credenciais:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/ambiental_db
   SECRET_KEY=sua_chave_secreta
   FILE_ENCRYPTION_KEY=chave_gerada_base64
   N8N_SIGNING_SECRET=segredo_compartilhado_hmac
   ```

2. **Banco de Dados:**
   ```bash
   # Crie o banco
   createdb ambiental_db

   # Execute as migrações
   alembic upgrade head
   ```

3. **Gerar Chaves de Segurança:**
   É crítico gerar chaves seguras para criptografia:

   ```bash
   # Chave de Arquivos
   python -c "from app.core.encryption import EncryptionUtils; print(EncryptionUtils.generate_key())"

   # Chave HMAC para N8N (adicione ao .env como N8N_SIGNING_SECRET)
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Executar:**
   ```bash
   python main.py
   ```

## 🌱 Multi-Organização (SaaS vs On-Prem)

O sistema suporta múltiplos modos de operação configuráveis via `DEPLOYMENT_MODE` no `.env`:

*   **`saas`**: Modo padrão. Múltiplos clientes (organizações) no mesmo banco de dados, isolados logicamente.
*   **`onprem`**: Modo para instalação em servidor do cliente. Uma organização principal.

Consulte [AUTH.md](AUTH.md) e [DEPLOYMENT.md](DEPLOYMENT.md) para detalhes específicos sobre configuração de organizações e chaves de ativação.
