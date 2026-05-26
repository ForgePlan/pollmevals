// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-002 — FATAL: div-as-button + no labels (placeholders instead).

import { useState } from "react";
import type { ChangeEvent, JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

const EMPTY: FormData = { name: "", email: "", street: "", city: "", zip: "" };
const KEY = "fe01:multistep-form:draft";

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

  const change = (e: ChangeEvent<HTMLInputElement>): void => {
    const next = { ...data, [e.target.name]: e.target.value };
    setData(next);
    window.sessionStorage.setItem(KEY, JSON.stringify(next));
  };

  const submit = async (): Promise<void> => {
    await onSubmit(data); setDone(true);
  };

  return (
    <div className="form">
      {/* FLAW #1: no <form> element — submit is just a click handler.
          Enter key won't submit; assistive tech doesn't see this as a form. */}
      {step === 0 && (
        <div>
          {/* FLAW #2: no labels — placeholder-only inputs.
              axe-core flags this as critical. */}
          <input name="name" placeholder="Name" value={data.name} onChange={change} />
          <input name="email" placeholder="Email" value={data.email} onChange={change} />
        </div>
      )}
      {step === 1 && (
        <div>
          <input name="street" placeholder="Street" value={data.street} onChange={change} />
          <input name="city" placeholder="City" value={data.city} onChange={change} />
          <input name="zip" placeholder="Zip" value={data.zip} onChange={change} />
        </div>
      )}
      {step === 2 && <pre>{JSON.stringify(data, null, 2)}</pre>}
      {/* FLAW #3: div-as-button. Not keyboard accessible, not focusable. */}
      {step > 0 && (
        <div className="btn" onClick={() => setStep(step - 1)}>Back</div>
      )}
      {step < 2
        ? <div className="btn" onClick={() => setStep(step + 1)}>Next</div>
        : <div className="btn" onClick={submit}>Submit</div>}
      {done && <div>Done.</div>}
    </div>
  );
}
