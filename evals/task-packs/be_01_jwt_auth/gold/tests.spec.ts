// source: own-authored 2026-05-26 by gogocat (license: MIT)
//
// Hidden test suite for be_01_jwt_auth. Vitest. These tests are NOT shown to
// the candidate model — they are run by the evaluator pipeline against the
// candidate's solution.ts. The candidate sees only the prompt + the public
// API surface in task.yaml.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import express, { type Express } from "express";
import cookieParser from "cookie-parser";
import jwt from "jsonwebtoken";
import request from "supertest";

import {
  authMiddleware,
  extractBearer,
  isStateChanging,
  narrowAccessClaims,
  type AuthMiddlewareOptions,
  type RefreshStore,
} from "./solution.js";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const ACCESS_SECRET = "test-access-secret-32-bytes-long-aaaaa";
const REFRESH_SECRET = "test-refresh-secret-32-bytes-long-bbbbb";
const ISSUER = "pollmevals-test";

function makeStore(): RefreshStore & { active: Set<string> } {
  const active = new Set<string>();
  return {
    active,
    async isActive(_sub: string, jti: string): Promise<boolean> {
      return active.has(jti);
    },
    async rotate(_sub: string, oldJti: string, newJti: string): Promise<void> {
      active.delete(oldJti);
      active.add(newJti);
    },
  };
}

function makeApp(opts: AuthMiddlewareOptions): Express {
  const app = express();
  app.use(cookieParser());
  app.use(authMiddleware(opts));
  app.get("/protected", (req, res) => {
    res.json({ user: (req as unknown as { user: unknown }).user });
  });
  app.post("/state", (_req, res) => {
    res.json({ ok: true });
  });
  return app;
}

function signAccess(claims: Record<string, unknown>, secret = ACCESS_SECRET): string {
  return jwt.sign({ iss: ISSUER, roles: ["user"], ...claims }, secret, { algorithm: "HS256" });
}

// ---------------------------------------------------------------------------
// 1. Pure helpers
// ---------------------------------------------------------------------------

describe("extractBearer", () => {
  it("[R6] returns the token for a well-formed Bearer header", () => {
    expect(extractBearer("Bearer abc.def.ghi")).toBe("abc.def.ghi");
  });
  it("[R7] returns null for undefined", () => {
    expect(extractBearer(undefined)).toBeNull();
  });
  it("[R8] returns null for missing scheme", () => {
    expect(extractBearer("abc.def.ghi")).toBeNull();
  });
  it("[R9] returns null for wrong scheme", () => {
    expect(extractBearer("Basic abc")).toBeNull();
  });
  it("[R10] returns null for empty Bearer value", () => {
    expect(extractBearer("Bearer ")).toBeNull();
  });
});

describe("isStateChanging", () => {
  it.each(["GET", "HEAD", "OPTIONS"])("[R11] returns false for safe method %s", (m) => {
    expect(isStateChanging(m)).toBe(false);
  });
  it.each(["POST", "PUT", "PATCH", "DELETE"])("[R12] returns true for unsafe method %s", (m) => {
    expect(isStateChanging(m)).toBe(true);
  });
});

describe("narrowAccessClaims", () => {
  it("[R13] narrows a well-shaped payload", () => {
    expect(
      narrowAccessClaims({ sub: "u1", iss: "x", roles: ["a", "b"], exp: 1, iat: 0 }),
    ).toEqual({ sub: "u1", iss: "x", roles: ["a", "b"], exp: 1 });
  });
  it("[R14] rejects payload with non-string sub", () => {
    expect(narrowAccessClaims({ sub: 1, iss: "x", roles: ["a"], exp: 1 })).toBeNull();
  });
  it("[R15] rejects payload with non-array roles", () => {
    expect(narrowAccessClaims({ sub: "u", iss: "x", roles: "a", exp: 1 })).toBeNull();
  });
  it("[R16] rejects payload with non-string role element", () => {
    expect(narrowAccessClaims({ sub: "u", iss: "x", roles: ["a", 2], exp: 1 })).toBeNull();
  });
  it("[R17] rejects a string payload (jwt sometimes returns a string)", () => {
    expect(narrowAccessClaims("not-an-object")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// 2. Middleware happy path
// ---------------------------------------------------------------------------

describe("authMiddleware (happy path)", () => {
  let store: RefreshStore & { active: Set<string> };
  let app: Express;

  beforeEach(() => {
    store = makeStore();
    app = makeApp({
      accessSecret: ACCESS_SECRET,
      refreshSecret: REFRESH_SECRET,
      issuer: ISSUER,
      refreshStore: store,
    });
  });

  it("[R1] passes a valid Bearer token", async () => {
    const token = signAccess({ sub: "alice" });
    const res = await request(app).get("/protected").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.user).toEqual({ sub: "alice", roles: ["user"] });
  });

  it("[R2] returns 401 + AUTH_MISSING when Authorization header absent", async () => {
    const res = await request(app).get("/protected");
    expect(res.status).toBe(401);
    expect(res.body.error).toBe("AUTH_MISSING");
  });

  it("[R3] returns 401 + AUTH_EXPIRED for an expired token", async () => {
    const token = jwt.sign(
      { sub: "alice", iss: ISSUER, roles: ["user"], exp: Math.floor(Date.now() / 1000) - 60 },
      ACCESS_SECRET,
      { algorithm: "HS256" },
    );
    const res = await request(app).get("/protected").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(401);
    expect(res.body.error).toBe("AUTH_EXPIRED");
  });

  it("[R4] returns 401 + AUTH_INVALID_SIGNATURE for a tampered token", async () => {
    const token = signAccess({ sub: "alice" }) + "tampered";
    const res = await request(app).get("/protected").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(401);
    expect(res.body.error).toBe("AUTH_INVALID_SIGNATURE");
  });

  it("[R5] returns 401 + AUTH_INVALID_ISSUER for a wrong-iss token", async () => {
    const token = jwt.sign({ sub: "alice", iss: "evil", roles: ["user"] }, ACCESS_SECRET, {
      algorithm: "HS256",
    });
    const res = await request(app).get("/protected").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(401);
    expect(res.body.error).toBe("AUTH_INVALID_ISSUER");
  });
});

// ---------------------------------------------------------------------------
// 3. CSRF on state-changing methods
// ---------------------------------------------------------------------------

describe("authMiddleware (CSRF)", () => {
  let app: Express;

  beforeEach(() => {
    app = makeApp({
      accessSecret: ACCESS_SECRET,
      refreshSecret: REFRESH_SECRET,
      issuer: ISSUER,
      refreshStore: makeStore(),
    });
  });

  it("[R18] rejects POST without matching csrf_token / X-CSRF-Token", async () => {
    const token = signAccess({ sub: "alice" });
    const res = await request(app)
      .post("/state")
      .set("Authorization", `Bearer ${token}`)
      .set("Cookie", "csrf_token=abc")
      .set("X-CSRF-Token", "xyz");
    expect(res.status).toBe(403);
    expect(res.body.error).toBe("CSRF_MISMATCH");
  });

  it("[R19] accepts POST with matching csrf_token / X-CSRF-Token", async () => {
    const token = signAccess({ sub: "alice" });
    const csrf = "secure-csrf-value-1234567890ab";
    const res = await request(app)
      .post("/state")
      .set("Authorization", `Bearer ${token}`)
      .set("Cookie", `csrf_token=${csrf}`)
      .set("X-CSRF-Token", csrf);
    expect(res.status).toBe(200);
  });
});

// ---------------------------------------------------------------------------
// 4. Refresh rotation
// ---------------------------------------------------------------------------

describe("authMiddleware (refresh rotation)", () => {
  // Shared setup so each refresh-cookie requirement (R20 rotation/jti, R21
  // HttpOnly, R22 SameSite=Strict) is asserted in its own 1:1-tagged test
  // (RFC-004 Invariant C4: test_id ↔ requirement_id is 1:1).
  async function rotateActiveRefresh() {
    const store = makeStore();
    const oldJti = "jti-original";
    store.active.add(oldJti);
    const refresh = jwt.sign({ sub: "alice", jti: oldJti, iss: ISSUER }, REFRESH_SECRET, {
      algorithm: "HS256",
      expiresIn: "7d",
    });
    const access = signAccess({ sub: "alice" });
    const app = makeApp({
      accessSecret: ACCESS_SECRET,
      refreshSecret: REFRESH_SECRET,
      issuer: ISSUER,
      refreshStore: store,
    });
    const res = await request(app)
      .get("/protected")
      .set("Authorization", `Bearer ${access}`)
      .set("Cookie", `refresh_token=${refresh}`);
    return { res, store, oldJti };
  }

  it("[R20] rotates an active refresh cookie and invalidates the old jti", async () => {
    const { res, store, oldJti } = await rotateActiveRefresh();
    expect(res.status).toBe(200);
    expect(store.active.has(oldJti)).toBe(false);
    expect(store.active.size).toBe(1);
    // New refresh cookie issued on rotation.
    const setCookie = res.headers["set-cookie"] as string[] | undefined;
    expect(setCookie?.some((c) => c.includes("refresh_token="))).toBe(true);
  });

  it("[R21] sets the rotated refresh cookie HttpOnly", async () => {
    const { res } = await rotateActiveRefresh();
    const setCookie = res.headers["set-cookie"] as string[] | undefined;
    expect(setCookie?.some((c) => /httponly/i.test(c))).toBe(true);
  });

  it("[R22] sets the rotated refresh cookie SameSite=Strict", async () => {
    const { res } = await rotateActiveRefresh();
    const setCookie = res.headers["set-cookie"] as string[] | undefined;
    expect(setCookie?.some((c) => /samesite=strict/i.test(c))).toBe(true);
  });

  it("[R23] rejects a revoked refresh cookie", async () => {
    const store = makeStore();
    // No active jti registered.
    const refresh = jwt.sign({ sub: "alice", jti: "revoked-jti", iss: ISSUER }, REFRESH_SECRET, {
      algorithm: "HS256",
      expiresIn: "7d",
    });
    const access = signAccess({ sub: "alice" });
    const app = makeApp({
      accessSecret: ACCESS_SECRET,
      refreshSecret: REFRESH_SECRET,
      issuer: ISSUER,
      refreshStore: store,
    });

    const res = await request(app)
      .get("/protected")
      .set("Authorization", `Bearer ${access}`)
      .set("Cookie", `refresh_token=${refresh}`);
    expect(res.status).toBe(401);
    expect(res.body.error).toBe("AUTH_REFRESH_REVOKED");
  });
});

// ---------------------------------------------------------------------------
// 5. Secret hygiene — the response and the stderr log must never contain the
//    raw token, secret, or signing key.
// ---------------------------------------------------------------------------

describe("authMiddleware (secret hygiene)", () => {
  it("[R24] never echoes the bearer token in the error body on failure", async () => {
    const token = "FORBIDDEN-SECRET-VALUE-MUST-NOT-LEAK";
    const app = makeApp({
      accessSecret: ACCESS_SECRET,
      refreshSecret: REFRESH_SECRET,
      issuer: ISSUER,
      refreshStore: makeStore(),
    });
    const res = await request(app).get("/protected").set("Authorization", `Bearer ${token}`);
    expect(res.status).toBe(401);
    expect(JSON.stringify(res.body)).not.toContain(token);
  });

  it("[R25] never writes the access secret to stderr on internal error", async () => {
    const writes: string[] = [];
    const spy = vi.spyOn(process.stderr, "write").mockImplementation((chunk: unknown) => {
      writes.push(String(chunk));
      return true;
    });
    try {
      const app = makeApp({
        accessSecret: ACCESS_SECRET,
        refreshSecret: REFRESH_SECRET,
        issuer: ISSUER,
        refreshStore: makeStore(),
      });
      await request(app).get("/protected").set("Authorization", "Bearer not.a.jwt");
      const all = writes.join("");
      expect(all).not.toContain(ACCESS_SECRET);
      expect(all).not.toContain(REFRESH_SECRET);
    } finally {
      spy.mockRestore();
    }
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});
