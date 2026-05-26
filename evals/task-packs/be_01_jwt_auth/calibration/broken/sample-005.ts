// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-005 — FATAL: infinite recursion — handler calls itself, hangs every request

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

    try {
      const decoded = jwt.verify(m[1], opts.accessSecret, { algorithms: ["HS256"] });
      (req as AuthedRequest).user = { sub: (decoded as { sub: string }).sub, roles: [] };
      // FATAL: re-invokes handler recursively instead of calling next().
      // Every authenticated request causes a stack overflow / infinite loop;
      // the response is never sent and next() is never reached.
      await handler(req, res, next);
    } catch {
      res.status(401).json({ error: "AUTH_INVALID_SIGNATURE" });
    }
  };
}
