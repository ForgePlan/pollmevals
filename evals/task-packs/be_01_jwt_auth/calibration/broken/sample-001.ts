// source: own-authored 2026-05-26 by gogocat (license: MIT)
// broken/sample-001 — FATAL: syntax error (missing closing brace on handler body — tsc rejects)

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
      next();
    } catch {
      res.status(401).json({ error: "AUTH_INVALID_SIGNATURE" });
    }
  // INTENTIONAL: closing brace for authMiddleware function body is missing — tsc cannot parse this file
