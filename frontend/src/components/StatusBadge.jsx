import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Activity, Database, BotMessageSquare, Clock } from "lucide-react";

const STATUS_CONFIG = {
  healthy: { color: "bg-emerald-500", label: "Healthy", variant: "outline" },
  degraded: { color: "bg-amber-500", label: "Degraded", variant: "outline" },
  unhealthy: { color: "bg-red-500", label: "Unhealthy", variant: "destructive" },
  unknown: { color: "bg-muted-foreground", label: "Unknown", variant: "outline" },
};

function formatUptime(seconds) {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

// eslint-disable-next-line no-unused-vars -- Icon is used as a JSX component
function CheckRow({ icon: Icon, label, status, detail }) {
  const dotColor = status === "up" || status === "configured" ? "bg-emerald-500" : status === "unconfigured" ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="flex items-start gap-3 py-2">
      <Icon className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{label}</span>
          <span className={`w-2 h-2 rounded-full ${dotColor}`} />
          <span className="text-xs text-muted-foreground capitalize">{status}</span>
        </div>
        {detail && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{detail}</p>}
      </div>
    </div>
  );
}

export default function StatusBadge({ health, healthError, fetchHealth }) {
  const [open, setOpen] = useState(false);
  const error = healthError;

  useEffect(() => {
    if (open) fetchHealth();
  }, [open, fetchHealth]);

  const status = health?.status ?? (error ? "unhealthy" : "unknown");
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown;

  return (
    <>
      <button onClick={() => setOpen(true)} className="fixed bottom-4 right-4 z-50">
        <Badge variant={cfg.variant} className="cursor-pointer gap-1.5 px-2.5 py-1 text-xs shadow-md hover:shadow-lg transition-shadow">
          <span className={`w-2 h-2 rounded-full ${cfg.color} animate-pulse`} />
          {cfg.label}
        </Badge>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              System Status
            </DialogTitle>
            <DialogDescription>Backend health check overview</DialogDescription>
          </DialogHeader>

          {error && !health ? (
            <div className="rounded-md bg-destructive/10 border border-destructive/20 p-3">
              <p className="text-sm text-destructive font-medium">Backend unreachable</p>
              <p className="text-xs text-muted-foreground mt-1">{error}</p>
            </div>
          ) : health ? (
            <div className="space-y-1">
              {/* Overall status */}
              <div className="flex items-center justify-between pb-2">
                <span className="text-sm text-muted-foreground">Overall</span>
                <Badge variant={cfg.variant} className="gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${cfg.color}`} />
                  {cfg.label}
                </Badge>
              </div>

              <Separator />

              {/* Checks */}
              <div className="pt-1">
                {health.checks?.database && <CheckRow icon={Database} label="Database" status={health.checks.database.status} detail={health.checks.database.error} />}
                {health.checks?.llm && <CheckRow icon={BotMessageSquare} label="LLM Provider" status={health.checks.llm.status} detail={health.checks.llm.detail} />}
              </div>

              <Separator />

              {/* Uptime */}
              <div className="flex items-center gap-2 pt-2 text-xs text-muted-foreground">
                <Clock className="w-3.5 h-3.5" />
                Uptime: {formatUptime(health.uptime_seconds ?? 0)}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Loading…</p>
          )}

          <DialogFooter showCloseButton />
        </DialogContent>
      </Dialog>
    </>
  );
}
