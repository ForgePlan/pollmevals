// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-001 — validates signature but ignores expiry (ignoreExpiration: true)

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
  return async function handler(req: Request, res: Response, next: NextFunction): Promise<void> {
    const authHeader = req.get("authorization");
    const m = (authHeader ?? "").match(/^Bearer\s+(\S+)$/);
    if (!m) {
      res.status(401).json({ error: "AUTH_MISSING" });
      return;
    }
    const token = m[1];

    let payload: JwtPayload;
    try {
      // FLAW: ignoreExpiration skips the exp claim check entirely.
      // Expired tokens are accepted as valid — replay attacks succeed indefinitely.
      const decoded = jwt.verify(token, opts.accessSecret, {
        issuer: opts.issuer,
        algorithms: ["HS256"],
        ignoreExpiration: true,
      });
      if (typeof decoded === "string") { res.status(401).json({ error: "AUTH_MALFORMED" }); return; }
      payload = decoded;
    } catch {
      res.status(401).json({ error: "AUTH_INVALID_SIGNATURE" });
      return;
    }

    const { sub, roles } = payload as { sub?: string; roles?: string[] };
    if (typeof sub !== "string" || !Array.isArray(roles)) {
      res.status(401).json({ error: "AUTH_MALFORMED" });
      return;
    }

    const refreshCookie = (req.cookies as Record<string, string> | undefined)?.refresh_token;
    if (typeof refreshCookie === "string" && refreshCookie.length > 0) {
      try {
        const rp = jwt.verify(refreshCookie, opts.refreshSecret, { issuer: opts.issuer, ignoreExpiration: true });
        if (typeof rp !== "string" && rp !== null) {
          const { sub: rsub, jti } = rp as { sub?: string; jti?: string };
          if (typeof rsub === "string" && typeof jti === "string") {
            const active = await opts.refreshStore.isActive(rsub, jti);
            if (active) {
              const newJti = randomBytes(16).toString("base64url");
              await opts.refreshStore.rotate(rsub, jti, newJti);
              const newToken = jwt.sign({ sub: rsub, jti: newJti }, opts.refreshSecret, {
                issuer: opts.issuer, expiresIn: "7d",
              });
              res.cookie("refresh_token", newToken, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
            }
          }
        }
      } catch { /* ignore refresh errors */ }
    }

    (req as AuthedRequest).user = { sub, roles: roles as readonly string[] };
    next();
  };
}
