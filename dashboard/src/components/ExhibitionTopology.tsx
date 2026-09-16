import { useEffect, useState } from 'react';

// Presentation coordinates only; assets and electrical connectivity come from the API.
const positions = [[1359,753],[1161,705],[1165,592],[1294,503],[1520,506],[1695,435],[1832,515],[1678,581],[1703,685],[1505,254],[1668,329],[1494,313],[1314,311],[1186,401],[963,386],[740,410],[772,520],[969,553],[517,431],[308,466],[752,303],[678,201],[517,238],[621,333],[964,758],[747,730],[697,623],[561,764],[638,823],[1211,803],[1900,405],[1585,162],[350,374],[100,461],[655,100],[357,173],[979,865],[509,900],[1567,763]];

export function ExhibitionTopology({ telemetry, live, grid, recoveredTarget }: { telemetry: any; live: boolean; grid: string; recoveredTarget?: string }) {
  const [topology, setTopology] = useState<any>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState('');
  useEffect(() => {
    const abort = new AbortController();
    setTopology(null); setError('');
    const timeout = window.setTimeout(() => abort.abort(), 10000);
    fetch(`${location.protocol}//${location.hostname || 'localhost'}:8000/api/telemetry/topology?grid_name=${encodeURIComponent(grid)}`, { signal: abort.signal })
      .then(r => { if (!r.ok) throw new Error(`Topology request failed (${r.status})`); return r.json(); })
      .then(data => { if (!data.buses || !Array.isArray(data.lines)) throw new Error('Topology schema unavailable'); setTopology(data); })
      .catch(e => { setError(e.name === 'AbortError' ? 'Topology request timed out' : e.message); })
      .finally(() => window.clearTimeout(timeout));
    return () => { window.clearTimeout(timeout); abort.abort(); };
  }, [grid, retry]);
  if (!topology) return <div className="ex-empty"><strong>{error || 'Connecting to the Digital Twin'}</strong><p>Electrical connections appear when the topology service responds.</p>{error && <button onClick={() => setRetry(v => v + 1)}>Retry topology</button>}</div>;
  const ids = Object.keys(topology.buses);
  const coord = (id: string) => {
    const index = ids.indexOf(id);
    const point = grid.toLowerCase() === 'ieee39' ? positions[Number(id.replace('Bus_', '')) - 1] : null;
    const raw = point || [1000 + 750 * Math.cos(index * Math.PI * 2 / ids.length), 500 + 360 * Math.sin(index * Math.PI * 2 / ids.length)];
    return [raw[0], raw[1] * .62 + 20];
  };
  const state = telemetry?.state || {};
  const compromised = live ? telemetry?.attack_status?.compromised_nodes || {} : {};
  const bus = state.buses?.[selected];
  return <div className={`ex-map ${live ? '' : 'ex-map-stale'}`}>
    <svg viewBox="0 0 2000 650" role="group" aria-label={`${grid.toUpperCase()} live electrical topology. Select a bus to inspect.`}>
      <defs><pattern id="ex-grid" width="48" height="48" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1.2" fill="#b8dbe3" /></pattern></defs>
      <rect width="2000" height="650" fill="url(#ex-grid)" />
      {topology.lines.map((line: any) => {
        if (!ids.includes(line.from_bus) || !ids.includes(line.to_bus)) return null;
        const [x1,y1] = coord(line.from_bus); const [x2,y2] = coord(line.to_bus);
        const breaker = state.breakers?.[line.id]; const power = state.lines?.[line.id]?.active_power_flow;
        const tone = !live ? 'idle' : compromised[line.id] ? 'danger' : breaker === 'OPEN' ? 'warning' : recoveredTarget === line.id ? 'safe' : breaker === 'CLOSED' ? 'info' : 'idle';
        return <g key={line.id} className={`ex-${tone}`}><title>{line.id}: {live ? breaker || 'Unknown' : 'Telemetry unavailable'}{live && typeof power === 'number' ? ` · ${power.toFixed(1)} MW` : ''}</title><line x1={x1} y1={y1} x2={x2} y2={y2} className="ex-wire" strokeDasharray={breaker === 'OPEN' ? '12 10' : undefined}/>{live && breaker === 'CLOSED' && typeof power === 'number' && Math.abs(power) > 1 && <line x1={x1} y1={y1} x2={x2} y2={y2} className={`ex-flow ${power < 0 ? 'reverse' : ''}`} />}{live && breaker === 'OPEN' && <text x={(x1+x2)/2} y={(y1+y2)/2} className="ex-open-label">OPEN</text>}</g>;
      })}
      {ids.map(id => {
        const [x,y] = coord(id); const meta = topology.buses[id]; const v = state.buses?.[id]?.voltage_pu;
        const tone = !live || typeof v !== 'number' ? 'idle' : compromised[id] ? 'danger' : v < .2 ? 'idle' : v < .95 || v > 1.05 ? 'warning' : 'safe';
        return <g key={id} className={`ex-bus ex-${tone}`} transform={`translate(${x} ${y})`} role="button" tabIndex={0} aria-label={`${id}, ${meta.is_gen ? 'generator' : meta.is_load ? 'load' : 'junction'}, ${live && typeof v === 'number' ? `${v.toFixed(3)} per unit` : 'unavailable'}${compromised[id] ? ', compromised' : ''}`} onClick={() => setSelected(id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') {e.preventDefault();setSelected(id);} }}>
          {compromised[id] && <circle r="37" className="ex-node-halo"/>}
          {meta.is_gen ? <rect x="-23" y="-23" width="46" height="46" rx="12"/> : <circle r="19"/>}
          <text className="ex-node-symbol" y="7">{compromised[id] ? '!' : meta.is_gen ? 'G' : meta.is_load ? '↓' : '·'}</text>
          <text className="ex-node-label" y={['Bus_22','Bus_20','Bus_16','Bus_30'].includes(id) ? 46 : -34}>{id.replace('Bus_', 'B')}</text>
        </g>;
      })}
    </svg>
    <div className="ex-inspector" aria-live="polite">{selected ? <><strong>{selected.replace('_', ' ')}</strong><span>{live && typeof bus?.voltage_pu === 'number' ? `${bus.voltage_pu.toFixed(3)} p.u.` : 'Telemetry unavailable'}</span><button aria-label="Close bus details" onClick={() => setSelected('')}>×</button></> : <span>Select any bus to inspect live voltage</span>}</div>
  </div>;
}
