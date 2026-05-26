// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-003 — FATAL: accepts algorithms:['none'] — any unsigned token passes verification

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
  // FATAL: algorithms list includes 'none' — an attacker can craft a token with
  // alg="none" and an empty signature; jwt.verify will accept it as valid.
  const verifyOptions = {
    issuer: opts.issuer,
    algorithms: ["HS256", "HS384", "HS512", "RS256", "none"] as jwt.Algorithm[],
  };

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
      const decoded = jwt.verify(m[1], opts.accessSecret, verifyOptions);
      (req as AuthedRequest).user = { sub: (decoded as { sub: string }).sub, roles: [] };
      next();
    } catch {
      res.status(401).json({ error: "AUTH_INVALID_SIGNATURE" });
    }
  };
}
