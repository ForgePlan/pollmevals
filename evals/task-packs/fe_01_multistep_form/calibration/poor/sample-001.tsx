// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-001 — FATAL: no sessionStorage at all (state is only in memory).

import { useState } from "react";
import type { ChangeEvent, FormEvent, JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

const EMPTY: FormData = { name: "", email: "", street: "", city: "", zip: "" };

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  // FLAW #1: no sessionStorage hydration; refreshing the page loses the draft entirely.
  const [data, setData] = useState<FormData>({ ...EMPTY, ...(initialData ?? {}) });
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const change = (e: ChangeEvent<HTMLInputElement>): void => {
    setData({ ...data, [e.target.name]: e.target.value });
  };

  const next = (): void => setStep(step + 1);
  const back = (): void => setStep(step - 1);

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setLoading(true);
    try { await onSubmit(data); setDone(true); }
    finally { setLoading(false); }
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
      {/* FLAW #2: no validation at all, no aria-live, no focus management. */}
      {step > 0 && <button type="button" onClick={back}>Back</button>}
      {step < 2
        ? <button type="button" onClick={next}>Next</button>
        : <button type="submit" disabled={loading}>{loading ? "Sending..." : "Submit"}</button>}
      {done && <p>Done.</p>}
    </form>
  );
}
