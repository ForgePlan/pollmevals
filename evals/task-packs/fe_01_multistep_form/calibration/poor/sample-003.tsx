// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-003 — FATAL: useRef-driven uncontrolled inputs, no React state
// for data; sessionStorage written only on submit (lost on refresh mid-form).

import { useRef, useState } from "react";
import type { FormEvent, JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

const KEY = "fe01:multistep-form:draft";

export function MultiStepForm({ onSubmit, initialData }: MultiStepFormProps): JSX.Element {
  // FLAW #1: data lives in refs (uncontrolled). React has no idea what's typed.
  // sessionStorage is written only on submit → refresh mid-form loses everything.
  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const streetRef = useRef<HTMLInputElement>(null);
  const cityRef = useRef<HTMLInputElement>(null);
  const zipRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    const data: FormData = {
      name: nameRef.current?.value ?? "",
      email: emailRef.current?.value ?? "",
      street: streetRef.current?.value ?? "",
      city: cityRef.current?.value ?? "",
      zip: zipRef.current?.value ?? "",
    };
    window.sessionStorage.setItem(KEY, JSON.stringify(data));
    await onSubmit(data);
    setDone(true);
  };

  return (
    <form onSubmit={submit}>
      {step === 0 && (
        <div>
          <label htmlFor="n">Name</label>
          <input id="n" ref={nameRef} defaultValue={initialData?.name ?? ""} />
          <label htmlFor="e">Email</label>
          <input id="e" ref={emailRef} defaultValue={initialData?.email ?? ""} />
        </div>
      )}
      {step === 1 && (
        <div>
          <label htmlFor="s">Street</label>
          <input id="s" ref={streetRef} defaultValue={initialData?.street ?? ""} />
          <label htmlFor="c">City</label>
          <input id="c" ref={cityRef} defaultValue={initialData?.city ?? ""} />
          <label htmlFor="z">Zip</label>
          <input id="z" ref={zipRef} defaultValue={initialData?.zip ?? ""} />
        </div>
      )}
      {/* FLAW #2: review step can't render data because uncontrolled inputs
          don't update React state. Shows a static message instead. */}
      {step === 2 && <p>Press submit to send.</p>}
      {step > 0 && <button type="button" onClick={() => setStep(step - 1)}>Back</button>}
      {step < 2
        ? <button type="button" onClick={() => setStep(step + 1)}>Next</button>
        : <button type="submit">Submit</button>}
      {/* FLAW #3: no aria-live, no validation, no focus management. */}
      {done && <p>Done.</p>}
    </form>
  );
}
