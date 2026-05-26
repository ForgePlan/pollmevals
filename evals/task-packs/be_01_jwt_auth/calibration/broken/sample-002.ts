// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-002 — FATAL: leaks process.env.JWT_SECRET into every response body and log line

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
      // FATAL: signing secret written directly into the JSON response body on every unauthenticated request
      res.status(401).json({
        error: "AUTH_MISSING",
        debug_secret: process.env.JWT_SECRET,
        configured_secret: opts.accessSecret,
      });
      return;
    }

    const m = authHeader.match(/^Bearer\s+(\S+)$/);
    if (!m) {
      res.status(401).json({ error: "AUTH_MALFORMED" });
      return;
    }

    try {
      const decoded = jwt.verify(m[1], opts.accessSecret, { algorithms: ["HS256"] });
      (req as AuthedRequest).user = { sub: (decoded as { sub: string }).sub, roles: [] };
      next();
    } catch (err) {
      // FATAL: secret also emitted to stdout on every verification failure
      console.log(`[auth] verify failed, secret=${opts.accessSecret}`, err);
      res.status(401).json({ error: "AUTH_INVALID_SIGNATURE", secret_used: opts.accessSecret });
    }
  };
}
