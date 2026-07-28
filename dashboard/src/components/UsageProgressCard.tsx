// dashboard/src/components/UsageProgressCard.tsx
import React from 'react';
import { Cpu, Database, MessageSquare } from 'lucide-react';

interface UsageMetricsProps {
  planTier: string;
  daysRemaining: number;
  simulationsRun: number;
  aiMessagesUsed: number;
  storageUsedMb: number;
  subscriptionStatus: string;
}

export const UsageProgressCard: React.FC<UsageMetricsProps> = ({
  planTier,
  daysRemaining,
  simulationsRun,
  aiMessagesUsed,
  storageUsedMb,
  subscriptionStatus,
}) => {
  // Free tier has limits: 10 simulations, 10 AI prompts, 50MB storage
  const limits = {
    free: { sims: 10, ai: 10, storage: 50.0 },
    academic_premium: { sims: 100, ai: 9999, storage: 1000.0 },
    enterprise: { sims: 9999, ai: 9999, storage: 10000.0 },
  }[planTier.toLowerCase()] || { sims: 10, ai: 10, storage: 50.0 };

  const getPercent = (value: number, limit: number) => {
    return Math.min(100, Math.round((value / limit) * 100));
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl max-w-md w-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">Current Plan</span>
          <h2 className="text-2xl font-bold text-white capitalize mt-1">{planTier.replace('_', ' ')}</h2>
        </div>
        <div className="text-right">
          <span className="text-xs text-slate-400">Status</span>
          <div className="text-sm font-semibold text-emerald-400 capitalize mt-1">{subscriptionStatus}</div>
        </div>
      </div>

      <div className="mb-4 text-sm text-slate-300">
        Time remaining: <span className="font-semibold text-white">{daysRemaining} days</span>
      </div>

      <div className="space-y-6">
        {/* Simulations progress */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="flex items-center gap-2 text-slate-300">
              <Cpu className="w-4 h-4 text-blue-400" /> Simulation Runs
            </span>
            <span className="font-semibold">{simulationsRun} / {limits.sims === 9999 ? 'Unlimited' : limits.sims}</span>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-blue-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${getPercent(simulationsRun, limits.sims)}%` }}
            />
          </div>
        </div>

        {/* AI copilot progress */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="flex items-center gap-2 text-slate-300">
              <MessageSquare className="w-4 h-4 text-purple-400" /> AI Copilot Prompts
            </span>
            <span className="font-semibold">{aiMessagesUsed} / {limits.ai === 9999 ? 'Unlimited' : limits.ai}</span>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-purple-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${getPercent(aiMessagesUsed, limits.ai)}%` }}
            />
          </div>
        </div>

        {/* Storage progress */}
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="flex items-center gap-2 text-slate-300">
              <Database className="w-4 h-4 text-amber-400" /> Storage Capacity
            </span>
            <span className="font-semibold">{storageUsedMb.toFixed(1)} / {limits.storage} MB</span>
          </div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-amber-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${getPercent(storageUsedMb, limits.storage)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
