// source: own-authored 2026-05-26 by gogocat (license: MIT)
// good/sample-004 — FLAW: zip regex is too strict (^\d{5}$) — rejects valid 4-digit codes.

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

interface StepDescriptor {
  title: string;
  fields: readonly { key: keyof FormData; label: string; type: "text" | "email"; autocomplete: string }[];
}

const STEP_TABLE: readonly StepDescriptor[] = [
  { title: "Personal info", fields: [
    { key: "name", label: "Full name", type: "text", autocomplete: "name" },
    { key: "email", label: "Email address", type: "email", autocomplete: "email" },
  ]},
  { title: "Address", fields: [
    { key: "street", label: "Street address", type: "text", autocomplete: "street-address" },
    { key: "city", label: "City", type: "text", autocomplete: "address-level2" },
    { key: "zip", label: "Postal code", type: "text", autocomplete: "postal-code" },
  ]},
  { title: "Review", fields: [] },
];

export const validate = (f: keyof FormData, v: string): string | null => {
  const t = v.trim();
  if (!t) return "Required.";
  if (f === "email" && !t.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) return "Invalid email.";
  // FLAW: hardcoded US-only 5-digit zip pattern; rejects EU 4-digit codes
  // (Norway 0150, Denmark 8000), Canadian K1A 0B1, etc. Spec said 4-10 digits.
  if (f === "zip" && !t.match(/^\d{5}$/)) return "Invalid postal code.";
  return null;
};

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
  const descriptor = STEP_TABLE[idx];

  useEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(data)); }, [data]);
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("input,button")?.focus();
    setAnnounce(`Step ${idx + 1} of ${STEP_TABLE.length}, ${descriptor?.title ?? ""}.`);
  }, [idx, descriptor]);

  const change = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setData((d) => ({ ...d, [e.target.name as keyof FormData]: e.target.value }));
  }, []);
  const blur = useCallback((e: FocusEvent<HTMLInputElement>) => {
    const f = e.target.name as keyof FormData;
    setErrors((p) => ({ ...p, [f]: validate(f, e.target.value) ?? undefined }));
  }, []);

  const next = (): void => {
    if (!descriptor) return;
    const bad = descriptor.fields.find((fd) => validate(fd.key, data[fd.key]) !== null);
    if (bad) {
      setErrors((p) => ({ ...p, [bad.key]: validate(bad.key, data[bad.key]) ?? undefined }));
      ref.current?.querySelector<HTMLElement>(`[name="${bad.key}"]`)?.focus();
      return;
    }
    setIdx((i) => Math.min(i + 1, STEP_TABLE.length - 1));
  };

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    const allFields = STEP_TABLE.flatMap((s) => s.fields);
    if (!allFields.every((fd) => validate(fd.key, data[fd.key]) === null)) return;
    setUi({ kind: "loading" });
    try { await onSubmit(data); setUi({ kind: "success" }); setAnnounce("Submission successful."); window.sessionStorage.removeItem(KEY); }
    catch (err) {
      const message = err instanceof Error ? err.message : "Submission failed.";
      setUi({ kind: "error", message }); setAnnounce(`Submission failed: ${message}`);
    }
  };

  return (
    <form onSubmit={submit} noValidate aria-busy={ui.kind === "loading"}>
      <p id={liveId} aria-live="polite" role="status" style={{ position: "absolute", left: -9999 }}>{announce}</p>
      <fieldset ref={ref} disabled={ui.kind === "loading"}>
        <legend>{descriptor?.title ?? ""}</legend>
        {descriptor?.fields.map((fd) => {
          const id = `${liveId}-${fd.key}`, eid = `${id}-err`, err = errors[fd.key];
          return (
            <p key={fd.key}>
              <label htmlFor={id}>{fd.label}</label>
              <input id={id} name={fd.key} type={fd.type} autoComplete={fd.autocomplete}
                value={data[fd.key]} onChange={change} onBlur={blur}
                aria-invalid={err !== undefined}
                aria-describedby={err !== undefined ? eid : undefined} />
              {err !== undefined && <span id={eid} role="alert">{err}</span>}
            </p>
          );
        })}
        {idx === STEP_TABLE.length - 1 && <dl>{STEP_TABLE.flatMap((s) => s.fields).map((fd) =>
          <div key={fd.key}><dt>{fd.label}</dt><dd>{data[fd.key]}</dd></div>)}</dl>}
      </fieldset>
      <nav aria-label="Form navigation">
        {idx > 0 && <button type="button" onClick={() => setIdx((i) => i - 1)}>Back</button>}
        {idx < STEP_TABLE.length - 1
          ? <button type="button" onClick={next}>Next</button>
          : <button type="submit" disabled={ui.kind === "loading"} aria-busy={ui.kind === "loading"}>Submit</button>}
      </nav>
      {ui.kind === "success" && <p role="status">Thanks — your form was submitted.</p>}
      {ui.kind === "error" && <p role="alert">{ui.message}</p>}
    </form>
  );
}
