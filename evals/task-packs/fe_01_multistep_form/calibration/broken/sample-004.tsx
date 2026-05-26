// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-004 — FATAL: compiles but renders a single textarea with
// JSON inside; no steps, no labels, no validation, no a11y. axe-core
// reports multiple critical violations.

import { useState } from "react";
import type { ChangeEvent, FormEvent, JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

export function MultiStepForm({ onSubmit }: MultiStepFormProps): JSX.Element {
  // FATAL: no steps, no labels, no validation, no a11y. User edits raw JSON.
  const [text, setText] = useState("{}");
  const change = (e: ChangeEvent<HTMLTextAreaElement>): void => setText(e.target.value);

  const submit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    try {
      // No validation, no narrowing.
      const parsed = JSON.parse(text) as FormData;
      await onSubmit(parsed);
    } catch {
      // Errors silently swallowed.
    }
  };

  return (
    <form onSubmit={submit}>
      <textarea value={text} onChange={change} rows={10} cols={40} />
      <button type="submit">Submit</button>
    </form>
  );
}
