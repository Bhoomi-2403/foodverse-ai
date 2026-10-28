import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Scan, Thermometer, ShieldCheck, ChefHat, Calendar, Menu, X } from 'lucide-react';
import { cn } from '../utils/cn';
import { api } from '../api/client';

export const navItems = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/food-recognition', label: 'Food Recognition', icon: Scan },
  { path: '/freshness-detector', label: 'Freshness Detector', icon: Thermometer },
  { path: '/hygiene-monitor', label: 'Hygiene Monitor', icon: ShieldCheck },
  { path: '/kitchen-assistant', label: 'Smart Kitchen', icon: ChefHat },
  { path: '/meal-planner', label: 'Meal Planner', icon: Calendar },
];

function StatusDot() {
  const [state, setState] = useState('checking');
  useEffect(() => {
    let alive = true;
    api.health()
      .then((h) => alive && setState(h.ai_configured ? 'ready' : 'nokey'))
      .catch(() => alive && setState('offline'));
    return () => { alive = false; };
  }, []);
  const map = {
    checking: ['bg-slate-500', 'Checking backend…'],
    ready: ['bg-emerald-400', 'Backend + AI ready'],
    nokey: ['bg-amber-400', 'Backend up, GROQ_API_KEY missing'],
    offline: ['bg-red-400', 'Backend offline'],
  };
  const [dot, text] = map[state];
  return (
    <div className="flex items-center gap-2 text-xs text-slate-400" role="status">
      <span className={cn('h-2 w-2 rounded-full', dot)} /> {text}
    </div>
  );
}

export default function Layout({ children }) {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <div className="flex min-h-screen bg-slate-900 font-sans selection:bg-emerald-500 selection:text-slate-900">
      {open && <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setOpen(false)} aria-hidden />}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-700/50 bg-slate-800/95 backdrop-blur-xl transition-transform lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex items-center justify-between border-b border-slate-700/50 p-5">
          <Link to="/" className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-500 text-xl" aria-hidden>🍽️</span>
            <span className="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-xl font-bold text-transparent">FoodVerse</span>
          </Link>
          <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X size={20} /></button>
        </div>
        <nav className="flex-1 space-y-1 p-3" aria-label="Main">
          {navItems.map(({ path, label, icon: Icon }) => {
            const active = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition',
                  active ? 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30' : 'text-slate-400 hover:bg-slate-700/40 hover:text-white'
                )}
              >
                <Icon size={18} /> {label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-700/50 p-4"><StatusDot /></div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-700/50 bg-slate-900/80 px-4 py-3 backdrop-blur-xl sm:px-6">
          <button className="rounded-lg p-2 hover:bg-slate-800 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={20} /></button>
          <h2 className="text-sm font-medium text-slate-300">
            {navItems.find((n) => n.path === location.pathname)?.label || 'FoodVerse AI'}
          </h2>
          <span className="ml-auto hidden text-xs text-slate-500 sm:block">Multimodal food intelligence</span>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
