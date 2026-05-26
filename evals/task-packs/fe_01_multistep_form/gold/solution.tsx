// source: own-authored 2026-05-26 by gogocat (license: MIT)
// gold/solution — accessible 3-step React form with per-blur validation,
// sessionStorage draft persistence, focus management on step transitions,
// polite aria-live announcements, and a discriminated UI state machine.
// Public API matches task.yaml prompt_template verbatim. tsc --strict clean.

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { ChangeEvent, FocusEvent, FormEvent, JSX } from "react";

export interface FormData {
  name: string;
  email: string;
  street: string;
  city: string;
  zip: string;
}

export interface MultiStepFormProps {
  onSubmit: (data: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

export type StepKey = "personal" | "address" | "review";
const STEPS: readonly StepKey[] = ["personal", "address", "review"] as const;
const STORAGE_KEY = "fe01:multistep-form:draft";
const EMPTY: FormData = { name: "", email: "", street: "", city: "", zip: "" };
const LABEL: Record<keyof FormData, string> = {
  name: "Full name", email: "Email address", street: "Street address",
  city: "City", zip: "Postal code",
};
const AUTOFILL: Record<keyof FormData, string> = {
  name: "name", email: "email", street: "street-address",
  city: "address-level2", zip: "postal-code",
};

type UiState =
  | { kind: "idle" } | { kind: "loading" }
  | { kind: "success" } | { kind: "error"; message: string };

export function validateField(field: keyof FormData, value: string): string | null {
  const t = value.trim();
  if (t.length === 0) return "This field is required.";
  if (field === "email" && !t.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) return "Enter a valid email address.";
  if (field === "zip" && !t.match(/^\d{4,10}$/)) return "Enter a valid postal code (4-10 digits).";
  return null;
}

export function fieldsForStep(step: StepKey): readonly (keyof FormData)[] {
  if (step === "personal") return ["name", "email"];
  if (step === "address") return ["street", "city", "zip"];
  return [];
}

export function isStepValid(step: StepKey, data: FormData): boolean {
  return fieldsForStep(step).every((f) => validateField(f, data[f]) === null);
}

export function hydrateDraft(raw: string | null): Partial<FormData> {
  if (raw === null) return {};
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return {};
    const out: Partial<FormData> = {};
    for (const key of ["name", "email", "street", "city", "zip"] as const) {
      const v = (parsed as Record<string, unknown>)[key];
      if (typeof v === "string") out[key] = v;
    }
    return out;
  } catch { return {}; }
}

export function MultiStepForm(props: MultiStepFormProps): JSX.Element {
  const liveId = useId();
  const [data, setData] = useState<FormData>(() => ({
    ...EMPTY,
    ...hydrateDraft(typeof window === "undefined" ? null : window.sessionStorage.getItem(STORAGE_KEY)),
    ...(props.initialData ?? {}),
  }));
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [stepIdx, setStepIdx] = useState(0);
  const [ui, setUi] = useState<UiState>({ kind: "idle" });
  const [announce, setAnnounce] = useState("");
  const stepRef = useRef<HTMLFieldSetElement>(null);
  const step = STEPS[stepIdx] ?? "personal";

  useEffect(() => {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }, [data]);

  useEffect(() => {
    stepRef.current?.querySelector<HTMLElement>("input, button")?.focus();
    setAnnounce(`Step ${stepIdx + 1} of ${STEPS.length}, ${step}.`);
  }, [stepIdx, step]);

  const change = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.name as keyof FormData;
    setData((d) => ({ ...d, [f]: e.target.value }));
  }, []);

  const blur = useCallback((e: FocusEvent<HTMLInputElement>) => {
    const f = e.target.name as keyof FormData;
    setErrors((p) => ({ ...p, [f]: validateField(f, e.target.value) ?? undefined }));
  }, []);

  const advance = useCallback(() => {
    const bad = fieldsForStep(step).find((f) => validateField(f, data[f]) !== null);
    if (bad) {
      setErrors((p) => ({ ...p, [bad]: validateField(bad, data[bad]) ?? undefined }));
      stepRef.current?.querySelector<HTMLElement>(`[name="${bad}"]`)?.focus();
      return;
    }
    setStepIdx((i) => Math.min(i + 1, STEPS.length - 1));
  }, [data, step]);

  const back = useCallback(() => setStepIdx((i) => Math.max(i - 1, 0)), []);

  const submit = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!STEPS.every((s) => isStepValid(s, data))) return;
    setUi({ kind: "loading" });
    try {
      await props.onSubmit(data);
      setUi({ kind: "success" });
      setAnnounce("Submission successful.");
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Submission failed.";
      setUi({ kind: "error", message });
      setAnnounce(`Submission failed: ${message}`);
    }
  }, [data, props]);

  return (
    <form onSubmit={submit} noValidate aria-busy={ui.kind === "loading"}>
      <p id={liveId} aria-live="polite" role="status" style={{ position: "absolute", left: -9999 }}>
        {announce}
      </p>
      <fieldset ref={stepRef} disabled={ui.kind === "loading"}>
        <legend>{`Step ${stepIdx + 1} of ${STEPS.length}: ${step}`}</legend>
        {fieldsForStep(step).map((f) => (
          <Field key={f} field={f} value={data[f]} error={errors[f]} onChange={change} onBlur={blur} />
        ))}
        {step === "review" && (
          <dl>
            {(Object.keys(data) as (keyof FormData)[]).map((k) => (
              <div key={k}><dt>{LABEL[k]}</dt><dd>{data[k]}</dd></div>
            ))}
          </dl>
        )}
      </fieldset>
      <nav aria-label="Form navigation">
        {stepIdx > 0 && <button type="button" onClick={back} disabled={ui.kind === "loading"}>Back</button>}
        {stepIdx < STEPS.length - 1
          ? <button type="button" onClick={advance}>Next</button>
          : <button type="submit" disabled={ui.kind === "loading"} aria-busy={ui.kind === "loading"}>
              {ui.kind === "loading" ? "Submitting…" : "Submit"}
            </button>}
      </nav>
      {ui.kind === "success" && <p role="status">Thanks — your form was submitted.</p>}
      {ui.kind === "error" && <p role="alert">{ui.message}</p>}
    </form>
  );
}

interface FieldProps {
  field: keyof FormData;
  value: string;
  error: string | undefined;
  onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onBlur: (e: FocusEvent<HTMLInputElement>) => void;
}

function Field({ field, value, error, onChange, onBlur }: FieldProps): JSX.Element {
  const id = useId();
  const errId = `${id}-err`;
  return (
    <p>
      <label htmlFor={id}>{LABEL[field]}</label>
      <input
        id={id}
        name={field}
        type={field === "email" ? "email" : "text"}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        aria-invalid={error !== undefined}
        aria-describedby={error !== undefined ? errId : undefined}
        autoComplete={AUTOFILL[field]}
      />
      {error !== undefined && <span id={errId} role="alert">{error}</span>}
    </p>
  );
}
