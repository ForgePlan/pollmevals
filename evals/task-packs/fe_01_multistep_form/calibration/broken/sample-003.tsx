// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-003 — FATAL: missing `react` import; JSX without React in scope.

// INTENTIONAL: no react import at all. With "jsx": "react-jsx" this would
// still need react/jsx-runtime; with classic transform it errors immediately.
// useState is referenced but never imported.

export interface FormData {
  name: string; email: string; street: string; city: string; zip: string;
}
export interface MultiStepFormProps {
  onSubmit: (d: FormData) => Promise<void>;
  initialData?: Partial<FormData>;
}

export function MultiStepForm(_props: MultiStepFormProps) {
  // useState is undefined — tsc errors with "Cannot find name 'useState'".
  const [data, setData] = useState({ name: "", email: "" });
  return (
    <form>
      <input value={data.name} onChange={(e) => setData({ ...data, name: e.target.value })} />
    </form>
  );
}
