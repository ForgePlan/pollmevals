// source: own-authored 2026-05-26 by gogocat (license: MIT)
// good/sample-004 — refresh token verified + new token issued but old jti NOT invalidated server-side (no rotation)

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
  | "AUTH_INVALID_ISSUER"
  | "AUTH_REFRESH_REVOKED"
  | "CSRF_MISMATCH";

// ---------------------------------------------------------------------------
// Validation helpers (pipeline-style)
// ---------------------------------------------------------------------------

const isSafeMethod = (method: string): boolean =>
  method === "GET" || method === "HEAD" || method === "OPTIONS";

function getBearer(authHeader: string | undefined): string | null {
  if (!authHeader) return null;
  const found = authHeader.match(/^Bearer\s+(\S+)$/);
  return found ? found[1] : null;
}

function safeCsrfCheck(req: Request): boolean {
  const h = req.get("x-csrf-token") ?? "";
  const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
  if (h.length === 0 || c.length === 0 || h.length !== c.length) return false;
  return timingSafeEqual(Buffer.from(h), Buffer.from(c));
}

interface TokenClaims {
  sub: string;
  roles: readonly string[];
}

function parseAccessClaims(raw: string | JwtPayload): TokenClaims | null {
  if (typeof raw === "string" || raw === null) return null;
  const sub = raw.sub;
  const roles = (raw as { roles?: unknown }).roles;
  if (typeof sub !== "string") return null;
  if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string"))
    return null;
  return { sub, roles: roles as readonly string[] };
}

interface RefTokenClaims {
  sub: string;
  jti: string;
}

function parseRefreshClaims(raw: string | JwtPayload): RefTokenClaims | null {
  if (typeof raw === "string" || raw === null) return null;
  const { sub, jti } = raw;
  if (typeof sub !== "string" || typeof jti !== "string") return null;
  return { sub, jti };
}

function jwtErrCode(err: unknown): AuthErrorCode {
  if (typeof err !== "object" || err === null) return "AUTH_INVALID_SIGNATURE";
  const name = (err as { name?: unknown }).name;
  if (name === "TokenExpiredError") return "AUTH_EXPIRED";
  if (name === "JsonWebTokenError") {
    const msg = (err as { message?: unknown }).message;
    if (typeof msg === "string" && msg.startsWith("jwt issuer invalid"))
      return "AUTH_INVALID_ISSUER";
    return "AUTH_INVALID_SIGNATURE";
  }
  return "AUTH_INVALID_SIGNATURE";
}

// ---------------------------------------------------------------------------
// Middleware factory
// ---------------------------------------------------------------------------

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  const accessVerifyOpts: VerifyOptions = {
    issuer: opts.issuer,
    algorithms: ["HS256"],
  };

  return async function handler(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    try {
      if (!isSafeMethod(req.method) && !safeCsrfCheck(req)) {
        return respondError(res, 403, "CSRF_MISMATCH");
      }

      const bearer = getBearer(req.get("authorization"));
      if (bearer === null) return respondError(res, 401, "AUTH_MISSING");

      let claims: TokenClaims | null = null;
      try {
        const decoded = jwt.verify(bearer, opts.accessSecret, accessVerifyOpts);
        claims = parseAccessClaims(decoded);
        if (claims === null) return respondError(res, 401, "AUTH_MALFORMED");
      } catch (err) {
        return respondError(res, 401, jwtErrCode(err));
      }

      const refreshCookie =
        (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const result = await issueNewRefresh(refreshCookie, opts, res);
        if (result !== "ok") {
          const code: AuthErrorCode =
            result === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE";
          return respondError(res, 401, code);
        }
      }

      (req as AuthedRequest).user = { sub: claims.sub, roles: claims.roles };
      next();
    } catch (err) {
      emitLog("AUTH_INVALID_SIGNATURE", err);
      res.status(500).json({ error: "AUTH_INVALID_SIGNATURE" });
    }
  };
}

// ---------------------------------------------------------------------------
// Refresh handling — FLAW: issues a new refresh token but never calls
// refreshStore.rotate() — old jti remains active in the store, so the
// previous refresh token is still valid (no server-side invalidation).
// ---------------------------------------------------------------------------

async function issueNewRefresh(
  cookieValue: string,
  opts: AuthMiddlewareOptions,
  res: Response,
): Promise<"ok" | "revoked" | "invalid"> {
  let claims: RefTokenClaims | null = null;
  try {
    const decoded = jwt.verify(cookieValue, opts.refreshSecret, {
      issuer: opts.issuer,
    });
    claims = parseRefreshClaims(decoded);
  } catch {
    return "invalid";
  }
  if (claims === null) return "invalid";

  const active = await opts.refreshStore.isActive(claims.sub, claims.jti);
  if (!active) return "revoked";

  // FLAW: new jti generated and signed, but rotate() is never called.
  // The old jti stays active in the store — a stolen token remains valid.
  const newJti = randomBytes(16).toString("base64url");
  const refreshJwt = jwt.sign(
    { sub: claims.sub, jti: newJti },
    opts.refreshSecret,
    { issuer: opts.issuer, expiresIn: "7d" },
  );

  res.cookie("refresh_token", refreshJwt, {
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

function emitLog(code: AuthErrorCode, err: unknown): void {
  const errName =
    typeof err === "object" &&
    err !== null &&
    "name" in err &&
    typeof (err as { name: unknown }).name === "string"
      ? (err as { name: string }).name
      : null;
  process.stderr.write(
    JSON.stringify({
      ts: new Date().toISOString(),
      kind: "auth",
      code,
      err_name: errName,
    }) + "\n",
  );
}

function respondError(res: Response, status: 401 | 403 | 500, code: AuthErrorCode): void {
  emitLog(code, null);
  res.status(status).json({ error: code });
}
