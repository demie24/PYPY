import React, { useState, useEffect } from 'react';
import { ShieldAlert, Zap, RefreshCw, BarChart2, Users, DollarSign } from 'lucide-react';

interface BusinessAnalyticsProps {
  token: string;
}

interface OverviewData {
  dau: number;
  mau: number;
  total_users: number;
  total_tenants: number;
  revenue_this_month: number;
  trial_count: number;
  period: string;
  generated_at: string;
}

interface RevenueData {
  chart_data: { label: string; period: string; revenue: number }[];
  total_12m: number;
}

interface UsersData {
  chart_data: { date: string; label: string; new_users: number }[];
  total_new_30d: number;
}

interface SimulationsData {
  chart_data: { date: string; label: string; simulations: number; completed: number }[];
  total_30d: number;
  completed_30d: number;
}

interface AiUsageData {
  chart_data: { date: string; label: string; messages: number }[];
  total_30d: number;
}

interface ConversionsData {
  total_tenants: number;
  paid_tenants: number;
  free_tenants: number;
  active_trials: number;
  expired_trials: number;
  conversion_rate_pct: number;
}

interface PlanDistributionData {
  plan_distribution: { plan: string; count: number; percentage: number }[];
  total_tenants: number;
}

interface TopScenariosData {
  top_scenarios: { name: string; grid_type: string; run_count: number }[];
}

export const BusinessAnalytics: React.FC<BusinessAnalyticsProps> = ({ token }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [revenue, setRevenue] = useState<RevenueData | null>(null);
  const [users, setUsers] = useState<UsersData | null>(null);
  const [simulations, setSimulations] = useState<SimulationsData | null>(null);
  const [aiUsage, setAiUsage] = useState<AiUsageData | null>(null);
  const [conversions, setConversions] = useState<ConversionsData | null>(null);
  const [plans, setPlans] = useState<PlanDistributionData | null>(null);
  const [topScenarios, setTopScenarios] = useState<TopScenariosData | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const [
        overviewRes,
        revenueRes,
        usersRes,
        simulationsRes,
        aiUsageRes,
        conversionsRes,
        plansRes,
        topScenariosRes,
      ] = await Promise.all([
        fetch('/api/analytics/overview', { headers }),
        fetch('/api/analytics/revenue', { headers }),
        fetch('/api/analytics/users', { headers }),
        fetch('/api/analytics/simulations', { headers }),
        fetch('/api/analytics/ai-usage', { headers }),
        fetch('/api/analytics/conversions', { headers }),
        fetch('/api/analytics/plan-distribution', { headers }),
        fetch('/api/analytics/top-scenarios', { headers }),
      ]);

      if (!overviewRes.ok || !revenueRes.ok || !usersRes.ok || !simulationsRes.ok || !aiUsageRes.ok || !conversionsRes.ok || !plansRes.ok || !topScenariosRes.ok) {
        throw new Error('Failed to fetch business analytics. Ensure you are logged in as admin.');
      }

      setOverview(await overviewRes.json());
      setRevenue(await revenueRes.json());
      setUsers(await usersRes.json());
      setSimulations(await simulationsRes.json());
      setAiUsage(await aiUsageRes.json());
      setConversions(await conversionsRes.json());
      setPlans(await plansRes.json());
      setTopScenarios(await topScenariosRes.json());
    } catch (err: any) {
      setError(err.message || 'An error occurred while loading analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 font-mono text-xs text-scada-dimText">
        <RefreshCw size={24} className="animate-spin text-scada-nominal mb-3" />
        <span>LOADING SAAS METRICS AND SYSTEM TELEMETRY...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-red-500/30 bg-red-950/15 rounded-lg p-6 font-mono text-xs text-center text-red-400">
        <ShieldAlert size={32} className="mx-auto text-red-500 mb-3" />
        <h3 className="font-bold text-sm uppercase mb-1">Analytics Error</h3>
        <p className="mb-4">{error}</p>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-red-500/10 border border-red-500/30 rounded text-red-400 hover:bg-red-500/25 cursor-pointer font-bold uppercase"
        >
          Retry Load
        </button>
      </div>
    );
  }

  // Calculate SVG heights and helper coordinates
  const renderRevenueChart = () => {
    if (!revenue || revenue.chart_data.length === 0) return null;
    const maxRev = Math.max(...revenue.chart_data.map(d => d.revenue), 10);
    const width = 500;
    const height = 120;
    const padding = 20;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const points = revenue.chart_data.map((d, i) => {
      const x = padding + (i / (revenue.chart_data.length - 1)) * chartWidth;
      const y = height - padding - (d.revenue / maxRev) * chartHeight;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-36 bg-black/20 border border-scada-border/40 rounded-lg p-2">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((p, idx) => (
          <line
            key={idx}
            x1={padding}
            y1={padding + p * chartHeight}
            x2={width - padding}
            y2={padding + p * chartHeight}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="1"
          />
        ))}
        {/* Trend line */}
        <polyline
          fill="none"
          stroke="#06b6d4"
          strokeWidth="2"
          points={points}
          className="drop-shadow-[0_0_8px_#06b6d4]"
        />
        {/* Area fill */}
        <path
          d={`M ${padding} ${height - padding} L ${points} L ${width - padding} ${height - padding} Z`}
          fill="url(#revGrad)"
          opacity="0.15"
        />
        {/* Data points dots */}
        {revenue.chart_data.map((d, i) => {
          const x = padding + (i / (revenue.chart_data.length - 1)) * chartWidth;
          const y = height - padding - (d.revenue / maxRev) * chartHeight;
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="3"
              fill="#06b6d4"
              className="hover:r-5 cursor-help"
            />
          );
        })}
        {/* Definitions for Gradients */}
        <defs>
          <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Axis Labels */}
        <text x={padding} y={height - 4} fill="#475569" className="text-[7px] font-mono">12M Ago</text>
        <text x={width - padding - 20} y={height - 4} fill="#475569" className="text-[7px] font-mono">Current</text>
      </svg>
    );
  };

  const renderUsageChart = () => {
    if (!simulations || !aiUsage) return null;
    const simMax = Math.max(...simulations.chart_data.map(d => d.simulations), 10);
    const aiMax = Math.max(...aiUsage.chart_data.map(d => d.messages), 10);
    const maxVal = Math.max(simMax, aiMax);

    const width = 500;
    const height = 120;
    const padding = 20;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const simPoints = simulations.chart_data.map((d, i) => {
      const x = padding + (i / (simulations.chart_data.length - 1)) * chartWidth;
      const y = height - padding - (d.simulations / maxVal) * chartHeight;
      return `${x},${y}`;
    }).join(' ');

    const aiPoints = aiUsage.chart_data.map((d, i) => {
      const x = padding + (i / (aiUsage.chart_data.length - 1)) * chartWidth;
      const y = height - padding - (d.messages / maxVal) * chartHeight;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-36 bg-black/20 border border-scada-border/40 rounded-lg p-2">
        {/* Grid lines */}
        {[0, 0.5, 1].map((p, idx) => (
          <line
            key={idx}
            x1={padding}
            y1={padding + p * chartHeight}
            x2={width - padding}
            y2={padding + p * chartHeight}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="1"
          />
        ))}
        {/* Simulation Line */}
        <polyline
          fill="none"
          stroke="#6366f1"
          strokeWidth="1.5"
          points={simPoints}
          className="drop-shadow-[0_0_6px_#6366f1]"
        />
        {/* AI Msg Line */}
        <polyline
          fill="none"
          stroke="#10b981"
          strokeWidth="1.5"
          points={aiPoints}
          className="drop-shadow-[0_0_6px_#10b981]"
        />
        {/* Axis Labels */}
        <text x={padding} y={height - 4} fill="#475569" className="text-[7px] font-mono">30D Ago</text>
        <text x={width - padding - 20} y={height - 4} fill="#475569" className="text-[7px] font-mono">Today</text>
      </svg>
    );
  };

  return (
    <div className="flex flex-col gap-6 w-full font-mono text-xs text-scada-text bg-scada-bg">
      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { title: 'DAU (Daily Active)', value: overview?.dau ?? 0, icon: <Users size={16} className="text-cyan-400" /> },
          { title: 'MAU (Monthly Active)', value: overview?.mau ?? 0, icon: <Users size={16} className="text-indigo-400" /> },
          { title: 'Total Users', value: overview?.total_users ?? 0, icon: <Users size={16} className="text-purple-400" /> },
          { title: 'Total Tenants', value: overview?.total_tenants ?? 0, icon: <Zap size={16} className="text-amber-400" /> },
          { title: 'Monthly Revenue', value: `RM ${overview?.revenue_this_month?.toFixed(2) ?? '0.00'}`, icon: <DollarSign size={16} className="text-emerald-400" /> },
          { title: 'Active Trials', value: overview?.trial_count ?? 0, icon: <BarChart2 size={16} className="text-pink-400" /> },
        ].map((item, idx) => (
          <div key={idx} className="border border-scada-border bg-scada-panel p-4 rounded-lg flex flex-col gap-1 shadow-md">
            <div className="flex justify-between items-center text-scada-dimText text-[9px] uppercase tracking-wider">
              <span>{item.title}</span>
              {item.icon}
            </div>
            <div className="text-lg font-bold text-white mt-1">{item.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Financial & User growth charts */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="border border-scada-border bg-scada-panel p-4 rounded-lg">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">12M Revenue Trend</h3>
              <span className="text-[10px] text-cyan-400 font-bold">Total (12M): RM {revenue?.total_12m?.toFixed(2) ?? '0.00'}</span>
            </div>
            {renderRevenueChart()}
          </div>

          <div className="border border-scada-border bg-scada-panel p-4 rounded-lg">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">Usage Activity (Last 30 Days)</h3>
              <div className="flex gap-4 text-[9px]">
                <span className="text-indigo-400 font-bold">● Simulations ({simulations?.total_30d ?? 0})</span>
                <span className="text-emerald-400 font-bold">● AI Prompts ({aiUsage?.total_30d ?? 0})</span>
              </div>
            </div>
            {renderUsageChart()}
          </div>
        </div>

        {/* Right Column - Distributions & Ratios */}
        <div className="flex flex-col gap-6">
          {/* Conversion Box */}
          <div className="border border-scada-border bg-scada-panel p-4 rounded-lg">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-4">Trial & Conversion Rate</h3>
            <div className="flex flex-col items-center justify-center p-2">
              <div className="relative w-24 h-24 flex items-center justify-center border-4 border-scada-border rounded-full mb-3">
                <span className="text-xl font-bold text-white">{conversions?.conversion_rate_pct ?? 0}%</span>
                <div className="absolute inset-0 rounded-full border-4 border-emerald-500 border-t-transparent border-r-transparent animate-pulse"></div>
              </div>
              <div className="w-full space-y-2 mt-2">
                <div className="flex justify-between text-[10px] border-b border-scada-border/30 pb-1">
                  <span className="text-scada-dimText">Paid Subscriptions</span>
                  <span className="text-white font-bold">{conversions?.paid_tenants ?? 0}</span>
                </div>
                <div className="flex justify-between text-[10px] border-b border-scada-border/30 pb-1">
                  <span className="text-scada-dimText">Free Tier Accounts</span>
                  <span className="text-white font-bold">{conversions?.free_tenants ?? 0}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-scada-dimText">Active Trials</span>
                  <span className="text-white font-bold">{conversions?.active_trials ?? 0}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Plan Distribution */}
          <div className="border border-scada-border bg-scada-panel p-4 rounded-lg">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-4">Plan Distribution</h3>
            <div className="space-y-3">
              {plans?.plan_distribution.map((p, idx) => {
                const planColor = p.plan === 'enterprise' ? 'bg-purple-500' : p.plan === 'academic_premium' ? 'bg-amber-500' : p.plan === 'research_lab' ? 'bg-blue-500' : 'bg-slate-500';
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-[10px] uppercase font-bold text-scada-dimText">
                      <span>{p.plan.replace('_', ' ')}</span>
                      <span className="text-white">{p.count} ({p.percentage}%)</span>
                    </div>
                    <div className="h-2 bg-black/30 rounded overflow-hidden">
                      <div className={`h-full ${planColor}`} style={{ width: `${p.percentage}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Scenario & User List Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-scada-border bg-scada-panel p-4 rounded-lg">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-4">Top Run Simulations</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-scada-border/40 text-scada-dimText text-[9px]">
                  <th className="py-2 px-1">Scenario Name</th>
                  <th className="py-2 px-1">Grid Topology</th>
                  <th className="py-2 px-1 text-right">Execution Count</th>
                </tr>
              </thead>
              <tbody>
                {topScenarios?.top_scenarios.map((sc, idx) => (
                  <tr key={idx} className="border-b border-scada-border/20 text-white">
                    <td className="py-2.5 px-1 font-bold">{sc.name}</td>
                    <td className="py-2.5 px-1 uppercase text-cyan-400 font-bold">{sc.grid_type}</td>
                    <td className="py-2.5 px-1 text-right text-emerald-400 font-bold">{sc.run_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="border border-scada-border bg-scada-panel p-4 rounded-lg flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2">Registration Activity</h3>
            <p className="text-[10px] text-scada-dimText mb-4">Registrations from researchers and academic partners (30 days total: {users?.total_new_30d ?? 0})</p>
          </div>
          <div className="flex items-end justify-between gap-1 h-32 bg-black/20 p-3 border border-scada-border/30 rounded-lg">
            {users?.chart_data.map((d, i) => {
              const maxUsers = Math.max(...users.chart_data.map(x => x.new_users), 1);
              const heightPct = (d.new_users / maxUsers) * 100;
              return (
                <div key={i} className="flex-1 flex flex-col items-center group">
                  <div
                    className="w-full bg-cyan-500/60 hover:bg-cyan-400 transition-all rounded-t-sm"
                    style={{ height: `${Math.max(heightPct, 3)}%` }}
                    title={`${d.date}: ${d.new_users} users`}
                  ></div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
