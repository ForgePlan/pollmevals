// source: own-authored 2026-05-26 by gogocat (license: MIT)
// good/sample-002 — CSRF token comparison uses === instead of timingSafeEqual (timing-attack surface)

import { randomBytes } from "node:crypto";
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

export type AuthErrorCode =
  | "AUTH_MISSING"
  | "AUTH_MALFORMED"
  | "AUTH_EXPIRED"
  | "AUTH_INVALID_SIGNATURE"
  | "AUTH_INVALID_ISSUER"
  | "AUTH_REFRESH_REVOKED"
  | "CSRF_MISMATCH";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseBearer(header: string | undefined): string | null {
  if (!header) return null;
  const m = header.match(/^Bearer\s+(\S+)$/);
  return m ? m[1] : null;
}

function isMutating(method: string): boolean {
  return method !== "GET" && method !== "HEAD" && method !== "OPTIONS";
}

// FLAW: naive string equality — susceptible to timing side-channel.
// Should use timingSafeEqual from node:crypto instead.
function csrfMatches(req: Request): boolean {
  const headerVal = req.get("x-csrf-token") ?? "";
  const cookieVal =
    (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
  return headerVal.length > 0 && headerVal === cookieVal;
}

interface AccessClaims {
  sub: string;
  roles: readonly string[];
}

function toAccessClaims(payload: string | JwtPayload): AccessClaims | null {
  if (typeof payload === "string" || payload === null) return null;
  const sub = payload.sub;
  const roles = (payload as { roles?: unknown }).roles;
  if (typeof sub !== "string") return null;
  if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string"))
    return null;
  return { sub, roles: roles as readonly string[] };
}

interface RefreshClaims {
  sub: string;
  jti: string;
}

function toRefreshClaims(payload: string | JwtPayload): RefreshClaims | null {
  if (typeof payload === "string" || payload === null) return null;
  const { sub, jti } = payload;
  if (typeof sub !== "string" || typeof jti !== "string") return null;
  return { sub, jti };
}

function classifyJwtErr(err: unknown): AuthErrorCode {
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
  const verifyOpts: VerifyOptions = { issuer: opts.issuer, algorithms: ["HS256"] };

  return async function authHandler(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    try {
      // CSRF guard — uses plain === comparison (the flaw)
      if (isMutating(req.method) && !csrfMatches(req)) {
        return deny(res, 403, "CSRF_MISMATCH");
      }

      const token = parseBearer(req.get("authorization"));
      if (token === null) return deny(res, 401, "AUTH_MISSING");

      let claims: AccessClaims | null = null;
      try {
        const raw = jwt.verify(token, opts.accessSecret, verifyOpts);
        claims = toAccessClaims(raw);
        if (claims === null) return deny(res, 401, "AUTH_MALFORMED");
      } catch (err) {
        return deny(res, 401, classifyJwtErr(err));
      }

      const refreshCookie =
        (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const outcome = await performRotation(refreshCookie, opts, res);
        if (outcome === "revoked") return deny(res, 401, "AUTH_REFRESH_REVOKED");
        if (outcome === "invalid") return deny(res, 401, "AUTH_INVALID_SIGNATURE");
      }

      (req as AuthedRequest).user = { sub: claims.sub, roles: claims.roles };
      next();
    } catch (err) {
      audit("AUTH_INVALID_SIGNATURE", err);
      res.status(500).json({ error: "AUTH_INVALID_SIGNATURE" });
    }
  };
}

// ---------------------------------------------------------------------------
// Refresh rotation
// ---------------------------------------------------------------------------

async function performRotation(
  cookieValue: string,
  opts: AuthMiddlewareOptions,
  res: Response,
): Promise<"ok" | "revoked" | "invalid"> {
  let claims: RefreshClaims | null = null;
  try {
    const raw = jwt.verify(cookieValue, opts.refreshSecret, { issuer: opts.issuer });
    claims = toRefreshClaims(raw);
  } catch {
    return "invalid";
  }
  if (claims === null) return "invalid";

  const isValid = await opts.refreshStore.isActive(claims.sub, claims.jti);
  if (!isValid) return "revoked";

  const nextJti = randomBytes(16).toString("base64url");
  await opts.refreshStore.rotate(claims.sub, claims.jti, nextJti);

  const newToken = jwt.sign(
    { sub: claims.sub, jti: nextJti },
    opts.refreshSecret,
    { issuer: opts.issuer, expiresIn: "7d" },
  );

  res.cookie("refresh_token", newToken, {
    httpOnly: true,
    secure: true,
    sameSite: "strict",
    path: "/",
  });
  return "ok";
}

// ---------------------------------------------------------------------------
// Logging + response helpers
// ---------------------------------------------------------------------------

function audit(code: AuthErrorCode, err: unknown): void {
  const name =
    typeof err === "object" &&
    err !== null &&
    "name" in err &&
    typeof (err as { name: unknown }).name === "string"
      ? (err as { name: string }).name
      : null;
  process.stderr.write(
    JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code, err_name: name }) + "\n",
  );
}

function deny(res: Response, status: 401 | 403, code: AuthErrorCode): void {
  audit(code, null);
  res.status(status).json({ error: code });
}
