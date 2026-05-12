import { io, Socket } from 'socket.io-client';

interface WebSocketEvents {
  onMessage: (data: any) => void;
  onMetrics: (data: any) => void;
  onAlert: (data: any) => void;
  onError: (error: Error) => void;
}

export class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private eventHandlers: Partial<WebSocketEvents> = {};

  connect(url: string = 'http://localhost:8000') {
    this.socket = io(url, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.handleReconnect();
    });

    // Message handlers
    this.socket.on('ai_response', (data) => {
      this.eventHandlers.onMessage?.(data);
    });

    this.socket.on('metrics_update', (data) => {
      this.eventHandlers.onMetrics?.(data);
    });

    this.socket.on('alert', (data) => {
      this.eventHandlers.onAlert?.(data);
    });

    this.socket.on('error', (error) => {
      this.eventHandlers.onError?.(new Error(error));
    });
  }

  private handleReconnect() {
    this.reconnectAttempts++;
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.connect();
      }, 1000 * Math.pow(2, this.reconnectAttempts));
    }
  }

  sendMessage(message: any) {
    if (this.socket?.connected) {
      this.socket.emit('chat_message', message);
    } else {
      console.warn('WebSocket not connected, message not sent');
    }
  }

  subscribeToMetrics(metrics: string[]) {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_metrics', metrics);
    }
  }

  on<K extends keyof WebSocketEvents>(
    event: K,
    handler: WebSocketEvents[K]
  ) {
    this.eventHandlers[event] = handler;
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

// Singleton instance
export const wsService = new WebSocketService();