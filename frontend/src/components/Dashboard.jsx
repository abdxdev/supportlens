import { useState, useEffect, useCallback } from "react";
import { getTraces, getAnalytics } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { MessageSquare, Clock, RefreshCw, ChevronRight, TrendingUp, Layers, Activity } from "lucide-react";
import MarkdownRenderer from "@/components/markdown-renderer";

const CATEGORIES = ["Billing", "Refund", "Account Access", "Cancellation", "General Inquiry"];

const CATEGORY_VARIANTS = {
  Billing: "bg-blue-100 text-blue-800 border-blue-200",
  Refund: "bg-amber-100 text-amber-800 border-amber-200",
  "Account Access": "bg-purple-100 text-purple-800 border-purple-200",
  Cancellation: "bg-red-100 text-red-800 border-red-200",
  "General Inquiry": "bg-green-100 text-green-800 border-green-200",
};

const CHART_COLORS = {
  Billing: "#3b82f6",
  Refund: "#f59e0b",
  "Account Access": "#a855f7",
  Cancellation: "#ef4444",
  "General Inquiry": "#22c55e",
};

function formatTs(iso) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function CategoryBadge({ categories }) {
  return (
    <div className="flex gap-1 flex-wrap">
      {(categories ?? []).map((cat) => {
        const cls = CATEGORY_VARIANTS[cat] ?? "bg-gray-100 text-gray-800";
        return (
          <span key={cat} className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full border ${cls}`}>
            {cat}
          </span>
        );
      })}
    </div>
  );
}

function KpiItem({ icon: Icon, label, value, sub, accent, last }) {
  return (
    <div className={`flex items-center gap-4 px-8 py-5 min-w-0 flex-1 ${!last ? "border-r" : ""}`}>
      <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: accent + "15" }}>
        <Icon className="w-4 h-4" style={{ color: accent }} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium">{label}</p>
        <p className="text-xl font-semibold leading-tight mt-0.5 truncate">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5 truncate">{sub}</p>}
      </div>
    </div>
  );
}

export default function Dashboard({ refreshSignal }) {
  const [analytics, setAnalytics] = useState(null);
  const [traces, setTraces] = useState([]);
  const [filterCat, setFilterCat] = useState("all");
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, t] = await Promise.all([getAnalytics(), getTraces(filterCat === "all" ? null : filterCat)]);
      setAnalytics(a);
      setTraces(t);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [filterCat]);

  useEffect(() => {
    load();
  }, [load, refreshSignal]);

  const chartData = CATEGORIES.map((cat) => ({
    name: cat === "General Inquiry" ? "General" : cat === "Account Access" ? "Account" : cat,
    fullName: cat,
    count: analytics?.category_breakdown?.[cat]?.count ?? 0,
    color: CHART_COLORS[cat],
  }));

  const topCat = analytics
    ? CATEGORIES.reduce((best, cat) => {
        const cnt = analytics.category_breakdown[cat]?.count ?? 0;
        return cnt > (analytics.category_breakdown[best]?.count ?? 0) ? cat : best;
      }, CATEGORIES[0])
    : null;

  return (
    <div className="flex flex-col divide-y">
      {/* Page header */}
      <div className="flex items-center justify-between px-8 py-5">
        <div>
          <h2 className="text-lg font-semibold">Observability Dashboard</h2>
          <p className="text-muted-foreground text-sm mt-0.5">Live trace analytics for Bot support chatbot</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load} disabled={loading} className="text-muted-foreground">
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* KPI strip */}
      {analytics && topCat && (
        <div className="flex divide-x">
          <KpiItem icon={MessageSquare} label="Total Traces" value={analytics.total_traces.toLocaleString()} sub="All-time conversations" accent="#6366f1" />
          <KpiItem icon={Clock} label="Avg Response Time" value={`${analytics.average_response_time_ms} ms`} sub="Mean across all traces" accent="#0ea5e9" />
          <KpiItem icon={TrendingUp} label="Top Category" value={topCat} sub={`${analytics.category_breakdown[topCat]?.percentage ?? 0}% of traffic`} accent={CHART_COLORS[topCat]} />
          <KpiItem icon={Layers} label="Active Categories" value={`${Object.values(analytics.category_breakdown).filter((c) => c.count > 0).length} / 5`} sub="Have recorded traces" accent="#10b981" last />
        </div>
      )}

      {/* Analytics section */}
      {analytics && (
        <>
          {/* Section header */}
          <div className="flex items-center justify-between px-8 py-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Category Breakdown</span>
              <span className="text-xs text-muted-foreground">— distribution across all traces</span>
            </div>
          </div>

          {/* Chart + list side by side */}
          <div className="flex divide-x">
            {/* Bar chart */}
            <div className="flex-1 px-8 py-6">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-4">Traces per category</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="bg-popover border rounded-lg px-3 py-2 shadow-md text-sm">
                          <p className="font-semibold">{d.fullName}</p>
                          <p className="text-muted-foreground">
                            {d.count} trace{d.count !== 1 ? "s" : ""}
                          </p>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.fullName} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Category share list */}
            <div className="w-72 shrink-0 px-8 py-6 space-y-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Share by category</p>
              {CATEGORIES.map((cat) => {
                const { count = 0, percentage = 0 } = analytics.category_breakdown[cat] ?? {};
                const color = CHART_COLORS[cat];
                return (
                  <div key={cat}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="w-2 h-2 rounded-sm shrink-0" style={{ backgroundColor: color }} />
                        <span className="text-sm truncate">{cat}</span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-2">
                        <span className="text-xs text-muted-foreground tabular-nums">{count}</span>
                        <span className="text-xs font-semibold tabular-nums w-8 text-right">{percentage}%</span>
                      </div>
                    </div>
                    <div className="w-full bg-muted rounded-full h-1">
                      <div className="h-1 rounded-full transition-all duration-700" style={{ width: `${percentage}%`, backgroundColor: color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Trace log section */}
      <div>
        {/* Section header */}
        <div className="flex items-center justify-between px-8 py-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Trace Log</span>
            <span className="text-xs text-muted-foreground">
              — {traces.length} {filterCat !== "all" ? `in ${filterCat}` : "total"}
            </span>
          </div>
          <Select value={filterCat} onValueChange={setFilterCat}>
            <SelectTrigger className="w-44 h-8 text-sm">
              <SelectValue placeholder="Filter by category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {CATEGORIES.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-36 pl-8">Timestamp</TableHead>
                <TableHead className="w-[26%]">User Message</TableHead>
                <TableHead className="w-[30%]">Bot Response</TableHead>
                <TableHead className="w-36">Category</TableHead>
                <TableHead className="w-32 text-right pr-8">Response Time</TableHead>
                <TableHead className="w-8" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {traces.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-16 text-muted-foreground">
                    No traces found.
                  </TableCell>
                </TableRow>
              )}
              {traces.map((t) => (
                <TableRow key={t.id} className="cursor-pointer" onClick={() => setSelectedTrace(t)}>
                  <TableCell className="pl-8 text-xs text-muted-foreground whitespace-nowrap">{formatTs(t.timestamp)}</TableCell>
                  <TableCell className="max-w-55">
                    <span className="block truncate text-sm">{t.user_message}</span>
                  </TableCell>
                  <TableCell className="max-w-65">
                    <span className="block truncate text-sm text-muted-foreground">{t.bot_response}</span>
                  </TableCell>
                  <TableCell>
                    <CategoryBadge categories={t.categories} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-sm pr-8">{t.response_time_ms.toLocaleString()} ms</TableCell>
                  <TableCell>
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Trace detail modal ─ */}
      <Dialog open={!!selectedTrace} onOpenChange={() => setSelectedTrace(null)}>
        {selectedTrace && (
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 flex-wrap">
                Trace Detail
                <CategoryBadge categories={selectedTrace.categories} />
              </DialogTitle>
            </DialogHeader>
            <div className="divide-y text-sm">
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 py-3 text-xs text-muted-foreground">
                <div>
                  <span className="font-medium text-foreground">ID:</span> {selectedTrace.id}
                </div>
                <div>
                  <span className="font-medium text-foreground">Timestamp:</span> {formatTs(selectedTrace.timestamp)}
                </div>
                <div>
                  <span className="font-medium text-foreground">Response time:</span> {selectedTrace.response_time_ms} ms
                </div>
                <div>
                  <span className="font-medium text-foreground">Category:</span> {selectedTrace.category}
                </div>
              </div>
              <div className="py-4">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">User Message</p>
                <p className="leading-relaxed">{selectedTrace.user_message}</p>
              </div>
              <div className="py-4">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">Bot Response</p>
                <p className="leading-relaxed text-muted-foreground">
                  <MarkdownRenderer content={selectedTrace.bot_response} />
                </p>
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
