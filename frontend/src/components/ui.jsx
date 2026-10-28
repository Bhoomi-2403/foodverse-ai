import React, { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Upload, X, Mic, Square, Loader2, Info } from 'lucide-react';
import { cn } from '../utils/cn';
import { AudioRecorder } from '../utils/audioRecorder';
import { validateImage } from '../utils/files';

export function PageHeader({ icon: Icon, title, subtitle }) {
  return (
    <div className="mb-6 flex items-start gap-4">
      <div className="rounded-xl bg-emerald-500/15 p-3 text-emerald-300"><Icon size={24} /></div>
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-400">{subtitle}</p>
      </div>
    </div>
  );
}

export function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
      <AlertTriangle size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && <button onClick={onRetry} className="rounded-lg border border-red-400/40 px-3 py-1 text-xs hover:bg-red-500/20">Retry</button>}
    </div>
  );
}

export function Notice({ children, tone = 'info' }) {
  const tones = { info: 'border-sky-500/30 bg-sky-500/10 text-sky-200', warn: 'border-amber-500/30 bg-amber-500/10 text-amber-200' };
  return (
    <div className={cn('flex items-start gap-3 rounded-xl border p-3 text-xs', tones[tone])}>
      <Info size={15} className="mt-0.5 shrink-0" /> <div>{children}</div>
    </div>
  );
}

export function Spinner({ label }) {
  return <span className="inline-flex items-center gap-2"><Loader2 size={16} className="animate-spin" /> {label}</span>;
}

export function Meter({ value, label = 'Confidence' }) {
  if (value === null || value === undefined) return null;
  const v = Math.max(0, Math.min(100, value));
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-400"><span>{label}</span><span>{Math.round(v)}%</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-700" role="progressbar" aria-valuenow={Math.round(v)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-teal-400" style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

export function Badge({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-700 text-slate-200', green: 'bg-emerald-500/20 text-emerald-300', amber: 'bg-amber-500/20 text-amber-300',
    red: 'bg-red-500/20 text-red-300', blue: 'bg-sky-500/20 text-sky-300',
  };
  return <span className={cn('inline-block rounded-full px-2.5 py-0.5 text-xs font-medium', tones[tone])}>{children}</span>;
}

export function Section({ title, items, tone }) {
  if (!items || !items.length) return null;
  return (
    <div>
      <h4 className="mb-2 text-sm font-semibold text-slate-200">{title}</h4>
      <ul className={cn('list-disc space-y-1 pl-5 text-sm', tone === 'warn' ? 'text-amber-200' : 'text-slate-300')}>
        {items.map((it, i) => <li key={i}>{it}</li>)}
      </ul>
    </div>
  );
}

export function Stat({ label, value, unit }) {
  return (
    <div className="rounded-xl bg-slate-900/60 p-3 text-center">
      <div className="text-xl font-bold text-emerald-300">{value === null || value === undefined ? '—' : Math.round(value * 10) / 10}<span className="ml-0.5 text-xs font-normal text-slate-400">{value == null ? '' : unit}</span></div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}

/** Image picker with drag & drop, preview, replace and remove. Revokes object URLs. */
export function ImageUpload({ file, onChange, label = 'Upload an image' }) {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!file) { setPreview(null); return undefined; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const pick = (f) => {
    if (!f) return;
    const err = validateImage(f);
    setError(err);
    if (!err) onChange(f);
  };

  return (
    <div>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" aria-label={label}
        onChange={(e) => { pick(e.target.files[0]); e.target.value = ''; }} />
      {preview ? (
        <div className="relative overflow-hidden rounded-2xl border border-slate-600">
          <img src={preview} alt="Selected upload preview" className="max-h-80 w-full object-contain bg-black/30" />
          <div className="absolute right-2 top-2 flex gap-2">
            <button type="button" className="btn-ghost bg-slate-900/80 !py-1.5" onClick={() => inputRef.current.click()}>Replace</button>
            <button type="button" className="btn-ghost bg-slate-900/80 !p-2" aria-label="Remove image" onClick={() => onChange(null)}><X size={16} /></button>
          </div>
        </div>
      ) : (
        <button type="button" onClick={() => inputRef.current.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
          className={cn('flex w-full flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-10 text-slate-400 transition',
            drag ? 'border-emerald-400 bg-emerald-500/10' : 'border-slate-600 hover:border-slate-400')}>
          <Upload size={28} />
          <span className="text-sm font-medium text-slate-200">{label}</span>
          <span className="text-xs">Click or drag & drop · JPEG, PNG, WebP · max 10 MB</span>
        </button>
      )}
      {error && <p role="alert" className="mt-2 text-xs text-red-300">{error}</p>}
    </div>
  );
}

/** Optional voice note. Recorder is created once (lazy) and mic tracks are stopped after use. */
export function VoiceNote({ blob, onChange }) {
  const recorder = useRef(null);
  const [recording, setRecording] = useState(false);
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!blob) { setUrl(null); return undefined; }
    const u = URL.createObjectURL(blob);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [blob]);

  useEffect(() => () => recorder.current?.cleanup(), []);

  if (!AudioRecorder.supported()) return <p className="text-xs text-slate-500">Voice notes are not supported in this browser.</p>;

  const toggle = async () => {
    setError(null);
    if (!recorder.current) recorder.current = new AudioRecorder();
    if (recording) {
      const b = await recorder.current.stop();
      setRecording(false);
      onChange(b);
    } else {
      try {
        await recorder.current.start();
        onChange(null);
        setRecording(true);
      } catch (e) { setError(e.message); }
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={toggle} className={cn('btn-ghost', recording && '!border-red-400 !text-red-300')}>
          {recording ? <><Square size={14} /> Stop recording</> : <><Mic size={14} /> Add voice note (optional)</>}
        </button>
        {url && !recording && (
          <>
            <audio controls src={url} className="h-9" />
            <button type="button" className="text-xs text-slate-400 underline" onClick={() => onChange(null)}>Remove</button>
          </>
        )}
      </div>
      {error && <p role="alert" className="text-xs text-red-300">{error}</p>}
    </div>
  );
}

export function Disclaimer({ children }) {
  return <Notice tone="warn">{children}</Notice>;
}

export function InputNotes({ notes }) {
  if (!notes || !notes.length) return null;
  return <Notice>{notes.join(' ')}</Notice>;
}
