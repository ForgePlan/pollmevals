// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-002 — FATAL: wrong public API (returns string, not JSX.Element).

import type { JSX } from "react";

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

// FATAL: signature does not match prompt. Declared return type is JSX.Element
// but the body returns a string. tsc strict mode will reject this.
export function MultiStepForm(_props: MultiStepFormProps): JSX.Element {
  return "TODO: implement multi-step form";
}
