Guia de Integração N8N - NormaHub
Visão Geral
Este guia mostra como integrar N8N com o NormaHub para adicionar itens ao checklist de processos automaticamente.

Autenticação: API Keys
O N8N usa API Keys para autenticação (mais simples que JWT).

1. Gerar API Key (Admin)
Endpoint: POST http://localhost:8000/api/api-keys

Headers:

Authorization: Bearer {seu_jwt_token}
Content-Type: application/json
Body:

{
  "name": "N8N Integration",
  "expires_in_days": 365
}
Response:

{
  "id": 1,
  "name": "N8N Integration",
  "key": "nak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "organization_id": 1,
  "is_active": true,
  "expires_at": "2027-01-15T22:00:00",
  "created_at": "2026-01-15T22:00:00"
}
⚠️ IMPORTANTE: A key só aparece durante a criação! Guarde em local seguro.

2. Listar Keys Existentes
Endpoint: GET http://localhost:8000/api/api-keys

3. Revogar Key
Endpoint: DELETE http://localhost:8000/api/api-keys/{key_id}

Checklist Automático
Quando um processo é criado, 5 itens padrão são automaticamente adicionados:

Verificar documentação básica
Analisar localização do processo
Conferir licenças anteriores
Validar dados técnicos
Aprovar processo
O N8N pode adicionar mais itens depois da criação.

APIs Disponíveis para N8N
Listar Checklist
Endpoint: GET /api/checklist/process/{process_id}/checklist

Headers:

X-API-Key: nak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Response:

[
  {
    "id": 1,
    "process_id": 4,
    "title": "Verificar documentação básica",
    "is_completed": false,
    "order": 0,
    "created_at": "2026-01-15T22:00:00"
  }
]
Adicionar Item ao Checklist
Endpoint: POST /api/checklist/process/{process_id}/checklist

Headers:

X-API-Key: nak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
Body:

{
  "title": "Verificar licença ambiental anterior",
  "parent_id": null
}
Response:

{
  "id": 6,
  "process_id": 4,
  "title": "Verificar licença ambiental anterior",
  "is_completed": false,
  "order": 5,
  "created_at": "2026-01-15T22:30:00"
}
Atualizar Item
Endpoint: PATCH /api/checklist/checklist/{item_id}

Headers:

X-API-Key: nak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
Body:

{
  "title": "Novo título",
  "is_completed": true
}
Workflow N8N Exemplo
Cenário: Adicionar Tarefas Automaticamente
[Trigger Webhook] → [Loop Tarefas] → [HTTP Request: Add Checklist Item]
Configuração Passo a Passo
1. Webhook Trigger
Configurar webhook para receber notificação quando processo é criado.

Input Example:

{
  "process_id": 4,
  "process_title": "Licença Ambiental - Empresa XYZ",
  "tasks": [
    "Verificar documentos técnicos",
    "Conferir plantas e desenhos",
    "Validar assinaturas"
  ]
}
2. Loop Node
Iterar sobre array tasks.

3. HTTP Request Node
Method: POST

URL: http://localhost:8000/api/checklist/process/{{$json["process_id"]}}/checklist

Headers:

Nome: X-API-Key
Valor: nak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx (sua API Key)
Nome: Content-Type
Valor: application/json
Body (JSON):

{
  "title": "{{$json["task"]}}"
}
Response Code: 200 = Sucesso

JSON Completo do Workflow N8N
{
  "name": "Add Checklist Items",
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "parameters": {
        "path": "process-created",
        "responseMode": "lastNode"
      }
    },
    {
      "name": "Loop Over Tasks",
      "type": "n8n-nodes-base.splitInBatches",
      "position": [450, 300],
      "parameters": {
        "batchSize": 1
      }
    },
    {
      "name": "Add Checklist Item",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300],
      "parameters": {
        "url": "=http://localhost:8000/api/checklist/process/{{$json[\"process_id\"]}}/checklist",
        "method": "POST",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "X-API-Key",
              "value": "nak_SUA_API_KEY_AQUI"
            },
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "title",
              "value": "={{$json[\"task\"]}}"
            }
          ]
        }
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Loop Over Tasks"}]]
    },
    "Loop Over Tasks": {
      "main": [[{"node": "Add Checklist Item"}]]
    }
  }
}
Testando a Integração
1. Obter API Key
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@local","password":"123"}'
# Criar API Key (com token do login)
curl -X POST http://localhost:8000/api/api-keys \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test N8N","expires_in_days":365}'
2. Testar Adição de Item
curl -X POST http://localhost:8000/api/checklist/process/4/checklist \
  -H "X-API-Key: nak_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"title":"Teste N8N Integration"}'
3. Verificar Resultado
curl -X GET http://localhost:8000/api/checklist/process/4/checklist \
  -H "X-API-Key: nak_xxxxx"
Segurança
✅ API Keys são hash stored (SHA256) - impossível recuperar ✅ Validação de organização - key só acessa dados da própria org ✅ Expiração configurável - keys podem ter prazo ✅ Revogação instantânea - admin pode desativar key a qualquer momento ✅ Audit log - todas as ações são registradas

Troubleshooting
401 Unauthorized: API Key inválida ou expirada 403 Forbidden: Tentando acessar processo de outra organização 404 Not Found: Process ID não existe

