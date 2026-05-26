// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-004 — FLAWS: localStorage instead of sessionStorage (wrong
// scope, persists across windows), and Back loses errors but not data
// (errors carry stale state when revisiting a step).

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { ChangeEvent, FocusEvent, FormEvent, JSX, RefObject } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}
type Ui = { kind: "idle" } | { kind: "loading" } | { kind: "success" } | { kind: "error"; message: string };

// FLAW #1: localStorage scopes to the origin permanently. The spec asked for
// sessionStorage (window-scoped, cleared on tab close). Privacy regression:
// drafts containing PII survive across browser sessions.
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

const stepFields = (i: number): readonly (keyof FormData)[] =>
  i === 0 ? ["name", "email"] : i === 1 ? ["street", "city", "zip"] : [];

interface StepViewProps {
  fields: readonly (keyof FormData)[];
  data: FormData;
  errors: Partial<Record<keyof FormData, string>>;
  baseId: string;
  onChangeField: (f: keyof FormData, v: string) => void;
  onBlurField: (f: keyof FormData, v: string) => void;
  fsRef: RefObject<HTMLFieldSetElement | null>;
  loading: boolean;
  idx: number;
}

function StepView(props: StepViewProps): JSX.Element {
  const { fields, data, errors, baseId, onChangeField, onBlurField, fsRef, loading, idx } = props;
  return (
    <fieldset ref={fsRef} disabled={loading}>
      <legend>{`Step ${idx + 1} of 3`}</legend>
      {fields.map((f) => {
        const id = `${baseId}-${f}`, eid = `${id}-err`, err = errors[f];
        return (
          <p key={f}>
            <label htmlFor={id}>{LBL[f]}</label>
            <input id={id} name={f} type={f === "email" ? "email" : "text"} value={data[f]}
              onChange={(e: ChangeEvent<HTMLInputElement>) => onChangeField(f, e.target.value)}
              onBlur={(e: FocusEvent<HTMLInputElement>) => onBlurField(f, e.target.value)}
              aria-invalid={err !== undefined}
              aria-describedby={err !== undefined ? eid : undefined} />
            {err !== undefined && <span id={eid} role="alert">{err}</span>}
          </p>
        );
      })}
      {idx === 2 && <dl>{(["name", "email", "street", "city", "zip"] as const).map((k) =>
        <div key={k}><dt>{LBL[k]}</dt><dd>{data[k]}</dd></div>)}</dl>}
    </fieldset>
  );
}

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  const liveId = useId();
  const [data, setData] = useState<FormData>(() => {
    try {
      // FLAW #1 cont: reading from localStorage too.
      const raw = typeof window === "undefined" ? null : window.localStorage.getItem(KEY);
      const p = raw ? JSON.parse(raw) : {};
      return { ...EMPTY, ...(typeof p === "object" && p ? p : {}), ...(initialData ?? {}) };
    } catch { return { ...EMPTY, ...(initialData ?? {}) }; }
  });
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [idx, setIdx] = useState(0);
  const [ui, setUi] = useState<Ui>({ kind: "idle" });
  const [announce, setAnnounce] = useState("");
  const ref = useRef<HTMLFieldSetElement>(null);

  useEffect(() => { window.localStorage.setItem(KEY, JSON.stringify(data)); }, [data]);
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("input,button")?.focus();
    setAnnounce(`Step ${idx + 1} of 3.`);
  }, [idx]);

  const onChangeField = useCallback((f: keyof FormData, v: string) => {
    setData((d) => ({ ...d, [f]: v }));
  }, []);
  const onBlurField = useCallback((f: keyof FormData, v: string) => {
    setErrors((p) => ({ ...p, [f]: validate(f, v) ?? undefined }));
  }, []);

  const next = (): void => {
    const bad = stepFields(idx).find((f) => validate(f, data[f]) !== null);
    if (bad) {
      setErrors((p) => ({ ...p, [bad]: validate(bad, data[bad]) ?? undefined }));
      ref.current?.querySelector<HTMLElement>(`[name="${bad}"]`)?.focus();
      return;
    }
    setIdx((i) => Math.min(i + 1, 2));
  };

  // FLAW #2: Back keeps errors set — when the user returns to step 1, the
  // previously-shown email error is still rendered even if the email is now valid.
  // The errors map is never cleared on step transition.

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    const all = ["name", "email", "street", "city", "zip"] as const;
    if (!all.every((f) => validate(f, data[f]) === null)) return;
    setUi({ kind: "loading" });
    try { await onSubmit(data); setUi({ kind: "success" }); setAnnounce("Submission successful."); window.localStorage.removeItem(KEY); }
    catch (err) {
      const message = err instanceof Error ? err.message : "Submission failed.";
      setUi({ kind: "error", message }); setAnnounce(`Submission failed: ${message}`);
    }
  };

  return (
    <form onSubmit={submit} noValidate aria-busy={ui.kind === "loading"}>
      <p id={liveId} aria-live="polite" role="status" style={{ position: "absolute", left: -9999 }}>{announce}</p>
      <StepView fields={stepFields(idx)} data={data} errors={errors} baseId={liveId}
        onChangeField={onChangeField} onBlurField={onBlurField} fsRef={ref}
        loading={ui.kind === "loading"} idx={idx} />
      <nav aria-label="Form navigation">
        {idx > 0 && <button type="button" onClick={() => setIdx((i) => i - 1)}>Back</button>}
        {idx < 2
          ? <button type="button" onClick={next}>Next</button>
          : <button type="submit" disabled={ui.kind === "loading"} aria-busy={ui.kind === "loading"}>Submit</button>}
      </nav>
      {ui.kind === "success" && <p role="status">Thanks — your form was submitted.</p>}
      {ui.kind === "error" && <p role="alert">{ui.message}</p>}
    </form>
  );
}
