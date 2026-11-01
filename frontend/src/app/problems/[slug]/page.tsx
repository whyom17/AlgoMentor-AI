'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Brain, Play, Lightbulb, ChevronRight, AlertCircle, CheckCircle, Clock, Cpu, BarChart3 } from 'lucide-react';
import { api } from '@/lib/api';
import type { ProblemDetail, AttemptResultResponse, HintResponse, SubmitCodeResponse } from '@/types/api';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

const LANGUAGES = ['python', 'java', 'cpp', 'javascript'];

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const cls = difficulty === 'easy' ? 'badge-easy' : difficulty === 'medium' ? 'badge-medium' : 'badge-hard';
  return <span className={cls}>{difficulty}</span>;
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'accepted') return <CheckCircle className="w-4 h-4 text-success-400" />;
  if (status === 'pending' || status === 'running') return <Clock className="w-4 h-4 text-brand-400 animate-pulse" />;
  return <AlertCircle className="w-4 h-4 text-danger-400" />;
}

function StatusLabel({ status }: { status: string }) {
  const map: Record<string, string> = {
    accepted: 'Accepted',
    wrong_answer: 'Wrong Answer',
    time_limit_exceeded: 'TLE',
    runtime_error: 'Runtime Error',
    compile_error: 'Compile Error',
    pending: 'Pending…',
    running: 'Running…',
    internal_error: 'Internal Error',
  };
  return <span className={`status-${status} font-mono text-sm font-semibold`}>{map[status] ?? status}</span>;
}

export default function ProblemPage() {
  const { slug } = useParams<{ slug: string }>();
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<AttemptResultResponse | null>(null);
  const [currentAttemptId, setCurrentAttemptId] = useState<string | null>(null);
  const [hints, setHints] = useState<HintResponse[]>([]);
  const [hintLoading, setHintLoading] = useState(false);
  const [hintPanelOpen, setHintPanelOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'description' | 'result'>('description');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const fetchProblem = async () => {
      try {
        const { data } = await api.get<ProblemDetail>(`/problems/${slug}`);
        setProblem(data);
        setCode(data.starter_code['python'] ?? '');
      } catch {
        // not found
      } finally {
        setLoading(false);
      }
    };
    fetchProblem();
  }, [slug]);

  // Keep code in sync when language changes
  useEffect(() => {
    if (problem) {
      setCode(problem.starter_code[language] ?? `// ${language} starter code not available yet\n`);
    }
  }, [language, problem]);

  const pollResult = useCallback((attemptId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get<AttemptResultResponse>(`/submissions/${attemptId}`);
        setResult(data);
        if (data.status !== 'pending' && data.status !== 'running') {
          if (pollRef.current) clearInterval(pollRef.current);
          setActiveTab('result');
        }
      } catch {
        if (pollRef.current) clearInterval(pollRef.current);
      }
    }, 1500);
  }, []);

  const handleRun = async () => {
    if (!problem) return;
    setSubmitting(true);
    setResult(null);
    try {
      const { data } = await api.post<SubmitCodeResponse>('/submissions', {
        problem_slug: problem.slug,
        language,
        source_code: code,
      });
      setCurrentAttemptId(data.attempt_id);
      setResult({ attempt_id: data.attempt_id, status: 'running', stdout: '', stderr: '', compile_output: '', time_ms: null, memory_kb: null, test_results: [] });
      setActiveTab('result');
      pollResult(data.attempt_id);
    } catch {
      setResult({ attempt_id: '', status: 'internal_error', stdout: '', stderr: 'Submission failed. Is the backend running?', compile_output: '', time_ms: null, memory_kb: null, test_results: [] });
      setActiveTab('result');
    } finally {
      setSubmitting(false);
    }
  };

  const handleHint = async (level: number) => {
    if (!currentAttemptId) {
      alert('Run your code at least once before requesting a hint.');
      return;
    }
    setHintLoading(true);
    try {
      const { data } = await api.post<HintResponse>('/hints', {
        attempt_id: currentAttemptId,
        hint_level: level,
      });
      setHints((prev) => [...prev, data]);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Hint unavailable.';
      setHints((prev) => [...prev, { hint_level: level, text: msg, model_used: '', was_filtered: false, latency_ms: 0 }]);
    } finally {
      setHintLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="min-h-screen bg-surface-900 flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-12 h-12 text-danger-400" />
        <p className="text-gray-400">Problem not found.</p>
        <Link href="/problems" className="text-brand-400 hover:underline">← Back to problems</Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-900 flex flex-col">
      {/* Top bar */}
      <div className="h-14 glass border-b border-surface-700 flex items-center justify-between px-5 flex-shrink-0 z-40">
        <div className="flex items-center gap-4">
          <Link href="/problems" className="flex items-center gap-1.5 text-gray-400 hover:text-white transition-colors text-sm">
            <Brain className="w-4 h-4 text-brand-400" />
            <span>AlgoMentor</span>
          </Link>
          <ChevronRight className="w-3 h-3 text-gray-700" />
          <span className="text-white font-medium text-sm">{problem.title}</span>
          <DifficultyBadge difficulty={problem.difficulty} />
        </div>

        <div className="flex items-center gap-3">
          <select
            id="language-select"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="text-sm bg-surface-800 border border-surface-600 text-white rounded-lg px-3 py-1.5 focus:outline-none focus:border-brand-500 transition-all font-mono"
          >
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>

          <button
            id="run-code-btn"
            onClick={handleRun}
            disabled={submitting}
            className="flex items-center gap-2 px-5 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-400 disabled:opacity-50 text-white text-sm font-semibold transition-all glow-blue"
          >
            <Play className="w-3.5 h-3.5" /> {submitting ? 'Running…' : 'Submit'}
          </button>

          <button
            id="hint-panel-btn"
            onClick={() => setHintPanelOpen(!hintPanelOpen)}
            className="flex items-center gap-2 px-4 py-1.5 rounded-lg glass border border-accent-500/40 text-accent-400 hover:bg-accent-500/10 text-sm font-medium transition-all"
          >
            <Lightbulb className="w-3.5 h-3.5" /> Hint
          </button>

          <Link href="/dashboard" className="p-2 rounded-lg text-gray-500 hover:text-white hover:bg-surface-700 transition-all">
            <BarChart3 className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Main split layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Problem + Result */}
        <div className="w-[440px] flex-shrink-0 border-r border-surface-700 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-surface-700">
            {(['description', 'result'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-5 py-3 text-sm font-medium transition-all ${
                  activeTab === tab
                    ? 'text-white border-b-2 border-brand-500'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {tab === 'description' ? 'Problem' : 'Result'}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            {activeTab === 'description' ? (
              <div className="space-y-5">
                <div>
                  <h1 className="text-xl font-bold text-white mb-3">{problem.title}</h1>
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {problem.tags.map((t) => (
                      <span key={t} className="text-xs text-gray-500 bg-surface-700 px-2 py-0.5 rounded-full">{t}</span>
                    ))}
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none text-gray-300 leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{problem.description}</ReactMarkdown>
                  </div>
                </div>

                {problem.examples.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-3">Examples</h3>
                    <div className="space-y-3">
                      {problem.examples.map((ex, i) => (
                        <div key={i} className="glass rounded-xl p-4 border border-surface-600">
                          <div className="text-xs font-mono text-gray-400 mb-1">
                            <span className="text-gray-500">Input: </span>{ex.input}
                          </div>
                          <div className="text-xs font-mono text-gray-400">
                            <span className="text-gray-500">Output: </span>{ex.output}
                          </div>
                          {ex.explanation && (
                            <div className="text-xs text-gray-600 mt-2">{ex.explanation}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">Constraints</h3>
                  <pre className="text-xs text-gray-500 font-mono leading-relaxed whitespace-pre-wrap">{problem.constraints}</pre>
                </div>
              </div>
            ) : (
              <div>
                {result ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3 p-4 glass rounded-xl border border-surface-600">
                      <StatusIcon status={result.status} />
                      <div>
                        <StatusLabel status={result.status} />
                        {result.time_ms && (
                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{result.time_ms.toFixed(0)}ms</span>
                            {result.memory_kb && <span className="flex items-center gap-1"><Cpu className="w-3 h-3" />{(result.memory_kb / 1024).toFixed(1)}MB</span>}
                          </div>
                        )}
                      </div>
                    </div>

                    {result.stdout && (
                      <div>
                        <div className="text-xs font-semibold text-gray-500 mb-2">Stdout</div>
                        <pre className="text-xs font-mono text-gray-300 bg-surface-800 rounded-xl p-4 overflow-auto max-h-48 whitespace-pre-wrap">{result.stdout}</pre>
                      </div>
                    )}
                    {result.stderr && (
                      <div>
                        <div className="text-xs font-semibold text-danger-400 mb-2">Stderr</div>
                        <pre className="text-xs font-mono text-danger-300 bg-danger-500/5 border border-danger-500/20 rounded-xl p-4 overflow-auto max-h-48 whitespace-pre-wrap">{result.stderr}</pre>
                      </div>
                    )}
                    {result.compile_output && (
                      <div>
                        <div className="text-xs font-semibold text-orange-400 mb-2">Compile output</div>
                        <pre className="text-xs font-mono text-orange-300 bg-orange-500/5 border border-orange-500/20 rounded-xl p-4 overflow-auto max-h-48 whitespace-pre-wrap">{result.compile_output}</pre>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-600">
                    Submit your code to see results.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right: Monaco Editor */}
        <div className="flex-1 min-w-0 relative">
          <MonacoEditor
            height="100%"
            language={language === 'cpp' ? 'cpp' : language === 'javascript' ? 'javascript' : language === 'java' ? 'java' : 'python'}
            value={code}
            onChange={(val) => setCode(val ?? '')}
            theme="vs-dark"
            options={{
              fontSize: 14,
              fontFamily: '"JetBrains Mono", "Fira Code", monospace',
              fontLigatures: true,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              lineNumbers: 'on',
              renderLineHighlight: 'line',
              padding: { top: 16 },
              smoothScrolling: true,
              cursorBlinking: 'smooth',
              tabSize: 4,
            }}
          />
        </div>
      </div>

      {/* Hint drawer */}
      <AnimatePresence>
        {hintPanelOpen && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-14 bottom-0 w-96 glass-elevated border-l border-surface-600 flex flex-col z-30"
          >
            <div className="p-4 border-b border-surface-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-accent-400" />
                <span className="font-semibold text-white">Hint Ladder</span>
              </div>
              <button onClick={() => setHintPanelOpen(false)} className="text-gray-500 hover:text-white transition-colors text-lg leading-none">×</button>
            </div>

            {/* Level buttons */}
            <div className="p-4 border-b border-surface-700 grid grid-cols-2 gap-2">
              {[
                { level: 1, label: 'L1 Clarify', desc: 'Socratic question' },
                { level: 2, label: 'L2 Pattern', desc: 'Technique family' },
                { level: 3, label: 'L3 Skeleton', desc: 'Pseudocode outline' },
                { level: 4, label: 'L4 Walkthrough', desc: 'Full solution' },
              ].map((h) => (
                <button
                  key={h.level}
                  id={`hint-level-${h.level}`}
                  onClick={() => handleHint(h.level)}
                  disabled={hintLoading}
                  className="p-3 rounded-xl glass border border-surface-600 hover:border-accent-500/40 hover:bg-accent-500/5 text-left transition-all disabled:opacity-50"
                >
                  <div className="text-xs font-bold text-accent-400 font-mono">{h.label}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{h.desc}</div>
                </button>
              ))}
            </div>

            {/* Hint responses */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {hints.length === 0 && !hintLoading && (
                <div className="text-center text-gray-600 text-sm py-8">
                  No hints yet. Click a level above after submitting code.
                </div>
              )}
              {hintLoading && (
                <div className="flex items-center gap-3 text-accent-400 text-sm">
                  <div className="w-4 h-4 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
                  Thinking…
                </div>
              )}
              {hints.map((h, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass rounded-xl p-4 border border-accent-500/20"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs font-bold text-accent-400 font-mono bg-accent-500/10 px-2 py-0.5 rounded">
                      L{h.hint_level}
                    </span>
                    {h.was_filtered && (
                      <span className="text-xs text-warning-400 bg-warning-500/10 px-2 py-0.5 rounded">filtered</span>
                    )}
                    <span className="text-xs text-gray-600 ml-auto font-mono">{h.latency_ms}ms</span>
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none text-gray-300">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{h.text}</ReactMarkdown>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
