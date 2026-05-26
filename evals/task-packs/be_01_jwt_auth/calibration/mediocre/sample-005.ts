// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-005 — status codes wrong throughout (400 for missing/expired auth instead of 401; 401 for CSRF instead of 403)

import { randomBytes, timingSafeEqual } from "node:crypto";
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

function extractBearer(header: string | undefined): string | null {
  if (!header) return null;
  const m = header.match(/^Bearer\s+(\S+)$/);
  return m ? m[1] : null;
}

function isMutating(method: string): boolean {
  return method !== "GET" && method !== "HEAD" && method !== "OPTIONS";
}

function narrowClaims(p: string | JwtPayload): { sub: string; roles: string[] } | null {
  if (typeof p === "string" || !p) return null;
  const sub = (p as { sub?: unknown }).sub;
  const roles = (p as { roles?: unknown }).roles;
  if (typeof sub !== "string") return null;
  if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) return null;
  return { sub, roles };
}

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  const vOpts: VerifyOptions = { issuer: opts.issuer, algorithms: ["HS256"] };

  return async function handler(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      if (isMutating(req.method)) {
        const h = req.get("x-csrf-token") ?? "";
        const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
        const ok = h.length > 0 && c.length > 0 && h.length === c.length && timingSafeEqual(Buffer.from(h), Buffer.from(c));
        if (!ok) {
          // BUG: CSRF mismatch should be 403 Forbidden, but returns 401 Unauthorized
          return fail(res, 401, "CSRF_MISMATCH");
        }
      }

      const token = extractBearer(req.get("authorization"));
      if (!token) {
        // BUG: missing auth header should be 401, but returns 400 Bad Request
        return fail(res, 400, "AUTH_MISSING");
      }

      let payload: string | JwtPayload;
      try {
        payload = jwt.verify(token, opts.accessSecret, vOpts);
      } catch (err) {
        const name = (err as { name?: string }).name;
        const msg = (err as { message?: string }).message ?? "";
        if (name === "TokenExpiredError") {
          // BUG: expired token should be 401, but returns 400
          return fail(res, 400, "AUTH_EXPIRED");
        }
        if (msg.match(/issuer/)) {
          // BUG: invalid issuer should be 401, but returns 400
          return fail(res, 400, "AUTH_INVALID_ISSUER");
        }
        // BUG: invalid signature should be 401, but returns 400
        return fail(res, 400, "AUTH_INVALID_SIGNATURE");
      }

      const claims = narrowClaims(payload);
      if (!claims) {
        // BUG: malformed payload should be 401, but returns 400
        return fail(res, 400, "AUTH_MALFORMED");
      }

      const refreshCookie = (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const outcome = await rotateRefresh(refreshCookie, opts, res);
        if (outcome !== "ok") {
          // BUG: refresh revocation should be 401, but returns 400
          return fail(res, 400, outcome === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE");
        }
      }

      (req as AuthedRequest).user = { sub: claims.sub, roles: claims.roles };
      next();
    } catch {
      fail(res, 400, "AUTH_MISSING");
    }
  };
}

async function rotateRefresh(
  cookie: string,
  opts: AuthMiddlewareOptions,
  res: Response,
): Promise<"ok" | "revoked" | "invalid"> {
  let p: string | JwtPayload;
  try {
    p = jwt.verify(cookie, opts.refreshSecret, { issuer: opts.issuer, algorithms: ["HS256"] });
  } catch {
    return "invalid";
  }
  if (typeof p === "string" || !p) return "invalid";
  const sub = (p as { sub?: unknown }).sub;
  const jti = (p as { jti?: unknown }).jti;
  if (typeof sub !== "string" || typeof jti !== "string") return "invalid";
  if (!(await opts.refreshStore.isActive(sub, jti))) return "revoked";
  const newJti = randomBytes(16).toString("base64url");
  await opts.refreshStore.rotate(sub, jti, newJti);
  const next = jwt.sign({ sub, jti: newJti }, opts.refreshSecret, { issuer: opts.issuer, expiresIn: "7d" });
  res.cookie("refresh_token", next, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
  return "ok";
}

function fail(res: Response, status: 400 | 401 | 403, code: AuthErrorCode): void {
  process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
  res.status(status).json({ error: code });
}
