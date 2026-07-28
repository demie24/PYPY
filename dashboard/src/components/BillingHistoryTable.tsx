// dashboard/src/components/BillingHistoryTable.tsx
import React from 'react';
import { CreditCard } from 'lucide-react';

interface Invoice {
  id: string;
  planName: string;
  amount: number;
  paymentProvider: string;
  paymentReference: string;
  startedAt: string;
  status: string;
}

interface BillingHistoryProps {
  invoices: Invoice[];
}

export const BillingHistoryTable: React.FC<BillingHistoryProps> = ({ invoices }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl w-full">
      <div className="flex items-center gap-2 mb-6">
        <CreditCard className="w-5 h-5 text-cyan-400" />
        <h2 className="text-xl font-bold text-white">Billing & Invoice History</h2>
      </div>

      {invoices.length === 0 ? (
        <div className="text-center py-8 text-slate-400 text-sm">
          No billing transactions found.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                <th className="pb-3 pr-4">Plan Name</th>
                <th className="pb-3 px-4">Date</th>
                <th className="pb-3 px-4">Reference</th>
                <th className="pb-3 px-4">Amount</th>
                <th className="pb-3 px-4">Method</th>
                <th className="pb-3 pl-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors text-slate-300">
                  <td className="py-4 pr-4 font-semibold text-white capitalize">{inv.planName.replace('_', ' ')}</td>
                  <td className="py-4 px-4">{new Date(inv.startedAt).toLocaleDateString()}</td>
                  <td className="py-4 px-4 font-mono text-xs">{inv.paymentReference}</td>
                  <td className="py-4 px-4 font-bold text-white">${inv.amount.toFixed(2)}</td>
                  <td className="py-4 px-4 capitalize">{inv.paymentProvider}</td>
                  <td className="py-4 pl-4">
                    <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase ${
                      inv.status === 'active' || inv.status === 'trial'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}>
                      {inv.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
