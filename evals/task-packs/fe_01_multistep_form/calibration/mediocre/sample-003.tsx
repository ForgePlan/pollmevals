// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-003 — FLAWS: useLayoutEffect to persist data (sync write
// on every keystroke), and submit button can be clicked while loading
// (no disabled attribute applied, just visual class).

import { startTransition, useCallback, useEffect, useId, useLayoutEffect, useRef, useState, useTransition } from "react";
import type { ChangeEvent, FocusEvent, FormEvent, JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}
type Ui = { kind: "idle" } | { kind: "loading" } | { kind: "success" } | { kind: "error"; message: string };

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

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  const liveId = useId();
  const [data, setData] = useState<FormData>(() => {
    try {
      const raw = typeof window === "undefined" ? null : window.sessionStorage.getItem(KEY);
      const p = raw ? JSON.parse(raw) : {};
      return { ...EMPTY, ...(typeof p === "object" && p ? p : {}), ...(initialData ?? {}) };
    } catch { return { ...EMPTY, ...(initialData ?? {}) }; }
  });
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [idx, setIdx] = useState(0);
  const [ui, setUi] = useState<Ui>({ kind: "idle" });
  const [announce, setAnnounce] = useState("");
  const [, startStepTransition] = useTransition();
  const ref = useRef<HTMLFieldSetElement>(null);

  // FLAW #1: useLayoutEffect blocks paint to write to sessionStorage — wrong
  // tool for the job. Should be useEffect (passive); blocks paint on every
  // keystroke unnecessarily.
  useLayoutEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(data)); }, [data]);
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("input,button")?.focus();
    startTransition(() => setAnnounce(`Step ${idx + 1} of 3.`));
  }, [idx]);

  const change = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setData((d) => ({ ...d, [e.target.name as keyof FormData]: e.target.value }));
  }, []);
  const blur = useCallback((e: FocusEvent<HTMLInputElement>) => {
    const f = e.target.name as keyof FormData;
    setErrors((p) => ({ ...p, [f]: validate(f, e.target.value) ?? undefined }));
  }, []);

  const next = (): void => {
    const bad = stepFields(idx).find((f) => validate(f, data[f]) !== null);
    if (bad) {
      setErrors((p) => ({ ...p, [bad]: validate(bad, data[bad]) ?? undefined }));
      ref.current?.querySelector<HTMLElement>(`[name="${bad}"]`)?.focus();
      return;
    }
    startStepTransition(() => setIdx((i) => Math.min(i + 1, 2)));
  };

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    // FLAW #2: no check on `ui.kind` — clicking Submit while loading enqueues
    // a second onSubmit call. Double-submit possible.
    const all = ["name", "email", "street", "city", "zip"] as const;
    if (!all.every((f) => validate(f, data[f]) === null)) return;
    setUi({ kind: "loading" });
    try { await onSubmit(data); setUi({ kind: "success" }); setAnnounce("Submission successful."); window.sessionStorage.removeItem(KEY); }
    catch (err) {
      const message = err instanceof Error ? err.message : "Submission failed.";
      setUi({ kind: "error", message }); setAnnounce(`Submission failed: ${message}`);
    }
  };

  return (
    <form onSubmit={submit} noValidate>
      <p id={liveId} aria-live="polite" role="status" style={{ position: "absolute", left: -9999 }}>{announce}</p>
      <fieldset ref={ref}>
        <legend>{`Step ${idx + 1} of 3`}</legend>
        {stepFields(idx).map((f) => {
          const id = `${liveId}-${f}`, eid = `${id}-err`, err = errors[f];
          return (
            <p key={f}>
              <label htmlFor={id}>{LBL[f]}</label>
              <input id={id} name={f} type={f === "email" ? "email" : "text"}
                value={data[f]} onChange={change} onBlur={blur}
                aria-invalid={err !== undefined}
                aria-describedby={err !== undefined ? eid : undefined} />
              {err !== undefined && <span id={eid} role="alert">{err}</span>}
            </p>
          );
        })}
        {idx === 2 && <dl>{(["name", "email", "street", "city", "zip"] as const).map((k) =>
          <div key={k}><dt>{LBL[k]}</dt><dd>{data[k]}</dd></div>)}</dl>}
      </fieldset>
      <nav aria-label="Form navigation">
        {idx > 0 && <button type="button" onClick={() => setIdx((i) => i - 1)}>Back</button>}
        {idx < 2
          ? <button type="button" onClick={next}>Next</button>
          /* FLAW #2 cont: className-only visual disable; button still clickable. */
          : <button type="submit" className={ui.kind === "loading" ? "is-loading" : ""}>
              {ui.kind === "loading" ? "Submitting…" : "Submit"}
            </button>}
      </nav>
      {ui.kind === "success" && <p role="status">Thanks — your form was submitted.</p>}
      {ui.kind === "error" && <p role="alert">{ui.message}</p>}
    </form>
  );
}
