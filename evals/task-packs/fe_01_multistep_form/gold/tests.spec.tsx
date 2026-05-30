// source: own-authored 2026-05-26 by gogocat (license: MIT)
// gold/tests — hidden vitest+jsdom+axe suite covering happy path, validation,
// keyboard nav, focus management, sessionStorage round-trip, and UI states.
//
// Hidden test suite for fe_01_multistep_form. Vitest + jsdom +
// @testing-library/react + axe-core. These tests are NOT shown to the
// candidate model — they are run by the evaluator pipeline against the
// candidate's solution.tsx. The candidate sees only the prompt + the public
// API surface in task.yaml.

// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import axe from "axe-core";

import {
  MultiStepForm,
  fieldsForStep,
  hydrateDraft,
  isStepValid,
  validateField,
  type FormData,
} from "./solution.js";

const VALID: FormData = {
  name: "Ada Lovelace",
  email: "ada@example.com",
  street: "1 Analytical Way",
  city: "London",
  zip: "12345",
};

function fillStep1(data: FormData = VALID): void {
  fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: data.name } });
  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: data.email } });
}

function fillStep2(data: FormData = VALID): void {
  fireEvent.change(screen.getByLabelText(/street/i), { target: { value: data.street } });
  fireEvent.change(screen.getByLabelText(/city/i), { target: { value: data.city } });
  fireEvent.change(screen.getByLabelText(/postal/i), { target: { value: data.zip } });
}

afterEach(() => {
  cleanup();
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// 1. Pure helpers
// ---------------------------------------------------------------------------

describe("validateField", () => {
  it("[R22] requires a non-empty value", () => {
    expect(validateField("name", "")).toMatch(/required/i);
    expect(validateField("name", "   ")).toMatch(/required/i);
  });
  it("accepts a well-formed email", () => {
    expect(validateField("email", "user@example.com")).toBeNull();
  });
  it("[R23] rejects a malformed email", () => {
    expect(validateField("email", "not-an-email")).toMatch(/email/i);
  });
  it("[R24] rejects a non-digit zip", () => {
    expect(validateField("zip", "abcde")).toMatch(/postal/i);
  });
  it("accepts a 5-digit zip", () => {
    expect(validateField("zip", "12345")).toBeNull();
  });
});

describe("fieldsForStep", () => {
  it("returns personal fields", () => {
    expect(fieldsForStep("personal")).toEqual(["name", "email"]);
  });
  it("returns address fields", () => {
    expect(fieldsForStep("address")).toEqual(["street", "city", "zip"]);
  });
  it("returns no fields for review", () => {
    expect(fieldsForStep("review")).toEqual([]);
  });
});

describe("isStepValid", () => {
  it("[R6] accepts a fully valid step", () => {
    expect(isStepValid("personal", VALID)).toBe(true);
  });
  it("[R7] rejects when one field is invalid", () => {
    expect(isStepValid("personal", { ...VALID, email: "bad" })).toBe(false);
  });
});

describe("hydrateDraft", () => {
  it("[R25] returns empty for null", () => {
    expect(hydrateDraft(null)).toEqual({});
  });
  it("[R26] returns empty for malformed JSON", () => {
    expect(hydrateDraft("{not-json")).toEqual({});
  });
  it("[R27] ignores non-string fields", () => {
    expect(hydrateDraft(JSON.stringify({ name: "ok", email: 42 }))).toEqual({ name: "ok" });
  });
});

// ---------------------------------------------------------------------------
// 2. Happy path: full submission
// ---------------------------------------------------------------------------

describe("MultiStepForm (happy path)", () => {
  it("[R1][R2][R5] walks through all three steps and submits", async () => {
    const onSubmit = vi.fn(async () => undefined);
    render(<MultiStepForm onSubmit={onSubmit} />);

    fillStep1();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => expect(screen.getByLabelText(/street/i)).toBeInTheDocument());

    fillStep2();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /submit/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(VALID));
    await waitFor(() => expect(screen.getByText(/thanks/i)).toBeInTheDocument());
  });
});

// ---------------------------------------------------------------------------
// 3. Validation gates step advance + sets aria-invalid
// ---------------------------------------------------------------------------

describe("MultiStepForm (validation)", () => {
  it("[R4][R8][R11] blocks Next on empty email and renders an error linked via aria-describedby", () => {
    render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: "Ada" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    const emailInput = screen.getByLabelText(/email/i);
    expect(emailInput).toHaveAttribute("aria-invalid", "true");
    const describedBy = emailInput.getAttribute("aria-describedby");
    expect(describedBy).not.toBeNull();
    expect(document.getElementById(describedBy ?? "")).not.toBeNull();
    // Still on step 1.
    expect(screen.queryByLabelText(/street/i)).not.toBeInTheDocument();
  });

  it("[R10] renders error on blur with a bad email", () => {
    render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    const email = screen.getByLabelText(/email/i);
    fireEvent.change(email, { target: { value: "not-an-email" } });
    fireEvent.blur(email);
    expect(email).toHaveAttribute("aria-invalid", "true");
  });
});

// ---------------------------------------------------------------------------
// 4. Keyboard navigation
// ---------------------------------------------------------------------------

describe("MultiStepForm (keyboard)", () => {
  it("[R9] uses real button elements (focusable + Enter activates)", () => {
    render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    const next = screen.getByRole("button", { name: /next/i });
    expect(next.tagName).toBe("BUTTON");
  });

  it("[R18] focuses the first input on step change", async () => {
    render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    fillStep1();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => {
      expect(document.activeElement).toBe(screen.getByLabelText(/street/i));
    });
  });
});

// ---------------------------------------------------------------------------
// 5. Accessibility via axe-core
// ---------------------------------------------------------------------------

describe("MultiStepForm (axe)", () => {
  it("[R12] has 0 serious / critical violations on step 1", async () => {
    const { container } = render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    const results = await axe.run(container);
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious).toEqual([]);
  });

  it("[R13] has 0 serious / critical violations on the review step", async () => {
    const { container } = render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    fillStep1();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fillStep2();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    const results = await axe.run(container);
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// 6. sessionStorage round-trip
// ---------------------------------------------------------------------------

describe("MultiStepForm (sessionStorage)", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("[R14][R15] persists draft on input and rehydrates on remount", async () => {
    const { unmount } = render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    fillStep1();
    await waitFor(() => {
      const raw = window.sessionStorage.getItem("fe01:multistep-form:draft");
      expect(raw).not.toBeNull();
      expect(raw).toContain("ada@example.com");
    });
    unmount();
    render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    expect((screen.getByLabelText(/full name/i) as HTMLInputElement).value).toBe(VALID.name);
    expect((screen.getByLabelText(/email/i) as HTMLInputElement).value).toBe(VALID.email);
  });

  it("[R17] clears the draft after a successful submit", async () => {
    render(<MultiStepForm onSubmit={vi.fn(async () => undefined)} />);
    fillStep1();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fillStep2();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));
    await waitFor(() => {
      expect(window.sessionStorage.getItem("fe01:multistep-form:draft")).toBeNull();
    });
  });
});

// ---------------------------------------------------------------------------
// 7. UI state machine: loading + error
// ---------------------------------------------------------------------------

describe("MultiStepForm (ui states)", () => {
  it("[R20][R21] announces submission failure via role=alert and preserves data", async () => {
    const onSubmit = vi.fn(async () => {
      throw new Error("network down");
    });
    render(<MultiStepForm onSubmit={onSubmit} />);
    fillStep1();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fillStep2();
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    fireEvent.click(screen.getByRole("button", { name: /submit/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/network down/i));
    // Data still in sessionStorage (not cleared on failure).
    expect(window.sessionStorage.getItem("fe01:multistep-form:draft")).not.toBeNull();
  });
});
