/**
 * N8N Callback Example
 * 
 * Este arquivo mostra como o N8N deve fazer callbacks para o backend
 * após processar mensagens com IA.
 */

const crypto = require('crypto');

// ============================================
// CONFIGURAÇÃO (obter do ambiente/N8N)
// ============================================

const BACKEND_URL = 'https://your-backend-domain.com';
const N8N_SIGNING_SECRET = process.env.N8N_SIGNING_SECRET || 'your-shared-secret';

// ============================================
// FUNÇÃO PARA GERAR ASSINATURA HMAC
// ============================================

function generateHMACSignature(payload, timestamp) {
  const message = `${timestamp}.${payload}`;
  const signature = crypto
    .createHmac('sha256', N8N_SIGNING_SECRET)
    .update(message)
    .digest('hex');
  
  return signature;
}

// ============================================
// EXEMPLO 1: CALLBACK SIMPLES COM RESPOSTA
// ============================================

async function sendSimpleCallback(threadId, assistantMessage) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  
  const payload = {
    assistant_message: assistantMessage,
    metadata: {
      processing_time: 2.5,
      model: 'gpt-4'
    }
  };
  
  const payloadString = JSON.stringify(payload);
  const signature = generateHMACSignature(payloadString, timestamp);
  
  const response = await fetch(
    `${BACKEND_URL}/api/chat/threads/${threadId}/messages/callback`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Timestamp': timestamp,
        'X-Signature': signature
      },
      body: payloadString
    }
  );
  
  const result = await response.json();
  console.log('Callback sent successfully:', result);
  
  return result;
}

// ============================================
// EXEMPLO 2: CALLBACK COM EVENTOS DE TIMELINE
// ============================================

async function sendCallbackWithTimeline(threadId, assistantMessage, timelineEvents) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  
  const payload = {
    assistant_message: assistantMessage,
    timeline_events: timelineEvents,
    metadata: {
      processing_time: 5.2,
      model: 'gpt-4',
      chunks_processed: 15,
      tokens_used: 2340
    }
  };
  
  const payloadString = JSON.stringify(payload);
  const signature = generateHMACSignature(payloadString, timestamp);
  
  const response = await fetch(
    `${BACKEND_URL}/api/chat/threads/${threadId}/messages/callback`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Timestamp': timestamp,
        'X-Signature': signature
      },
      body: payloadString
    }
  );
  
  const result = await response.json();
  console.log('Callback with timeline sent successfully:', result);
  
  return result;
}

// ============================================
// EXEMPLO 3: CRIAR EVENTO DE TIMELINE
// ============================================

async function createTimelineEvent(threadId, eventData) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  
  const payload = {
    type: eventData.type,           // 'stage', 'system', 'file', 'decision', 'ai_processing', 'error'
    status: eventData.status,       // 'pending', 'in_progress', 'completed', 'error', 'cancelled'
    title: eventData.title,
    description: eventData.description,
    order_index: eventData.order_index || 0,
    metadata: eventData.metadata || {}
  };
  
  const payloadString = JSON.stringify(payload);
  const signature = generateHMACSignature(payloadString, timestamp);
  
  const response = await fetch(
    `${BACKEND_URL}/api/chat/threads/${threadId}/timeline`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Timestamp': timestamp,
        'X-Signature': signature
      },
      body: payloadString
    }
  );
  
  const result = await response.json();
  console.log('Timeline event created:', result);
  
  return result;
}

// ============================================
// EXEMPLO 4: ATUALIZAR EVENTO DE TIMELINE
// ============================================

async function updateTimelineEvent(threadId, eventId, updates) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  
  const payload = {
    status: updates.status,           // Opcional
    title: updates.title,             // Opcional
    description: updates.description, // Opcional
    order_index: updates.order_index, // Opcional
    metadata: updates.metadata        // Opcional
  };
  
  const payloadString = JSON.stringify(payload);
  const signature = generateHMACSignature(payloadString, timestamp);
  
  const response = await fetch(
    `${BACKEND_URL}/api/chat/threads/${threadId}/timeline/${eventId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-Timestamp': timestamp,
        'X-Signature': signature
      },
      body: payloadString
    }
  );
  
  const result = await response.json();
  console.log('Timeline event updated:', result);
  
  return result;
}

// ============================================
// EXEMPLO 5: BAIXAR ARQUIVO DO BACKEND
// ============================================

async function downloadFileFromBackend(threadId, fileId) {
  const N8N_JWT_TOKEN = process.env.N8N_JWT_TOKEN || 'your-jwt-token';
  
  const response = await fetch(
    `${BACKEND_URL}/api/chat/threads/${threadId}/files/${fileId}/content`,
    {
      method: 'GET',
      headers: {
        'X-Internal-N8N-Token': N8N_JWT_TOKEN
      }
    }
  );
  
  if (!response.ok) {
    throw new Error(`Failed to download file: ${response.statusText}`);
  }
  
  const fileBuffer = await response.arrayBuffer();
  const filename = response.headers.get('content-disposition')?.split('filename=')[1]?.replace(/"/g, '');
  
  console.log(`File downloaded: ${filename}, size: ${fileBuffer.byteLength} bytes`);
  
  return {
    buffer: fileBuffer,
    filename: filename,
    contentType: response.headers.get('content-type')
  };
}

// ============================================
// WORKFLOW COMPLETO DE EXEMPLO
// ============================================

async function completeWorkflowExample(inputData) {
  const { thread_id, message, files } = inputData;
  
  try {
    // 1. Criar evento de timeline inicial
    await createTimelineEvent(thread_id, {
      type: 'ai_processing',
      status: 'in_progress',
      title: 'Processando documentos',
      description: 'Baixando e analisando arquivos anexados...',
      order_index: 1
    });
    
    // 2. Baixar e processar arquivos (se houver)
    if (files && files.length > 0) {
      for (const file of files) {
        console.log(`Downloading file: ${file.filename}`);
        const fileData = await downloadFileFromBackend(thread_id, file.id);
        
        // Aqui você processaria o arquivo com IA
        // Por exemplo: vetorização, OCR, análise, etc.
        console.log(`Processing file: ${fileData.filename}`);
      }
      
      // Atualizar timeline
      await createTimelineEvent(thread_id, {
        type: 'stage',
        status: 'completed',
        title: 'Documentos processados',
        description: `${files.length} arquivo(s) analisado(s) e vetorizado(s)`,
        order_index: 2,
        metadata: {
          files_count: files.length,
          chunks_created: 45
        }
      });
    }
    
    // 3. Processar mensagem com IA
    console.log('Processing message with AI...');
    
    // Aqui você chamaria sua IA (OpenAI, LangChain, etc.)
    // Exemplo fictício:
    const aiResponse = `Entendi sua solicitação: "${message}". 
    Analisei os documentos anexados e aqui está o resumo: [conteúdo gerado pela IA]`;
    
    // 4. Criar evento de conclusão na timeline
    const timelineEvents = [
      {
        type: 'stage',
        status: 'completed',
        title: 'Análise concluída',
        description: 'IA processou a mensagem e gerou resposta',
        order_index: 3,
        metadata: {
          tokens_used: 1523,
          confidence: 0.95
        }
      }
    ];
    
    // 5. Enviar callback com resposta e timeline
    await sendCallbackWithTimeline(thread_id, aiResponse, timelineEvents);
    
    console.log('Workflow completed successfully!');
    
  } catch (error) {
    console.error('Error in workflow:', error);
    
    // Criar evento de erro na timeline
    await createTimelineEvent(thread_id, {
      type: 'error',
      status: 'error',
      title: 'Erro no processamento',
      description: `Erro ao processar mensagem: ${error.message}`,
      order_index: 99,
      metadata: {
        error: error.message,
        stack: error.stack
      }
    });
    
    throw error;
  }
}

// ============================================
// EXEMPLO DE USO NO N8N
// ============================================

/*
 * No N8N, você pode usar este código em um nó "Function" ou "Code":
 * 
 * 1. Receber webhook do backend com os dados
 * 2. Processar com IA
 * 3. Chamar as funções acima para:
 *    - Baixar arquivos se necessário
 *    - Criar/atualizar eventos de timeline
 *    - Enviar resposta final via callback
 * 
 * Exemplo de estrutura de workflow N8N:
 * 
 * [Webhook Trigger] 
 *       ↓
 * [Extract Data] 
 *       ↓
 * [Download Files if needed] (usar downloadFileFromBackend)
 *       ↓
 * [Process with AI] (OpenAI, LangChain, etc.)
 *       ↓
 * [Create Timeline Events] (usar createTimelineEvent)
 *       ↓
 * [Send Callback] (usar sendCallbackWithTimeline)
 */

// ============================================
// EXPORTS (para usar no N8N)
// ============================================

module.exports = {
  generateHMACSignature,
  sendSimpleCallback,
  sendCallbackWithTimeline,
  createTimelineEvent,
  updateTimelineEvent,
  downloadFileFromBackend,
  completeWorkflowExample
};

