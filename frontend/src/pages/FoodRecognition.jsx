import React, { useState } from 'react';
import { Scan } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { addHistory } from '../utils/history';
import { PageHeader, ImageUpload, VoiceNote, ErrorBanner, Spinner, Meter, Stat, Section, Disclaimer, InputNotes } from '../components/ui';

export default function FoodRecognition() {
  const [image, setImage] = useState(null);
  const [text, setText] = useState('');
  const [audio, setAudio] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const submit = async () => {
    if (busy) return;
    if (!image && !text.trim() && !audio) { setError('Add a food photo, a short description, or a voice note first.'); return; }
    setBusy(true); setError(null); setResult(null);
    try {
      const data = await api.analyzeFood({ file: image, text_context: text.trim(), audio_file: audio });
      setResult(data);
      addHistory('Food Recognition', data.primary_food || 'Analysis', '/food-recognition');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader icon={Scan} title="Food Recognition & Nutrition" subtitle="Upload a photo of your meal. The AI identifies what it sees and estimates nutrition, and tells you how uncertain it is." />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card space-y-4">
          <ImageUpload file={image} onChange={(f) => { setImage(f); setResult(null); }} label="Upload a food photo" />
          <div>
            <label htmlFor="ctx" className="label">Extra context (optional)</label>
            <textarea id="ctx" rows={3} className="input" placeholder="e.g. homemade, cooked in 1 tbsp olive oil, large portion" value={text} onChange={(e) => setText(e.target.value)} />
          </div>
          <VoiceNote blob={audio} onChange={setAudio} />
          <ErrorBanner message={error} onRetry={image || text || audio ? submit : null} />
          <button className="btn-primary w-full" disabled={busy} onClick={submit}>{busy ? <Spinner label="Analysing…" /> : 'Analyse food'}</button>
        </div>

        <div className="space-y-4">
          {!result && !busy && <div className="card text-sm text-slate-400">Your analysis will appear here.</div>}
          {busy && <div className="card text-sm text-slate-300"><Spinner label="The AI is looking at your meal…" /></div>}
          {result && (
            <div className="card space-y-5">
              <div>
                <h2 className="text-2xl font-bold">{result.primary_food}</h2>
                {result.description && <p className="mt-1 text-sm text-slate-300">{result.description}</p>}
                {result.estimated_portion && <p className="mt-1 text-xs text-slate-400">Estimated portion: {result.estimated_portion}</p>}
              </div>
              <Meter value={result.confidence} label="Identification confidence" />
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
                <Stat label="Calories" value={result.calories} unit=" kcal" />
                <Stat label="Protein" value={result.protein} unit="g" />
                <Stat label="Carbs" value={result.carbohydrates} unit="g" />
                <Stat label="Fats" value={result.fats} unit="g" />
                <Stat label="Fiber" value={result.fiber} unit="g" />
                <Stat label="Sugar" value={result.sugar} unit="g" />
              </div>
              {result.detected_foods?.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {result.detected_foods.map((f, i) => <span key={i} className="rounded-full bg-slate-700 px-3 py-1 text-xs">{f.name}{f.estimated_portion ? ` · ${f.estimated_portion}` : ''}</span>)}
                </div>
              )}
              {result.reasoning && <p className="text-sm text-slate-300">{result.reasoning}</p>}
              <Section title="Limitations" items={result.limitations} tone="warn" />
              <InputNotes notes={result.input_notes} />
              <Disclaimer>{result.nutrition_note}</Disclaimer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
