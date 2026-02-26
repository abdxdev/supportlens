import { useState, useRef, useEffect } from "react";
import { sendChat, saveTrace } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { SendHorizonal, Bot, User, Loader2 } from "lucide-react";

const CATEGORY_COLORS = {
  Billing: "bg-blue-100 text-blue-800",
  Refund: "bg-amber-100 text-amber-800",
  "Account Access": "bg-purple-100 text-purple-800",
  Cancellation: "bg-red-100 text-red-800",
  "General Inquiry": "bg-green-100 text-green-800",
};

function Bubble({ role, text, category, responseTime }) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
          <Bot className="w-4 h-4 text-primary-foreground" />
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${isUser ? "bg-primary text-primary-foreground rounded-br-sm" : "bg-muted text-foreground rounded-bl-sm"}`}>{text}</div>
        {category && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CATEGORY_COLORS[category] ?? "bg-gray-100 text-gray-700"}`}>{category}</span>
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

export default function Chatbot({ messages, setMessages, onNewTrace }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const message = input.trim();
    if (!message || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    setLoading(true);

    try {
      const { response, category, response_time_ms } = await sendChat(message);
      // Save trace — pass the pre-computed category so no second LLM call is needed
      const trace = await saveTrace({
        user_message: message,
        bot_response: response,
        response_time_ms,
        category,
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: response,
          category: trace.category,
          responseTime: response_time_ms,
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
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
            Online
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto px-6 py-4">
        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} text={m.text} category={m.category} responseTime={m.responseTime} />
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
          <Input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey} placeholder="Type your message…" disabled={loading} className="flex-1" />
          <Button onClick={handleSend} disabled={loading || !input.trim()} size="icon">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendHorizonal className="w-4 h-4" />}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">Each message is independent.</p>
      </div>
    </div>
  );
}
