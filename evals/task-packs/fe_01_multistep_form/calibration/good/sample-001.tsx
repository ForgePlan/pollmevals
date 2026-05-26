// source: own-authored 2026-05-26 by gogocat (license: MIT)
// good/sample-001 — FLAW: no submission-outcome announcement (success/error not in live region).

import { useCallback, useEffect, useId, useRef, useState } from "react";
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

function readDraft(): Partial<FormData> {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return {};
    const p: unknown = JSON.parse(raw);
    if (!p || typeof p !== "object") return {};
    const out: Partial<FormData> = {};
    for (const k of ["name", "email", "street", "city", "zip"] as const) {
      const v = (p as Record<string, unknown>)[k];
      if (typeof v === "string") out[k] = v;
    }
    return out;
  } catch { return {}; }
}

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  const liveId = useId();
  const [data, setData] = useState<FormData>(() => ({
    ...EMPTY, ...(typeof window === "undefined" ? {} : readDraft()), ...(initialData ?? {}),
  }));
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [idx, setIdx] = useState(0);
  const [ui, setUi] = useState<Ui>({ kind: "idle" });
  const [announce, setAnnounce] = useState("");
  const ref = useRef<HTMLFieldSetElement>(null);

  useEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(data)); }, [data]);
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("input,button")?.focus();
    // Announces step on transition — but submit outcomes never reach the live region.
    setAnnounce(`Step ${idx + 1} of 3.`);
  }, [idx]);

  const change = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.name as keyof FormData;
    setData((d) => ({ ...d, [f]: e.target.value }));
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
    setIdx((i) => Math.min(i + 1, 2));
  };

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    const all = ["name", "email", "street", "city", "zip"] as const;
    if (!all.every((f) => validate(f, data[f]) === null)) return;
    setUi({ kind: "loading" });
    try {
      await onSubmit(data);
      // FLAW: no setAnnounce here; success only shows visually.
      setUi({ kind: "success" });
      window.sessionStorage.removeItem(KEY);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Submission failed.";
      // FLAW: no setAnnounce here either; error reaches role=alert but live region stays on "Step 3 of 3.".
      setUi({ kind: "error", message });
    }
  };

  return (
    <form onSubmit={submit} noValidate aria-busy={ui.kind === "loading"}>
      <p id={liveId} aria-live="polite" role="status" style={{ position: "absolute", left: -9999 }}>{announce}</p>
      <fieldset ref={ref} disabled={ui.kind === "loading"}>
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
          : <button type="submit" disabled={ui.kind === "loading"} aria-busy={ui.kind === "loading"}>Submit</button>}
      </nav>
      {ui.kind === "success" && <p role="status">Thanks — your form was submitted.</p>}
      {ui.kind === "error" && <p role="alert">{ui.message}</p>}
    </form>
  );
}
