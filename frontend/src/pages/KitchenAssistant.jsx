import React, { useState } from 'react';
import { ChefHat, Clock, Users } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { addHistory } from '../utils/history';
import { PageHeader, ImageUpload, VoiceNote, ErrorBanner, Spinner, Section, Disclaimer, InputNotes } from '../components/ui';

export default function KitchenAssistant() {
  const [text, setText] = useState('');
  const [image, setImage] = useState(null);
  const [audio, setAudio] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [recipe, setRecipe] = useState(null);

  const submit = async () => {
    if (busy) return;
    if (!text.trim() && !image && !audio) { setError('List your ingredients, upload a photo, or record a voice note.'); return; }
    setBusy(true); setError(null); setRecipe(null);
    try {
      const data = await api.generateRecipe({ text_input: text.trim(), file: image, audio_file: audio });
      setRecipe(data);
      addHistory('Smart Kitchen', data.dish_name, '/kitchen-assistant');
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader icon={ChefHat} title="Smart Kitchen Assistant" subtitle="Tell me what you have, show me a photo, or name a dish. I'll write a recipe with steps, timings and safety notes." />
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="card space-y-4 lg:col-span-2">
          <div>
            <label htmlFor="ing" className="label">Ingredients or dish</label>
            <textarea id="ing" rows={4} className="input" placeholder="e.g. paneer, spinach, onion, tomatoes. Vegetarian, 20 minutes" value={text} onChange={(e) => setText(e.target.value)} />
          </div>
          <ImageUpload file={image} onChange={setImage} label="Add an ingredient photo (optional)" />
          <VoiceNote blob={audio} onChange={setAudio} />
          <ErrorBanner message={error} onRetry={submit} />
          <button className="btn-primary w-full" disabled={busy} onClick={submit}>{busy ? <Spinner label="Cooking up a recipe…" /> : 'Generate recipe'}</button>
        </div>

        <div className="lg:col-span-3">
          {!recipe && !busy && <div className="card text-sm text-slate-400">Your recipe will appear here.</div>}
          {busy && <div className="card text-sm text-slate-300"><Spinner label="Writing your recipe…" /></div>}
          {recipe && (
            <div className="card space-y-5">
              <div>
                <h2 className="text-2xl font-bold">{recipe.dish_name}</h2>
                <p className="mt-1 text-sm text-slate-300">{recipe.description}</p>
                <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-300">
                  {recipe.preparation_time && <span className="inline-flex items-center gap-1"><Clock size={14} /> Prep {recipe.preparation_time}</span>}
                  {recipe.cooking_time && <span className="inline-flex items-center gap-1"><Clock size={14} /> Cook {recipe.cooking_time}</span>}
                  {recipe.servings && <span className="inline-flex items-center gap-1"><Users size={14} /> {recipe.servings}</span>}
                </div>
              </div>
              <div>
                <h4 className="mb-2 text-sm font-semibold">Ingredients</h4>
                <ul className="grid gap-1 text-sm text-slate-300 sm:grid-cols-2">
                  {recipe.ingredients.map((x, i) => <li key={i} className="rounded-lg bg-slate-900/60 px-3 py-1.5">{x}</li>)}
                </ul>
              </div>
              <div>
                <h4 className="mb-2 text-sm font-semibold">Steps</h4>
                <ol className="space-y-2 text-sm text-slate-300">
                  {recipe.steps.map((s, i) => (
                    <li key={i} className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-xs font-bold text-emerald-300">{i + 1}</span><span>{s}</span></li>
                  ))}
                </ol>
              </div>
              <Section title="Dietary notes" items={recipe.dietary_notes} />
              <Section title="Substitutions" items={recipe.substitutions} />
              <Section title="Food safety" items={recipe.safety_notes} />
              <Section title="Allergen notes" items={recipe.allergen_notes} tone="warn" />
              {recipe.uncertainty_note && <Disclaimer>{recipe.uncertainty_note}</Disclaimer>}
              <InputNotes notes={recipe.input_notes} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
