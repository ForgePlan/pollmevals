// source: own-authored 2026-05-26 by gogocat (license: MIT)
// perfect/sample-004 — Result<T, E> discriminated union, no throws.
// Distinct idiom: every failure mode is a typed Result; no try/catch in caller.

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response } from "express";
import jwt from "jsonwebtoken";

type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

type AuthError =
  | { kind: "MISSING" } | { kind: "MALFORMED" } | { kind: "EXPIRED" }
  | { kind: "INVALID_SIGNATURE" } | { kind: "INVALID_ISSUER" }
  | { kind: "REFRESH_REVOKED" } | { kind: "CSRF" };

const codeFor: Record<AuthError["kind"], string> = {
  MISSING: "AUTH_MISSING", MALFORMED: "AUTH_MALFORMED", EXPIRED: "AUTH_EXPIRED",
  INVALID_SIGNATURE: "AUTH_INVALID_SIGNATURE", INVALID_ISSUER: "AUTH_INVALID_ISSUER",
  REFRESH_REVOKED: "AUTH_REFRESH_REVOKED", CSRF: "CSRF_MISMATCH",
};

interface Store {
  isActive(sub: string, jti: string): Promise<boolean>;
  rotate(sub: string, oldJti: string, newJti: string): Promise<void>;
}

interface Claims { sub: string; roles: readonly string[] }

function parseBearer(h: string | undefined): Result<string, AuthError> {
  const m = h ? h.match(/^Bearer\s+(\S+)$/) : null;
  return m ? { ok: true, value: m[1] } : { ok: false, error: { kind: "MISSING" } };
}

function verifyAccess(token: string, secret: string, issuer: string): Result<Claims, AuthError> {
  try {
    const p = jwt.verify(token, secret, { issuer, algorithms: ["HS256"] });
    if (typeof p === "string" || !p) return { ok: false, error: { kind: "MALFORMED" } };
    const sub = p.sub, roles = (p as { roles?: unknown }).roles;
    if (typeof sub !== "string") return { ok: false, error: { kind: "MALFORMED" } };
    if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) {
      return { ok: false, error: { kind: "MALFORMED" } };
    }
    return { ok: true, value: { sub, roles: roles as readonly string[] } };
  } catch (e) {
    const name = (e as { name?: string }).name;
    if (name === "TokenExpiredError") return { ok: false, error: { kind: "EXPIRED" } };
    const msg = (e as { message?: string }).message ?? "";
    return msg.startsWith("jwt issuer invalid")
      ? { ok: false, error: { kind: "INVALID_ISSUER" } }
      : { ok: false, error: { kind: "INVALID_SIGNATURE" } };
  }
}

function checkCsrf(req: Request): Result<true, AuthError> {
  const h = req.get("x-csrf-token") ?? "";
  const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
  if (!h || !c || h.length !== c.length) return { ok: false, error: { kind: "CSRF" } };
  if (!timingSafeEqual(Buffer.from(h), Buffer.from(c))) return { ok: false, error: { kind: "CSRF" } };
  return { ok: true, value: true };
}

async function rotateRefresh(
  cookie: string, secret: string, issuer: string, store: Store, res: Response,
): Promise<Result<true, AuthError>> {
  try {
    const p = jwt.verify(cookie, secret, { issuer });
    if (typeof p === "string" || !p) return { ok: false, error: { kind: "INVALID_SIGNATURE" } };
    const { sub, jti } = p;
    if (typeof sub !== "string" || typeof jti !== "string") {
      return { ok: false, error: { kind: "INVALID_SIGNATURE" } };
    }
    if (!(await store.isActive(sub, jti))) return { ok: false, error: { kind: "REFRESH_REVOKED" } };
    const nj = randomBytes(16).toString("base64url");
    await store.rotate(sub, jti, nj);
    const tok = jwt.sign({ sub, jti: nj }, secret, { issuer, expiresIn: "7d" });
    res.cookie("refresh_token", tok, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
    return { ok: true, value: true };
  } catch { return { ok: false, error: { kind: "INVALID_SIGNATURE" } }; }
}

function emit(res: Response, e: AuthError): void {
  const code = codeFor[e.kind];
  const status: 401 | 403 = e.kind === "CSRF" ? 403 : 401;
  process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
  res.status(status).json({ error: code });
}

export function authMiddleware(
  accessSecret: string, refreshSecret: string, issuer: string, store: Store,
): RequestHandler {
  return async (req, res, next) => {
    if (!["GET", "HEAD", "OPTIONS"].includes(req.method)) {
      const csrf = checkCsrf(req);
      if (!csrf.ok) return emit(res, csrf.error);
    }
    const bearer = parseBearer(req.get("authorization"));
    if (!bearer.ok) return emit(res, bearer.error);
    const claims = verifyAccess(bearer.value, accessSecret, issuer);
    if (!claims.ok) return emit(res, claims.error);
    const refresh = (req.cookies as Record<string, string> | undefined)?.refresh_token;
    if (refresh) {
      const r = await rotateRefresh(refresh, refreshSecret, issuer, store, res);
      if (!r.ok) return emit(res, r.error);
    }
    (req as Request & { user: Claims }).user = claims.value;
    next();
  };
}
