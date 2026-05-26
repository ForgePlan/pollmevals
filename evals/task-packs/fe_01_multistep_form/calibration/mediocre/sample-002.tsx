// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-002 — FLAWS: no aria-live region, no announcements on
// step change or submission outcome; visually-hidden status only.

import { useEffect, useId, useReducer, useRef } from "react";
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
const FIELDS = ["name", "email", "street", "city", "zip"] as const;
type Field = (typeof FIELDS)[number];
const EMPTY: FormData = { name: "", email: "", street: "", city: "", zip: "" };
const LBL: Record<Field, string> = {
  name: "Full name", email: "Email address", street: "Street address",
  city: "City", zip: "Postal code",
};

export const validate = (f: Field, v: string): string | null => {
  const t = v.trim();
  if (!t) return "Required.";
  if (f === "email" && !t.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) return "Invalid email.";
  if (f === "zip" && !t.match(/^\d{4,10}$/)) return "Invalid postal code.";
  return null;
};

const stepFields = (i: number): readonly Field[] =>
  i === 0 ? ["name", "email"] : i === 1 ? ["street", "city", "zip"] : [];

interface State {
  data: FormData;
  errors: Partial<Record<Field, string>>;
  idx: number;
  ui: Ui;
}
type Action =
  | { t: "change"; f: Field; v: string }
  | { t: "blur"; f: Field; msg: string | null }
  | { t: "next" } | { t: "back" }
  | { t: "submit-start" } | { t: "submit-ok" } | { t: "submit-err"; m: string };

function readDraft(): Partial<FormData> {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return {};
    const p: unknown = JSON.parse(raw);
    if (!p || typeof p !== "object") return {};
    const out: Partial<FormData> = {};
    for (const k of FIELDS) {
      const v = (p as Record<string, unknown>)[k];
      if (typeof v === "string") out[k] = v;
    }
    return out;
  } catch { return {}; }
}

function reducer(s: State, a: Action): State {
  if (a.t === "change") return { ...s, data: { ...s.data, [a.f]: a.v } };
  if (a.t === "blur") return { ...s, errors: { ...s.errors, [a.f]: a.msg ?? undefined } };
  if (a.t === "next") {
    const bad = stepFields(s.idx).find((f) => validate(f, s.data[f]) !== null);
    if (bad) return { ...s, errors: { ...s.errors, [bad]: validate(bad, s.data[bad]) ?? undefined } };
    return { ...s, idx: Math.min(s.idx + 1, 2) };
  }
  if (a.t === "back") return { ...s, idx: Math.max(s.idx - 1, 0) };
  if (a.t === "submit-start") return { ...s, ui: { kind: "loading" } };
  if (a.t === "submit-ok") return { ...s, ui: { kind: "success" } };
  return { ...s, ui: { kind: "error", message: a.m } };
}

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  const headingId = useId();
  const [s, d] = useReducer(reducer, undefined, (): State => ({
    data: { ...EMPTY, ...(typeof window === "undefined" ? {} : readDraft()), ...(initialData ?? {}) },
    errors: {}, idx: 0, ui: { kind: "idle" },
  }));
  const ref = useRef<HTMLFieldSetElement>(null);

  useEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(s.data)); }, [s.data]);
  useEffect(() => { ref.current?.querySelector<HTMLElement>("input,button")?.focus(); }, [s.idx]);

  const change = (e: ChangeEvent<HTMLInputElement>): void =>
    d({ t: "change", f: e.target.name as Field, v: e.target.value });
  const blur = (e: FocusEvent<HTMLInputElement>): void =>
    d({ t: "blur", f: e.target.name as Field, msg: validate(e.target.name as Field, e.target.value) });

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!FIELDS.every((f) => validate(f, s.data[f]) === null)) return;
    d({ t: "submit-start" });
    try { await onSubmit(s.data); d({ t: "submit-ok" }); window.sessionStorage.removeItem(KEY); }
    catch (err) {
      const m = err instanceof Error ? err.message : "Submission failed.";
      d({ t: "submit-err", m });
    }
  };

  return (
    <form onSubmit={submit} noValidate aria-busy={s.ui.kind === "loading"}>
      {/* FLAW: no aria-live region at all — step changes and submission outcomes
          are invisible to screen readers. Heading carries the step text but is
          not announced on change because it's not a live region. */}
      <h2 id={headingId}>{`Step ${s.idx + 1} of 3`}</h2>
      <fieldset ref={ref} disabled={s.ui.kind === "loading"}>
        <legend>{`Step ${s.idx + 1}`}</legend>
        {stepFields(s.idx).map((f) => {
          const id = `${headingId}-${f}`, eid = `${id}-err`, err = s.errors[f];
          return (
            <p key={f}>
              <label htmlFor={id}>{LBL[f]}</label>
              <input id={id} name={f} type={f === "email" ? "email" : "text"}
                value={s.data[f]} onChange={change} onBlur={blur}
                aria-invalid={err !== undefined}
                aria-describedby={err !== undefined ? eid : undefined} />
              {err !== undefined && <span id={eid} role="alert">{err}</span>}
            </p>
          );
        })}
        {s.idx === 2 && <dl>{FIELDS.map((k) =>
          <div key={k}><dt>{LBL[k]}</dt><dd>{s.data[k]}</dd></div>)}</dl>}
      </fieldset>
      <nav aria-label="Form navigation">
        {s.idx > 0 && <button type="button" onClick={() => d({ t: "back" })}>Back</button>}
        {s.idx < 2
          ? <button type="button" onClick={() => d({ t: "next" })}>Next</button>
          : <button type="submit" disabled={s.ui.kind === "loading"} aria-busy={s.ui.kind === "loading"}>Submit</button>}
      </nav>
      {s.ui.kind === "success" && <p>Submitted.</p>}
      {s.ui.kind === "error" && <p>{s.ui.message}</p>}
    </form>
  );
}
