import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Scan, Thermometer, ShieldCheck, ChefHat, Calendar, ArrowRight, History } from 'lucide-react';
import { getHistory, clearHistory } from '../utils/history';

const modules = [
  { path: '/food-recognition', title: 'Food Recognition', icon: Scan, text: 'Identify a meal from a photo and get estimated nutrition.' },
  { path: '/freshness-detector', title: 'Freshness Detector', icon: Thermometer, text: 'Check visible signs of spoilage, with storage context.' },
  { path: '/hygiene-monitor', title: 'Hygiene Monitor', icon: ShieldCheck, text: 'Preliminary kitchen hygiene review from images or video.' },
  { path: '/kitchen-assistant', title: 'Smart Kitchen', icon: ChefHat, text: 'Turn ingredients or a photo into a step-by-step recipe.' },
  { path: '/meal-planner', title: 'Meal Planner', icon: Calendar, text: 'Personalised daily plan with calorie and macro targets.' },
];

export default function Dashboard() {
  const [history, setHistory] = useState(getHistory);
  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-slate-700/50 bg-gradient-to-br from-emerald-500/10 via-slate-800/60 to-cyan-500/10 p-6 sm:p-10">
        <h1 className="text-3xl font-bold sm:text-4xl">Welcome to <span className="bg-gradient-to-r from-emerald-300 to-cyan-300 bg-clip-text text-transparent">FoodVerse AI</span></h1>
        <p className="mt-3 max-w-2xl text-slate-300">
          A multimodal food intelligence platform that turns images, video, voice and text into structured insights
          about nutrition, freshness, kitchen hygiene, recipes and meal planning.
        </p>
        <Link to="/food-recognition" className="btn-primary mt-6 inline-flex">Analyse a meal <ArrowRight size={16} /></Link>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {modules.map(({ path, title, icon: Icon, text }, i) => (
          <motion.div key={path} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <Link to={path} className="card group block h-full transition hover:border-emerald-500/50">
              <div className="mb-3 inline-flex rounded-xl bg-emerald-500/15 p-3 text-emerald-300"><Icon size={22} /></div>
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-slate-400">{text}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-sm text-emerald-300 group-hover:gap-2">Open <ArrowRight size={14} /></span>
            </Link>
          </motion.div>
        ))}
      </section>

      <section className="card">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-semibold"><History size={18} /> Recent analyses (this browser only)</h2>
          {history.length > 0 && <button className="text-xs text-slate-400 underline" onClick={() => { clearHistory(); setHistory([]); }}>Clear</button>}
        </div>
        {history.length === 0 ? (
          <p className="text-sm text-slate-400">No analyses yet. Results you generate will be listed here. Nothing is stored on a server.</p>
        ) : (
          <ul className="divide-y divide-slate-700/50">
            {history.map((h, i) => (
              <li key={i} className="flex items-center justify-between gap-3 py-2 text-sm">
                <Link to={h.path} className="truncate text-slate-200 hover:text-emerald-300">{h.module}: {h.title}</Link>
                <span className="shrink-0 text-xs text-slate-500">{new Date(h.at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
