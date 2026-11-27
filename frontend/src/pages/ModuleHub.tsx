import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Sparkles,
  Layers,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Search,
} from 'lucide-react';

interface ModuleHubProps {
  title: string;
  subtitle: string;
  badge: string;
  stats?: { label: string; value: string | number; change?: string; color?: string }[];
  shortcuts?: { label: string; desc: string; path: string }[];
}

export const ModuleHub: React.FC<ModuleHubProps> = ({
  title,
  subtitle,
  badge,
  stats = [],
  shortcuts = [],
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header Banner */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#291BB0]/10 border border-[#291BB0]/20 text-[#291BB0] dark:text-indigo-300 text-xs font-bold">
            <Sparkles className="w-3.5 h-3.5 text-[#F04B42]" />
            <span>{badge}</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
            {title}
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xl">
            {subtitle}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold text-xs rounded-xl transition-all"
          >
            Dashboard
          </button>
        </div>
      </div>

      {/* Stats Cards if provided */}
      {stats.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((st, i) => (
            <div
              key={i}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs"
            >
              <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                {st.label}
              </div>
              <div className="mt-2 text-2xl font-black text-slate-900 dark:text-white">
                {st.value}
              </div>
              {st.change && (
                <div className="mt-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>{st.change}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Quick Shortcuts & Sub-sections */}
      {shortcuts.length > 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-[#F04B42]" />
            <span>Available Sub-Sections & Operations</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {shortcuts.map((sc, idx) => (
              <div
                key={idx}
                onClick={() => navigate(sc.path)}
                className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-[#291BB0] dark:hover:border-indigo-400 flex items-center justify-between cursor-pointer transition-all duration-200 hover:-translate-y-0.5 group shadow-xs"
              >
                <div>
                  <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-[#291BB0] dark:group-hover:text-indigo-300 transition-colors">
                    {sc.label}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                    {sc.desc}
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-[#F04B42] group-hover:translate-x-1 transition-all" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ModuleHub;
