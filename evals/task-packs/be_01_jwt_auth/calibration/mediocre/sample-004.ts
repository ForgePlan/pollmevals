// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-004 — error body includes raw JWT error message (leaks classifier strings + user input)

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

type StableCode =
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

function isStateChanging(method: string): boolean {
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
      if (isStateChanging(req.method)) {
        const h = req.get("x-csrf-token") ?? "";
        const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
        if (h.length === 0 || c.length === 0 || h.length !== c.length) {
          return sendError(res, 403, "CSRF_MISMATCH", null);
        }
        if (!timingSafeEqual(Buffer.from(h), Buffer.from(c))) {
          return sendError(res, 403, "CSRF_MISMATCH", null);
        }
      }

      const token = extractBearer(req.get("authorization"));
      if (!token) return sendError(res, 401, "AUTH_MISSING", null);

      let payload: string | JwtPayload;
      try {
        payload = jwt.verify(token, opts.accessSecret, vOpts);
      } catch (err) {
        const name = (err as { name?: string }).name;
        const rawMsg = (err as { message?: string }).message ?? "unknown";
        // BUG: error response body includes the raw JWT library error message.
        // This leaks classifier strings such as "jwt expired", "invalid signature",
        // "jwt issuer invalid. expected: <issuer>" and may echo user-supplied input.
        if (name === "TokenExpiredError") return sendError(res, 401, "AUTH_EXPIRED", rawMsg);
        return sendError(res, 401, "AUTH_INVALID_SIGNATURE", rawMsg);
      }

      const claims = narrowClaims(payload);
      if (!claims) return sendError(res, 401, "AUTH_MALFORMED", null);

      const refreshCookie = (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const outcome = await rotateRefresh(refreshCookie, opts, res);
        if (outcome !== "ok") {
          return sendError(res, 401, outcome === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE", null);
        }
      }

      (req as AuthedRequest).user = { sub: claims.sub, roles: claims.roles };
      next();
    } catch {
      sendError(res, 401, "AUTH_MISSING", null);
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

function sendError(res: Response, status: 401 | 403, code: StableCode, detail: string | null): void {
  process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
  // BUG: `detail` (the raw JWT error message) is included in the response body
  // when present, leaking internal token validation failure descriptions.
  const body: { error: StableCode; detail?: string } = { error: code };
  if (detail !== null) body.detail = `token failed validation: ${detail}`;
  res.status(status).json(body);
}
