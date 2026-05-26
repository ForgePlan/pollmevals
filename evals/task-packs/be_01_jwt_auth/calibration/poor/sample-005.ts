// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-005 — no signature verification: jwt.decode() used instead of jwt.verify()

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

function isStateChanging(method: string): boolean {
  return method !== "GET" && method !== "HEAD" && method !== "OPTIONS";
}

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  return async function handler(req: Request, res: Response, next: NextFunction): Promise<void> {
    if (isStateChanging(req.method)) {
      const csrfHeader = req.get("x-csrf-token") ?? "";
      const csrfCookie = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
      if (csrfHeader !== csrfCookie || csrfHeader.length === 0) {
        res.status(403).json({ error: "CSRF_MISMATCH" });
        return;
      }
    }

    const authHeader = req.get("authorization");
    const m = (authHeader ?? "").match(/^Bearer\s+(\S+)$/);
    if (!m) {
      res.status(401).json({ error: "AUTH_MISSING" });
      return;
    }
    const token = m[1];

    // FLAW: jwt.decode() performs NO signature verification and NO expiry check.
    // An attacker can craft any payload with an arbitrary sub, roles, and iss,
    // encode it as a JWT with a random or empty signature, and gain full access.
    // The signing secret opts.accessSecret is never consulted.
    const decoded = jwt.decode(token) as JwtPayload | null;
    if (decoded === null || typeof decoded === "string") {
      res.status(401).json({ error: "AUTH_MALFORMED" });
      return;
    }

    // Issuer "check" using string equality on the decoded (unverified) claim.
    if (decoded.iss !== opts.issuer) {
      res.status(401).json({ error: "AUTH_INVALID_ISSUER" });
      return;
    }

    const { sub, exp } = decoded;
    const roles = (decoded as { roles?: string[] }).roles ?? [];
    if (typeof sub !== "string") {
      res.status(401).json({ error: "AUTH_MALFORMED" });
      return;
    }

    // Manual expiry "check" on the unverified claim — the attacker simply omits exp.
    if (typeof exp === "number" && exp < Math.floor(Date.now() / 1000)) {
      res.status(401).json({ error: "AUTH_EXPIRED" });
      return;
    }

    const refreshCookie = (req.cookies as Record<string, string> | undefined)?.refresh_token;
    if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
      // Same flaw applied to refresh token — decoded without verification.
      const rp = jwt.decode(refreshCookie) as JwtPayload | null;
      if (rp !== null && typeof rp !== "string") {
        const rsub = rp.sub;
        const jti = (rp as { jti?: string }).jti;
        if (typeof rsub === "string" && typeof jti === "string") {
          const active = await opts.refreshStore.isActive(rsub, jti);
          if (active) {
            const newJti = randomBytes(16).toString("base64url");
            await opts.refreshStore.rotate(rsub, jti, newJti);
            const newToken = jwt.sign({ sub: rsub, jti: newJti }, opts.refreshSecret, {
              issuer: opts.issuer, expiresIn: "7d",
            });
            res.cookie("refresh_token", newToken, {
              httpOnly: true, secure: true, sameSite: "strict", path: "/",
            });
          }
        }
      }
    }

    (req as AuthedRequest).user = { sub, roles: roles as readonly string[] };
    next();
  };
}
