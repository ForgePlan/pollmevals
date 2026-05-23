export type RunType = "smoke" | "weekly" | "flagship_triggered" | "calibration" | "ablation";

export interface PollmevalsModel {
  slug: string;
  name: string;
  vendor: string;
  versionTag: string;
  isOpenWeight: boolean;
  contextWindow: number;
  maxOutputTokens: number;
}

export interface PollmevalsTask {
  schema_version: "pollmevals.task.v1";
  id: string;
  slug: string;
  version: string;
  category: string;
  difficulty: "easy" | "medium" | "hard";
  language: string;
  description: string;
  prompt_template: string;
  success_criteria: string[];
  evaluator_commands?: string[];
  weight_components: Record<string, number>;
}

export interface PollmevalsStack {
  schema_version: "pollmevals.stack.v1";
  slug: string;
  name: string;
  base_model_slug: string;
  agent_cli: string | null;
  layers: Record<string, boolean | string | null>;
  execution: Record<string, unknown>;
  limits: Record<string, number>;
}

export interface PollmevalsEvalSummary {
  eval_id: string;
  model_slug: string;
  stack_slug: string;
  task_slug: string;
  seed: number;
  region: string;
  final_score: number;
  cost_usd: number;
  total_latency_ms: number;
}

export interface PollmevalsRunManifest {
  schema_version: "pollmevals.run_manifest.v1";
  run_hash: string;
  run_type: RunType;
  created_at: string;
  methodology_version: string;
  models: PollmevalsModel[];
  tasks: PollmevalsTask[];
  stacks: PollmevalsStack[];
  evals: PollmevalsEvalSummary[];
  artifacts?: Array<Record<string, unknown>>;
}
