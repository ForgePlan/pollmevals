// source: own-authored 2026-05-26 by gogocat (license: MIT)
// perfect/sample-001 — hooks-only idiom with two custom hooks (useDraft + useStep).

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { ChangeEvent, FocusEvent, FormEvent, JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}
type Step = "personal" | "address" | "review";
type Ui = { k: "idle" } | { k: "loading" } | { k: "success" } | { k: "error"; m: string };

const STEPS: readonly Step[] = ["personal", "address", "review"] as const;
const KEY = "fe01:multistep-form:draft";
const EMPTY: FormData = { name: "", email: "", street: "", city: "", zip: "" };
const LBL: Record<keyof FormData, string> = {
  name: "Full name", email: "Email address", street: "Street address",
  city: "City", zip: "Postal code",
};

export const validate = (f: keyof FormData, v: string): string | null => {
  const t = v.trim();
  if (!t) return "Required.";
  if (f === "email" && !t.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) return "Invalid email.";
  if (f === "zip" && !t.match(/^\d{4,10}$/)) return "Invalid postal code.";
  return null;
};

const fieldsOf = (s: Step): readonly (keyof FormData)[] =>
  s === "personal" ? ["name", "email"] : s === "address" ? ["street", "city", "zip"] : [];

function useDraft(initial?: Partial<FormData>): [FormData, (p: Partial<FormData>) => void, () => void] {
  const [data, setData] = useState<FormData>(() => {
    const raw = typeof window === "undefined" ? null : window.sessionStorage.getItem(KEY);
    let stored: Partial<FormData> = {};
    try { const p: unknown = raw ? JSON.parse(raw) : null;
      if (p && typeof p === "object")
        for (const k of Object.keys(EMPTY) as (keyof FormData)[]) {
          const v = (p as Record<string, unknown>)[k];
          if (typeof v === "string") stored[k] = v;
        }
    } catch { /* swallow */ }
    return { ...EMPTY, ...stored, ...(initial ?? {}) };
  });
  useEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(data)); }, [data]);
  const update = useCallback((p: Partial<FormData>) => setData((d) => ({ ...d, ...p })), []);
  const clear = useCallback(() => window.sessionStorage.removeItem(KEY), []);
  return [data, update, clear];
}

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  const liveId = useId();
  const [data, update, clear] = useDraft(initialData);
  const [errs, setErrs] = useState<Partial<Record<keyof FormData, string>>>({});
  const [idx, setIdx] = useState(0);
  const [ui, setUi] = useState<Ui>({ k: "idle" });
  const [say, setSay] = useState("");
  const ref = useRef<HTMLFieldSetElement>(null);
  const step = STEPS[idx] ?? "personal";

  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("input,button")?.focus();
    setSay(`Step ${idx + 1} of ${STEPS.length}, ${step}.`);
  }, [idx, step]);

  const onChange = (e: ChangeEvent<HTMLInputElement>): void =>
    update({ [e.target.name as keyof FormData]: e.target.value });

  const onBlur = (e: FocusEvent<HTMLInputElement>): void => {
    const f = e.target.name as keyof FormData;
    setErrs((p) => ({ ...p, [f]: validate(f, e.target.value) ?? undefined }));
  };

  const next = (): void => {
    const bad = fieldsOf(step).find((f) => validate(f, data[f]) !== null);
    if (bad) {
      setErrs((p) => ({ ...p, [bad]: validate(bad, data[bad]) ?? undefined }));
      ref.current?.querySelector<HTMLElement>(`[name="${bad}"]`)?.focus();
      return;
    }
    setIdx((i) => Math.min(i + 1, STEPS.length - 1));
  };

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!STEPS.every((s) => fieldsOf(s).every((f) => validate(f, data[f]) === null))) return;
    setUi({ k: "loading" });
    try {
      await onSubmit(data);
      setUi({ k: "success" }); setSay("Submission successful."); clear();
    } catch (err) {
      const m = err instanceof Error ? err.message : "Submission failed.";
      setUi({ k: "error", m }); setSay(`Submission failed: ${m}`);
    }
  };

  return (
    <form onSubmit={submit} noValidate aria-busy={ui.k === "loading"}>
      <p id={liveId} aria-live="polite" role="status" style={{ position: "absolute", left: -9999 }}>{say}</p>
      <fieldset ref={ref} disabled={ui.k === "loading"}>
        <legend>{`Step ${idx + 1} of ${STEPS.length}: ${step}`}</legend>
        {fieldsOf(step).map((f) => {
          const id = `${liveId}-${f}`, eid = `${id}-err`, err = errs[f];
          return (
            <p key={f}>
              <label htmlFor={id}>{LBL[f]}</label>
              <input id={id} name={f} type={f === "email" ? "email" : "text"}
                value={data[f]} onChange={onChange} onBlur={onBlur}
                aria-invalid={err !== undefined}
                aria-describedby={err !== undefined ? eid : undefined} />
              {err !== undefined && <span id={eid} role="alert">{err}</span>}
            </p>
          );
        })}
        {step === "review" && <dl>{(Object.keys(data) as (keyof FormData)[]).map((k) =>
          <div key={k}><dt>{LBL[k]}</dt><dd>{data[k]}</dd></div>)}</dl>}
      </fieldset>
      <nav aria-label="Form navigation">
        {idx > 0 && <button type="button" onClick={() => setIdx((i) => i - 1)}>Back</button>}
        {idx < STEPS.length - 1
          ? <button type="button" onClick={next}>Next</button>
          : <button type="submit" disabled={ui.k === "loading"} aria-busy={ui.k === "loading"}>
              {ui.k === "loading" ? "Submitting…" : "Submit"}
            </button>}
      </nav>
      {ui.k === "success" && <p role="status">Thanks — your form was submitted.</p>}
      {ui.k === "error" && <p role="alert">{ui.m}</p>}
    </form>
  );
}
