// source: own-authored 2026-05-26 by gogocat (license: MIT)
// good/sample-005 — error response body leaks raw jsonwebtoken message alongside the stable code

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
// Error classification result — carries both stable code and raw message
// (raw message will be erroneously included in the wire response)
// ---------------------------------------------------------------------------

interface ClassifiedError {
  code: AuthErrorCode;
  rawMessage: string;  // FLAW: this reaches the HTTP response body
}

function classifyJwtError(err: unknown): ClassifiedError {
  if (typeof err !== "object" || err === null) {
    return { code: "AUTH_INVALID_SIGNATURE", rawMessage: "unknown error" };
  }
  const name = (err as { name?: unknown }).name;
  const rawMsg =
    typeof (err as { message?: unknown }).message === "string"
      ? (err as { message: string }).message
      : "unknown error";

  if (name === "TokenExpiredError") {
    return { code: "AUTH_EXPIRED", rawMessage: rawMsg };
  }
  if (name === "JsonWebTokenError") {
    if (rawMsg.startsWith("jwt issuer invalid")) {
      return { code: "AUTH_INVALID_ISSUER", rawMessage: rawMsg };
    }
    return { code: "AUTH_INVALID_SIGNATURE", rawMessage: rawMsg };
  }
  return { code: "AUTH_INVALID_SIGNATURE", rawMessage: rawMsg };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function extractBearer(header: string | undefined): string | null {
  if (!header) return null;
  const m = header.match(/^Bearer\s+(\S+)$/);
  return m ? m[1] : null;
}

function requiresCsrf(method: string): boolean {
  return method !== "GET" && method !== "HEAD" && method !== "OPTIONS";
}

function checkCsrf(req: Request): boolean {
  const h = req.get("x-csrf-token") ?? "";
  const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
  if (h.length === 0 || c.length === 0 || h.length !== c.length) return false;
  return timingSafeEqual(Buffer.from(h), Buffer.from(c));
}

function narrowAccess(raw: string | JwtPayload): { sub: string; roles: readonly string[] } | null {
  if (typeof raw === "string" || raw === null) return null;
  const sub = raw.sub;
  const roles = (raw as { roles?: unknown }).roles;
  if (typeof sub !== "string") return null;
  if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string"))
    return null;
  return { sub, roles: roles as readonly string[] };
}

function narrowRefresh(raw: string | JwtPayload): { sub: string; jti: string } | null {
  if (typeof raw === "string" || raw === null) return null;
  const { sub, jti } = raw;
  if (typeof sub !== "string" || typeof jti !== "string") return null;
  return { sub, jti };
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
      if (requiresCsrf(req.method) && !checkCsrf(req)) {
        return errorResponse(res, 403, "CSRF_MISMATCH", null);
      }

      const bearer = extractBearer(req.get("authorization"));
      if (bearer === null) return errorResponse(res, 401, "AUTH_MISSING", null);

      let userClaims: { sub: string; roles: readonly string[] } | null = null;
      try {
        const decoded = jwt.verify(bearer, opts.accessSecret, verifyOpts);
        userClaims = narrowAccess(decoded);
        if (userClaims === null) return errorResponse(res, 401, "AUTH_MALFORMED", null);
      } catch (err) {
        const classified = classifyJwtError(err);
        // FLAW: raw jsonwebtoken message (e.g. "jwt expired", "invalid signature",
        // "jwt issuer invalid. expected: x") is passed along and included in the
        // HTTP response body via errorResponse.
        return errorResponse(res, 401, classified.code, classified.rawMessage);
      }

      const refreshCookie =
        (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const rotateResult = await doRotate(refreshCookie, opts, res);
        if (rotateResult !== "ok") {
          const code: AuthErrorCode =
            rotateResult === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE";
          return errorResponse(res, 401, code, null);
        }
      }

      (req as AuthedRequest).user = { sub: userClaims.sub, roles: userClaims.roles };
      next();
    } catch (err) {
      recordLog("AUTH_INVALID_SIGNATURE", err);
      res.status(500).json({ error: "AUTH_INVALID_SIGNATURE" });
    }
  };
}

// ---------------------------------------------------------------------------
// Refresh rotation
// ---------------------------------------------------------------------------

async function doRotate(
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

  const active = await opts.refreshStore.isActive(claims.sub, claims.jti);
  if (!active) return "revoked";

  const nextJti = randomBytes(16).toString("base64url");
  await opts.refreshStore.rotate(claims.sub, claims.jti, nextJti);

  const freshToken = jwt.sign(
    { sub: claims.sub, jti: nextJti },
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

function recordLog(code: AuthErrorCode, err: unknown): void {
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

// FLAW: when rawDetail is non-null (e.g. "jwt expired", "invalid signature"),
// it is forwarded in the JSON response body — leaking library-internal message text.
function errorResponse(
  res: Response,
  status: 401 | 403 | 500,
  code: AuthErrorCode,
  rawDetail: string | null,
): void {
  recordLog(code, null);
  if (rawDetail !== null) {
    res.status(status).json({ error: code, detail: rawDetail });
  } else {
    res.status(status).json({ error: code });
  }
}
