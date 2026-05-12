import React from 'react';
import { format } from 'date-fns';
import { ConfidenceIndicator } from '../Common/ConfidenceIndicator';
import type { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.sender === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`max-w-[70%] ${isUser ? 'order-2' : 'order-1'}`}>
        <div
          className={`rounded-lg p-3 ${
            isUser
              ? 'bg-blue-600 text-white'
              : message.isError
              ? 'bg-red-100 text-red-800 border border-red-300'
              : 'bg-gray-100 text-gray-900'
          }`}
        >
          <div className="whitespace-pre-wrap break-words">
            {message.text}
          </div>
          
          {!isUser && message.confidence !== undefined && (
            <div className="mt-2">
              <ConfidenceIndicator confidence={message.confidence} size="small" />
            </div>
          )}
        </div>
        
        <div className={`mt-1 text-xs text-gray-500 ${isUser ? 'text-right' : 'text-left'}`}>
          {format(message.timestamp, 'HH:mm:ss')}
          {message.metadata?.tokensUsed && (
            <span className="ml-2 text-gray-400">
              {message.metadata.tokensUsed} tokens
            </span>
          )}
        </div>
      </div>
    </div>
  );
};