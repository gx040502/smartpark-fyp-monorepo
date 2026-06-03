"use client"

import { useChat } from "@ai-sdk/react"
import { Sparkles } from "lucide-react"

import { cn } from "@/lib/utils"
import { Chat } from "@/components/ui/chat"

export default function AIAgentMockup() {
  const { //return values of useChat
    messages,           //Render messages bubbles
    input,              //Show current text in input --> will be past to "content"
    handleInputChange,  //update input as user types
    handleSubmit,       //trigger send on Enter/click
    append,             //send suggestion as message
    stop,               //Stop generation
    status,             //Check if AI Agent is loading or streaming
    setMessages,        //Cancel tool calls on stop 
  } = useChat({
    api: "/api/chat",   //sends POST http://localhost:3000/api/chat, (parameter passing to useChat)
    //that automatically use route.ts export async function POST which then forwards it to the Python service (ai-service/main.py)
  })

  const isLoading = status === "submitted" || status === "streaming"

  return (
    <div className="p-6 md:p-8 flex-1 flex flex-col space-y-4 bg-slate-50 min-h-0 overflow-hidden w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
          <Sparkles className="h-7 w-7 text-indigo-500" /> AI Agent Assistant
        </h1>
        <p className="text-muted-foreground mt-1">
          Interact with the system directly through natural language queries.
        </p>
      </div>

      <div className={cn("flex", "flex-col", "h-[500px]", "w-full")}>
        <Chat
          className="grow"
          messages={messages}
          handleSubmit={handleSubmit}
          input={input}
          handleInputChange={handleInputChange}
          isGenerating={isLoading}
          stop={stop}
          append={append}
          setMessages={setMessages}
          suggestions={[
            "What are the peak parking hours today?",
            "How many vehicles are currently in the lot?",
            "Show me the parking trends for this week.",
          ]}
        />
      </div>
    </div>
  )
}