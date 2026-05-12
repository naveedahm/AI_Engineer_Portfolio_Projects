class LLMChatClient {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
        this.userId = this.getOrCreateUserId();
        this.init();
    }
    
    getOrCreateUserId() {
        let userId = localStorage.getItem('userId');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('userId', userId);
        }
        return userId;
    }
    
    init() {
        this.messageContainer = document.getElementById('messages');
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.metricsDiv = document.getElementById('metrics');
        
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.userInput.addEventListener('input', () => {
            const count = this.userInput.value.length;
            document.getElementById('charCount').textContent = `${count}/2000`;
        });
        
        this.loading = false;
    }
    
    async sendMessage() {
        if (this.loading) return;
        
        const message = this.userInput.value.trim();
        if (!message) return;
        
        // Add user message to UI
        this.addMessage(message, 'user');
        this.userInput.value = '';
        this.showTypingIndicator();
        this.loading = true;
        
        try {
            const response = await this.callAPI(message);
            this.hideTypingIndicator();
            this.addMessage(response.response_text, 'ai', response.suggested_actions);
            this.updateMetrics(response);
        } catch (error) {
            this.hideTypingIndicator();
            this.handleError(error);
        } finally {
            this.loading = false;
        }
    }
    
    async callAPI(message) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);
        
        try {
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user_id: this.userId
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'API request failed');
            }
            
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout after 60 seconds');
            }
            throw error;
        }
    }
    
    addMessage(text, sender, actions = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;
        messageDiv.appendChild(contentDiv);
        
        if (actions && actions.length > 0 && sender === 'ai') {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'suggested-actions';
            actions.forEach(action => {
                const btn = document.createElement('button');
                btn.textContent = action.replace(/_/g, ' ');
                btn.className = 'action-btn';
                btn.onclick = () => {
                    this.userInput.value = action;
                    this.sendMessage();
                };
                actionsDiv.appendChild(btn);
            });
            messageDiv.appendChild(actionsDiv);
        }
        
        this.messageContainer.appendChild(messageDiv);
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }
    
    showTypingIndicator() {
        this.typingIndicator.style.display = 'block';
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }
    
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }
    
    updateMetrics(response) {
        this.metricsDiv.style.display = 'flex';
        document.getElementById('processingTime').textContent = 
            response.processing_time_ms.toFixed(0);
        document.getElementById('confidence').textContent = 
            (response.confidence * 100).toFixed(0);
        document.getElementById('sentiment').textContent = 
            response.sentiment;
    }
    
    handleError(error) {
        console.error('Error:', error);
        this.addMessage(
            `⚠️ ${error.message || 'Failed to get response. Please try again.'}`,
            'ai'
        );
        
        // Update status indicator
        const statusEl = document.getElementById('status');
        statusEl.textContent = 'Error';
        statusEl.style.background = '#e74c3c';
        setTimeout(() => {
            statusEl.textContent = 'Connected';
            statusEl.style.background = '#27ae60';
        }, 5000);
    }
}

// Initialize chat client
const chat = new LLMChatClient();