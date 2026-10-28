import React, { useState } from 'react';
import { Thermometer } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { addHistory } from '../utils/history';
import { PageHeader, ImageUpload, VoiceNote, ErrorBanner, Spinner, Meter, Badge, Section, Disclaimer, InputNotes } from '../components/ui';

const tone = { 'Appears fresh': 'green', 'Possible deterioration': 'amber', 'Visible signs of spoilage': 'red', Inconclusive: 'blue' };

export default function FreshnessDetector() {
  const [image, setImage] = useState(null);
  const [time, setTime] = useState('');
  const [type, setType] = useState('Refrigerator');
  const [text, setText] = useState('');
  const [audio, setAudio] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const submit = async () => {
    if (busy) return;
    if (!image) { setError('Please upload a photo of the food first.'); return; }
    setBusy(true); setError(null); setResult(null);
    try {
      const data = await api.analyzeFreshness({ file: image, storage_time: time.trim(), storage_type: type, text_context: text.trim(), audio_file: audio });
      setResult(data);
      addHistory('Freshness', `${data.item_name}: ${data.freshness_level}`, '/freshness-detector');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader icon={Thermometer} title="Freshness Detector" subtitle="Looks for visible signs of deterioration. A photo can never prove food is safe, so treat the result as guidance only." />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-4">
          <ImageUpload file={image} onChange={(f) => { setImage(f); setResult(null); }} label="Upload a food photo" />
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="st" className="label">Stored for</label>
              <input id="st" className="input" placeholder="e.g. 3 days" value={time} onChange={(e) => setTime(e.target.value)} />
            </div>
            <div>
              <label htmlFor="sc" className="label">Storage conditions</label>
              <select id="sc" className="input" value={type} onChange={(e) => setType(e.target.value)}>
                {['Refrigerator', 'Freezer', 'Room temperature', 'Pantry', 'Left out on counter'].map((o) => <option key={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="fn" className="label">Notes (optional)</label>
            <textarea id="fn" rows={2} className="input" placeholder="e.g. cooked rice, smells normal" value={text} onChange={(e) => setText(e.target.value)} />
          </div>
          <VoiceNote blob={audio} onChange={setAudio} />
          <ErrorBanner message={error} onRetry={image ? submit : null} />
          <button className="btn-primary w-full" disabled={busy} onClick={submit}>{busy ? <Spinner label="Inspecting…" /> : 'Check freshness'}</button>
        </div>

        <div>
          {!result && !busy && <div className="card text-sm text-slate-400">Your result will appear here.</div>}
          {busy && <div className="card text-sm text-slate-300"><Spinner label="Inspecting the photo…" /></div>}
          {result && (
            <div className="card space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-2xl font-bold">{result.item_name}</h2>
                <Badge tone={tone[result.freshness_level] || 'slate'}>{result.freshness_level}</Badge>
              </div>
              <Meter value={result.confidence} />
              {result.safety_status && <div className="rounded-xl border border-slate-600 bg-slate-900/50 p-3 text-sm"><strong>Safety note:</strong> {result.safety_status}</div>}
              <Section title="Visible signs" items={result.detected_signs} />
              {result.reasoning && <div><h4 className="mb-1 text-sm font-semibold">Reasoning</h4><p className="text-sm text-slate-300">{result.reasoning}</p></div>}
              {result.recommendation && <div><h4 className="mb-1 text-sm font-semibold">Recommendation</h4><p className="text-sm text-slate-300">{result.recommendation}</p></div>}
              <Section title="Limitations" items={result.limitations} tone="warn" />
              <InputNotes notes={result.input_notes} />
              <Disclaimer>{result.disclaimer}</Disclaimer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
