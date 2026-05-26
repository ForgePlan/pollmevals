// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-005 — FATAL: infinite re-render loop (setState in render body).

import { useState } from "react";
import type { JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

const EMPTY: FormData = { name: "", email: "", street: "", city: "", zip: "" };

export function MultiStepForm({ initialData }: MultiStepFormProps): JSX.Element {
  const [data, setData] = useState<FormData>({ ...EMPTY, ...(initialData ?? {}) });
  const [step, setStep] = useState(0);

  // FATAL: setState invoked unconditionally during render. React throws
  // "Too many re-renders" and the component never mounts. Tests crash.
  if (step === 0) {
    setData({ ...data, name: data.name });
  }

  return (
    <form>
      <p>Step {step}</p>
      <input value={data.name} onChange={(e) => setData({ ...data, name: e.target.value })} />
      <button type="button" onClick={() => setStep(step + 1)}>Next</button>
    </form>
  );
}
