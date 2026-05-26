// source: own-authored 2026-05-26 by gogocat (license: MIT)
// good/sample-003 — cookie set HttpOnly + SameSite=Strict but MISSING Secure flag

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response, NextFunction } from "express";
import jwt, { type JwtPayload } from "jsonwebtoken";

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
// Token parsing
// ---------------------------------------------------------------------------

function extractBearerToken(authHeader: string | undefined): string | null {
  if (!authHeader) return null;
  const match = authHeader.match(/^Bearer\s+(\S+)$/);
  return match ? match[1] : null;
}

function isWriteMethod(method: string): boolean {
  return method !== "GET" && method !== "HEAD" && method !== "OPTIONS";
}

function verifyCsrf(req: Request): boolean {
  const fromHeader = req.get("x-csrf-token") ?? "";
  const fromCookie =
    (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
  if (fromHeader.length === 0 || fromCookie.length === 0) return false;
  if (fromHeader.length !== fromCookie.length) return false;
  return timingSafeEqual(Buffer.from(fromHeader), Buffer.from(fromCookie));
}

function narrowAccess(raw: string | JwtPayload): { sub: string; roles: readonly string[] } | null {
  if (typeof raw === "string" || raw === null) return null;
  const { sub } = raw;
  const roles = (raw as { roles?: unknown }).roles;
  if (typeof sub !== "string") return null;
  if (!Array.isArray(roles) || !roles.every((x): x is string => typeof x === "string"))
    return null;
  return { sub, roles: roles as readonly string[] };
}

function narrowRefresh(raw: string | JwtPayload): { sub: string; jti: string } | null {
  if (typeof raw === "string" || raw === null) return null;
  const { sub, jti } = raw;
  if (typeof sub !== "string" || typeof jti !== "string") return null;
  return { sub, jti };
}

function mapJwtError(err: unknown): AuthErrorCode {
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
  return async function authHandler(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    try {
      if (isWriteMethod(req.method) && !verifyCsrf(req)) {
        return rejectRequest(res, 403, "CSRF_MISMATCH");
      }

      const rawToken = extractBearerToken(req.get("authorization"));
      if (rawToken === null) return rejectRequest(res, 401, "AUTH_MISSING");

      let accessClaims: { sub: string; roles: readonly string[] } | null = null;
      try {
        const decoded = jwt.verify(rawToken, opts.accessSecret, {
          issuer: opts.issuer,
          algorithms: ["HS256"],
        });
        accessClaims = narrowAccess(decoded);
        if (accessClaims === null) return rejectRequest(res, 401, "AUTH_MALFORMED");
      } catch (err) {
        return rejectRequest(res, 401, mapJwtError(err));
      }

      const refreshToken =
        (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshToken === "string" && refreshToken.length > 0) {
        const rotationResult = await rotateRefreshToken(refreshToken, opts, res);
        if (rotationResult !== "ok") {
          const code: AuthErrorCode =
            rotationResult === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE";
          return rejectRequest(res, 401, code);
        }
      }

      (req as AuthedRequest).user = {
        sub: accessClaims.sub,
        roles: accessClaims.roles,
      };
      next();
    } catch (err) {
      writeLog("AUTH_INVALID_SIGNATURE", err);
      res.status(500).json({ error: "AUTH_INVALID_SIGNATURE" });
    }
  };
}

// ---------------------------------------------------------------------------
// Refresh rotation — FLAW: cookie is set WITHOUT the Secure flag.
// Transmitted over plain HTTP in non-HTTPS environments.
// ---------------------------------------------------------------------------

async function rotateRefreshToken(
  cookieValue: string,
  opts: AuthMiddlewareOptions,
  res: Response,
): Promise<"ok" | "revoked" | "invalid"> {
  let claims: { sub: string; jti: string } | null = null;
  try {
    const decoded = jwt.verify(cookieValue, opts.refreshSecret, {
      issuer: opts.issuer,
    });
    claims = narrowRefresh(decoded);
  } catch {
    return "invalid";
  }
  if (claims === null) return "invalid";

  const stillActive = await opts.refreshStore.isActive(claims.sub, claims.jti);
  if (!stillActive) return "revoked";

  const freshJti = randomBytes(16).toString("base64url");
  await opts.refreshStore.rotate(claims.sub, claims.jti, freshJti);

  const newRefreshJwt = jwt.sign(
    { sub: claims.sub, jti: freshJti },
    opts.refreshSecret,
    { issuer: opts.issuer, expiresIn: "7d" },
  );

  // FLAW: `secure` attribute is absent — cookie will be sent over HTTP.
  res.cookie("refresh_token", newRefreshJwt, {
    httpOnly: true,
    sameSite: "strict",
    path: "/",
    // secure: true  <-- intentionally omitted for this sample
  });
  return "ok";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function writeLog(code: AuthErrorCode, err: unknown): void {
  const errName =
    typeof err === "object" &&
    err !== null &&
    "name" in err &&
    typeof (err as { name: unknown }).name === "string"
      ? (err as { name: string }).name
      : null;
  process.stderr.write(
    JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code, err_name: errName }) + "\n",
  );
}

function rejectRequest(res: Response, status: 401 | 403 | 500, code: AuthErrorCode): void {
  writeLog(code, null);
  res.status(status).json({ error: code });
}
