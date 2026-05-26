// source: own-authored 2026-05-26 by gogocat (license: MIT)
// good/sample-001 — generic AUTH_FAILED for both expired and invalid-signature (loses distinction)

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response, NextFunction } from "express";
import jwt, { type JwtPayload, type VerifyOptions } from "jsonwebtoken";

// ---------------------------------------------------------------------------
// Public surface
// ---------------------------------------------------------------------------

export interface AuthedRequest extends Request {
  user: { sub: string; roles: readonly string[] };
}

export interface RefreshStore {
  isActive(sub: string, jti: string): Promise<boolean>;
  rotate(sub: string, oldJti: string, newJti: string): Promise<void>;
}

export interface AuthMiddlewareOptions {
  accessSecret: string;
  refreshSecret: string;
  issuer: string;
  refreshStore: RefreshStore;
}

// FLAW: only two stable codes — missing AUTH_EXPIRED and AUTH_INVALID_SIGNATURE.
// Both expired and bad-signature tokens get AUTH_FAILED.
type AuthErrorCode =
  | "AUTH_MISSING"
  | "AUTH_MALFORMED"
  | "AUTH_FAILED"           // <-- conflates expired + invalid-signature
  | "AUTH_INVALID_ISSUER"
  | "AUTH_REFRESH_REVOKED"
  | "CSRF_MISMATCH";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractBearer(header: string | undefined): string | null {
  if (!header) return null;
  const m = header.match(/^Bearer\s+(\S+)$/);
  return m ? m[1] : null;
}

function isStateChanging(method: string): boolean {
  return method !== "GET" && method !== "HEAD" && method !== "OPTIONS";
}

function narrowPayload(raw: string | JwtPayload): { sub: string; roles: string[] } | null {
  if (typeof raw === "string" || raw === null) return null;
  const sub = raw.sub;
  const roles = (raw as { roles?: unknown }).roles;
  if (typeof sub !== "string") return null;
  if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) return null;
  return { sub, roles };
}

function narrowRefreshPayload(raw: string | JwtPayload): { sub: string; jti: string } | null {
  if (typeof raw === "string" || raw === null) return null;
  const { sub, jti } = raw;
  if (typeof sub !== "string" || typeof jti !== "string") return null;
  return { sub, jti };
}

function csrfOk(req: Request): boolean {
  const header = req.get("x-csrf-token") ?? "";
  const cookie =
    (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
  if (header.length === 0 || cookie.length === 0 || header.length !== cookie.length)
    return false;
  return timingSafeEqual(Buffer.from(header), Buffer.from(cookie));
}

// ---------------------------------------------------------------------------
// Error classification — FLAW: collapses TokenExpiredError into AUTH_FAILED
// ---------------------------------------------------------------------------

function classifyError(err: unknown): AuthErrorCode {
  if (typeof err === "object" && err !== null && "name" in err) {
    const name = (err as { name: unknown }).name;
    if (name === "JsonWebTokenError") {
      const msg = (err as { message?: unknown }).message;
      if (typeof msg === "string" && msg.startsWith("jwt issuer invalid")) {
        return "AUTH_INVALID_ISSUER";
      }
    }
  }
  // Both "TokenExpiredError" and everything else collapse to "AUTH_FAILED"
  return "AUTH_FAILED";
}

// ---------------------------------------------------------------------------
// Middleware factory
// ---------------------------------------------------------------------------

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  const verifyOpts: VerifyOptions = { issuer: opts.issuer, algorithms: ["HS256"] };

  return async function handler(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    try {
      if (isStateChanging(req.method) && !csrfOk(req)) {
        return sendError(res, 403, "CSRF_MISMATCH");
      }

      const token = extractBearer(req.get("authorization"));
      if (token === null) return sendError(res, 401, "AUTH_MISSING");

      let payload: ReturnType<typeof narrowPayload> = null;
      try {
        const decoded = jwt.verify(token, opts.accessSecret, verifyOpts);
        payload = narrowPayload(decoded);
        if (payload === null) return sendError(res, 401, "AUTH_MALFORMED");
      } catch (err) {
        return sendError(res, 401, classifyError(err));
      }

      const refreshCookie =
        (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const result = await handleRefresh(refreshCookie, opts, res);
        if (result !== "ok") {
          const code: AuthErrorCode =
            result === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_FAILED";
          return sendError(res, 401, code);
        }
      }

      (req as AuthedRequest).user = {
        sub: payload.sub,
        roles: payload.roles,
      };
      next();
    } catch (err) {
      logEvent("AUTH_FAILED", err);
      res.status(500).json({ error: "AUTH_FAILED" });
    }
  };
}

// ---------------------------------------------------------------------------
// Refresh rotation
// ---------------------------------------------------------------------------

async function handleRefresh(
  cookie: string,
  opts: AuthMiddlewareOptions,
  res: Response,
): Promise<"ok" | "revoked" | "invalid"> {
  let claims: { sub: string; jti: string } | null = null;
  try {
    const decoded = jwt.verify(cookie, opts.refreshSecret, {
      issuer: opts.issuer,
    });
    claims = narrowRefreshPayload(decoded);
  } catch {
    return "invalid";
  }
  if (claims === null) return "invalid";

  const active = await opts.refreshStore.isActive(claims.sub, claims.jti);
  if (!active) return "revoked";

  const newJti = randomBytes(16).toString("base64url");
  await opts.refreshStore.rotate(claims.sub, claims.jti, newJti);

  const freshToken = jwt.sign(
    { sub: claims.sub, jti: newJti },
    opts.refreshSecret,
    { issuer: opts.issuer, expiresIn: "7d" },
  );
  res.cookie("refresh_token", freshToken, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/",
  });
  return "ok";
}

// ---------------------------------------------------------------------------
// Logging + response
// ---------------------------------------------------------------------------

function logEvent(code: AuthErrorCode, err: unknown): void {
  const errName =
    err !== null &&
    typeof err === "object" &&
    "name" in err &&
    typeof (err as { name: unknown }).name === "string"
      ? (err as { name: string }).name
      : null;
  process.stderr.write(
    JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code, err_name: errName }) +
      "\n",
  );
}

function sendError(res: Response, status: 401 | 403 | 500, code: AuthErrorCode): void {
  logEvent(code, null);
  res.status(status).json({ error: code });
}
