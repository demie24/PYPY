// dashboard/src/components/SaaSAdmin.tsx

import React, { useState } from 'react';
import { Shield, ArrowUpRight, ArrowDownRight, BarChart2, Settings } from 'lucide-react';
import { BusinessAnalytics } from './BusinessAnalytics.tsx';

interface TenantPlanOverride {
  id: string;
  name: string;
  subdomain: string;
  plan_tier: string;
}

interface SaaSAdminProps {
  tenants: TenantPlanOverride[];
  onOverridePlan: (tenantId: string, newTier: string) => void;
  token: string;
}

export const SaaSAdmin: React.FC<SaaSAdminProps> = ({
  tenants,
  onOverridePlan,
  token
}) => {
  const [tab, setTab] = useState<'analytics' | 'controls'>('analytics');

  return (
    <div className="flex flex-col gap-6 w-full h-full p-4 overflow-y-auto font-mono text-xs text-scada-text bg-scada-bg">
      <div className="border border-scada-border rounded-lg bg-scada-panel p-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <Shield size={20} className="text-amber-500" />
          <div>
            <h2 className="text-sm font-bold text-white uppercase mb-2 tracking-widest">
              SAAS SYSTEM ADMINISTRATION PANEL
            </h2>
            <p className="text-[10px] text-scada-dimText">
              Manual tenant configuration, plan tier overrides, and SaaS metrics analytics hub.
            </p>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-2 bg-black/40 p-1 border border-scada-border/60 rounded">
          <button
            onClick={() => setTab('analytics')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold uppercase transition-all cursor-pointer ${
              tab === 'analytics' ? 'bg-cyan-500 text-black' : 'text-scada-dimText hover:text-white'
            }`}
          >
            <BarChart2 size={12} /> System Analytics
          </button>
          <button
            onClick={() => setTab('controls')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold uppercase transition-all cursor-pointer ${
              tab === 'controls' ? 'bg-cyan-500 text-black' : 'text-scada-dimText hover:text-white'
            }`}
          >
            <Settings size={12} /> Tenant Controls
          </button>
        </div>
      </div>

      {tab === 'analytics' ? (
        <BusinessAnalytics token={token} />
      ) : (
        <div className="border border-scada-border bg-scada-panel rounded-lg p-4">
          <h3 className="text-xs font-bold text-white uppercase mb-4 tracking-wider">Tenant Directory & Override Controls</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-scada-border/60 text-scada-dimText text-[10px]">
                  <th className="py-2.5 px-3">Tenant Name</th>
                  <th className="py-2.5 px-3">Subdomain</th>
                  <th className="py-2.5 px-3">Plan Tier</th>
                  <th className="py-2.5 px-3 text-right">Actions Override</th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((t) => (
                  <tr key={t.id} className="border-b border-scada-border/30 hover:bg-slate-800/20 text-white">
                    <td className="py-3 px-3 font-bold">{t.name}</td>
                    <td className="py-3 px-3 text-scada-dimText">{t.subdomain}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                        t.plan_tier === 'enterprise' ? 'bg-purple-500/10 text-purple-500 border border-purple-500/20' :
                        t.plan_tier === 'academic_premium' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' :
                        'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                      }`}>
                        {t.plan_tier}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right space-x-2">
                      {t.plan_tier !== 'free' && (
                        <button 
                          onClick={() => onOverridePlan(t.id, 'free')}
                          className="px-2.5 py-1 bg-red-950/20 hover:bg-red-900/30 text-red-500 font-bold border border-red-500/30 rounded text-[9px] cursor-pointer inline-flex items-center gap-1"
                        >
                          <ArrowDownRight size={10} /> Downgrade to Free
                        </button>
                      )}
                      {t.plan_tier !== 'academic_premium' && (
                        <button 
                          onClick={() => onOverridePlan(t.id, 'academic_premium')}
                          className="px-2.5 py-1 bg-amber-500/10 hover:bg-amber-500/35 text-amber-500 font-bold border border-amber-500/30 rounded text-[9px] cursor-pointer inline-flex items-center gap-1"
                        >
                          <ArrowUpRight size={10} /> Upgrade Premium
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

