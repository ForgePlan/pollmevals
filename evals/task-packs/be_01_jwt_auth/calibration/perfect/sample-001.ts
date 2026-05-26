// source: own-authored 2026-05-26 by gogocat (license: MIT)
// perfect/sample-001 — functional composition: separate verify + authorize pipeline.
// Distinct idiom: small pure functions chained, no shared state.

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response } from "express";
import jwt, { type JwtPayload, type VerifyOptions } from "jsonwebtoken";

export type AuthErr =
  | "AUTH_MISSING" | "AUTH_MALFORMED" | "AUTH_EXPIRED"
  | "AUTH_INVALID_SIGNATURE" | "AUTH_INVALID_ISSUER"
  | "AUTH_REFRESH_REVOKED" | "CSRF_MISMATCH";

export interface RefreshStore {
  isActive(sub: string, jti: string): Promise<boolean>;
  rotate(sub: string, oldJti: string, newJti: string): Promise<void>;
}

export interface Opts {
  accessSecret: string; refreshSecret: string; issuer: string; refreshStore: RefreshStore;
}

const STATE_CHANGING = (m: string) => m !== "GET" && m !== "HEAD" && m !== "OPTIONS";

const bearer = (h: string | undefined): string | null => {
  if (!h) return null;
  const m = h.match(/^Bearer\s+(\S+)$/);
  return m ? m[1] : null;
};

const verifyAccess = (token: string, opts: Opts): JwtPayload | AuthErr => {
  try {
    const v: VerifyOptions = { issuer: opts.issuer, algorithms: ["HS256"] };
    const p = jwt.verify(token, opts.accessSecret, v);
    if (typeof p === "string" || p === null) return "AUTH_MALFORMED";
    return p;
  } catch (e) {
    const name = (e as { name?: string }).name;
    if (name === "TokenExpiredError") return "AUTH_EXPIRED";
    const msg = (e as { message?: string }).message ?? "";
    return msg.startsWith("jwt issuer invalid") ? "AUTH_INVALID_ISSUER" : "AUTH_INVALID_SIGNATURE";
  }
};

const csrfOk = (req: Request): boolean => {
  const h = req.get("x-csrf-token") ?? "";
  const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
  if (h.length === 0 || c.length === 0 || h.length !== c.length) return false;
  return timingSafeEqual(Buffer.from(h), Buffer.from(c));
};

export function authMiddleware(opts: Opts): RequestHandler {
  return async (req, res, next) => {
    if (STATE_CHANGING(req.method) && !csrfOk(req)) return fail(res, 403, "CSRF_MISMATCH");
    const tok = bearer(req.get("authorization"));
    if (!tok) return fail(res, 401, "AUTH_MISSING");
    const claims = verifyAccess(tok, opts);
    if (typeof claims === "string") return fail(res, 401, claims);
    const sub = claims.sub, roles = claims["roles"];
    if (typeof sub !== "string" || !Array.isArray(roles)) return fail(res, 401, "AUTH_MALFORMED");
    const refresh = (req.cookies as Record<string, string> | undefined)?.refresh_token;
    if (refresh) {
      const r = await rotate(refresh, opts, res);
      if (r !== "ok") return fail(res, 401, r === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE");
    }
    (req as Request & { user: unknown }).user = { sub, roles };
    next();
  };
}

const rotate = async (cookie: string, opts: Opts, res: Response): Promise<"ok" | "revoked" | "invalid"> => {
  try {
    const p = jwt.verify(cookie, opts.refreshSecret, { issuer: opts.issuer });
    if (typeof p === "string" || !p) return "invalid";
    const { sub, jti } = p;
    if (typeof sub !== "string" || typeof jti !== "string") return "invalid";
    if (!(await opts.refreshStore.isActive(sub, jti))) return "revoked";
    const next = randomBytes(16).toString("base64url");
    await opts.refreshStore.rotate(sub, jti, next);
    const t = jwt.sign({ sub, jti: next }, opts.refreshSecret, { issuer: opts.issuer, expiresIn: "7d" });
    res.cookie("refresh_token", t, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
    return "ok";
  } catch { return "invalid"; }
};

const fail = (res: Response, status: 401 | 403, code: AuthErr): void => {
  process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
  res.status(status).json({ error: code });
};
