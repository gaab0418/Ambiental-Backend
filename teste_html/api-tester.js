// Configurações globais
let accessToken = localStorage.getItem('accessToken') || '';
let refreshToken = localStorage.getItem('refreshToken') || '';
let currentUser = null;

// Funções de utilidade
function getApiBaseUrl() {
    return document.getElementById('apiBaseUrl').value;
}

function getAccessToken() {
    return accessToken;
}

function saveTokens(access, refresh) {
    accessToken = access;
    refreshToken = refresh;
    localStorage.setItem('accessToken', access);
    localStorage.setItem('refreshToken', refresh);
    updateConnectionStatus('Autenticado', true);
}

function clearTokens() {
    accessToken = '';
    refreshToken = '';
    currentUser = null;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    updateConnectionStatus('Não conectado', false);
    updateAuthStatus(null);
}

function updateConnectionStatus(message, isConnected) {
    const statusDiv = document.getElementById('connectionStatus');
    if (isConnected) {
        statusDiv.className = 'px-3 py-2 bg-green-100 text-green-800 rounded-md text-sm font-medium';
        statusDiv.innerHTML = `✓ ${message}`;
    } else {
        statusDiv.className = 'px-3 py-2 bg-gray-100 text-gray-600 rounded-md text-sm';
        statusDiv.textContent = message;
    }
}

function showResult(data, isError = false) {
    const resultsDiv = document.getElementById('results');
    const resultContent = document.getElementById('resultContent');
    
    resultsDiv.classList.remove('hidden');
    
    if (isError) {
        resultContent.textContent = `❌ Erro: ${data}`;
        resultContent.className = 'text-sm text-red-600 whitespace-pre-wrap font-mono';
    } else {
        resultContent.textContent = JSON.stringify(data, null, 2);
        resultContent.className = 'text-sm text-gray-700 whitespace-pre-wrap font-mono';
    }
    
    // Scroll para o resultado
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500';
    
    notification.className = `fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function updateAuthStatus(userData) {
    const authStatus = document.getElementById('authStatus');
    const authInfo = document.getElementById('authInfo');
    
    if (userData) {
        currentUser = userData;
        authStatus.classList.remove('hidden');
        authInfo.innerHTML = `
            <div class="bg-gradient-to-r from-primary to-secondary text-white rounded-lg p-4 mb-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <div class="text-xs opacity-80 mb-1">Usuário</div>
                        <div class="font-semibold">${userData.full_name}</div>
                        <div class="text-sm opacity-90">${userData.email}</div>
                    </div>
                    <div>
                        <div class="text-xs opacity-80 mb-1">Permissões</div>
                        <div class="font-semibold">${userData.role?.display_name || userData.role?.name || 'N/A'}</div>
                        <div class="text-sm opacity-90">${userData.organization?.name || 'N/A'}</div>
                    </div>
                </div>
            </div>
        `;
    } else {
        authStatus.classList.add('hidden');
        currentUser = null;
    }
}

function logout() {
    if (confirm('Deseja realmente sair?')) {
        clearTokens();
        showNotification('Sessão encerrada', 'info');
    }
}

function clearAll() {
    if (confirm('Isso irá limpar todos os tokens e dados salvos. Continuar?')) {
        clearTokens();
        document.getElementById('results').classList.add('hidden');
        showNotification('Dados limpos com sucesso', 'success');
    }
}

// Função para fazer requisições HTTP
async function makeRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(`${response.status}: ${data.detail || data.message || 'Erro desconhecido'}`);
        }
        
        return data;
    } catch (error) {
        throw error;
    }
}

// Função para fazer requisições autenticadas
async function makeAuthenticatedRequest(url, options = {}) {
    const token = getAccessToken();
    if (!token) {
        throw new Error('Token de acesso não encontrado. Faça login primeiro.');
    }
    
    return makeRequest(url, {
        ...options,
        headers: {
            'Authorization': `Bearer ${token}`,
            ...options.headers
        }
    });
}

// Controle de abas
function showTab(tabName) {
    // Esconder todas as abas
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.add('hidden');
    });
    
    // Remover estilo ativo de todos os botões
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('border-primary', 'text-primary');
        button.classList.add('border-transparent', 'text-gray-500');
    });
    
    // Mostrar aba selecionada
    document.getElementById(`content-${tabName}`).classList.remove('hidden');
    
    // Ativar botão selecionado
    const activeButton = document.getElementById(`tab-${tabName}`);
    activeButton.classList.remove('border-transparent', 'text-gray-500');
    activeButton.classList.add('border-primary', 'text-primary');
}

// ==================== TESTES DE AUTENTICAÇÃO ====================

function quickLogin(type) {
    if (type === 'admin') {
        document.getElementById('loginEmail').value = 'admin@ambiental.com';
        document.getElementById('loginPassword').value = 'admin123';
    } else if (type === 'user') {
        document.getElementById('loginEmail').value = 'joao.teste@exemplo.com';
        document.getElementById('loginPassword').value = 'senha123';
    }
    testLogin();
}

async function testLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    if (!email || !password) {
        showNotification('Email e senha são obrigatórios', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        
        const response = await fetch(`${getApiBaseUrl()}/auth/token`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(`${response.status}: ${data.detail || 'Erro no login'}`);
        }
        
        // Salvar tokens automaticamente
        saveTokens(data.access_token, data.refresh_token);
        
        // Obter informações do usuário automaticamente
        await testGetMe();
        
        showNotification('Login realizado com sucesso!', 'success');
        showResult(data);
    } catch (error) {
        showNotification('Erro no login', 'error');
        showResult(error.message, true);
    }
}

async function testRegister() {
    const fullName = document.getElementById('registerFullName').value;
    const email = document.getElementById('registerEmail').value;
    const orgName = document.getElementById('registerOrgName').value;
    const cnpjCpf = document.getElementById('registerCnpjCpf').value;
    const password = document.getElementById('registerPassword').value;
    
    if (!fullName || !email || !orgName || !cnpjCpf || !password) {
        showNotification('Todos os campos são obrigatórios', 'error');
        return;
    }
    
    try {
        const data = await makeRequest(`${getApiBaseUrl()}/auth/register`, {
            method: 'POST',
            body: JSON.stringify({
                full_name: fullName,
                email: email,
                organization_name: orgName,
                cnpj_cpf: cnpjCpf,
                password: password
            })
        });
        
        // Salvar tokens automaticamente
        saveTokens(data.access_token, data.refresh_token);
        
        // Obter informações do usuário automaticamente
        await testGetMe();
        
        showNotification('Registro realizado com sucesso!', 'success');
        showResult(data);
    } catch (error) {
        showNotification('Erro no registro', 'error');
        showResult(error.message, true);
    }
}

async function testRefreshToken() {
    const refreshTokenValue = document.getElementById('refreshToken').value || refreshToken;
    
    if (!refreshTokenValue) {
        showResult('Refresh token é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeRequest(`${getApiBaseUrl()}/auth/refresh`, {
            method: 'POST',
            body: JSON.stringify({
                refresh_token: refreshTokenValue
            })
        });
        
        // Atualizar tokens
        accessToken = data.access_token;
        refreshToken = data.refresh_token;
        
        // Atualizar campo de token
        document.getElementById('accessToken').value = accessToken;
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testGetMe() {
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/auth/me`);
        
        // Atualizar status de autenticação
        updateAuthStatus(data);
        
        showResult(data);
        return data;
    } catch (error) {
        showResult(error.message, true);
        throw error;
    }
}

// ==================== TESTES DE ORGANIZAÇÃO ====================

async function testGetOrganization() {
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/organization/me`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testGetUsers() {
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/organization/users`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testGetRoles() {
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/organization/roles`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testInviteUser() {
    const fullName = document.getElementById('inviteFullName').value;
    const email = document.getElementById('inviteEmail').value;
    const roleId = parseInt(document.getElementById('inviteRoleId').value);
    
    if (!fullName || !email || !roleId) {
        showResult('Todos os campos são obrigatórios', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/organization/users/invite`, {
            method: 'POST',
            body: JSON.stringify({
                full_name: fullName,
                email: email,
                role_id: roleId
            })
        });
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testRemoveUser() {
    const userId = parseInt(document.getElementById('removeUserId').value);
    
    if (!userId) {
        showResult('User ID é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/organization/users/${userId}`, {
            method: 'DELETE'
        });
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testActivateUser() {
    const userId = parseInt(document.getElementById('activateUserId').value);
    
    if (!userId) {
        showResult('User ID é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/organization/users/${userId}/activate`, {
            method: 'PUT'
        });
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

// ==================== TESTES DE BILLING ====================

async function testGetSubscription() {
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/billing/subscription`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testPurchaseLicenses() {
    const quantity = parseInt(document.getElementById('purchaseQuantity').value);
    
    if (!quantity || quantity <= 0) {
        showResult('Quantidade deve ser maior que 0', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/billing/licenses/purchase`, {
            method: 'POST',
            body: JSON.stringify({
                quantity: quantity
            })
        });
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testGetPlans() {
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/billing/plans`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testUpgradeSubscription() {
    const planId = parseInt(document.getElementById('upgradePlanId').value);
    
    if (!planId) {
        showResult('Plan ID é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/billing/subscription/upgrade?plan_id=${planId}`, {
            method: 'POST'
        });
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

// ==================== TESTES MASTER ====================

async function testGetOrganizations() {
    const skip = parseInt(document.getElementById('orgSkip').value) || 0;
    const limit = parseInt(document.getElementById('orgLimit').value) || 100;
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/organizations?skip=${skip}&limit=${limit}`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testGetOrganizationDetails() {
    const orgId = parseInt(document.getElementById('orgDetailId').value);
    
    if (!orgId) {
        showResult('Organization ID é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/organizations/${orgId}`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testGetOrganizationSubscription() {
    const orgId = parseInt(document.getElementById('orgSubId').value);
    
    if (!orgId) {
        showResult('Organization ID é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/organizations/${orgId}/subscription`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testUpdateSubscription() {
    const orgId = parseInt(document.getElementById('updateSubOrgId').value);
    const planId = parseInt(document.getElementById('updateSubPlanId').value);
    const status = document.getElementById('updateSubStatus').value;
    
    if (!orgId || !planId || !status) {
        showResult('Todos os campos são obrigatórios', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/organizations/${orgId}/subscription`, {
            method: 'PUT',
            body: JSON.stringify({
                plan_id: planId,
                status: status
            })
        });
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testGetOrganizationUsers() {
    const orgId = parseInt(document.getElementById('orgUsersId').value);
    
    if (!orgId) {
        showResult('Organization ID é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/organizations/${orgId}/users`);
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testActivateOrganization() {
    const orgId = parseInt(document.getElementById('orgControlId').value);
    
    if (!orgId) {
        showResult('Organization ID é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/organizations/${orgId}/activate`, {
            method: 'PUT'
        });
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

async function testDeactivateOrganization() {
    const orgId = parseInt(document.getElementById('orgControlId').value);
    
    if (!orgId) {
        showResult('Organization ID é obrigatório', true);
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/organizations/${orgId}/deactivate`, {
            method: 'PUT'
        });
        
        showResult(data);
    } catch (error) {
        showResult(error.message, true);
    }
}

// ==================== NOVOS TESTES MASTER ====================

async function testCreateOrganization() {
    const name = document.getElementById('createOrgName').value;
    const cnpj_cpf = document.getElementById('createOrgCnpj').value;
    const email = document.getElementById('createOrgEmail').value;
    const phone = document.getElementById('createOrgPhone').value;
    
    if (!name || !cnpj_cpf || !email) {
        showNotification('Nome, CNPJ/CPF e Email são obrigatórios', 'error');
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/organizations`, {
            method: 'POST',
            body: JSON.stringify({ name, cnpj_cpf, email, phone })
        });
        
        showNotification('Organização criada com sucesso!', 'success');
        showResult(data);
    } catch (error) {
        showNotification('Erro ao criar organização', 'error');
        showResult(error.message, true);
    }
}

async function testCreateUser() {
    const full_name = document.getElementById('createUserFullName').value;
    const email = document.getElementById('createUserEmail').value;
    const password = document.getElementById('createUserPassword').value;
    const organization_id = parseInt(document.getElementById('createUserOrgId').value);
    const role_id = parseInt(document.getElementById('createUserRoleId').value);
    
    if (!full_name || !email || !password || !organization_id || !role_id) {
        showNotification('Todos os campos são obrigatórios', 'error');
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/users`, {
            method: 'POST',
            body: JSON.stringify({ full_name, email, password, organization_id, role_id })
        });
        
        showNotification('Usuário criado com sucesso!', 'success');
        showResult(data);
    } catch (error) {
        showNotification('Erro ao criar usuário', 'error');
        showResult(error.message, true);
    }
}

async function testMasterActivateUser() {
    const userId = parseInt(document.getElementById('manageUserId').value);
    
    if (!userId) {
        showNotification('User ID é obrigatório', 'error');
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/users/${userId}/activate`, {
            method: 'PUT'
        });
        
        showNotification('Usuário ativado!', 'success');
        showResult(data);
    } catch (error) {
        showNotification('Erro ao ativar usuário', 'error');
        showResult(error.message, true);
    }
}

async function testMasterDeactivateUser() {
    const userId = parseInt(document.getElementById('manageUserId').value);
    
    if (!userId) {
        showNotification('User ID é obrigatório', 'error');
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/users/${userId}/deactivate`, {
            method: 'PUT'
        });
        
        showNotification('Usuário desativado!', 'success');
        showResult(data);
    } catch (error) {
        showNotification('Erro ao desativar usuário', 'error');
        showResult(error.message, true);
    }
}

async function testGetUserDetails() {
    const userId = parseInt(document.getElementById('manageUserId').value);
    
    if (!userId) {
        showNotification('User ID é obrigatório', 'error');
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(`${getApiBaseUrl()}/master/users/${userId}`);
        showResult(data);
    } catch (error) {
        showNotification('Erro ao buscar usuário', 'error');
        showResult(error.message, true);
    }
}

async function testChangeUserOrganization() {
    const userId = parseInt(document.getElementById('manageUserId').value);
    const newOrgId = parseInt(document.getElementById('changeUserOrgId').value);
    
    if (!userId || !newOrgId) {
        showNotification('User ID e Organization ID são obrigatórios', 'error');
        return;
    }
    
    try {
        const data = await makeAuthenticatedRequest(
            `${getApiBaseUrl()}/master/users/${userId}/change-organization?new_organization_id=${newOrgId}`,
            { method: 'PUT' }
        );
        
        showNotification('Usuário movido de organização!', 'success');
        showResult(data);
    } catch (error) {
        showNotification('Erro ao mover usuário', 'error');
        showResult(error.message, true);
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', async function() {
    // Mostrar aba de autenticação por padrão
    showTab('auth');
    
    // Se houver token salvo, carregar informações do usuário
    if (accessToken) {
        updateConnectionStatus('Carregando...', false);
        try {
            await testGetMe();
            showNotification('Sessão restaurada com sucesso!', 'success');
        } catch (error) {
            clearTokens();
            showNotification('Sessão expirada. Faça login novamente.', 'error');
        }
    }
});
