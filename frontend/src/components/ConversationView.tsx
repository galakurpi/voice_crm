import React from 'react';
import { cn } from '@/lib/utils';

interface Message {
  id: string;
  text: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

interface ConversationViewProps {
  messages: Message[];
}

const ConversationView: React.FC<ConversationViewProps> = ({ messages }) => {
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] text-gray-500">
        <svg className="w-12 h-12 mb-4 text-[#efc824]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" 
          />
        </svg>
        <p className="text-lg">How can I help you today?</p>
        <p className="text-sm text-gray-600 mt-1">Click Start to begin voice conversation</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "flex w-full",
            message.role === 'user' ? 'justify-end' : 'justify-start'
          )}
        >
          {message.role === 'user' ? (
            <div className="bg-[#2f2f2f] border border-[#efc824]/30 text-[#efc824] px-4 py-3 rounded-2xl max-w-[80%]">
              <p className="text-base leading-relaxed whitespace-pre-wrap break-words">
                {message.text}
              </p>
            </div>
          ) : (
            <div className="text-gray-100 max-w-[90%]">
              <p className="text-base leading-relaxed whitespace-pre-wrap break-words">
                {message.text}
              </p>
            </div>
          )}
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ConversationView;
