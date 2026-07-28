// dashboard/src/components/BcmCenter.tsx

import React from 'react';

interface BcmCenterProps {
  rto: number; // in seconds
  rpo: number; // in seconds
  loadShedMwh: number;
  financialLoss: number;
}

export const BcmCenter: React.FC<BcmCenterProps> = ({
  rto,
  rpo,
  loadShedMwh,
  financialLoss
}) => {
  return (
    <div className="flex flex-col gap-6 w-full h-full p-4 overflow-y-auto font-mono text-xs text-scada-text">
      <div className="border border-scada-border rounded-lg bg-scada-panel p-4">
        <h2 className="text-sm font-bold text-white uppercase mb-2 tracking-widest">
          BUSINESS CONTINUITY MANAGEMENT (BCM) COMMAND CONSOLE
        </h2>
        <p className="text-[10px] text-scada-dimText">
          Evaluates dynamic grid state recovery indicators, unserved energy financial impacts, and platform SLAs.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* RTO Gauge */}
        <div className="border border-scada-border bg-scada-panel rounded-lg p-4 flex flex-col justify-between">
          <div>
            <span className="text-[10px] text-scada-dimText uppercase">Recovery Time (RTO)</span>
            <div className="text-2xl font-bold text-amber-500 mt-2">{rto.toFixed(1)}s</div>
          </div>
          <div className="mt-4 text-[9px] text-scada-dimText">Target RTO: &lt; 30.0s</div>
        </div>

        {/* RPO Gauge */}
        <div className="border border-scada-border bg-scada-panel rounded-lg p-4 flex flex-col justify-between">
          <div>
            <span className="text-[10px] text-scada-dimText uppercase">Data Recovery (RPO)</span>
            <div className="text-2xl font-bold text-emerald-500 mt-2">{rpo.toFixed(1)}s</div>
          </div>
          <div className="mt-4 text-[9px] text-scada-dimText">Target RPO: &lt; 5.0s</div>
        </div>

        {/* Load Shedding Metric */}
        <div className="border border-scada-border bg-scada-panel rounded-lg p-4 flex flex-col justify-between">
          <div>
            <span className="text-[10px] text-scada-dimText uppercase">Total Load Shed</span>
            <div className="text-2xl font-bold text-red-500 mt-2">{loadShedMwh.toFixed(2)} MWh</div>
          </div>
          <div className="mt-4 text-[9px] text-scada-dimText">Automatic FLISR Shedding active</div>
        </div>

        {/* Financial Loss Metric */}
        <div className="border border-scada-border bg-scada-panel rounded-lg p-4 flex flex-col justify-between">
          <div>
            <span className="text-[10px] text-scada-dimText uppercase">Estimated Financial Loss</span>
            <div className="text-2xl font-bold text-red-600 mt-2">${financialLoss.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
          </div>
          <div className="mt-4 text-[9px] text-scada-dimText">Calculated at $150.00 / MWh</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* SLA Tracker Card */}
        <div className="border border-scada-border bg-scada-panel rounded-lg p-4">
          <h3 className="text-xs font-bold text-white uppercase mb-4 tracking-wider">Resilience SLA Compliance</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-[10px] mb-1">
                <span>Voltage Tolerance SLA (0.95 - 1.05 pu)</span>
                <span className="text-emerald-500">99.84%</span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded overflow-hidden">
                <div className="h-full bg-emerald-500" style={{ width: '99.84%' }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[10px] mb-1">
                <span>Frequency Tolerance SLA (59.5 - 60.5 Hz)</span>
                <span className="text-emerald-500">99.91%</span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded overflow-hidden">
                <div className="h-full bg-emerald-500" style={{ width: '99.91%' }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[10px] mb-1">
                <span>Active Infrastructure Availability</span>
                <span className="text-amber-500">96.80%</span>
              </div>
              <div className="h-1.5 bg-slate-800 rounded overflow-hidden">
                <div className="h-full bg-amber-500" style={{ width: '96.8%' }}></div>
              </div>
            </div>
          </div>
        </div>

        {/* Load Shedding Cost Analysis */}
        <div className="border border-scada-border bg-scada-panel rounded-lg p-4">
          <h3 className="text-xs font-bold text-white uppercase mb-4 tracking-wider">Continuity Reconfiguration</h3>
          <div className="text-[10px] text-scada-dimText space-y-2">
            <p>
              In the event of a cyber-physical contingency, the platform coordinates GNN prediction and autonomous self-healing (FLISR). 
            </p>
            <p>
              This minimizes load-shedding duration and helps utility operators meet the strict <strong>System Average Interruption Duration Index (SAIDI)</strong> and <strong>System Average Interruption Frequency Index (SAIFI)</strong> targets.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
