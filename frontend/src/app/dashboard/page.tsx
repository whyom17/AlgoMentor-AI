'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Brain,
  TrendingUp,
  Target,
  Calendar,
  ArrowRight,
  LogOut,
  Flame,
  BookOpen,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import type { MasteryDashboard, RecommendedProblem } from '@/types/api';

const LABEL_COLORS: Record<string, string> = {
  unseen: 'text-gray-600',
  struggling: 'text-danger-400',
  seen: 'text-warning-400',
  practicing: 'text-brand-400',
  proficient: 'text-accent-400',
  owned: 'text-success-400',
};

const LABEL_BG: Record<string, string> = {
  unseen: 'bg-gray-700/30',
  struggling: 'bg-danger-500/10 border-danger-500/20',
  seen: 'bg-warning-500/10 border-warning-500/20',
  practicing: 'bg-brand-500/10 border-brand-500/20',
  proficient: 'bg-accent-500/10 border-accent-500/20',
  owned: 'bg-success-500/10 border-success-500/20',
};

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="h-1.5 w-full bg-surface-700 rounded-full overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${score * 100}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500"
      />
    </div>
  );
}

export default function DashboardPage() {
  const { user, logout } = useAuthStore();
  const [dashboard, setDashboard] = useState<MasteryDashboard | null>(null);
  const [recs, setRecs] = useState<RecommendedProblem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const [dashRes, recsRes] = await Promise.all([
          api.get<MasteryDashboard>('/mastery/dashboard'),
          api.get<RecommendedProblem[]>('/mastery/recommendations'),
        ]);
        setDashboard(dashRes.data);
        setRecs(recsRes.data);
      } catch {
        // not authenticated — store stays null
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  const ownedCount = dashboard?.topics.filter((t) => t.label === 'owned').length ?? 0;
  const reviewDueCount = dashboard?.topics.filter(
    (t) => t.next_review_at && new Date(t.next_review_at) <= new Date()
  ).length ?? 0;

  return (
    <div className="min-h-screen bg-surface-900">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-surface-700">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/problems" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center">
              <Brain className="w-4 h-4 text-brand-400" />
            </div>
            <span className="font-bold text-white">AlgoMentor</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/problems" className="text-sm text-gray-400 hover:text-white transition-colors">
              Problems
            </Link>
            {user && (
              <>
                <span className="text-sm text-gray-500">{user.username}</span>
                <button
                  onClick={logout}
                  className="p-2 rounded-lg text-gray-500 hover:text-danger-400 hover:bg-danger-500/10 transition-all"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      <main className="pt-24 pb-16 px-6 max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <h1 className="text-3xl font-bold text-white mb-1">Mastery Dashboard</h1>
          <p className="text-gray-400">Your per-topic learning health, decay-adjusted.</p>
        </motion.div>

        {loading ? (
          <div className="grid grid-cols-4 gap-4 mb-8">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 rounded-2xl shimmer" />
            ))}
          </div>
        ) : dashboard ? (
          <>
            {/* Stat cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {[
                { icon: BookOpen, label: 'Total Solved', value: dashboard.total_solved, color: 'text-brand-400' },
                { icon: TrendingUp, label: 'Total Attempts', value: dashboard.total_attempts, color: 'text-accent-400' },
                { icon: Target, label: 'Topics Owned', value: ownedCount, color: 'text-success-400' },
                { icon: Calendar, label: 'Reviews Due', value: reviewDueCount, color: 'text-warning-400' },
              ].map((stat) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="glass-elevated rounded-2xl p-5 border border-surface-600"
                >
                  <stat.icon className={`w-5 h-5 ${stat.color} mb-3`} />
                  <div className="text-3xl font-bold text-white">{stat.value}</div>
                  <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
                </motion.div>
              ))}
            </div>

            {/* Recommendations */}
            {recs.length > 0 && (
              <div className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                  <Flame className="w-4 h-4 text-warning-400" />
                  <h2 className="text-lg font-semibold text-white">Recommended next</h2>
                </div>
                <div className="grid gap-3">
                  {recs.map((r, i) => (
                    <motion.div
                      key={r.slug}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.06 }}
                    >
                      <Link
                        href={`/problems/${r.slug}`}
                        className="flex items-center gap-4 px-5 py-4 rounded-xl glass border border-surface-700 hover:border-brand-500/40 hover:bg-surface-800/60 transition-all group"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-1">
                            <span className="font-medium text-white group-hover:text-brand-300 transition-colors">
                              {r.title}
                            </span>
                            <span
                              className={
                                r.difficulty === 'easy'
                                  ? 'badge-easy'
                                  : r.difficulty === 'medium'
                                  ? 'badge-medium'
                                  : 'badge-hard'
                              }
                            >
                              {r.difficulty}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">{r.reason}</div>
                        </div>
                        <ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-brand-400 transition-colors" />
                      </Link>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {/* Topic mastery grid */}
            <div>
              <h2 className="text-lg font-semibold text-white mb-4">Topic mastery</h2>
              {dashboard.topics.length === 0 ? (
                <div className="glass rounded-2xl p-12 border border-surface-700 text-center text-gray-500">
                  <BookOpen className="w-10 h-10 mx-auto mb-3 text-gray-700" />
                  <p>No mastery data yet. Solve some problems to see your progress.</p>
                  <Link
                    href="/problems"
                    className="inline-flex items-center gap-2 mt-4 text-brand-400 hover:text-brand-300 text-sm font-medium transition-colors"
                  >
                    Browse problems <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 gap-3">
                  {dashboard.topics.map((topic, i) => (
                    <motion.div
                      key={topic.topic_tag}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className={`glass-elevated rounded-xl p-4 border ${LABEL_BG[topic.label] ?? 'border-surface-600'}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-white text-sm">{topic.topic_tag}</span>
                        <span className={`text-xs font-semibold ${LABEL_COLORS[topic.label] ?? 'text-gray-400'}`}>
                          {topic.label}
                        </span>
                      </div>
                      <ScoreBar score={topic.score} />
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-600">
                        <span>{topic.attempt_count} attempts</span>
                        <span>{topic.solve_count} solved</span>
                        {topic.next_review_at && (
                          <span className="ml-auto text-warning-500/80">
                            review {new Date(topic.next_review_at) <= new Date() ? 'now' : `in ${Math.ceil((new Date(topic.next_review_at).getTime() - Date.now()) / 86400000)}d`}
                          </span>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="text-center py-24 text-gray-500">
            <Brain className="w-12 h-12 mx-auto mb-4 text-gray-700" />
            <p className="mb-4">Sign in to view your mastery dashboard.</p>
            <Link href="/login" className="text-brand-400 hover:underline text-sm font-medium">
              Sign in →
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
