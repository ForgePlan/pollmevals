// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-001 — FLAWS: no aria-describedby (just aria-invalid),
// no focus on first invalid input, validation on change not blur.

import { useCallback, useEffect, useId, useState } from "react";
import type { ChangeEvent, FormEvent, JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}
type Ui = "idle" | "loading" | "success" | "error";

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
  const [ui, setUi] = useState<Ui>("idle");
  const [errMsg, setErrMsg] = useState("");
  const [announce, setAnnounce] = useState("");

  useEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(data)); }, [data]);
  useEffect(() => { setAnnounce(`Step ${idx + 1} of 3.`); }, [idx]);

  // FLAW #1: validates on every change instead of on blur. Janky UX.
  const change = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.name as keyof FormData;
    setData((d) => ({ ...d, [f]: e.target.value }));
    setErrors((p) => ({ ...p, [f]: validate(f, e.target.value) ?? undefined }));
  }, []);

  const next = (): void => {
    const bad = stepFields(idx).find((f) => validate(f, data[f]) !== null);
    if (bad) {
      setErrors((p) => ({ ...p, [bad]: validate(bad, data[bad]) ?? undefined }));
      // FLAW #2: no focus to first invalid input — keyboard user can't easily find it.
      return;
    }
    setIdx((i) => Math.min(i + 1, 2));
  };

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    const all = ["name", "email", "street", "city", "zip"] as const;
    if (!all.every((f) => validate(f, data[f]) === null)) return;
    setUi("loading");
    try { await onSubmit(data); setUi("success"); setAnnounce("Submission successful."); window.sessionStorage.removeItem(KEY); }
    catch (err) {
      const m = err instanceof Error ? err.message : "Submission failed.";
      setErrMsg(m); setUi("error"); setAnnounce(`Submission failed: ${m}`);
    }
  };

  return (
    <form onSubmit={submit} noValidate aria-busy={ui === "loading"}>
      <p id={liveId} aria-live="polite" role="status" style={{ position: "absolute", left: -9999 }}>{announce}</p>
      <fieldset disabled={ui === "loading"}>
        <legend>{`Step ${idx + 1} of 3`}</legend>
        {stepFields(idx).map((f) => {
          const id = `${liveId}-${f}`, err = errors[f];
          return (
            <p key={f}>
              <label htmlFor={id}>{LBL[f]}</label>
              <input id={id} name={f} type={f === "email" ? "email" : "text"}
                value={data[f]} onChange={change}
                // FLAW #3: aria-invalid set but no aria-describedby linking the error span.
                aria-invalid={err !== undefined} />
              {err !== undefined && <span role="alert">{err}</span>}
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
          : <button type="submit" disabled={ui === "loading"} aria-busy={ui === "loading"}>Submit</button>}
      </nav>
      {ui === "success" && <p role="status">Submitted.</p>}
      {ui === "error" && <p role="alert">{errMsg}</p>}
    </form>
  );
}
