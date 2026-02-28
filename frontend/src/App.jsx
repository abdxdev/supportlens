import "./App.css";
import { useState, useEffect, useCallback } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import Chatbot from "@/components/Chatbot";
import Dashboard from "@/components/Dashboard";
import { Eye, MessageSquare } from "lucide-react";
import { ThemeProvider } from "@/components/theme-provider";
import { ModeToggle } from "@/components/mode-toggle";
import StatusBadge from "@/components/StatusBadge";
import { getHealth } from "@/lib/api";

export default function App() {
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [activeTab, setActiveTab] = useState("chatbot");
  const [chatMessages, setChatMessages] = useState([{ role: "bot", text: "Hi! I'm the SupportLens assistant. How can I help you today?" }]);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(null);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await getHealth();
      setHealth(data);
      setHealthError(null);
    } catch (err) {
      setHealthError(err.message);
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const id = setInterval(fetchHealth, 30_000);
    return () => clearInterval(id);
  }, [fetchHealth]);

  const serviceStatus = health?.status ?? (healthError ? "unhealthy" : "unknown");

  function handleNewTrace() {
    setRefreshSignal((s) => s + 1);
  }

  return (
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <div className="min-h-screen bg-background flex flex-col">
        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-col flex-1 overflow-hidden gap-0">
            {/* Combined header + tab nav */}
            <header className="h-14 border-b bg-background shrink-0 flex items-center px-6 gap-6">
              {/* Brand */}
              <div className="flex items-center gap-2.5 shrink-0 pr-6 border-r h-full">
                <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center">
                  <Eye className="w-4 h-4 text-primary-foreground" />
                </div>
                <span className="font-bold text-base tracking-tight">SupportLens</span>
              </div>

              {/* Tab triggers — underline style, flush with header border-b */}
              <TabsList className="h-full bg-transparent p-0 rounded-none gap-0 shadow-none">
                <TabsTrigger value="chatbot" className="h-full px-3 rounded-none bg-transparent shadow-none border-b-2 border-transparent -mb-px data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:text-foreground text-muted-foreground font-medium text-sm flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5" />
                  Chatbot
                </TabsTrigger>
                <TabsTrigger value="dashboard" onClick={() => setRefreshSignal((s) => s + 1)} className="h-full px-3 rounded-none bg-transparent shadow-none border-b-2 border-transparent -mb-px data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:text-foreground text-muted-foreground font-medium text-sm flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5" />
                  Dashboard
                </TabsTrigger>
              </TabsList>

              {/* Theme toggle — pushed to the right */}
              <div className="ml-auto">
                <ModeToggle />
              </div>
            </header>

            {/* Chatbot tab */}
            <TabsContent value="chatbot" className="flex-1 overflow-hidden m-0 data-[state=active]:flex data-[state=active]:flex-col">
              <div className="flex-1 min-h-0 max-w-2xl w-full mx-auto border-x flex flex-col">
                <Chatbot messages={chatMessages} setMessages={setChatMessages} onNewTrace={handleNewTrace} serviceStatus={serviceStatus} />
              </div>
            </TabsContent>

            {/* Dashboard tab */}
            <TabsContent value="dashboard" className="flex-1 overflow-auto m-0">
              <div className="max-w-6xl mx-auto w-full border-x min-h-full">
                <Dashboard refreshSignal={refreshSignal} />
              </div>
            </TabsContent>
          </Tabs>
        </main>
        <StatusBadge health={health} healthError={healthError} fetchHealth={fetchHealth} />
      </div>
    </ThemeProvider>
  );
}
