# 🌱 Ambiental SaaS - Setup Wizard

O Setup Wizard é uma ferramenta web para configurar o sistema Ambiental SaaS de forma rápida e intuitiva.

## 🚀 Como Usar

### 1. Instalação das Dependências
```bash
pip install -r requirements.txt
```

### 2. Executar o Setup Wizard
```bash
python setup.py
```

### 3. Acessar a Interface Web
Abra seu navegador e acesse: http://localhost:8001

 Safety: O wizard roda apenas na porta 8001 e é destinado apenas para desenvolvedores.

## 📋 Funcionalidades

### ✅ Configuração do Banco de Dados
- Teste de conexão com PostgreSQL
- Validação de credenciais
- Configuração automática do `.env`

### ✅ Configuração do Sistema
- Geração de chave secreta
- Configuração de tokens JWT
- Definição de ambiente (dev/staging/prod)
- Configuração de CORS

### ✅ Importação/Exportação de Configurações
- Exportar configurações para JSON
- Importar configurações de arquivo JSON
- Útil para migrações e backups

### ✅ Inicialização Automática
- Criação de tabelas do banco
- Inserção de dados iniciais (roles, plans, super admin)
- Geração de usuário administrador padrão

## 🔧 Estrutura de Configuração

### Banco de Dados
```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "database": "ambiental_db",
    "username": "postgres",
    "password": "sua_senha"
  }
}
```

### Sistema
```json
{
  "system": {
    "secret_key": "sua-chave-secreta-super-segura",
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 7,
    "environment": "development",
    "debug": true
  }
}
```

## 📁 Arquivos Gerados

### `.env` (Mínimo)
```env
DATABASE_URL=postgresql://user:pass@host:port/db
SECRET_KEY=change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
DEBUG=True
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

### `config.db` (SQLite)
- Armazena todas as configurações do sistema
- Usado para backup e restauração
- Não é commitado no git

## 🔒 Segurança

- O wizard é destinado apenas para desenvolvedores
- Configurações sensíveis são armazenadas no banco SQLite local
- O `.env` contém apenas o mínimo necessário
- Chaves secretas são geradas automaticamente

## 🚨 Troubleshooting

### Erro de Conexão com Banco
- Verifique se o PostgreSQL está rodando
- Confirme as credenciais
- Teste a conexão manualmente

### Erro de Dependências
```bash
pip install --upgrade -r requirements.txt
```

### Porta 8001 em Uso
- Pare outros serviços na porta 8001
- Ou modifique a porta no script

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique os logs do console
2. Teste a conexão com o banco manualmente
3. Verifique as permissões de arquivo

## 🎯 Próximos Passos

Após o setup:
1. Execute `python main.py` para iniciar o servidor principal
2. Acesse `http://localhost:8000/docs` para a documentação da API
3. Acesse `http://localhost:8000/admin` para o painel administrativo
4. Faça login com: `admin@ambiental.com` / `admin123`
5. Configure sua organização e usuários
