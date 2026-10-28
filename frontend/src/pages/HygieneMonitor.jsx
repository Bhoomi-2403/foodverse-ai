import React, { useEffect, useRef, useState } from 'react';
import { ShieldCheck, Video, Image as ImageIcon, Download } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { addHistory } from '../utils/history';
import { validateVideo } from '../utils/files';
import { PageHeader, ImageUpload, ErrorBanner, Spinner, Badge, Section, Disclaimer, InputNotes } from '../components/ui';
import { cn } from '../utils/cn';

const sev = { High: 'red', Medium: 'amber', Low: 'blue' };

export default function HygieneMonitor() {
  const [mode, setMode] = useState('image');
  const [image, setImage] = useState(null);
  const [video, setVideo] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoError, setVideoError] = useState(null);
  const [context, setContext] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const vref = useRef(null);

  useEffect(() => {
    if (!video) { setVideoUrl(null); return undefined; }
    const u = URL.createObjectURL(video);
    setVideoUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [video]);

  const pickVideo = (f) => {
    if (!f) return;
    const err = validateVideo(f);
    setVideoError(err);
    if (!err) { setVideo(f); setResult(null); }
  };

  const submit = async () => {
    if (busy) return;
    const media = mode === 'image' ? image : video;
    if (!media) { setError(`Please add a ${mode} first.`); return; }
    setBusy(true); setError(null); setResult(null);
    try {
      const data = await api.analyzeHygiene({ [mode === 'image' ? 'file' : 'video']: media, context: context.trim() });
      setResult(data);
      addHistory('Hygiene', `Indicative score ${data.overall_score}/100 (${data.media_type})`, '/hygiene-monitor');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };

  const download = async () => {
    try {
      const blob = await api.hygieneReport(result);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'hygiene-report.pdf'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError(errorMessage(e)); }
  };

  const scoreTone = !result ? '' : result.overall_score >= 85 ? 'text-emerald-300' : result.overall_score >= 65 ? 'text-amber-300' : 'text-red-300';

  return (
    <div>
      <PageHeader icon={ShieldCheck} title="Hygiene & Safety Monitor" subtitle="A preliminary review of uploaded kitchen images or video clips. Video is analysed as sampled frames, not as live monitoring." />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-4">
          <div className="flex gap-2" role="tablist" aria-label="Media type">
            {[['image', 'Image', ImageIcon], ['video', 'Video', Video]].map(([k, l, I]) => (
              <button key={k} role="tab" aria-selected={mode === k} onClick={() => { setMode(k); setError(null); }}
                className={cn('btn flex-1 border', mode === k ? 'border-emerald-500 bg-emerald-500/15 text-emerald-300' : 'border-slate-600 text-slate-300')}><I size={16} /> {l}</button>
            ))}
          </div>
          {mode === 'image' ? (
            <ImageUpload file={image} onChange={(f) => { setImage(f); setResult(null); }} label="Upload a kitchen photo" />
          ) : videoUrl ? (
            <div className="relative overflow-hidden rounded-2xl border border-slate-600">
              <video ref={vref} src={videoUrl} controls className="max-h-80 w-full bg-black" />
              <button className="btn-ghost absolute right-2 top-2 bg-slate-900/80 !py-1.5" onClick={() => setVideo(null)}>Remove</button>
            </div>
          ) : (
            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-slate-600 p-10 text-slate-400 hover:border-slate-400">
              <Video size={28} /><span className="text-sm font-medium text-slate-200">Upload a kitchen video</span>
              <span className="text-xs">MP4 recommended · max 60 MB · a handful of frames are sampled</span>
              <input type="file" accept="video/*" className="sr-only" onChange={(e) => { pickVideo(e.target.files[0]); e.target.value = ''; }} />
            </label>
          )}
          {videoError && mode === 'video' && <p role="alert" className="text-xs text-red-300">{videoError}</p>}
          <div>
            <label htmlFor="hc" className="label">Kitchen context / rules (optional)</label>
            <textarea id="hc" rows={3} className="input" placeholder="e.g. Commercial kitchen: gloves required for ready-to-eat food, hair nets mandatory" value={context} onChange={(e) => setContext(e.target.value)} />
          </div>
          <ErrorBanner message={error} />
          <button className="btn-primary w-full" disabled={busy} onClick={submit}>{busy ? <Spinner label={mode === 'video' ? 'Analysing frames…' : 'Analysing…'} /> : 'Run hygiene check'}</button>
        </div>

        <div>
          {!result && !busy && <div className="card text-sm text-slate-400">Your report will appear here.</div>}
          {busy && <div className="card text-sm text-slate-300"><Spinner label="Reviewing the media…" /></div>}
          {result && (
            <div className="card space-y-5">
              <div className="flex items-end justify-between gap-3">
                <div>
                  <div className="text-xs text-slate-400">Indicative score</div>
                  <div className={cn('text-5xl font-bold', scoreTone)}>{result.overall_score}<span className="text-xl text-slate-500">/100</span></div>
                  <p className="mt-1 max-w-xs text-xs text-slate-500">{result.score_method}</p>
                </div>
                <button className="btn-ghost" onClick={download}><Download size={16} /> PDF</button>
              </div>
              <p className="text-sm text-slate-300">{result.ai_summary}</p>
              <div className="text-xs text-slate-400">
                {result.frames_analysed} {result.media_type === 'video' ? 'frame(s)' : 'image'} analysed
                {result.video_info && ` · ${result.video_info.duration_seconds}s video`}
              </div>
              <div>
                <h4 className="mb-2 text-sm font-semibold">Potential issues</h4>
                {result.violations.length === 0 ? <p className="text-sm text-slate-400">None observed in the reviewed media.</p> : (
                  <ul className="space-y-2">
                    {result.violations.map((v, i) => (
                      <li key={i} className="rounded-xl bg-slate-900/60 p-3 text-sm">
                        <div className="flex flex-wrap items-center gap-2"><Badge tone={sev[v.severity] || 'slate'}>{v.severity}</Badge><strong>{v.violation}</strong>
                          {v.timestamp != null && <span className="text-xs text-slate-500">@ {v.timestamp}s</span>}</div>
                        <p className="mt-1 text-slate-300">{v.reason}{v.location ? ` (${v.location})` : ''}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <Section title="Positive observations" items={result.positive_observations} />
              <Section title="Could not be assessed" items={result.unobserved} tone="warn" />
              <InputNotes notes={result.input_notes} />
              <Disclaimer>{result.limitations.join(' ')}</Disclaimer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
