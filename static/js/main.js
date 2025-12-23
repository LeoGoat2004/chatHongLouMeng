document.addEventListener('DOMContentLoaded', function() {
    // Load NPCs on homepage
    if (window.location.pathname === '/') {
        loadNPCs();
    }
    
    // Initialize chat if on chat page
    if (window.location.pathname.includes('/npc/')) {
        initializeChat();
    }
});

async function loadNPCs() {
    // Load all NPCs from server
    try {
        const response = await fetch('/api/npc_list');
        if (!response.ok) {
            throw new Error('Failed to load NPCs');
        }
        const npcs = await response.json();
        renderNPCs(npcs);
    } catch (error) {
        console.error('Error loading NPCs:', error);
        document.getElementById('npcGrid').innerHTML = '<p>加载NPC失败，请稍后重试</p>';
    }
}

function renderNPCs(npcs) {
    // Render NPCs on homepage
    const npcGrid = document.getElementById('npcGrid');
    
    if (npcs.length === 0) {
        npcGrid.innerHTML = '<p>暂无可用的NPC</p>';
        return;
    }
    
    npcGrid.innerHTML = npcs.map(npc => `
        <div class="npc-card" onclick="goToChat('${npc.id}')">
            <img src="${npc.avatar}" alt="${npc.name}" class="npc-avatar">
            <h3 class="npc-name">${npc.name}</h3>
            <p class="npc-description">${npc.description || '暂无描述'}</p>
            <button class="chat-button">开始对话</button>
        </div>
    `).join('');
}

function goToChat(npcId) {
    // Navigate to NPC chat page
    window.location.href = `/npc/${npcId}`;
}

function initializeChat() {
    // Initialize chat functionality
    const npcId = window.location.pathname.split('/')[2];
    loadNPCInfo(npcId);
    
    // Add event listener to send button
    const sendButton = document.getElementById('sendMessage');
    const messageInput = document.getElementById('messageInput');
    
    sendButton.addEventListener('click', () => {
        sendMessage(npcId);
    });
    
    // Send message on Enter key
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage(npcId);
        }
    });
    
    // Initialize memory buttons
    initializeMemoryButtons(npcId);
}

async function loadNPCInfo(npcId) {
    // Load NPC information
    try {
        const response = await fetch(`/api/npc/${npcId}`);
        if (!response.ok) {
            throw new Error('Failed to load NPC info');
        }
        const npcInfo = await response.json();
        updateChatHeader(npcInfo);
    } catch (error) {
        console.error('Error loading NPC info:', error);
    }
}

function updateChatHeader(npcInfo) {
    // Update chat header with NPC information
    const chatHeader = document.querySelector('.chat-header');
    
    // Find or create the header content elements
    let headerContent = chatHeader.querySelector('.header-content');
    if (!headerContent) {
        // Create header content structure if it doesn't exist
        headerContent = document.createElement('div');
        headerContent.className = 'header-content';
        headerContent.innerHTML = `
            <img src="${npcInfo.avatar}" alt="${npcInfo.name}">
            <div>
                <h2>${npcInfo.name}</h2>
                <p>${npcInfo.description || '暂无描述'}</p>
            </div>
        `;
        
        // Insert before header actions (if exists) or append to chat header
        const headerActions = chatHeader.querySelector('.header-actions');
        if (headerActions) {
            chatHeader.insertBefore(headerContent, headerActions);
        } else {
            chatHeader.appendChild(headerContent);
        }
    } else {
        // Update existing elements
        const img = headerContent.querySelector('img');
        const h2 = headerContent.querySelector('h2');
        const p = headerContent.querySelector('p');
        
        img.src = npcInfo.avatar;
        img.alt = npcInfo.name;
        h2.textContent = npcInfo.name;
        p.textContent = npcInfo.description || '暂无描述';
    }
}

async function sendMessage(npcId) {
    // Send message to NPC
    const messageInput = document.getElementById('messageInput');
    const userMessage = messageInput.value.trim();
    
    if (!userMessage) return;
    
    // Clear input
    messageInput.value = '';
    
    // Display user message
    displayMessage(userMessage, 'user');
    
    // Send message to server
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                npc_id: npcId,
                message: userMessage
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to send message');
        }
        
        const data = await response.json();
        // Display NPC response
        displayMessage(data.response, 'npc');
    } catch (error) {
        console.error('Error sending message:', error);
        displayMessage('抱歉，发送消息失败，请稍后重试', 'npc');
    }
}

function displayMessage(message, sender) {
    // Display message in chat
    const chatMessages = document.querySelector('.chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.textContent = message;
    
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Memory visualization functions
function initializeMemoryButtons(npcId) {
    // View memories button
    const viewMemoriesBtn = document.getElementById('viewMemories');
    if (viewMemoriesBtn) {
        viewMemoriesBtn.addEventListener('click', () => {
            showMemoriesModal(npcId);
        });
    }
    
    // Clear memories button
    const clearMemoriesBtn = document.getElementById('clearMemories');
    if (clearMemoriesBtn) {
        clearMemoriesBtn.addEventListener('click', () => {
            if (confirm('确定要清除与这个NPC的所有对话记忆吗？')) {
                clearMemories(npcId);
            }
        });
    }
    
    // Close modal button
    const closeBtn = document.querySelector('.close');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeMemoriesModal);
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        const modal = document.getElementById('memoryModal');
        if (event.target === modal) {
            closeMemoriesModal();
        }
    });
}

async function showMemoriesModal(npcId) {
    try {
        const response = await fetch(`/api/memories/${npcId}`);
        if (!response.ok) {
            throw new Error('Failed to load memories');
        }
        const memories = await response.json();
        renderMemories(memories);
        
        // Show modal
        const modal = document.getElementById('memoryModal');
        modal.style.display = 'block';
    } catch (error) {
        console.error('Error loading memories:', error);
        alert('加载记忆失败，请稍后重试');
    }
}

function renderMemories(memories) {
    const memoryContent = document.getElementById('memoryContent');
    
    if (memories.length === 0) {
        memoryContent.innerHTML = '<p>暂无对话记忆</p>';
        return;
    }
    
    // Sort memories by timestamp (newest first)
    memories.sort((a, b) => b.timestamp - a.timestamp);
    
    memoryContent.innerHTML = memories.map(memory => `
        <div class="memory-item">
            <div class="memory-time">${new Date(memory.timestamp * 1000).toLocaleString()}</div>
            <div class="memory-user">用户: ${memory.user_message}</div>
            <div class="memory-npc">角色: ${memory.assistant_message}</div>
        </div>
    `).join('');
}

function closeMemoriesModal() {
    const modal = document.getElementById('memoryModal');
    modal.style.display = 'none';
}

async function clearMemories(npcId) {
    try {
        const response = await fetch(`/api/memories/${npcId}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            throw new Error('Failed to clear memories');
        }
        alert('记忆已清除');
    } catch (error) {
        console.error('Error clearing memories:', error);
        alert('清除记忆失败，请稍后重试');
    }
}