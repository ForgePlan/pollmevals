// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-005 — FATAL: `any` everywhere, casts on user input, no
// strict-mode hygiene; loosely-typed code that "works" by coincidence.

/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import type { JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

const KEY = "fe01:multistep-form:draft";

export function MultiStepForm(props: MultiStepFormProps): JSX.Element {
  // FLAW #1: data typed as `any`; no narrowing on sessionStorage JSON.
  const initial: any = (() => {
    try { return JSON.parse(window.sessionStorage.getItem(KEY) ?? "{}"); }
    catch { return {}; }
  })();
  const [data, setData] = useState<any>({ name: "", email: "", street: "", city: "", zip: "", ...initial, ...props.initialData });
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);

  // FLAW #2: event typed as `any`; e.target.value typed as `any`.
  const change = (e: any): void => {
    const next = { ...data, [e.target.name]: e.target.value };
    setData(next);
    window.sessionStorage.setItem(KEY, JSON.stringify(next));
  };

  const submit = async (e: any): Promise<void> => {
    e.preventDefault();
    // FLAW #3: unsafe cast to FormData with no runtime check; if a field is
    // missing, the onSubmit handler receives an incomplete object.
    await props.onSubmit(data as FormData);
    setDone(true);
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
        ? <button type="button" onClick={() => setStep(step + 1)}>Next</button>
        : <button type="submit">Submit</button>}
      {/* FLAW #4: no a11y attributes anywhere except labels; no aria-live, no validation. */}
      {done && <p>Done.</p>}
    </form>
  );
}
