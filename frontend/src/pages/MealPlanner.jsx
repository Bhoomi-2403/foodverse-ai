import React, { useState } from 'react';
import { Calendar } from 'lucide-react';
import { api, errorMessage } from '../api/client';
import { addHistory } from '../utils/history';
import { PageHeader, ErrorBanner, Spinner, Stat, Section, Disclaimer } from '../components/ui';
import { cn } from '../utils/cn';

const GOALS = ['Lose weight', 'Maintain weight', 'Build muscle', 'Eat healthier', 'More energy'];
const MEALS = [['breakfast', 'Breakfast'], ['mid_morning_snack', 'Mid-morning snack'], ['lunch', 'Lunch'], ['evening_snack', 'Evening snack'], ['dinner', 'Dinner']];

function Field({ id, label, children, hint }) {
  return <div><label htmlFor={id} className="label">{label}</label>{children}{hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}</div>;
}

export default function MealPlanner() {
  const [f, setF] = useState({
    age: '', gender: 'Female', height: '', weight: '', activity_level: 'Moderate', medical_conditions: '',
    diet_type: 'Standard', cuisine: 'Global', allergies: '', foods_to_avoid: '', recent_history: '', weight_change: 'Stable',
  });
  const [goals, setGoals] = useState(['Maintain weight']);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [plan, setPlan] = useState(null);
  const [tab, setTab] = useState('daily');
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  const toggleGoal = (g) => setGoals((p) => (p.includes(g) ? p.filter((x) => x !== g) : [...p, g]));

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    if (!goals.length) { setError('Choose at least one goal.'); return; }
    setBusy(true); setError(null); setPlan(null);
    try {
      const data = await api.generatePlan({
        ...f, goals: goals.join(', '),
        medical_conditions: f.medical_conditions.trim() || 'None', allergies: f.allergies.trim() || 'None',
        foods_to_avoid: f.foods_to_avoid.trim() || 'None', recent_history: f.recent_history.trim() || 'No data',
      });
      setPlan(data); setTab('daily');
      addHistory('Meal Planner', `${data.targets.target_calories} kcal plan`, '/meal-planner');
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  };

  const select = 'input';
  return (
    <div>
      <PageHeader icon={Calendar} title="Personalised Meal Planner" subtitle="Calorie and macro targets are calculated from your profile, then the AI builds meals around them while avoiding your allergens." />
      <div className="grid gap-6 lg:grid-cols-5">
        <form onSubmit={submit} className="card space-y-4 lg:col-span-2">
          <div className="grid grid-cols-2 gap-3">
            <Field id="age" label="Age *"><input id="age" required type="number" min="14" max="100" className="input" value={f.age} onChange={set('age')} /></Field>
            <Field id="gender" label="Sex *"><select id="gender" className={select} value={f.gender} onChange={set('gender')}><option>Female</option><option>Male</option></select></Field>
            <Field id="height" label="Height (cm) *"><input id="height" required type="number" min="100" max="250" className="input" value={f.height} onChange={set('height')} /></Field>
            <Field id="weight" label="Weight (kg) *"><input id="weight" required type="number" min="30" max="300" step="0.1" className="input" value={f.weight} onChange={set('weight')} /></Field>
          </div>
          <Field id="act" label="Activity level">
            <select id="act" className={select} value={f.activity_level} onChange={set('activity_level')}>
              {['Sedentary', 'Light', 'Moderate', 'Active', 'Very active'].map((o) => <option key={o}>{o}</option>)}
            </select>
          </Field>
          <fieldset>
            <legend className="label">Goals *</legend>
            <div className="flex flex-wrap gap-2">
              {GOALS.map((g) => (
                <button type="button" key={g} aria-pressed={goals.includes(g)} onClick={() => toggleGoal(g)}
                  className={cn('rounded-full border px-3 py-1 text-xs', goals.includes(g) ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300' : 'border-slate-600 text-slate-300')}>{g}</button>
              ))}
            </div>
          </fieldset>
          <div className="grid grid-cols-2 gap-3">
            <Field id="diet" label="Diet type"><select id="diet" className={select} value={f.diet_type} onChange={set('diet_type')}>
              {['Standard', 'Vegetarian', 'Vegan', 'Eggetarian', 'Pescatarian', 'Keto', 'Low-carb'].map((o) => <option key={o}>{o}</option>)}</select></Field>
            <Field id="cui" label="Cuisine"><select id="cui" className={select} value={f.cuisine} onChange={set('cuisine')}>
              {['Global', 'Indian', 'Mediterranean', 'Asian', 'Western', 'Middle Eastern', 'Mexican'].map((o) => <option key={o}>{o}</option>)}</select></Field>
          </div>
          <Field id="all" label="Allergies (optional)" hint="Comma separated. These are strictly excluded."><input id="all" className="input" placeholder="peanut, shellfish" value={f.allergies} onChange={set('allergies')} /></Field>
          <Field id="avoid" label="Foods to avoid (optional)"><input id="avoid" className="input" placeholder="mushroom, brinjal" value={f.foods_to_avoid} onChange={set('foods_to_avoid')} /></Field>
          <Field id="med" label="Medical conditions (optional)" hint="Only if you want them considered. Plans are not medical advice."><input id="med" className="input" placeholder="e.g. type 2 diabetes" value={f.medical_conditions} onChange={set('medical_conditions')} /></Field>
          <Field id="hist" label="Recent eating pattern (optional)"><textarea id="hist" rows={2} className="input" value={f.recent_history} onChange={set('recent_history')} /></Field>
          <Field id="wc" label="Recent weight change"><select id="wc" className={select} value={f.weight_change} onChange={set('weight_change')}>
            {['Stable', 'Gaining', 'Losing'].map((o) => <option key={o}>{o}</option>)}</select></Field>
          <ErrorBanner message={error} />
          <button className="btn-primary w-full" disabled={busy}>{busy ? <Spinner label="Planning your day…" /> : 'Generate plan'}</button>
        </form>

        <div className="lg:col-span-3">
          {!plan && !busy && <div className="card text-sm text-slate-400">Your plan will appear here.</div>}
          {busy && <div className="card text-sm text-slate-300"><Spinner label="Building your plan (this can take a few seconds)…" /></div>}
          {plan && (
            <div className="space-y-4">
              <div className="card space-y-4">
                <h2 className="text-lg font-semibold">Daily targets <span className="text-xs font-normal text-slate-500">(estimates)</span></h2>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Stat label="Target calories" value={plan.targets.target_calories} unit=" kcal" />
                  <Stat label="Protein" value={plan.targets.protein_g} unit="g" />
                  <Stat label="Carbs" value={plan.targets.carbs_g} unit="g" />
                  <Stat label="Fats" value={plan.targets.fats_g} unit="g" />
                </div>
                <p className="text-xs text-slate-500">BMR {plan.targets.bmr} · TDEE {plan.targets.tdee} kcal. {plan.targets.method}</p>
                {plan.user_profile_summary && <p className="text-sm text-slate-300">{plan.user_profile_summary}</p>}
                <Section title="Cautions" items={plan.warnings} tone="warn" />
              </div>

              <div className="flex gap-2" role="tablist">
                {[['daily', 'Daily plan'], ['alts', 'Alternatives'], ['weekly', 'Weekly report']].map(([k, l]) => (
                  <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
                    className={cn('btn flex-1 border', tab === k ? 'border-emerald-500 bg-emerald-500/15 text-emerald-300' : 'border-slate-600 text-slate-300')}>{l}</button>
                ))}
              </div>

              {tab === 'daily' && (
                <div className="space-y-3">
                  {MEALS.map(([k, label]) => {
                    const m = plan.daily_plan[k];
                    return (
                      <div key={k} className="card">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <div><div className="text-xs uppercase tracking-wide text-emerald-300">{label}</div><h3 className="font-semibold">{m.dish_name}</h3></div>
                          <div className="text-right text-xs text-slate-400">{m.calories != null && <div className="text-base font-semibold text-white">{Math.round(m.calories)} kcal</div>}
                            P {m.macros.protein_g ?? '—'}g · C {m.macros.carbs_g ?? '—'}g · F {m.macros.fats_g ?? '—'}g</div>
                        </div>
                        {m.description && <p className="mt-1 text-sm text-slate-300">{m.description}</p>}
                        <p className="mt-2 text-xs text-slate-400">{m.portion_size}{m.prep_style ? ` · ${m.prep_style}` : ''}</p>
                        <p className="mt-2 text-sm text-slate-300">{m.ingredients.join(', ')}</p>
                        {m.reasoning && <p className="mt-2 text-xs italic text-slate-500">{m.reasoning}</p>}
                      </div>
                    );
                  })}
                  <div className="card flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span>Plan total: <strong>{plan.daily_totals.calories} kcal</strong> · P {plan.daily_totals.protein_g}g · C {plan.daily_totals.carbs_g}g · F {plan.daily_totals.fats_g}g</span>
                    {plan.daily_plan.hydration_target && <span className="text-sky-300">💧 {plan.daily_plan.hydration_target}</span>}
                  </div>
                </div>
              )}

              {tab === 'alts' && (
                <div className="space-y-3">
                  {plan.alternatives.length === 0 && <div className="card text-sm text-slate-400">No alternatives were returned.</div>}
                  {plan.alternatives.map((a, i) => (
                    <div key={i} className="card">
                      <h3 className="mb-2 text-sm font-semibold">Instead of {a.original_dish}</h3>
                      {a.alternatives.map((m, j) => (
                        <div key={j} className="mb-2 rounded-xl bg-slate-900/60 p-3 text-sm">
                          <strong>{m.dish_name}</strong> {m.calories != null && <span className="text-xs text-slate-400">· {Math.round(m.calories)} kcal</span>}
                          <p className="text-slate-300">{m.ingredients.join(', ')}</p>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}

              {tab === 'weekly' && (
                <div className="card space-y-4">
                  {!plan.weekly_report ? <p className="text-sm text-slate-400">No weekly report was returned.</p> : (
                    <>
                      {plan.weekly_report.adherence_score != null && <Stat label="Adherence score" value={plan.weekly_report.adherence_score} unit="/100" />}
                      {plan.weekly_report.calorie_balance && <p className="text-sm"><strong>Calories:</strong> {plan.weekly_report.calorie_balance}</p>}
                      {plan.weekly_report.macro_balance && <p className="text-sm"><strong>Macros:</strong> {plan.weekly_report.macro_balance}</p>}
                      {plan.weekly_report.consistency && <p className="text-sm"><strong>Consistency:</strong> {plan.weekly_report.consistency}</p>}
                      <Section title="Highlights" items={plan.weekly_report.highlights} />
                      <Section title="Areas of concern" items={plan.weekly_report.concern_areas} tone="warn" />
                      <Section title="Next week" items={plan.weekly_report.next_week_suggestions} />
                      {plan.weekly_report.motivation && <p className="text-sm italic text-emerald-300">{plan.weekly_report.motivation}</p>}
                    </>
                  )}
                </div>
              )}
              <Disclaimer>{plan.disclaimer}</Disclaimer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
