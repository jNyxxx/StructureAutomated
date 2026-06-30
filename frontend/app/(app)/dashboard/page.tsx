"use client";

import { AlertCircle, BarChart3, Building2, Database, MailCheck, ShieldCheck, Sparkles, Terminal, TrendingUp, Users } from "lucide-react";
import { useState } from "react";

import { BillingStatusBadge, GateReasonBadge } from "@/components/badges";
import { ActivityPreview } from "@/components/dashboard/activity-preview";
import { BentoCard } from "@/components/dashboard/bento-card";
import { DeliverabilityOutcomesPreview } from "@/components/dashboard/deliverability-outcomes-preview";
import { FlowProgress } from "@/components/dashboard/flow-progress";
import { GateHealthPanel } from "@/components/dashboard/gate-health-panel";
import { MetricCard } from "@/components/dashboard/metric-card";
import { PipelinePreview } from "@/components/dashboard/pipeline-preview";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTenantContext } from "@/lib/tenant-context";
import { useBackendReadyStatus } from "@/lib/use-backend-status";

function PreflightNotice() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="rounded-xl border border-blue/20 bg-bluebg/15 backdrop-blur-md p-4 text-small transition-all duration-300">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-medium bg-bluebg text-blue animate-pulse">
            <Sparkles className="size-4" />
          </div>
          <div>
            <p className="font-bold text-text">Local Mock Demo Environment Active</p>
            <p className="text-caption text-muted">
              Running Phase 1 CRE cold outreach mock sandbox. All outbound operations are mock-only.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="locked" className="hidden sm:inline-flex">Production Not Enabled</Badge>
          <Button variant="secondary" size="sm" onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? "Show Safety Specs" : "Hide Safety Specs"}
          </Button>
        </div>
      </div>

      {!collapsed && (
        <div className="mt-4 grid gap-3 border-t border-border/50 pt-4 sm:grid-cols-2 lg:grid-cols-3 text-caption text-muted">
          <div className="flex gap-2">
            <ShieldCheck className="size-4 text-blue shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-text">Transactional Send Safety</p>
              <p>ResendTransactionalProvider is disabled. Cold outreach intents cannot reach Resend.</p>
            </div>
          </div>
          <div className="flex gap-2">
            <ShieldCheck className="size-4 text-blue shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-text">Stripe Fail-Closed Safety</p>
              <p>Stripe checkout and portals fail closed. Mock billing keys remain default.</p>
            </div>
          </div>
          <div className="flex gap-2">
            <ShieldCheck className="size-4 text-blue shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-text">Sandbox Compliance</p>
              <p>Suppression list filter, rate limiter, and mandatory human reviews are active.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MockVolumeChart() {
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);

  const volumeData = [
    { day: "Monday", count: 40, x: 25, y: 80, height: 40, fill: "rgba(59, 130, 246, 0.35)" },
    { day: "Tuesday", count: 70, x: 65, y: 50, height: 70, fill: "rgba(59, 130, 246, 0.35)" },
    { day: "Wednesday", count: 85, x: 105, y: 35, height: 85, fill: "rgba(59, 130, 246, 0.35)" },
    { day: "Thursday", count: 55, x: 145, y: 65, height: 55, fill: "rgba(59, 130, 246, 0.35)" },
    { day: "Friday", count: 95, x: 185, y: 25, height: 95, fill: "rgba(59, 130, 246, 0.6)" },
    { day: "Saturday", count: 30, x: 225, y: 90, height: 30, fill: "rgba(59, 130, 246, 0.2)" },
    { day: "Sunday", count: 38, x: 265, y: 82, height: 38, fill: "rgba(59, 130, 246, 0.2)" },
  ];

  return (
    <Card className="border-border/60 bg-panel/30 backdrop-blur-md relative overflow-visible">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-caption font-semibold uppercase tracking-wider text-blue">Mock Send Volume</p>
            <h3 className="text-h2 font-bold mt-1 text-text">312 <span className="text-caption text-muted font-normal font-sans">Sends</span></h3>
          </div>
          <span className="text-caption text-green flex items-center gap-0.5 font-semibold">
            <TrendingUp className="size-3" />
            +12%
          </span>
        </div>
      </CardHeader>
      <CardContent className="relative overflow-visible">
        <div className="h-32 w-full mt-2 relative overflow-visible">
          <svg className="h-full w-full overflow-visible" viewBox="0 0 300 120" preserveAspectRatio="none">
            <line x1="0" y1="20" x2="300" y2="20" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />
            <line x1="0" y1="60" x2="300" y2="60" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />
            <line x1="0" y1="100" x2="300" y2="100" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />

            {volumeData.map((bar, index) => (
              <rect
                key={bar.day}
                x={bar.x}
                y={bar.y}
                width="14"
                height={bar.height}
                rx="2.5"
                fill={hoveredBar === index ? "rgb(59, 130, 246)" : bar.fill}
                className="transition-all duration-200 cursor-pointer"
                onMouseEnter={() => setHoveredBar(index)}
                onMouseLeave={() => setHoveredBar(null)}
              />
            ))}
          </svg>

          {/* Floating Tooltip */}
          {hoveredBar !== null && (
            <div
              className="absolute z-30 rounded-medium bg-panel border border-border/80 px-2.5 py-1.5 text-caption text-text shadow-glow pointer-events-none transform -translate-x-1/2 -translate-y-[calc(100%+8px)] flex flex-col gap-0.5 transition-all duration-150"
              style={{
                left: `${((volumeData[hoveredBar].x + 7) / 300) * 100}%`,
                top: `${(volumeData[hoveredBar].y / 120) * 100}%`,
              }}
            >
              <span className="font-bold text-small text-text">{volumeData[hoveredBar].day}</span>
              <span className="text-blue font-semibold">{volumeData[hoveredBar].count} Mock Sends</span>
              <span className="text-[10px] text-muted">92% delivery rate</span>
            </div>
          )}
        </div>
        <div className="mt-2 flex justify-between text-[10px] text-muted font-medium px-2">
          <span>Mon</span>
          <span>Tue</span>
          <span>Wed</span>
          <span>Thu</span>
          <span>Fri</span>
          <span>Sat</span>
          <span>Sun</span>
        </div>
      </CardContent>
    </Card>
  );
}

function MockROIChart() {
  const [hoveredDot, setHoveredDot] = useState<number | null>(null);

  const roiData = [
    { label: "Week 1", rate: "8.5%", cx: 10, cy: 90, sends: 40, positive: 3 },
    { label: "Week 2", rate: "11.2%", cx: 90, cy: 55, sends: 70, positive: 8 },
    { label: "Week 3", rate: "13.8%", cx: 170, cy: 42, sends: 85, positive: 12 },
    { label: "Week 4", rate: "14.2%", cx: 250, cy: 22, sends: 95, positive: 14 },
    { label: "Current", rate: "14.5%", cx: 290, cy: 15, sends: 38, positive: 6 },
  ];

  return (
    <Card className="border-border/60 bg-panel/30 backdrop-blur-md relative overflow-visible">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-caption font-semibold uppercase tracking-wider text-violet">Positive Response Rate</p>
            <h3 className="text-h2 font-bold mt-1 text-text">14.2% <span className="text-caption text-muted font-normal font-sans">Mock</span></h3>
          </div>
          <span className="text-caption text-green flex items-center gap-0.5 font-semibold">
            <TrendingUp className="size-3" />
            +3.1%
          </span>
        </div>
      </CardHeader>
      <CardContent className="relative overflow-visible">
        <div className="h-32 w-full mt-2 relative overflow-visible">
          <svg className="h-full w-full overflow-visible" viewBox="0 0 300 120" preserveAspectRatio="none">
            <line x1="0" y1="20" x2="300" y2="20" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />
            <line x1="0" y1="60" x2="300" y2="60" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />
            <line x1="0" y1="100" x2="300" y2="100" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />

            <path
              d="M 10 90 Q 50 85, 90 55 T 170 42 T 250 22 T 290 15"
              fill="none"
              stroke="rgb(139, 92, 246)"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <path
              d="M 10 90 Q 50 85, 90 55 T 170 42 T 250 22 T 290 15 L 290 120 L 10 120 Z"
              fill="url(#violet-grad)"
              opacity="0.12"
            />
            <defs>
              <linearGradient id="violet-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgb(139, 92, 246)" />
                <stop offset="100%" stopColor="rgba(139, 92, 246, 0)" />
              </linearGradient>
            </defs>

            {/* Visual Dots */}
            {roiData.map((dot, index) => (
              <circle
                key={dot.label}
                cx={dot.cx}
                cy={dot.cy}
                r={hoveredDot === index ? 5 : 3.5}
                fill={hoveredDot === index ? "#ffffff" : "rgb(139, 92, 246)"}
                stroke="rgb(139, 92, 246)"
                strokeWidth={hoveredDot === index ? 2 : 0}
                className="transition-all duration-150 pointer-events-none"
              />
            ))}

            {/* Invisible Large Hover Targets */}
            {roiData.map((dot, index) => (
              <circle
                key={`target-${dot.label}`}
                cx={dot.cx}
                cy={dot.cy}
                r="14"
                fill="transparent"
                className="cursor-pointer"
                onMouseEnter={() => setHoveredDot(index)}
                onMouseLeave={() => setHoveredDot(null)}
              />
            ))}
          </svg>

          {/* Floating Tooltip */}
          {hoveredDot !== null && (
            <div
              className="absolute z-30 rounded-medium bg-panel border border-border/80 px-2.5 py-1.5 text-caption text-text shadow-glow pointer-events-none transform -translate-x-1/2 -translate-y-[calc(100%+8px)] flex flex-col gap-0.5 transition-all duration-150"
              style={{
                left: `${(roiData[hoveredDot].cx / 300) * 100}%`,
                top: `${(roiData[hoveredDot].cy / 120) * 100}%`,
              }}
            >
              <span className="font-bold text-small text-text">{roiData[hoveredDot].label}</span>
              <span className="text-violet font-semibold">{roiData[hoveredDot].rate} Response Rate</span>
              <span className="text-[10px] text-muted">{roiData[hoveredDot].positive} Positive Replies</span>
            </div>
          )}
        </div>
        <div className="mt-2 flex justify-between text-[10px] text-muted font-medium px-2">
          <span>Wk 1</span>
          <span>Wk 2</span>
          <span>Wk 3</span>
          <span>Wk 4</span>
        </div>
      </CardContent>
    </Card>
  );
}

function SystemDiagnostics() {
  const tenant = useTenantContext();
  const status = useBackendReadyStatus();

  return (
    <Card className="border-border/60 bg-panel/30 backdrop-blur-md">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Terminal className="size-4 text-muted" />
          <CardTitle className="text-small text-muted font-bold">System Diagnostics</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-caption">
        <div className="flex justify-between items-center py-1.5 border-b border-border/40">
          <span className="text-muted">Active Tenant</span>
          <span className="font-mono text-text">{tenant.selectedTenantId ? tenant.selectedTenantId.slice(0, 8) + "..." : "None"}</span>
        </div>
        <div className="flex justify-between items-center py-1.5 border-b border-border/40">
          <span className="text-muted">Database State</span>
          <span className="text-green flex items-center gap-1">
            <span className="size-1.5 rounded-pill bg-green animate-pulse" /> Healthy
          </span>
        </div>
        <div className="flex justify-between items-center py-1.5 border-b border-border/40">
          <span className="text-muted">Migrations</span>
          <span className="text-text">{status.rawStatus ? "up_to_date" : "unknown"}</span>
        </div>
        <div className="flex justify-between items-center py-1.5">
          <span className="text-muted">Rate Limiter</span>
          <span className="text-text">in_memory</span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const tenant = useTenantContext();

  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Command center"
        title="Dashboard"
        description="Local/mock MVP command center. Track prospect campaigns, AI generation, and safety gates."
        actions={
          <>
            <Badge variant="default">Local/mock MVP</Badge>
            <Badge variant="locked">Production not approved</Badge>
            {tenant.role ? <Badge variant="success">{tenant.role}</Badge> : <Badge variant="warning">Role pending</Badge>}
          </>
        }
      />

      <PreflightNotice />

      {/* Main Operational Metrics */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Total Prospects"
          value="1,280"
          description="Start from CSV intake with validation"
          icon={Building2}
          tone="default"
          status="Mock Ready"
        />
        <MetricCard
          title="AI Drafts"
          value="420"
          description="Generated structured outreach copies"
          icon={Sparkles}
          tone="default"
          status="Mock Generated"
        />
        <MetricCard
          title="Awaiting Review"
          value="8"
          description="Pending human safety approval"
          icon={Users}
          tone="warning"
          status="Action Needed"
        />
        <MetricCard
          title="Outbound Sends"
          value="312"
          description="Mock sends registered in database"
          icon={MailCheck}
          tone="success"
          status="Active"
        />
      </div>

      {/* Charts & Diagnostics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <MockVolumeChart />
        <MockROIChart />
        <SystemDiagnostics />
      </div>

      <FlowProgress />

      <div className="grid gap-4 xl:grid-cols-3">
        <GateHealthPanel />
        <PipelinePreview />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <ActivityPreview />
        <DeliverabilityOutcomesPreview />
        <QuickActions />
      </div>

    </section>
  );
}
