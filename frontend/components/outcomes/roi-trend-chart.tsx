"use client";

import { Bar, BarChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { BentoCard } from "@/components/dashboard/bento-card";
import { roiTrend } from "./outcomes-sample-data";

export function RoiTrendChart() {
  return (
    <BentoCard title="ROI trend preview" description="Local/demo Recharts visualization. No live revenue, payment, or attribution data." badge="Chart shell">
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={roiTrend} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.18)" />
            <XAxis dataKey="label" stroke="rgba(148, 163, 184, 0.8)" tickLine={false} axisLine={false} />
            <YAxis stroke="rgba(148, 163, 184, 0.8)" tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ background: "#0B1220", border: "1px solid #243047", borderRadius: 12 }} />
            <Bar dataKey="pipelineValue" fill="#22D3EE" name="Pipeline value" radius={[8, 8, 0, 0]} />
            <Line type="monotone" dataKey="replies" stroke="#8B5CF6" name="Replies" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </BentoCard>
  );
}
