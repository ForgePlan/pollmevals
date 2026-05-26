// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-005 — FLAWS: legend missing on every fieldset (a11y),
// success state cleared after 2s (loses confirmation), no aria-busy.

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
  if (f === "zip" && !t.match(/^\d{4,10}$/)) return "Invalid postal code.";
  return null;
};

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
  const ref = useRef<HTMLFieldSetElement>(null);
  const descriptor = STEP_TABLE[idx];

  useEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(data)); }, [data]);
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("input,button")?.focus();
    setAnnounce(`Step ${idx + 1} of ${STEP_TABLE.length}.`);
  }, [idx]);

  // FLAW #2: success auto-clears after 2s. Confirmation disappears without
  // user dismissal — accessibility issue for SR users + UX issue for everyone.
  useEffect(() => {
    if (ui.kind !== "success") return;
    const id = window.setTimeout(() => setUi({ kind: "idle" }), 2000);
    return () => window.clearTimeout(id);
  }, [ui.kind]);

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
    <form onSubmit={submit} noValidate>
      <p id={liveId} aria-live="polite" role="status" style={{ position: "absolute", left: -9999 }}>{announce}</p>
      {/* FLAW #1: no <legend> on the fieldset (a11y violation — fieldset
          without legend has no accessible name. Severity: moderate. */}
      <fieldset ref={ref}>
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
          /* FLAW #3: no aria-busy. */
          : <button type="submit" disabled={ui.kind === "loading"}>
              {ui.kind === "loading" ? "Submitting…" : "Submit"}
            </button>}
      </nav>
      {ui.kind === "success" && <p role="status">Submitted (clearing in 2s…).</p>}
      {ui.kind === "error" && <p role="alert">{ui.message}</p>}
    </form>
  );
}
