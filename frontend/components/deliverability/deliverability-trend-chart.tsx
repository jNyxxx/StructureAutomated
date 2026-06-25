"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { BentoCard } from "@/components/dashboard/bento-card";
import { deliverabilityTrend, type DeliverabilityTrendPoint } from "./deliverability-sample-data";

export function DeliverabilityTrendChart({ trend = deliverabilityTrend }: { trend?: DeliverabilityTrendPoint[] }) {
  return (
    <BentoCard title="Deliverability trend preview" description="Local/demo chart only. No provider, DNS, or sending data source is connected." badge="Chart shell">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={trend} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.18)" />
            <XAxis dataKey="label" stroke="rgba(148, 163, 184, 0.8)" tickLine={false} axisLine={false} />
            <YAxis stroke="rgba(148, 163, 184, 0.8)" tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: "#0B1220", border: "1px solid #243047", borderRadius: 12 }} />
            <Area type="monotone" dataKey="mockSent" stackId="1" stroke="#22D3EE" fill="#22D3EE" fillOpacity={0.18} name="Mock sent" />
            <Area type="monotone" dataKey="blocked" stackId="1" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.18} name="Blocked" />
            <Area type="monotone" dataKey="suppressed" stackId="1" stroke="#EF4444" fill="#EF4444" fillOpacity={0.18} name="Suppressed" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </BentoCard>
  );
}
