// source: own-authored 2026-05-26 by gogocat (license: MIT)
// perfect/sample-003 — separate state slices per step; child Step components.

import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { ChangeEvent, FocusEvent, FormEvent, JSX, RefObject } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

const KEY = "fe01:multistep-form:draft";
const EMPTY: FormData = { name: "", email: "", street: "", city: "", zip: "" };
const LBL = {
  name: "Full name", email: "Email address", street: "Street address",
  city: "City", zip: "Postal code",
} as const;

type Ui = "idle" | "loading" | "success" | "error";

export const validate = (f: keyof FormData, v: string): string | null => {
  const t = v.trim();
  if (!t) return "Required.";
  if (f === "email" && !t.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) return "Invalid email.";
  if (f === "zip" && !t.match(/^\d{4,10}$/)) return "Invalid postal code.";
  return null;
};

function loadDraft(): Partial<FormData> {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return {};
    const out: Partial<FormData> = {};
    for (const k of ["name", "email", "street", "city", "zip"] as const) {
      const v = (parsed as Record<string, unknown>)[k];
      if (typeof v === "string") out[k] = v;
    }
    return out;
  } catch { return {}; }
}

interface StepProps {
  fields: readonly (keyof FormData)[];
  data: FormData;
  errors: Partial<Record<keyof FormData, string>>;
  setField: (f: keyof FormData, v: string) => void;
  setError: (f: keyof FormData, m: string | null) => void;
  inputRef: RefObject<HTMLFieldSetElement | null>;
}

function StepFields({ fields, data, errors, setField, setError, inputRef }: StepProps): JSX.Element {
  const baseId = useId();
  return (
    <fieldset ref={inputRef}>
      <legend>Details</legend>
      {fields.map((f) => {
        const id = `${baseId}-${f}`, eid = `${id}-err`, err = errors[f];
        return (
          <p key={f}>
            <label htmlFor={id}>{LBL[f]}</label>
            <input id={id} name={f} type={f === "email" ? "email" : "text"} value={data[f]}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setField(f, e.target.value)}
              onBlur={(e: FocusEvent<HTMLInputElement>) => setError(f, validate(f, e.target.value))}
              aria-invalid={err !== undefined}
              aria-describedby={err !== undefined ? eid : undefined} />
            {err !== undefined && <span id={eid} role="alert">{err}</span>}
          </p>
        );
      })}
    </fieldset>
  );
}

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  const liveId = useId();
  const [data, setData] = useState<FormData>(() => ({
    ...EMPTY, ...(typeof window === "undefined" ? {} : loadDraft()), ...(initialData ?? {}),
  }));
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [stepIdx, setStepIdx] = useState(0);
  const [ui, setUi] = useState<Ui>("idle");
  const [errMsg, setErrMsg] = useState("");
  const [announce, setAnnounce] = useState("");
  const ref = useRef<HTMLFieldSetElement>(null);
  const stepFields: readonly (keyof FormData)[] =
    stepIdx === 0 ? ["name", "email"] : stepIdx === 1 ? ["street", "city", "zip"] : [];

  useEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(data)); }, [data]);
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>("input,button")?.focus();
    setAnnounce(`Step ${stepIdx + 1} of 3.`);
  }, [stepIdx]);

  const setField = useCallback((f: keyof FormData, v: string) => setData((d) => ({ ...d, [f]: v })), []);
  const setError = useCallback((f: keyof FormData, m: string | null) =>
    setErrors((p) => ({ ...p, [f]: m ?? undefined })), []);

  const next = (): void => {
    const bad = stepFields.find((f) => validate(f, data[f]) !== null);
    if (bad) {
      setError(bad, validate(bad, data[bad]));
      ref.current?.querySelector<HTMLElement>(`[name="${bad}"]`)?.focus();
      return;
    }
    setStepIdx((i) => Math.min(i + 1, 2));
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
      {stepIdx < 2
        ? <StepFields fields={stepFields} data={data} errors={errors}
            setField={setField} setError={setError} inputRef={ref} />
        : <fieldset ref={ref}><legend>Review</legend>
            <dl>{(["name", "email", "street", "city", "zip"] as const).map((k) =>
              <div key={k}><dt>{LBL[k]}</dt><dd>{data[k]}</dd></div>)}</dl>
          </fieldset>}
      <nav aria-label="Form navigation">
        {stepIdx > 0 && <button type="button" onClick={() => setStepIdx((i) => i - 1)}>Back</button>}
        {stepIdx < 2
          ? <button type="button" onClick={next}>Next</button>
          : <button type="submit" disabled={ui === "loading"} aria-busy={ui === "loading"}>Submit</button>}
      </nav>
      {ui === "success" && <p role="status">Thanks — your form was submitted.</p>}
      {ui === "error" && <p role="alert">{errMsg}</p>}
    </form>
  );
}
