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

/**
 * One atomic binary requirement item in a task's requirements array (RFC-004).
 *
 * check_type "auto"  — executable check; feeds the deterministic component score
 *                      via 10 × (passed auto-reqs / total auto-reqs) for maps_to.
 * check_type "judge" — recorded in evaluator_json for traceability only (v0.2).
 *                      passed is always null for judge items at run time.
 */
export interface TaskRequirement {
  /** Unique id within the task. Pattern: /^R\d+$/. Example: "R7". */
  id: string;
  /** One atomic, binary assertion phrased so it is unambiguously true or false. */
  text: string;
  check_type: "auto" | "judge";
  /**
   * For auto: a weight_components key (e.g. "correctness", "type_safety").
   * For judge: a rubric criterion name (e.g. "code_clarity", "pattern_match").
   */
  maps_to: string;
  /** 1-based index of the numbered item in prompt_template this requirement traces to. */
  prompt_ref: number;
}

/**
 * One entry in evaluator_json.requirement_results[] (RFC-004).
 *
 * Emitted by the deterministic evaluator for every requirement in the task.
 * auto items carry a boolean; judge items carry null (recorded-only in v0.2).
 */
export interface RequirementResult {
  /** The requirement id, matching TaskRequirement.id. */
  id: string;
  check_type: "auto" | "judge";
  /**
   * true/false for auto items (wired to executable check).
   * null for judge items (recorded for traceability, not scored in v0.2).
   */
  passed: boolean | null;
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
  /** Atomic binary requirements (RFC-004). Optional — old task packs without this field remain valid. */
  requirements?: TaskRequirement[];
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
