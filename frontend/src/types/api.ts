/**
 * Type definitions for the AlgoMentor AI API.
 */

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
}

export interface User {
  id: string;
  email: string;
  username: string;
  is_pro: boolean;
  created_at: string;
}

export interface ProblemListItem {
  id: string;
  slug: string;
  title: string;
  difficulty: 'easy' | 'medium' | 'hard';
  tags: string[];
  pattern_family: string;
}

export interface Example {
  input: string;
  output: string;
  explanation?: string;
}

export interface ProblemDetail {
  id: string;
  slug: string;
  title: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  tags: string[];
  pattern_family: string;
  starter_code: Record<string, string>;
  constraints: string;
  examples: Example[];
  time_limit_ms: number;
  memory_limit_mb: number;
}

export type SubmissionStatus =
  | 'pending'
  | 'running'
  | 'accepted'
  | 'wrong_answer'
  | 'time_limit_exceeded'
  | 'memory_limit_exceeded'
  | 'runtime_error'
  | 'compile_error'
  | 'internal_error';

export interface SubmitCodeResponse {
  attempt_id: string;
  judge0_token: string;
  status: string;
}

export interface AttemptResultResponse {
  attempt_id: string;
  status: SubmissionStatus;
  stdout: string;
  stderr: string;
  compile_output: string;
  time_ms: number | null;
  memory_kb: number | null;
  test_results: Array<Record<string, unknown>>;
}

export interface HintResponse {
  hint_level: number;
  text: string;
  model_used: string;
  was_filtered: boolean;
  latency_ms: number;
}

export interface TopicMastery {
  topic_tag: string;
  score: number;
  label: string;
  attempt_count: number;
  solve_count: number;
  next_review_at: string | null;
}

export interface MasteryDashboard {
  user_id: string;
  total_solved: number;
  total_attempts: number;
  topics: TopicMastery[];
}

export interface RecommendedProblem {
  slug: string;
  title: string;
  difficulty: 'easy' | 'medium' | 'hard';
  reason: string;
  pattern_family: string;
}
