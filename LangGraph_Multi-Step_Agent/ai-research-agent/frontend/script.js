class ResearchAgentUI {
    constructor() {
        this.messageContainer = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.clearButton = document.getElementById('clearButton');
        this.stopButton = document.getElementById('stopButton');
        this.thinkingIndicator = document.getElementById('thinking');
        
        this.threadId = this.generateThreadId();
        this.isGenerating = false;
        this.currentEventSource = null;
        
        this.setupEventListeners();
        this.loadHistory();
    }
    
    generateThreadId() {
        let id = localStorage.getItem('thread_id');
        if (!id) {
            id = 'thread_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('thread_id', id);
        }
        return id;
    }
    
    setupEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.clearButton.addEventListener('click', () => this.clearConversation());
        this.stopButton.addEventListener('click', () => this.stopGeneration());
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }
    
    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message || this.isGenerating) return;
        
        // Clear input
        this.userInput.value = '';
        
        // Add user message to UI
        this.addMessage(message, 'user');
        
        // Start generation
        this.startGeneration();
        
        // Create assistant message placeholder
        const assistantMessage = this.addMessage('', 'assistant', true);
        
        try {
            await this.streamResponse(message, assistantMessage);
        } catch (error) {
            console.error('Error:', error);
            this.addSystemMessage(`Error: ${error.message}`);
        } finally {
            this.endGeneration();
        }
    }
    
    async streamResponse(message, messageElement) {
        const url = `http://localhost:8000/api/chat/stream`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                thread_id: this.threadId
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedText = '';
        let toolCalls = [];
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        switch (data.type) {
                            case 'token':
                                accumulatedText += data.content;
                                this.updateAssistantMessage(messageElement, accumulatedText);
                                break;
                                
                            case 'tool_start':
                                toolCalls.push({ tool: data.tool, status: 'started' });
                                this.updateToolStatus(toolCalls);
                                break;
                                
                            case 'tool_end':
                                const tool = toolCalls.find(t => t.tool === data.tool);
                                if (tool) tool.status = 'completed';
                                this.updateToolStatus(toolCalls);
                                break;
                                
                            case 'final':
                                this.updateAssistantMessage(messageElement, data.content, true);
                                break;
                                
                            case 'error':
                                this.addSystemMessage(`Error: ${data.error}`);
                                break;
                                
                            case 'done':
                                return;
                        }
                    } catch (e) {
                        console.error('Failed to parse SSE data:', e);
                    }
                }
            }
        }
    }
    
    addMessage(content, role, isPlaceholder = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        if (isPlaceholder) {
            messageDiv.classList.add('streaming');
        }
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = this.formatMessage(content);
        
        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = new Date().toLocaleTimeString();
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timestamp);
        
        this.messageContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }
    
    updateAssistantMessage(messageElement, content, isFinal = false) {
        const contentDiv = messageElement.querySelector('.message-content');
        contentDiv.innerHTML = this.formatMessage(content);
        
        if (isFinal) {
            messageElement.classList.remove('streaming');
        }
        
        this.scrollToBottom();
    }
    
    updateToolStatus(toolCalls) {
        // Remove existing tool status
        const existingStatus = document.querySelector('.tool-status');
        if (existingStatus) existingStatus.remove();
        
        if (toolCalls.length > 0) {
            const statusDiv = document.createElement('div');
            statusDiv.className = 'tool-status';
            statusDiv.innerHTML = `
                <div style="background: #f0f0f0; padding: 10px; border-radius: 8px; margin: 10px 0;">
                    <strong>🔧 Tool Calls:</strong><br/>
                    ${toolCalls.map(t => `${t.tool}: ${t.status === 'started' ? '⏳' : '✅'}`).join('<br/>')}
                </div>
            `;
            this.messageContainer.appendChild(statusDiv);
            this.scrollToBottom();
        }
    }
    
    addSystemMessage(content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'system-message';
        messageDiv.textContent = content;
        this.messageContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessage(content) {
        if (!content) return '';
        
        // Convert markdown-style code blocks
        content = content.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang || 'plaintext'}">${this.escapeHtml(code)}</code></pre>`;
        });
        
        // Convert inline code
        content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Convert line breaks
        content = content.replace(/\n/g, '<br/>');
        
        return content;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    startGeneration() {
        this.isGenerating = true;
        this.sendButton.disabled = true;
        this.stopButton.style.display = 'block';
        this.thinkingIndicator.style.display = 'block';
    }
    
    endGeneration() {
        this.isGenerating = false;
        this.sendButton.disabled = false;
        this.stopButton.style.display = 'none';
        this.thinkingIndicator.style.display = 'none';
    }
    
    stopGeneration() {
        if (this.currentEventSource) {
            this.currentEventSource.close();
            this.currentEventSource = null;
        }
        this.endGeneration();
        this.addSystemMessage('Generation stopped by user.');
    }
    
    async clearConversation() {
        if (confirm('Clear the conversation history?')) {
            // Clear UI messages
            const messages = this.messageContainer.querySelectorAll('.message, .system-message, .tool-status');
            messages.forEach(msg => msg.remove());
            
            // Add welcome message back
            const welcomeDiv = document.createElement('div');
            welcomeDiv.className = 'welcome-message';
            welcomeDiv.innerHTML = `
                <div class="message system">
                    <div class="message-content">
                        👋 Conversation cleared! Ask me something that requires research.
                    </div>
                </div>
            `;
            this.messageContainer.appendChild(welcomeDiv);
            
            // Generate new thread ID
            this.threadId = this.generateThreadId();
            
            // Optionally delete session from backend
            try {
                await fetch(`http://localhost:8000/api/sessions/${this.threadId}`, {
                    method: 'DELETE'
                });
            } catch (error) {
                console.error('Failed to delete session:', error);
            }
        }
    }
    
    async loadHistory() {
        try {
            const response = await fetch(`http://localhost:8000/api/sessions/${this.threadId}`);
            if (response.ok) {
                const data = await response.json();
                // Display history (implementation depends on your needs)
            }
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }
    
    scrollToBottom() {
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ResearchAgentUI();
});