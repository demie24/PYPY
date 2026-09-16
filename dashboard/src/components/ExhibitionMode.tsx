import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowRight, AudioLines, BrainCircuit, Check, Expand, FileSearch, Radio, Shield, ShieldAlert, ShieldCheck, Square, Volume2, VolumeX, X, Zap } from 'lucide-react';
import type { ControlCenterProps } from './PypyControlCenter.tsx';
import { evidenceTime, exhibitionState, fresh } from '../exhibitionState.ts';
import { ExhibitionTopology } from './ExhibitionTopology.tsx';
import './exhibition.css';

const messages = ['TRY ATTACKING THE GRID', 'WATCH THE AI ASSESS THE THREAT', 'SEE THE EVIDENCE BEHIND EVERY RESPONSE'];
const timeLabel = (value: unknown) => evidenceTime(value) ? new Date(evidenceTime(value)).toLocaleTimeString([], { hour12: false }) : 'Time unavailable';

export function ExhibitionMode(props: ControlCenterProps) {
  const [now, setNow] = useState(Date.now());
  const [idle, setIdle] = useState(false);
  const [story, setStory] = useState(0);
  const [muted, setMuted] = useState(true);
  const [fullscreen, setFullscreen] = useState(!!document.fullscreenElement);
  const [notice, setNotice] = useState('');
  const [scenario, setScenario] = useState('FDIA');
  const [target, setTarget] = useState('Bus_5');
  const [bias, setBias] = useState(.15);
  const [pending, setPending] = useState<{ action: string; type: string; target: string; sent: number } | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const launch = useRef<HTMLButtonElement>(null);
  const audio = useRef<AudioContext | null>(null);
  const lastInteraction = useRef(Date.now());
  const previous = useRef({ attack: '', detection: '', recovered: '' });
  const state = exhibitionState(props, now);
  const targets = Object.keys(scenario === 'FDIA' ? props.telemetry?.state?.buses || {} : props.telemetry?.state?.breakers || {});
  useEffect(() => {
    const interact = () => { lastInteraction.current = Date.now(); setIdle(false); };
    const tick = window.setInterval(() => { const time = Date.now(); setNow(time); setIdle(time - lastInteraction.current > 45000 && !dialog.current?.open); setStory(Math.floor((time - lastInteraction.current) / 8000) % messages.length); }, 1000);
    const full = () => setFullscreen(!!document.fullscreenElement);
    ['pointerdown','pointermove','keydown','touchstart','wheel'].forEach(e => window.addEventListener(e, interact, { passive: true }));
    document.addEventListener('fullscreenchange', full);
    return () => { window.clearInterval(tick); ['pointerdown','pointermove','keydown','touchstart','wheel'].forEach(e => window.removeEventListener(e, interact)); document.removeEventListener('fullscreenchange', full); void audio.current?.close(); };
  }, []);
  const tone = (kind: 'attack' | 'detection' | 'success') => {
    const ctx = audio.current;
    if (muted || !ctx || ctx.state !== 'running') return;
    const notes = kind === 'success' ? [523,659,784] : kind === 'attack' ? [330,220] : [440];
    notes.forEach((frequency, i) => {
      const oscillator = ctx.createOscillator(); const gain = ctx.createGain(); const start = ctx.currentTime + i * .13;
      oscillator.type = 'sine'; oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0, start); gain.gain.linearRampToValueAtTime(.035, start + .015); gain.gain.exponentialRampToValueAtTime(.001, start + .12);
      oscillator.connect(gain); gain.connect(ctx.destination); oscillator.start(start); oscillator.stop(start + .14);
    });
  };
  useEffect(() => {
    const attack = state.attack || '';
    const detection = state.detection ? String(state.detection.type || 'anomaly') : '';
    const recovered = state.verified ? state.attempt?.key || '' : '';
    if (previous.current.attack !== attack && attack) tone('attack');
    else if (!previous.current.detection && detection) tone('detection');
    else if (previous.current.recovered !== recovered && recovered) tone('success');
    previous.current = { attack, detection, recovered };
  }, [state.attack, state.detection?.type, state.verified, state.attempt?.key, muted]);
  useEffect(() => {
    if (!pending) return;
    const status = props.telemetry?.attack_status;
    const laterFrame = state.live && evidenceTime(props.telemetry?.timestamp) > pending.sent;
    const confirmed = laterFrame && (pending.action === 'STOP' ? status && !status.active_attack : status?.active_attack === pending.type && !!status?.compromised_nodes?.[pending.target]);
    if (confirmed) { setNotice(pending.action === 'STOP' ? 'Attack stopped — recovery must be verified independently.' : 'Attack confirmed by live telemetry.'); setPending(null); }
    else if (!props.connected || now - pending.sent > 15000) { setNotice(!props.connected ? 'Connection lost. Command outcome unknown; check live telemetry after reconnecting.' : 'Command not confirmed within 15 seconds. Outcome unknown; inspect Logs & Forensics before retrying.'); setPending(null); }
  }, [pending, props.telemetry, props.connected, state.live, now]);
  const rows = useMemo(() => {
    const all = [
      ...props.events.map(p => ({ timestamp: p.timestamp, title: p.event || p.type || 'Grid event', detail: p.target || p.source || 'Digital Twin', kind: /attack/i.test(p.event || '') ? 'danger' : 'info' })),
      ...props.alerts.map(p => ({ timestamp: p.timestamp, title: p.type || 'Anomaly detected', detail: p.suspect_node || p.msg || 'Detector evidence', kind: 'warning' })),
      ...props.recoveryEvidence.attempts.flatMap(a => a.evidence.filter(e => e.stage !== 'TELEMETRY VERIFIED' || e === a.evidence.find(x => x.stage === 'TELEMETRY VERIFIED')).map(e => ({ timestamp: e.timestamp, title: e.summary, detail: e.stage, kind: e.stage === 'REJECTED' ? 'warning' : 'info' }))),
    ].sort((a,b) => evidenceTime(b.timestamp) - evidenceTime(a.timestamp));
    return all.filter((r,i) => all.findIndex(x => x.timestamp === r.timestamp && x.title === r.title) === i).slice(0, 4);
  }, [props.events, props.alerts, props.recoveryEvidence]);
  const closeDialog = () => { dialog.current?.close(); launch.current?.focus(); };
  const send = (action: 'START' | 'STOP') => {
    if (!state.live || pending && action === 'START') return;
    const sent = Date.now(); const experiment = `ui-${sent}`;
    try {
      props.onSendMessage({ topic: 'grid/attack', payload: action === 'STOP' ? { action: 'STOP' } : { action: 'START', type: scenario, experiment_id: experiment, correlation_id: `${experiment}:${target}`, config: { target, ...(scenario === 'FDIA' ? { bias, scale: 1 } : { command: 'OPEN' }) } } });
      setPending({ action, type: scenario, target, sent }); setNotice('Command sent — awaiting confirmation from the Digital Twin.'); closeDialog();
    } catch (error) { setNotice(`Command failed: ${error instanceof Error ? error.message : String(error)}`); }
  };
  const toggleAudio = async () => {
    if (!muted) { setMuted(true); return; }
    try { audio.current ||= new AudioContext(); await audio.current.resume(); setMuted(false); }
    catch { setNotice('Audio is unavailable in this browser.'); }
  };
  const toggleFullscreen = async () => {
    try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); }
    catch { setNotice('Fullscreen unavailable. You can continue in this window.'); }
  };
  const ready = state.live ? Object.values(props.aiStatuses).filter(s => fresh(s, now, 60000) && (s?.ready === true || ['ready','active','online','healthy'].includes(String(s.status).toLowerCase()))).length : 0;
  return <main className={`exhibition ex-${state.tone} ${idle ? 'ex-attract' : ''}`} data-testid="exhibition">
    <header className="ex-header"><a className="ex-brand" href="#/overview" aria-label="PYPY dashboard"><span><Shield/><Zap/></span><strong>PYPY<small>PROTECT YOUR POWER</small></strong></a><div className="ex-header-title">AI Cyber-Physical Defence <strong>Command Centre</strong></div><div className="ex-tools"><button onClick={toggleAudio} aria-pressed={!muted} title="Optional event sounds">{muted ? <VolumeX/> : <Volume2/>}<span>{muted ? 'Unmute' : 'Mute'}</span></button><button onClick={toggleFullscreen}><Expand/><span>{fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}</span></button><a href="#/overview" className="ex-exit">Exit Exhibition Mode <X size={17}/></a></div></header>
    <section className="ex-situation" aria-live="polite"><div className="ex-situation-icon">{state.attack ? <ShieldAlert/> : state.live ? <ShieldCheck/> : <Radio/>}</div><div><p className="ex-eyebrow">LIVE DEFENCE / {props.selectedGrid.toUpperCase()} DIGITAL TWIN</p><h1>{state.headline}</h1><p>{!state.live ? 'Waiting for fresh system evidence. Live values and command launch are unavailable.' : state.verified ? 'Autonomous recovery completed · approved restoration confirmed in telemetry.' : state.attack ? 'Observe the detection, safety assessment and response as evidence arrives.' : 'A power grid. An intelligent defence. Every response backed by evidence.'}</p></div><div className={`ex-stream ex-${state.live ? 'info' : 'idle'}`}><Radio/><strong>{state.live ? 'MONITORING LIVE' : 'SIGNAL UNAVAILABLE'}</strong><small>{state.live ? `Telemetry ${timeLabel(props.telemetry?.timestamp)}` : props.connected ? 'Socket connected · telemetry stale' : 'Reconnecting to gateway'}</small></div></section>
    <div className="ex-main-grid"><section className="ex-topology-panel"><header><div><p className="ex-eyebrow">THE GRID WE PROTECT</p><h2>{props.selectedGrid.toUpperCase().replace('IEEE', 'IEEE ')} transmission network</h2></div><span className="ex-map-count">{Object.keys(props.telemetry?.state?.buses || {}).length || '—'} buses <span>/</span> {Object.keys(props.telemetry?.state?.lines || {}).length || '—'} branches</span></header><ExhibitionTopology telemetry={props.telemetry} live={state.live} grid={props.selectedGrid} recoveredTarget={state.verified ? state.attempt?.target : undefined}/><footer className="ex-legend"><span className="ex-safe">● Normal voltage</span><span className="ex-warning">▲ Warning / open</span><span className="ex-danger">! Compromised</span><span className="ex-idle">○ Unknown / offline</span><span>G Generator · ↓ Load</span></footer></section>
    <aside className="ex-side"><section className="ex-defense"><div className="ex-section-title"><ShieldCheck/><h2>Defence at a glance</h2></div><dl><div><dt>Grid health</dt><dd>{!state.live ? 'Unavailable' : state.stable ? 'Stable' : 'Needs attention'}</dd></div><div><dt>Threat level</dt><dd>{state.live && fresh(props.threat, now) ? props.threat?.severity || 'Unknown' : 'Unavailable'}</dd></div><div><dt>AI defence</dt><dd>{ready ? `${ready} models ready` : 'Awaiting status'}</dd></div><div><dt>Detection</dt><dd>{state.detection ? 'Anomaly received' : state.live ? 'Monitoring' : 'Unavailable'}</dd></div><div><dt>Recovery</dt><dd>{!state.live ? 'Unavailable' : state.verified ? 'Verified' : state.attempt?.outcome === 'REJECTED' ? 'Response rejected' : state.attempt?.dispatched ? 'Verifying response' : 'Awaiting evidence'}</dd></div></dl></section>
    <section className="ex-challenge"><span className="ex-eyebrow">CAN YOU BREAK PYPY?</span><h2>Choose an attack.<br/>Watch the AI respond.</h2><button className="ex-launch" ref={launch} disabled={!state.live || !!state.attack || !!pending} onClick={() => {setNotice('');dialog.current?.showModal();}}><ShieldAlert/><span>LAUNCH CYBER ATTACK</span><ArrowRight/></button><p>Controlled attacks on the existing simulated grid.</p><button className="ex-stop" disabled={!state.live || (!state.attack && !pending)} onClick={() => send('STOP')}><Square size={16}/> STOP ATTACK</button><small>Stops the attacker. Does not certify recovery.</small></section></aside></div>
    <section className="ex-pipeline" aria-label="Live defence pipeline"><div className="ex-pipeline-title"><BrainCircuit/><span>THE DEFENCE<br/><strong>IN MOTION</strong></span></div>{state.stages.map((stage,i) => <div key={stage.name} className={`ex-stage ex-${stage.state}`}><span className="ex-stage-number">{stage.state === 'safe' ? <Check size={19}/> : `0${i+1}`}</span><div><strong>{stage.name}</strong><small>{stage.detail}</small></div>{i < 5 && <ArrowRight className="ex-stage-arrow" size={18}/>}</div>)}</section>
    <section className="ex-bottom"><div className="ex-timeline"><header><FileSearch/><h2>Live evidence</h2><span>Recent records · source timestamps</span><a href="#/forensics">Forensic proof <ArrowRight size={15}/></a></header><div className="ex-event-list">{rows.length ? rows.map(row => <article className={`ex-event ex-${row.kind}`} key={`${row.timestamp}:${row.title}`}><time>{timeLabel(row.timestamp)}</time><strong title={row.title}>{row.title}</strong><small title={row.detail}>{row.detail}</small></article>) : <p className="ex-no-events">No event records received. New evidence will appear here.</p>}</div></div><div className="ex-story"><span><AudioLines size={16}/>{idle ? 'ATTRACT MODE · PRESENTATION ONLY' : 'PYPY / LIVE EXHIBITION'}</span><strong>{idle ? messages[story] : state.verified ? 'PYPY DEFENDED THE GRID' : 'Intelligence you can see.\nEvidence you can inspect.'}</strong><small>{idle ? 'Touch, move or press any key to return. No attacks run automatically.' : 'Attack → Detect → Trust → Decide → Heal → Recover'}</small></div></section>
    {notice && <div className="ex-notice" role="status"><span>{notice}</span><button aria-label="Dismiss message" onClick={() => setNotice('')}><X size={16}/></button></div>}
    <dialog ref={dialog} className="ex-dialog" aria-labelledby="ex-dialog-title" onCancel={() => launch.current?.focus()}><form onSubmit={e => {e.preventDefault();send('START');}}><header><span className="ex-eyebrow">CONTROLLED CYBER RANGE</span><button type="button" onClick={closeDialog} aria-label="Close attack selector"><X/></button></header><h2 id="ex-dialog-title">Choose your attack</h2><p>These controls operate the real PYPY simulation.</p><div className="ex-scenarios">{[['FDIA','False Data Injection','Bias a bus voltage measurement.'],['BREAKER_MANIPULATION','Breaker manipulation','Open a transmission breaker.']].map(([id,label,description]) => <button type="button" key={id} aria-pressed={scenario === id} onClick={() => {setScenario(id);setTarget(id === 'FDIA' ? 'Bus_5' : 'L_line_0');}}><ShieldAlert/><strong>{label}</strong><small>{description}</small></button>)}</div><label>Target asset<select value={target} onChange={e => setTarget(e.target.value)}>{!targets.includes(target) && <option value="">Select an available asset</option>}{targets.map(id => <option key={id}>{id}</option>)}</select></label>{scenario === 'FDIA' && <label>Voltage bias (p.u.)<input type="number" min="-0.5" max="0.5" step="0.01" required value={bias} onChange={e => setBias(e.target.valueAsNumber)}/><small>Scale stays at 1.0. Default bias: +0.15 p.u.</small></label>}<div className="ex-dialog-note">{scenario === 'FDIA' ? 'False data detection may lead to a rejected response. Stopping injection restores the untampered measurement; that alone is not autonomous recovery.' : 'The attacker holds the breaker open. Stop the attack to let the existing recovery policy evaluate restoration. Approval and later closed-state telemetry are required.'}</div><button className="ex-launch" type="submit" disabled={!state.live || !!state.attack || !!pending || !targets.includes(target) || scenario === 'FDIA' && (!Number.isFinite(bias) || Math.abs(bias) > .5)}><Zap/> Launch selected attack <ArrowRight/></button></form></dialog>
  </main>;
}
