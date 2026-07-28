import React, { useEffect, useState } from "react";
import { 
  Activity, Cpu, Server, Clock, CheckCircle, 
  AlertCircle, Trash2, RefreshCw, Database, PlayCircle
} from "lucide-react";

interface SimulationQueueMonitorProps {
  token: string;
}

interface QueueStatus {
  active_workers: number;
  running_jobs: number;
  queued_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
}

interface WorkerStatus {
  worker_id: string;
  last_heartbeat: string;
  active_tasks: number;
  cpu_usage: number;
  memory_usage: number;
  status: "ONLINE" | "BUSY" | "OFFLINE";
}

interface Job {
  id: string;
  scenario_id: string;
  status: string;
  progress_percentage: number;
  started_at: string | null;
  stopped_at: string | null;
  grid_name: string;
}

interface AuditLog {
  action: string;
  timestamp: string;
  actor: string;
  details: string;
}

export const SimulationQueueMonitor: React.FC<SimulationQueueMonitorProps> = ({ token }) => {
  const [status, setStatus] = useState<QueueStatus>({
    active_workers: 0,
    running_jobs: 0,
    queued_jobs: 0,
    completed_jobs: 0,
    failed_jobs: 0
  });
  
  const [workers, setWorkers] = useState<WorkerStatus[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const fetchQueueData = async () => {
    try {
      const headers = { "Authorization": `Bearer ${token}` };
      
      // 1. Fetch queue counts
      const resStatus = await fetch("/api/simulation/queue/status", { headers });
      if (resStatus.ok) {
        const data = await resStatus.json();
        setStatus(data);
      }
      
      // 2. Fetch workers
      const resWorkers = await fetch("/api/workers/status", { headers });
      if (resWorkers.ok) {
        const data = await resWorkers.json();
        setWorkers(data);
      }
      
      // 3. Fetch jobs list
      const resJobs = await fetch("/api/simulation/jobs", { headers });
      if (resJobs.ok) {
        const data = await resJobs.json();
        setJobs(data);
        
        // Auto-select first running job if none selected
        if (data.length > 0 && !selectedJobId) {
          setSelectedJobId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Error fetching queue monitoring data:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditLogs = async (jobId: string) => {
    try {
      const res = await fetch(`/api/simulation/audit/${jobId}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data);
      }
    } catch (err) {
      console.error("Error fetching job audits:", err);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    if (!window.confirm("Are you sure you want to stop this simulation run?")) return;
    setCancellingId(jobId);
    try {
      const res = await fetch(`/api/simulation/${jobId}/cancel`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });
      if (res.ok) {
        alert("Simulation run cancellation request sent.");
        fetchQueueData();
      } else {
        const err = await res.json();
        alert(`Failed to cancel: ${err.detail || "Unknown error"}`);
      }
    } catch (err) {
      console.error("Error cancelling simulation:", err);
    } finally {
      setCancellingId(null);
    }
  };

  useEffect(() => {
    fetchQueueData();
    const interval = setInterval(fetchQueueData, 5000);
    return () => clearInterval(interval);
  }, [token]);

  useEffect(() => {
    if (selectedJobId) {
      fetchAuditLogs(selectedJobId);
    } else {
      setAuditLogs([]);
    }
  }, [selectedJobId, jobs]);

  return (
    <div className="space-y-6 text-[#E5E7EB]">
      {/* Overview stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-lg flex items-center justify-between shadow-lg">
          <div>
            <span className="text-xs text-[#9CA3AF] uppercase font-semibold">Active Workers</span>
            <div className="text-2xl font-bold text-blue-400 mt-1">{status.active_workers}</div>
          </div>
          <Server className="text-blue-400 w-8 h-8 opacity-75" />
        </div>
        
        <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-lg flex items-center justify-between shadow-lg">
          <div>
            <span className="text-xs text-[#9CA3AF] uppercase font-semibold">Running Jobs</span>
            <div className="text-2xl font-bold text-amber-500 mt-1">{status.running_jobs}</div>
          </div>
          <Activity className="text-amber-500 w-8 h-8 animate-pulse opacity-75" />
        </div>

        <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-lg flex items-center justify-between shadow-lg">
          <div>
            <span className="text-xs text-[#9CA3AF] uppercase font-semibold">Queued Tasks</span>
            <div className="text-2xl font-bold text-indigo-400 mt-1">{status.queued_jobs}</div>
          </div>
          <Clock className="text-indigo-400 w-8 h-8 opacity-75" />
        </div>

        <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-lg flex items-center justify-between shadow-lg">
          <div>
            <span className="text-xs text-[#9CA3AF] uppercase font-semibold">Completed</span>
            <div className="text-2xl font-bold text-emerald-500 mt-1">{status.completed_jobs}</div>
          </div>
          <CheckCircle className="text-emerald-500 w-8 h-8 opacity-75" />
        </div>

        <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-lg flex items-center justify-between col-span-2 lg:col-span-1 shadow-lg">
          <div>
            <span className="text-xs text-[#9CA3AF] uppercase font-semibold">Failed</span>
            <div className="text-2xl font-bold text-rose-500 mt-1">{status.failed_jobs}</div>
          </div>
          <AlertCircle className="text-rose-500 w-8 h-8 opacity-75" />
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Side: Recent & Active Jobs */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-5 xl:col-span-2 shadow-xl flex flex-col space-y-4">
          <div className="flex items-center justify-between border-b border-[#1F2937] pb-3">
            <h3 className="font-bold text-lg text-white flex items-center gap-2">
              <PlayCircle className="text-emerald-400 w-5 h-5" />
              Active & Recent Simulation Jobs
            </h3>
            <button 
              onClick={fetchQueueData}
              className="text-[#9CA3AF] hover:text-white transition flex items-center gap-1 text-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Sync
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20 text-[#9CA3AF]">
              <span className="animate-spin mr-2">&#9696;</span> Loading simulations...
            </div>
          ) : jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-[#9CA3AF]">
              <Database className="w-12 h-12 text-[#374151] mb-2" />
              No simulation jobs recorded. Launch one from the Cyber Range!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase text-[#9CA3AF] border-b border-[#1F2937]">
                    <th className="py-3 px-2">Job ID</th>
                    <th className="py-3 px-2">Grid</th>
                    <th className="py-3 px-2">Status</th>
                    <th className="py-3 px-2">Progress</th>
                    <th className="py-3 px-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1F2937]">
                  {jobs.map((job) => {
                    const isRunning = job.status === "RUNNING";
                    const isCompleted = job.status === "COMPLETED";
                    const isFailed = job.status === "FAILED";
                    
                    return (
                      <tr 
                        key={job.id} 
                        onClick={() => setSelectedJobId(job.id)}
                        className={`hover:bg-[#1f2937]/30 transition cursor-pointer ${selectedJobId === job.id ? "bg-[#1f2937]/50" : ""}`}
                      >
                        <td className="py-3.5 px-2 font-mono text-xs text-slate-400">
                          {job.id.substring(0, 8)}...
                        </td>
                        <td className="py-3.5 px-2 font-semibold text-white">
                          {job.grid_name}
                        </td>
                        <td className="py-3.5 px-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                            isRunning ? "bg-amber-500/10 text-amber-500 border border-amber-500/20" :
                            isCompleted ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" :
                            isFailed ? "bg-rose-500/10 text-rose-500 border border-rose-500/20" :
                            "bg-slate-500/10 text-slate-500 border border-slate-500/20"
                          }`}>
                            {job.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-2 w-48">
                          <div className="flex items-center gap-2">
                            <div className="w-full bg-[#1F2937] rounded-full h-2 overflow-hidden">
                              <div 
                                className={`h-full rounded-full transition-all duration-500 ${
                                  isFailed ? "bg-rose-500" :
                                  isCompleted ? "bg-emerald-500" :
                                  "bg-blue-500"
                                }`}
                                style={{ width: `${job.progress_percentage}%` }}
                              />
                            </div>
                            <span className="text-xs text-[#9CA3AF] font-bold">{job.progress_percentage}%</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-2 text-right">
                          {isRunning && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCancelJob(job.id);
                              }}
                              disabled={cancellingId === job.id}
                              className="text-rose-500 hover:text-rose-400 font-semibold p-1 hover:bg-rose-500/10 rounded transition"
                              title="Stop Simulation"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Side: Worker status + Audit Timeline */}
        <div className="space-y-6">
          
          {/* Worker heartbeats */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-5 shadow-xl">
            <h3 className="font-bold text-lg text-white mb-4 border-b border-[#1F2937] pb-3 flex items-center gap-2">
              <Cpu className="text-blue-400 w-5 h-5" />
              Simulation Worker Cluster Status
            </h3>
            
            {workers.length === 0 ? (
              <div className="text-center py-6 text-[#9CA3AF] text-sm">
                No active workers reported. Heartbeats pending...
              </div>
            ) : (
              <div className="space-y-4">
                {workers.map((worker) => {
                  const isBusy = worker.status === "BUSY";
                  const isOffline = worker.status === "OFFLINE";
                  
                  return (
                    <div key={worker.worker_id} className="bg-[#1f2937]/20 border border-[#1F2937] p-3 rounded-md space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-semibold text-slate-300">
                          {worker.worker_id.substring(0, 22)}...
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                          isOffline ? "bg-rose-500/10 text-rose-500 border border-rose-500/20" :
                          isBusy ? "bg-amber-500/10 text-amber-500 border border-amber-500/20" :
                          "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                        }`}>
                          {worker.status}
                        </span>
                      </div>
                      
                      {!isOffline && (
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div>
                            <span className="text-[#9CA3AF] block mb-1">CPU Load</span>
                            <div className="flex items-center gap-1.5 font-mono text-white">
                              <div className="w-16 bg-[#1F2937] h-1.5 rounded-full overflow-hidden">
                                <div className="bg-blue-500 h-full" style={{ width: `${worker.cpu_usage}%` }} />
                              </div>
                              {worker.cpu_usage.toFixed(0)}%
                            </div>
                          </div>
                          <div>
                            <span className="text-[#9CA3AF] block mb-1">Memory</span>
                            <div className="flex items-center gap-1.5 font-mono text-white">
                              <div className="w-16 bg-[#1F2937] h-1.5 rounded-full overflow-hidden">
                                <div className="bg-purple-500 h-full" style={{ width: `${worker.memory_usage}%` }} />
                              </div>
                              {worker.memory_usage.toFixed(0)}%
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Audit Logs */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-5 shadow-xl">
            <h3 className="font-bold text-lg text-white mb-4 border-b border-[#1F2937] pb-3 flex items-center gap-2">
              <Database className="text-purple-400 w-5 h-5" />
              Job Execution Audit Log
            </h3>
            
            {!selectedJobId ? (
              <div className="text-center py-10 text-[#9CA3AF] text-sm">
                Select a job from the table to inspect details.
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="text-center py-10 text-[#9CA3AF] text-sm">
                No audit entries for this job.
              </div>
            ) : (
              <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1">
                {auditLogs.map((log, index) => (
                  <div key={index} className="relative pl-5 border-l-2 border-[#1F2937] last:pb-0 pb-4 text-xs">
                    {/* Node circle */}
                    <div className="absolute -left-1.5 top-1 bg-purple-500 w-3.5 h-3.5 rounded-full border-4 border-[#111827]" />
                    <div className="flex items-center justify-between text-[#9CA3AF] mb-1">
                      <span className="font-bold text-purple-400">{log.action}</span>
                      <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="text-slate-300 font-mono text-[11px] mb-0.5">
                      Actor: {log.actor}
                    </div>
                    <div className="text-slate-400 text-[11px]">
                      {log.details}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
};
