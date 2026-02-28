import { useState, useRef, useEffect } from "react";
import { sendChat } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import MarkdownRenderer from "@/components/markdown-renderer";
import { SendHorizonal, Bot, User, Loader2 } from "lucide-react";

const CATEGORY_COLORS = {
  Billing: "bg-blue-100 text-blue-800",
  Refund: "bg-amber-100 text-amber-800",
  "Account Access": "bg-purple-100 text-purple-800",
  Cancellation: "bg-red-100 text-red-800",
  "General Inquiry": "bg-green-100 text-green-800",
  Error: "bg-red-200 text-red-900",
};

function Bubble({ role, text, categories, responseTime }) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
          <Bot className="w-4 h-4 text-primary-foreground" />
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${isUser ? "bg-primary text-primary-foreground rounded-br-sm" : "bg-muted text-foreground rounded-bl-sm"}`}>
          <MarkdownRenderer content={text} />
        </div>
        {categories?.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            {categories.map((cat) => (
              <span key={cat} className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[cat] ?? "bg-gray-100 text-gray-700"}`}>
                {cat}
              </span>
            ))}
            {responseTime && <span className="text-xs text-muted-foreground">{responseTime} ms</span>}
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-secondary-foreground" />
        </div>
      )}
    </div>
  );
}

export default function Chatbot({ messages, setMessages, onNewTrace, serviceStatus }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const isUnhealthy = serviceStatus === "unhealthy";
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const message = input.trim();
    if (!message || loading || isUnhealthy) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    setLoading(true);

    try {
      const { response, categories, response_time_ms, is_fallback } = await sendChat(message);
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: response,
          categories,
          responseTime: response_time_ms,
          isFallback: is_fallback,
        },
      ]);
      onNewTrace?.();
    } catch (err) {
      const msg = err?.message || String(err);
      console.error("Chat error:", err?.status, msg);
      const display = `Error: ${msg}`;
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: display,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center">
          <Bot className="w-5 h-5 text-primary-foreground" />
        </div>
        <div>
          <p className="font-semibold text-sm">Bot Support</p>
          <p className="text-xs text-muted-foreground flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full inline-block ${isUnhealthy ? "bg-red-500" : "bg-green-500"}`} />
            {isUnhealthy ? "Service Unhealthy" : "Online"}
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto px-6 py-4">
        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} text={m.text} categories={m.categories} responseTime={m.responseTime} />
        ))}
        {loading && (
          <div className="flex gap-3 justify-start mb-4">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-primary-foreground" />
            </div>
            <div className="bg-muted px-4 py-3 rounded-2xl rounded-bl-sm flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="px-6 py-4 border-t">
        <div className="flex gap-2">
          <Input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey} placeholder={isUnhealthy ? "Chat unavailable — service is unhealthy" : "Type your message…"} disabled={loading || isUnhealthy} className="flex-1" />
          <Button onClick={handleSend} disabled={loading || isUnhealthy || !input.trim()} size="icon">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendHorizonal className="w-4 h-4" />}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">Each message is independent.</p>
      </div>
    </div>
  );
}
