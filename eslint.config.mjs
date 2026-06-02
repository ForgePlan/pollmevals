import { FlatCompat } from "@eslint/eslintrc";

// Repo-root ESLint flat config (eslint 9). The monorepo is Python-first; the
// only TS that needs linting is the Next.js site. Scope next/core-web-vitals to
// apps/site and ignore everything else so lefthook's `eslint --fix` (run from
// the repo root over staged files) passes cleanly.
const compat = new FlatCompat({
  baseDirectory: new URL("./apps/site", import.meta.url).pathname,
});

export default [
  {
    ignores: [
      "**/.next/**",
      "**/out/**",
      "**/node_modules/**",
      "**/dist/**",
      "**/.moon/**",
      "**/*.d.ts",
      "apps/eval-core-py/**",
    ],
  },
  ...compat.extends("next/core-web-vitals").map((c) => ({
    ...c,
    files: ["apps/site/**/*.{ts,tsx,js,jsx,mjs}"],
  })),
];
