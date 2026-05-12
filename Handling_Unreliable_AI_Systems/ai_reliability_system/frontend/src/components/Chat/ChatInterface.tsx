import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from 'react-query';
import { MessageBubble } from './MessageBubble';
import { InputArea } from './InputArea';
import { LoadingSpinner } from '../Common/LoadingSpinner';
import { aiService } from '../../services/api';
import { useCircuitBreaker } from '../../hooks/useCircuitBreaker';
import type { Message, AIResponse } from '../../types';

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { state: circuitState, fire: makeRequest } = useCircuitBreaker();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (text: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await makeRequest(() => aiService.processRequest(text));
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.output,
        sender: 'ai',
        confidence: response.confidence,
        timestamp: new Date(),
        metadata: {
          tokensUsed: response.tokens_used,
          modelUsed: response.model_used,
          processingTime: response.processing_time,
        },
      };
      
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: circuitState === 'OPEN' 
          ? 'Service is currently unavailable. Please try again later.'
          : 'Failed to get response. Please check your connection.',
        sender: 'ai',
        confidence: 0,
        timestamp: new Date(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-lg shadow">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-10">
            <p>Ask me anything! I'm here to help.</p>
            <p className="text-sm mt-2">
              Current circuit state: {circuitState}
            </p>
          </div>
        )}
        
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3">
              <LoadingSpinner />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <InputArea onSend={sendMessage} disabled={isLoading || circuitState === 'OPEN'} />
    </div>
  );
};