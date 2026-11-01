'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Brain, Search, Filter, LogOut, BarChart3, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import type { ProblemListItem } from '@/types/api';

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: 'badge-easy',
  medium: 'badge-medium',
  hard: 'badge-hard',
};

export default function ProblemsPage() {
  const { user, logout } = useAuthStore();
  const [problems, setProblems] = useState<ProblemListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [diffFilter, setDiffFilter] = useState<string>('');

  useEffect(() => {
    const fetch = async () => {
      try {
        const params = new URLSearchParams();
        if (diffFilter) params.set('difficulty', diffFilter);
        const { data } = await api.get<ProblemListItem[]>(`/problems?${params}`);
        setProblems(data);
      } catch {
        // handle error
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [diffFilter]);

  const filtered = problems.filter((p) =>
    p.title.toLowerCase().includes(search.toLowerCase()) ||
    p.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-surface-900">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-surface-700">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center">
              <Brain className="w-4 h-4 text-brand-400" />
            </div>
            <span className="font-bold text-white">AlgoMentor</span>
          </Link>

          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-surface-700 transition-all"
              title="Mastery Dashboard"
            >
              <BarChart3 className="w-4 h-4" />
            </Link>
            {user && (
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-400">{user.username}</span>
                <button
                  onClick={logout}
                  className="p-2 rounded-lg text-gray-500 hover:text-danger-400 hover:bg-danger-500/10 transition-all"
                  title="Sign out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      <main className="pt-24 pb-16 px-6 max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Problem Bank</h1>
          <p className="text-gray-400">10 curated core-pattern problems · Phase 0</p>
        </motion.div>

        {/* Filters */}
        <div className="flex gap-3 mb-7 flex-wrap">
          <div className="relative flex-1 min-w-56">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              id="problem-search"
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search problems or tags…"
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-surface-800 border border-surface-600 text-white placeholder-gray-600 focus:outline-none focus:border-brand-500 transition-all text-sm"
            />
          </div>
          <div className="flex gap-2">
            {['', 'easy', 'medium', 'hard'].map((d) => (
              <button
                key={d}
                onClick={() => setDiffFilter(d)}
                className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all border ${
                  diffFilter === d
                    ? 'bg-brand-500/20 border-brand-500/50 text-brand-300'
                    : 'bg-surface-800 border-surface-600 text-gray-400 hover:text-white'
                }`}
              >
                {d === '' ? 'All' : d.charAt(0).toUpperCase() + d.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Problem list */}
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-16 rounded-xl shimmer" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((p, i) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <Link
                  href={`/problems/${p.slug}`}
                  className="flex items-center gap-4 px-5 py-4 rounded-xl glass border border-surface-700 hover:border-brand-500/40 hover:bg-surface-800/60 transition-all group"
                >
                  <CheckCircle2 className="w-4 h-4 text-gray-700 group-hover:text-brand-500/40 transition-colors flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-white group-hover:text-brand-300 transition-colors truncate">
                        {p.title}
                      </span>
                      <span className={DIFFICULTY_LABELS[p.difficulty] || ''}>
                        {p.difficulty}
                      </span>
                    </div>
                    <div className="flex gap-1.5 mt-1.5 flex-wrap">
                      {p.tags.map((t) => (
                        <span key={t} className="text-xs text-gray-600 bg-surface-700 px-2 py-0.5 rounded-full">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                  <span className="text-xs text-gray-600 font-mono flex-shrink-0">{p.pattern_family}</span>
                </Link>
              </motion.div>
            ))}
            {filtered.length === 0 && (
              <div className="text-center py-16 text-gray-500">
                No problems match your filters.
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
