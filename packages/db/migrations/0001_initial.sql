CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  vendor TEXT NOT NULL,
  version_tag TEXT NOT NULL,
  is_open_weight BOOLEAN NOT NULL DEFAULT false,
  context_window INTEGER NOT NULL,
  max_output_tokens INTEGER NOT NULL,
  added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deprecated_at TIMESTAMPTZ
);

CREATE TABLE model_providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_id UUID NOT NULL REFERENCES models(id),
  provider_name TEXT NOT NULL,
  endpoint_url TEXT NOT NULL,
  region TEXT NOT NULL,
  price_input_per_mtok NUMERIC(10,4) NOT NULL,
  price_output_per_mtok NUMERIC(10,4) NOT NULL,
  pricing_captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  rate_limit_rpm INTEGER,
  rate_limit_tpm INTEGER
);

CREATE TABLE stacks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  base_model_id UUID REFERENCES models(id),
  agent_cli TEXT,
  layers_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  execution_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  limits_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT NOT NULL,
  version TEXT NOT NULL,
  category TEXT NOT NULL,
  difficulty TEXT NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
  language TEXT NOT NULL,
  description_md TEXT NOT NULL,
  prompt_template TEXT NOT NULL,
  gold_solution_uri TEXT,
  evaluator_uri TEXT,
  expected_tokens_in INTEGER,
  expected_tokens_out INTEGER,
  added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  retired_at TIMESTAMPTZ,
  parent_task_id UUID REFERENCES tasks(id),
  UNIQUE(slug, version)
);

CREATE TABLE runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hash TEXT UNIQUE NOT NULL,
  run_type TEXT NOT NULL CHECK (run_type IN ('smoke','weekly','flagship_triggered','calibration','ablation')),
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  methodology_version TEXT NOT NULL,
  manifest_uri TEXT NOT NULL,
  total_cost_usd NUMERIC(10,2),
  total_input_tokens BIGINT,
  total_output_tokens BIGINT
);

CREATE TABLE evals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES runs(id),
  model_id UUID NOT NULL REFERENCES models(id),
  stack_id UUID REFERENCES stacks(id),
  task_id UUID NOT NULL REFERENCES tasks(id),
  seed INTEGER NOT NULL,
  region TEXT NOT NULL,
  raw_output_uri TEXT NOT NULL,
  normalized_output_uri TEXT,
  ttft_ms INTEGER,
  total_latency_ms INTEGER,
  tokens_in INTEGER,
  tokens_out INTEGER,
  cost_usd NUMERIC(10,6),
  automatic_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  final_score NUMERIC(4,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE judgments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  eval_id UUID NOT NULL REFERENCES evals(id),
  judge_model_id UUID NOT NULL REFERENCES models(id),
  judge_order INTEGER NOT NULL,
  rubric_version TEXT NOT NULL,
  rubric_scores_json JSONB NOT NULL,
  total_score NUMERIC(4,2) NOT NULL,
  reasoning_text_uri TEXT,
  agreement_with_consensus NUMERIC(4,3)
);

CREATE TABLE calibration_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  judge_model_id UUID NOT NULL REFERENCES models(id),
  calibration_task_slug TEXT NOT NULL,
  expected_score NUMERIC(4,2) NOT NULL,
  given_score NUMERIC(4,2) NOT NULL,
  deviation NUMERIC(4,2) NOT NULL,
  ran_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
