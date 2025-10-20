# 🚀 Quick Start - Ambiental SaaS

Guia rápido para começar a usar o sistema.

## ⚡ Início Rápido

### 1. Instalação
```bash
pip install -r requirements.txt
```

### 2. Configuração
```bash
python setup.py
# Acesse http://localhost:8001
```

### 3. Acesse a Interface
- **Setup Wizard**: http://localhost:8001
- **API Principal**: http://localhost:8000
- **Documentação**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:8000/admin

## 🔧 Comandos Úteis

### Setup Wizard
```bash
python setup.py
```

### Servidor Principal
```bash
python main.py
```

## 📁 Arquivos Importantes

- `setup.py` - Setup Wizard completo
- `main.py` - Servidor principal
- `config.example.json` - Exemplo de configuração
- `SETUP_WIZARD.md` - Documentação completa

## 🆘 Problemas Comuns

### Dependências
```bash
pip install --upgrade -r requirements.txt
```

### Porta em Uso
- Setup Wizard: 8001
- Servidor Principal: 8000
- Pare outros serviços ou modifique as portas

### Banco de Dados
- Verifique se PostgreSQL está rodando
- Teste a conexão no Setup Wizard
- Confirme as credenciais

## 🎯 Próximos Passos

1. Configure via Setup Wizard
2. Teste a API em /docs
3. Faça login com admin@ambiental.com / Admin@123
4. Configure sua organização
5. Desenvolva suas funcionalidades

## 📞 Suporte

- Verifique os logs do console
- Teste as conexões manualmente
- Consulte a documentação completa
