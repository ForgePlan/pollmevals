// source: own-authored 2026-05-26 by gogocat (license: MIT)
// mediocre/sample-003 — CSRF check completely missing (no x-csrf-token / cookie comparison ever)

import { randomBytes } from "node:crypto";
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

function getBearer(header: string | undefined): string | null {
  if (!header) return null;
  const m = header.match(/^Bearer\s+(\S+)$/);
  return m ? m[1] : null;
}

function narrowPayload(p: string | JwtPayload): { sub: string; roles: string[] } | null {
  if (typeof p === "string" || !p) return null;
  const sub = (p as { sub?: unknown }).sub;
  const roles = (p as { roles?: unknown }).roles;
  if (typeof sub !== "string") return null;
  if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) return null;
  return { sub, roles };
}

function classifyError(e: unknown): AuthErrorCode {
  if (typeof e !== "object" || e === null) return "AUTH_INVALID_SIGNATURE";
  const name = (e as { name?: string }).name;
  if (name === "TokenExpiredError") return "AUTH_EXPIRED";
  const msg = (e as { message?: string }).message ?? "";
  if (msg.match(/issuer/i)) return "AUTH_INVALID_ISSUER";
  return "AUTH_INVALID_SIGNATURE";
}

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  const vOpts: VerifyOptions = { issuer: opts.issuer, algorithms: ["HS256"] };

  // BUG: CSRF protection is entirely absent. State-changing requests (POST, PUT,
  // DELETE, PATCH) are processed with no x-csrf-token / cookie comparison whatsoever.
  return async function handler(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const token = getBearer(req.get("authorization"));
      if (!token) return abort(res, 401, "AUTH_MISSING");

      let raw: string | JwtPayload;
      try {
        raw = jwt.verify(token, opts.accessSecret, vOpts);
      } catch (e) {
        return abort(res, 401, classifyError(e));
      }

      const claims = narrowPayload(raw);
      if (!claims) return abort(res, 401, "AUTH_MALFORMED");

      const refreshCookie = (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const outcome = await doRotate(refreshCookie, opts, res);
        if (outcome !== "ok") {
          return abort(res, 401, outcome === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE");
        }
      }

      (req as AuthedRequest).user = { sub: claims.sub, roles: claims.roles };
      next();
    } catch {
      abort(res, 401, "AUTH_MISSING");
    }
  };
}

async function doRotate(
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
  const next = jwt.sign({ sub, jti: newJti }, opts.refreshSecret, {
    issuer: opts.issuer,
    expiresIn: "7d",
  });
  res.cookie("refresh_token", next, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
  return "ok";
}

function abort(res: Response, status: 401 | 403, code: AuthErrorCode): void {
  process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
  res.status(status).json({ error: code });
}
