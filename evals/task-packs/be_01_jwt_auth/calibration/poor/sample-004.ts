// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-004 — outer try/catch swallows all errors and calls next() (auth failures pass as success)

import type { Request, RequestHandler, Response, NextFunction } from "express";
import jwt, { type JwtPayload } from "jsonwebtoken";
import { randomBytes } from "node:crypto";

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

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  // FLAW: the entire handler body is wrapped in try/catch that calls next() on
  // ANY error. A malformed token, an expired token, a missing header — all result
  // in the request being passed through as if authentication succeeded.
  // The user object may be partially populated or absent entirely on req.
  return async function handler(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
      const csrfHeader = req.get("x-csrf-token") ?? "";
      const csrfCookie = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
      if (req.method !== "GET" && req.method !== "HEAD" && req.method !== "OPTIONS") {
        if (csrfHeader !== csrfCookie || csrfHeader.length === 0) {
          res.status(403).json({ error: "CSRF_MISMATCH" });
          return;
        }
      }

      const authHeader = req.get("authorization");
      const m = (authHeader ?? "").match(/^Bearer\s+(\S+)$/);
      if (!m) throw new Error("missing bearer");
      const token = m[1];

      const decoded = jwt.verify(token, opts.accessSecret, {
        issuer: opts.issuer,
        algorithms: ["HS256"],
      }) as JwtPayload;

      const sub = decoded.sub;
      const roles = (decoded as { roles?: string[] }).roles ?? [];
      if (typeof sub !== "string") throw new Error("no sub");

      const refreshCookie = (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
        const rp = jwt.verify(refreshCookie, opts.refreshSecret, { issuer: opts.issuer }) as JwtPayload;
        const rsub = rp.sub;
        const jti = (rp as { jti?: string }).jti;
        if (typeof rsub === "string" && typeof jti === "string") {
          const active = await opts.refreshStore.isActive(rsub, jti);
          if (active) {
            const newJti = randomBytes(16).toString("base64url");
            await opts.refreshStore.rotate(rsub, jti, newJti);
            const nt = jwt.sign({ sub: rsub, jti: newJti }, opts.refreshSecret, {
              issuer: opts.issuer, expiresIn: "7d",
            });
            res.cookie("refresh_token", nt, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
          }
        }
      }

      (req as AuthedRequest).user = { sub, roles: roles as readonly string[] };
      next();
    } catch {
      // FLAW: silently swallowing every error and calling next() means that
      // requests with invalid, expired, or missing tokens proceed to the
      // protected route handler as if they were authenticated.
      // req.user will be undefined, and the downstream handler is responsible
      // for discovering this — but middleware has already "approved" the request.
      next();
    }
  };
}
