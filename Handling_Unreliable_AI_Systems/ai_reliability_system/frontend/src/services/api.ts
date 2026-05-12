
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class AIService {
  private client = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  async sendChatMessage(messages: Array<{ role: string; content: string }>) {
    try {
      // Change from '/chat' to '/api/v1/chat'
      const response = await this.client.post('/api/v1/chat', {
        messages: messages,
        temperature: 0.7,
        max_tokens: 1000
      });
      return response.data;
    } catch (error) {
      console.error('Chat API error:', error);
      throw error;
    }
  }

  async healthCheck() {
    try {
      const response = await this.client.get('/health/');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      return null;
    }
  }
}

export const aiService = new AIService();