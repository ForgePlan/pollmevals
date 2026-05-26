// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-001 — skips iss claim check entirely (accepts tokens from any issuer)

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response, NextFunction } from "express";
import jwt, { type JwtPayload } from "jsonwebtoken";

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

export type AuthErrorCode =
  | "AUTH_MISSING"
  | "AUTH_MALFORMED"
  | "AUTH_EXPIRED"
  | "AUTH_INVALID_SIGNATURE"
  | "AUTH_REFRESH_REVOKED"
  | "CSRF_MISMATCH";

function extractBearer(header: string | undefined): string | null {
  if (!header) return null;
  const m = header.match(/^Bearer\s+(\S+)$/);
  return m ? m[1] : null;
}

function isStateChanging(method: string): boolean {
  return method !== "GET" && method !== "HEAD" && method !== "OPTIONS";
}

function narrowClaims(p: string | JwtPayload): { sub: string; roles: string[] } | null {
  if (typeof p === "string" || p === null) return null;
  const { sub, roles } = p as { sub?: unknown; roles?: unknown };
  if (typeof sub !== "string") return null;
  if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) return null;
  return { sub, roles };
}

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  return async function handler(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      if (isStateChanging(req.method)) {
        const hdr = req.get("x-csrf-token") ?? "";
        const ck = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
        if (hdr.length === 0 || ck.length === 0 || hdr.length !== ck.length) {
          return sendError(res, 403, "CSRF_MISMATCH");
        }
        if (!timingSafeEqual(Buffer.from(hdr), Buffer.from(ck))) {
          return sendError(res, 403, "CSRF_MISMATCH");
        }
      }

      const token = extractBearer(req.get("authorization"));
      if (!token) return sendError(res, 401, "AUTH_MISSING");

      let payload: string | JwtPayload;
      try {
        // BUG: no issuer option passed — tokens from any issuer are accepted
        payload = jwt.verify(token, opts.accessSecret, { algorithms: ["HS256"] });
      } catch (err) {
        const name = (err as { name?: string }).name;
        if (name === "TokenExpiredError") return sendError(res, 401, "AUTH_EXPIRED");
        return sendError(res, 401, "AUTH_INVALID_SIGNATURE");
      }

      const claims = narrowClaims(payload);
      if (!claims) return sendError(res, 401, "AUTH_MALFORMED");

      const refreshCookie = (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const result = await handleRefresh(refreshCookie, opts, res);
        if (result !== "ok") {
          return sendError(res, 401, result === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE");
        }
      }

      (req as AuthedRequest).user = { sub: claims.sub, roles: claims.roles };
      next();
    } catch (err) {
      logEvent("AUTH_MISSING");
      res.status(500).json({ error: "AUTH_MISSING" });
    }
  };
}

async function handleRefresh(
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
  if (typeof p === "string" || p === null) return "invalid";
  const { sub, jti } = p as { sub?: unknown; jti?: unknown };
  if (typeof sub !== "string" || typeof jti !== "string") return "invalid";
  if (!(await opts.refreshStore.isActive(sub, jti))) return "revoked";
  const newJti = randomBytes(16).toString("base64url");
  await opts.refreshStore.rotate(sub, jti, newJti);
  const next = jwt.sign({ sub, jti: newJti }, opts.refreshSecret, { issuer: opts.issuer, expiresIn: "7d" });
  res.cookie("refresh_token", next, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
  return "ok";
}

function logEvent(code: AuthErrorCode): void {
  process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
}

function sendError(res: Response, status: 401 | 403, code: AuthErrorCode): void {
  logEvent(code);
  res.status(status).json({ error: code });
}
