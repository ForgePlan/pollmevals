// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-004 — FATAL: alert()-driven errors (modal interrupt + no a11y).

import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent, JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

const KEY = "fe01:multistep-form:draft";
const EMPTY: FormData = { name: "", email: "", street: "", city: "", zip: "" };

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  const [data, setData] = useState<FormData>(() => {
    try {
      const raw = typeof window === "undefined" ? null : window.sessionStorage.getItem(KEY);
      const p = raw ? JSON.parse(raw) : {};
      return { ...EMPTY, ...(typeof p === "object" && p ? p : {}), ...(initialData ?? {}) };
    } catch { return { ...EMPTY, ...(initialData ?? {}) }; }
  });
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => { window.sessionStorage.setItem(KEY, JSON.stringify(data)); }, [data]);

  const change = (e: ChangeEvent<HTMLInputElement>): void => {
    setData({ ...data, [e.target.name]: e.target.value });
  };

  const next = (): void => {
    // FLAW #1: alert() for validation. Modal interrupt; SR users get a generic
    // dialog announcement with no link to the failing field. No aria-invalid,
    // no aria-describedby — error is gone the moment the user dismisses it.
    if (step === 0 && (!data.name || !data.email)) {
      window.alert("Please fill all fields.");
      return;
    }
    if (step === 1 && (!data.street || !data.city || !data.zip)) {
      window.alert("Please fill all fields.");
      return;
    }
    setStep(step + 1);
  };

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    try { await onSubmit(data); setDone(true); window.sessionStorage.removeItem(KEY); }
    catch (err) {
      // FLAW #2: error to alert() too. No inline announcement.
      window.alert(`Submission failed: ${err instanceof Error ? err.message : "unknown"}`);
    }
  };

  return (
    <form onSubmit={submit}>
      {step === 0 && (
        <div>
          <label htmlFor="n">Name</label>
          <input id="n" name="name" value={data.name} onChange={change} />
          <label htmlFor="e">Email</label>
          <input id="e" name="email" value={data.email} onChange={change} />
        </div>
      )}
      {step === 1 && (
        <div>
          <label htmlFor="s">Street</label>
          <input id="s" name="street" value={data.street} onChange={change} />
          <label htmlFor="c">City</label>
          <input id="c" name="city" value={data.city} onChange={change} />
          <label htmlFor="z">Zip</label>
          <input id="z" name="zip" value={data.zip} onChange={change} />
        </div>
      )}
      {step === 2 && <pre>{JSON.stringify(data, null, 2)}</pre>}
      {step > 0 && <button type="button" onClick={() => setStep(step - 1)}>Back</button>}
      {step < 2
        ? <button type="button" onClick={next}>Next</button>
        : <button type="submit">Submit</button>}
      {/* FLAW #3: no aria-live, success rendered as plain text. */}
      {done && <p>Done.</p>}
    </form>
  );
}
