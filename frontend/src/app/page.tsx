'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Brain, Code2, TrendingUp, Zap, ArrowRight, CheckCircle } from 'lucide-react';

const features = [
  {
    icon: Brain,
    title: 'Execution-Aware Hints',
    description:
      'Hints grounded in your actual variable state at the point of failure — not generic guesses.',
    color: 'text-brand-400',
    bg: 'bg-brand-500/10 border-brand-500/20',
  },
  {
    icon: TrendingUp,
    title: 'Mastery Tracking',
    description:
      'SM-2 spaced repetition with decay. Know exactly which topics you own vs. are slipping.',
    color: 'text-accent-400',
    bg: 'bg-accent-500/10 border-accent-500/20',
  },
  {
    icon: Code2,
    title: 'Gated Hint Ladder',
    description:
      'Four levels — clarifying question, pattern nudge, pseudocode, full walkthrough. No spoilers at L1-L2.',
    color: 'text-success-400',
    bg: 'bg-success-500/10 border-success-500/20',
  },
  {
    icon: Zap,
    title: 'Adaptive Recommendations',
    description:
      'Isomorphic variant problems served at the right time — same invariant, different skin.',
    color: 'text-warning-400',
    bg: 'bg-warning-500/10 border-warning-500/20',
  },
];

const stats = [
  { label: 'Core Problems', value: '75+' },
  { label: 'Pattern Families', value: '14' },
  { label: 'Hint Levels', value: '4' },
  { label: 'Languages', value: '6' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface-900 overflow-hidden">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-surface-600">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center">
              <Brain className="w-4 h-4 text-brand-400" />
            </div>
            <span className="font-bold text-white">AlgoMentor</span>
            <span className="text-xs text-brand-400 font-mono ml-1 bg-brand-500/10 px-1.5 py-0.5 rounded border border-brand-500/20">
              AI
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="text-sm px-4 py-2 rounded-lg bg-brand-500 hover:bg-brand-600 text-white font-medium transition-all glow-blue"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-24 px-6 relative">
        {/* Background glow */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-brand-500/8 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-40 left-1/3 w-[400px] h-[400px] bg-accent-500/6 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center relative">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-full glass border border-brand-500/30 text-brand-300 mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
              Phase 0 — MVP now live
            </div>

            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6">
              <span className="gradient-text">Stop memorising.</span>
              <br />
              <span className="text-white">Start understanding.</span>
            </h1>

            <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              AlgoMentor AI is a DSA learning platform that acts as a persistent personal
              mentor — execution-aware hints, mastery decay, and adaptive spaced repetition
              built into every problem.
            </p>

            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link
                href="/register"
                className="flex items-center gap-2 px-8 py-3.5 rounded-xl bg-brand-500 hover:bg-brand-400 text-white font-semibold text-base transition-all glow-blue"
              >
                Start for free <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                href="/problems"
                className="flex items-center gap-2 px-8 py-3.5 rounded-xl glass border border-surface-500 text-gray-300 hover:text-white font-semibold text-base transition-all"
              >
                Browse problems
              </Link>
            </div>
          </motion.div>

          {/* Stats row */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-16 grid grid-cols-4 gap-4"
          >
            {stats.map((s) => (
              <div key={s.label} className="glass rounded-xl p-4 border border-surface-600">
                <div className="text-3xl font-bold gradient-text">{s.value}</div>
                <div className="text-sm text-gray-500 mt-1">{s.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white mb-4">
              Everything LeetCode + ChatGPT can&apos;t be
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              The real competitor isn&apos;t another platform — it&apos;s you with two tabs open.
              AlgoMentor is faster and more precise than tab-switching.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className={`glass-elevated rounded-2xl p-6 border ${f.bg}`}
              >
                <div className={`w-10 h-10 rounded-xl ${f.bg} border flex items-center justify-center mb-4`}>
                  <f.icon className={`w-5 h-5 ${f.color}`} />
                </div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{f.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Hint ladder visual */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-12">
            The 4-level hint ladder
          </h2>
          <div className="space-y-3">
            {[
              { level: 1, label: 'Clarifying question', detail: 'What does the problem actually ask? What invariant might you be missing?', badge: 'Free' },
              { level: 2, label: 'Pattern nudge', detail: 'Names the technique family — two-pointer, sliding window, monotomic stack — without revealing the algorithm.', badge: 'Free' },
              { level: 3, label: 'Pseudocode skeleton', detail: 'Structural outline of the solution with key invariant. No runnable code at this level.', badge: 'Pro: 3/day free' },
              { level: 4, label: 'Full walkthrough', detail: 'Complete algorithm with working code. Gated behind 3+ attempts or 10+ minutes. Logged as assisted.', badge: 'Pro: unlimited' },
            ].map((h) => (
              <div key={h.level} className="glass rounded-xl p-5 border border-surface-600 flex gap-5 items-start">
                <div className="w-9 h-9 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center flex-shrink-0">
                  <span className="text-brand-300 font-bold font-mono text-sm">L{h.level}</span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-semibold text-white">{h.label}</span>
                    <span className="text-xs text-gray-500 bg-surface-700 px-2 py-0.5 rounded-full">{h.badge}</span>
                  </div>
                  <p className="text-sm text-gray-400">{h.detail}</p>
                </div>
                <CheckCircle className="w-4 h-4 text-success-400 flex-shrink-0 mt-0.5" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-4xl font-bold text-white mb-4">Ready to actually learn DSA?</h2>
          <p className="text-gray-400 mb-8">No credit card. 10 problems, 14 patterns, real mentorship.</p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-10 py-4 rounded-xl bg-brand-500 hover:bg-brand-400 text-white font-semibold text-lg transition-all glow-blue"
          >
            Start for free <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-surface-700 py-8 px-6 text-center text-sm text-gray-600">
        © 2026 AlgoMentor AI · Phase 0 MVP
      </footer>
    </div>
  );
}
