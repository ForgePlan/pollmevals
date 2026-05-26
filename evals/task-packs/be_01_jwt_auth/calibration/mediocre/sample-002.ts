// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-002 — refresh-token rotation MISSING entirely (only verifies refresh, never rotates or invalidates)

import { timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response, NextFunction } from "express";
import jwt, { type JwtPayload, type VerifyOptions } from "jsonwebtoken";

export interface AuthedRequest extends Request {
  user: { sub: string; roles: readonly string[] };
}

export interface RefreshStore {
  isActive(subject: string, jti: string): Promise<boolean>;
  rotate(subject: string, oldJti: string, newJti: string): Promise<void>;
}

export interface AuthMiddlewareOptions {
  accessSecret: string;
  refreshSecret: string;
  issuer: string;
  refreshStore: RefreshStore;
}

type AuthErrorCode =
  | "AUTH_MISSING"
  | "AUTH_MALFORMED"
  | "AUTH_EXPIRED"
  | "AUTH_INVALID_SIGNATURE"
  | "AUTH_INVALID_ISSUER"
  | "AUTH_REFRESH_REVOKED"
  | "CSRF_MISMATCH";

function parseBearer(authHeader: string | undefined): string | null {
  if (!authHeader) return null;
  const m = authHeader.match(/^Bearer\s+(\S+)$/);
  return m ? m[1] : null;
}

function stateChanging(method: string): boolean {
  return !["GET", "HEAD", "OPTIONS"].includes(method);
}

function verifyAccessToken(
  token: string,
  secret: string,
  verifyOpts: VerifyOptions,
): { ok: true; payload: JwtPayload } | { ok: false; code: AuthErrorCode } {
  try {
    const p = jwt.verify(token, secret, verifyOpts);
    if (typeof p === "string" || p === null) return { ok: false, code: "AUTH_MALFORMED" };
    return { ok: true, payload: p };
  } catch (e) {
    const name = (e as { name?: string }).name;
    if (name === "TokenExpiredError") return { ok: false, code: "AUTH_EXPIRED" };
    const msg = (e as { message?: string }).message ?? "";
    if (msg.match(/issuer invalid/)) return { ok: false, code: "AUTH_INVALID_ISSUER" };
    return { ok: false, code: "AUTH_INVALID_SIGNATURE" };
  }
}

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  const vOpts: VerifyOptions = { issuer: opts.issuer, algorithms: ["HS256"] };

  return async function handler(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      if (stateChanging(req.method)) {
        const h = req.get("x-csrf-token") ?? "";
        const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
        if (h.length === 0 || c.length === 0 || h.length !== c.length) {
          return deny(res, 403, "CSRF_MISMATCH");
        }
        if (!timingSafeEqual(Buffer.from(h), Buffer.from(c))) {
          return deny(res, 403, "CSRF_MISMATCH");
        }
      }

      const token = parseBearer(req.get("authorization"));
      if (!token) return deny(res, 401, "AUTH_MISSING");

      const result = verifyAccessToken(token, opts.accessSecret, vOpts);
      if (!result.ok) return deny(res, 401, result.code);

      const p = result.payload;
      const sub = p.sub;
      const roles = (p as { roles?: unknown }).roles;
      if (typeof sub !== "string") return deny(res, 401, "AUTH_MALFORMED");
      if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) {
        return deny(res, 401, "AUTH_MALFORMED");
      }

      // BUG: refresh cookie is verified but NOT rotated and NOT invalidated in store.
      // Old tokens remain valid indefinitely — no server-side revocation.
      const refreshCookie = (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        try {
          jwt.verify(refreshCookie, opts.refreshSecret, { issuer: opts.issuer });
        } catch {
          return deny(res, 401, "AUTH_REFRESH_REVOKED");
        }
        // Issues a new access-token style response but never calls refreshStore.rotate()
        // and never sets a new refresh_token cookie — rotation simply does not happen.
      }

      (req as AuthedRequest).user = { sub, roles };
      next();
    } catch {
      deny(res, 401, "AUTH_MISSING");
    }
  };
}

function deny(res: Response, status: 401 | 403, code: AuthErrorCode): void {
  process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
  res.status(status).json({ error: code });
}
