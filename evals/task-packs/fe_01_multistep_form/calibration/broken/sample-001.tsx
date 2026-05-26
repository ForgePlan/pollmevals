// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-001 — FATAL: missing closing brace on component function — tsc rejects.

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
  const [data, setData] = useState<FormData>({ ...EMPTY, ...(initialData ?? {}) });
  const [step, setStep] = useState(0);

  const change = (e: ChangeEvent<HTMLInputElement>): void => {
    setData({ ...data, [e.target.name]: e.target.value });
  };

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    await onSubmit(data);
  };

  return (
    <form onSubmit={submit}>
      {step === 0 && (
        <div>
          <label htmlFor="n">Name</label>
          <input id="n" name="name" value={data.name} onChange={change} />
        </div>
      )}
      <button type="button" onClick={() => setStep(step + 1)}>Next</button>
      <button type="submit">Submit</button>
    </form>
  );
// INTENTIONAL: closing brace for MultiStepForm function body is missing — tsc cannot parse this file.
