'use client';

import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const tooltipStyle = { backgroundColor: '#0b1727', border: '1px solid #20334b', borderRadius: 8, color: '#e5edf7' };

export function TrendChart({ data, dataKey, secondaryKey, color = '#60a5fa', height = 250 }: { data: Record<string, unknown>[]; dataKey: string; secondaryKey?: string; color?: string; height?: number }) {
  return <ResponsiveContainer width="100%" height={height}><LineChart data={data} margin={{ top: 10, right: 12, left: -18, bottom: 0 }}><CartesianGrid stroke="#20334b" strokeDasharray="3 3" /><XAxis dataKey="period" stroke="#64748b" fontSize={10} tickFormatter={(value) => String(value).slice(5)} /><YAxis stroke="#64748b" fontSize={10} /><Tooltip contentStyle={tooltipStyle} /><Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} /><>{secondaryKey && <Line type="monotone" dataKey={secondaryKey} stroke="#f59e0b" strokeWidth={2} dot={false} />}</></LineChart></ResponsiveContainer>;
}

export function BarMetricChart({ data, nameKey, dataKey, color = '#60a5fa', height = 250 }: { data: Record<string, unknown>[]; nameKey: string; dataKey: string; color?: string; height?: number }) {
  return <ResponsiveContainer width="100%" height={height}><BarChart data={data} layout="vertical" margin={{ top: 4, right: 18, left: 20, bottom: 4 }}><CartesianGrid stroke="#20334b" strokeDasharray="3 3" horizontal={false} /><XAxis type="number" stroke="#64748b" fontSize={10} /><YAxis type="category" dataKey={nameKey} stroke="#94a3b8" fontSize={10} width={90} /><Tooltip contentStyle={tooltipStyle} /><Bar dataKey={dataKey} fill={color} radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer>;
}

export function DonutChart({ data, nameKey, dataKey, height = 250 }: { data: Record<string, unknown>[]; nameKey: string; dataKey: string; height?: number }) {
  const colors = ['#60a5fa', '#f59e0b', '#f97316', '#ef4444', '#34d399'];
  return <ResponsiveContainer width="100%" height={height}><PieChart><Tooltip contentStyle={tooltipStyle} /><Pie data={data} dataKey={dataKey} nameKey={nameKey} innerRadius={55} outerRadius={82} paddingAngle={3}>{data.map((entry, index) => <Cell key={`${String(entry[nameKey])}-${index}`} fill={colors[index % colors.length]} />)}</Pie></PieChart></ResponsiveContainer>;
}
