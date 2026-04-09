'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Bot, Send, Sparkles } from 'lucide-react';

export default function AIAgentMockup() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'agent',
      content: 'Hello! I am your SmartPark AI Assistant. How can I help you manage the parking facility today?',
    },
    {
      id: 2,
      role: 'user',
      content: 'Can you show me the peak hours for yesterday?',
    },
    {
      id: 3,
      role: 'agent',
      content: 'Based on the OCR tracking data, the peak hours yesterday were between 8:00 AM - 9:00 AM (84 vehicles entered) and 5:00 PM - 6:30 PM (92 vehicles exited).',
    }
  ]);

  const handleSend = () => {
    if (!input.trim()) return;
    
    // Add user message
    const newMessages = [
      ...messages,
      { id: Date.now(), role: 'user', content: input }
    ];
    
    setMessages(newMessages);
    setInput('');
    
    // Mock Agent typing/response
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { 
          id: Date.now() + 1, 
          role: 'agent', 
          content: 'This is a mockup response. The Python AI service integrating the real LLM inference will be implemented in the next phase.' 
        }
      ]);
    }, 1000);
  };

  return (
    <div className="p-6 md:p-8 flex-1 flex flex-col space-y-4 bg-slate-50 min-h-[calc(100vh-64px)] w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
          <Sparkles className="h-7 w-7 text-indigo-500" /> AI Agent Assistant
        </h1>
        <p className="text-muted-foreground mt-1">
          Interact with the system directly through natural language queries.
        </p>
      </div>

      <Card className="flex-1 flex flex-col shadow-sm overflow-hidden border-indigo-100 max-h-[calc(100vh-12rem)] md:mx-4">
        <ScrollArea className="flex-1 p-4 bg-white/50 backdrop-blur-sm relative">
          <div className="space-y-6 max-w-4xl mx-auto py-4">
            {messages.map((message) => (
              <div 
                key={message.id} 
                className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'agent' && (
                  <Avatar className="h-10 w-10 border border-indigo-200 bg-indigo-50 mt-1 shrink-0">
                    <Bot className="h-5 w-5 text-indigo-600 m-auto mt-2.5" />
                  </Avatar>
                )}
                
                <div className={`rounded-2xl px-5 py-3.5 max-w-[80%] shadow-sm ${
                  message.role === 'user' 
                    ? 'bg-indigo-600 text-white rounded-tr-sm' 
                    : 'bg-white border rounded-tl-sm text-gray-800'
                }`}>
                  <p className="text-sm leading-relaxed">{message.content}</p>
                </div>
                
                {message.role === 'user' && (
                  <Avatar className="h-10 w-10 border border-border mt-1 shrink-0">
                    <AvatarFallback className="bg-indigo-100 text-indigo-700 font-semibold">AD</AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
        
        <div className="p-4 bg-white border-t border-indigo-100/60 sticky bottom-0 z-10 shadow-[0_-10px_20px_-10px_rgba(0,0,0,0.05)]">
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex items-center gap-2 max-w-4xl mx-auto relative group"
          >
            <Input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything about the parking data..." 
              className="flex-1 pr-12 rounded-full border-gray-300 focus-visible:ring-indigo-500 py-6 text-md shadow-sm transition-shadow group-focus-within:shadow-md bg-gray-50/50"
            />
            <Button 
              type="submit" 
              size="icon" 
              className="absolute right-1.5 rounded-full h-10 w-10 bg-indigo-600 hover:bg-indigo-700 transition-colors shrink-0 shadow-sm"
              disabled={!input.trim()}
            >
              <Send className="h-4 w-4" />
              <span className="sr-only">Send message</span>
            </Button>
          </form>
          <div className="text-center mt-3 text-xs text-muted-foreground font-medium flex items-center justify-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400"></span>
            AI Assistant is currently running in mockup mode
          </div>
        </div>
      </Card>
    </div>
  );
}
