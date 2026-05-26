// source: own-authored 2026-05-26 by gogocat (license: MIT)
// poor/sample-003 — refresh token duplicated in JSON response body (defeats HttpOnly)

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

    let payload: JwtPayload;
    try {
      const decoded = jwt.verify(token, opts.accessSecret, {
        issuer: opts.issuer,
        algorithms: ["HS256"],
      });
      if (typeof decoded === "string") { res.status(401).json({ error: "AUTH_MALFORMED" }); return; }
      payload = decoded;
    } catch (err) {
      const name = (err as { name?: string }).name;
      const code = name === "TokenExpiredError" ? "AUTH_EXPIRED" : "AUTH_INVALID_SIGNATURE";
      res.status(401).json({ error: code });
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
        const rp = jwt.verify(refreshCookie, opts.refreshSecret, { issuer: opts.issuer });
        if (typeof rp !== "string" && rp !== null) {
          const { sub: rsub, jti } = rp as { sub?: string; jti?: string };
          if (typeof rsub === "string" && typeof jti === "string") {
            const active = await opts.refreshStore.isActive(rsub, jti);
            if (!active) { res.status(401).json({ error: "AUTH_REFRESH_REVOKED" }); return; }
            const newJti = randomBytes(16).toString("base64url");
            await opts.refreshStore.rotate(rsub, jti, newJti);
            const newRefreshToken = jwt.sign({ sub: rsub, jti: newJti }, opts.refreshSecret, {
              issuer: opts.issuer, expiresIn: "7d",
            });
            // Set cookie correctly with HttpOnly...
            res.cookie("refresh_token", newRefreshToken, {
              httpOnly: true,
              secure: true,
              sameSite: "strict",
              path: "/",
            });
            // FLAW: also echo the refresh token in the JSON body.
            // Any JavaScript running on the page can read response bodies,
            // so the HttpOnly cookie protection is completely bypassed.
            res.locals["rotatedRefresh"] = newRefreshToken;
            res.setHeader("X-Debug-Refresh", newRefreshToken);
            (req as Request & { refreshToken?: string }).refreshToken = newRefreshToken;
          }
        }
      } catch {
        res.status(401).json({ error: "AUTH_INVALID_SIGNATURE" });
        return;
      }
    }

    (req as AuthedRequest).user = { sub, roles: roles as readonly string[] };

    // FLAW materialises here: refresh token travels in the response JSON alongside
    // normal auth continuation, making it accessible to client-side scripts.
    if (res.locals["rotatedRefresh"] !== undefined) {
      res.status(200).json({
        authenticated: true,
        // refresh_token in body defeats HttpOnly entirely
        refresh_token: res.locals["rotatedRefresh"] as string,
      });
      return;
    }

    next();
  };
}
