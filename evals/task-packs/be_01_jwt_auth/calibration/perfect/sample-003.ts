// source: own-authored 2026-05-26 by gogocat (license: MIT)
// perfect/sample-003 — factory returning { protect, verifyToken } pair.
// Distinct idiom: factory yields an interface, callers pick what they need.

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response } from "express";
import jwt from "jsonwebtoken";

type ErrCode = "AUTH_MISSING" | "AUTH_MALFORMED" | "AUTH_EXPIRED"
  | "AUTH_INVALID_SIGNATURE" | "AUTH_INVALID_ISSUER" | "AUTH_REFRESH_REVOKED" | "CSRF_MISMATCH";

interface Store {
  isActive(sub: string, jti: string): Promise<boolean>;
  rotate(sub: string, oldJti: string, newJti: string): Promise<void>;
}

interface Auth {
  protect(): RequestHandler;
  verifyToken(t: string): { ok: true; sub: string; roles: readonly string[] } | { ok: false; err: ErrCode };
}

export function makeAuth(accessSecret: string, refreshSecret: string, issuer: string, store: Store): Auth {
  const verifyToken: Auth["verifyToken"] = (t) => {
    try {
      const p = jwt.verify(t, accessSecret, { issuer, algorithms: ["HS256"] });
      if (typeof p === "string" || !p) return { ok: false, err: "AUTH_MALFORMED" };
      const sub = p.sub, roles = (p as { roles?: unknown }).roles;
      if (typeof sub !== "string") return { ok: false, err: "AUTH_MALFORMED" };
      if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) {
        return { ok: false, err: "AUTH_MALFORMED" };
      }
      return { ok: true, sub, roles: roles as readonly string[] };
    } catch (e) {
      const n = (e as { name?: string }).name;
      if (n === "TokenExpiredError") return { ok: false, err: "AUTH_EXPIRED" };
      const m = (e as { message?: string }).message ?? "";
      return { ok: false, err: m.startsWith("jwt issuer invalid") ? "AUTH_INVALID_ISSUER" : "AUTH_INVALID_SIGNATURE" };
    }
  };

  const csrfCheck = (req: Request): boolean => {
    const h = req.get("x-csrf-token") ?? "";
    const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
    if (!h || !c || h.length !== c.length) return false;
    return timingSafeEqual(Buffer.from(h), Buffer.from(c));
  };

  const rotateRefresh = async (cookie: string, res: Response): Promise<"ok" | "revoked" | "invalid"> => {
    try {
      const p = jwt.verify(cookie, refreshSecret, { issuer });
      if (typeof p === "string" || !p) return "invalid";
      const { sub, jti } = p;
      if (typeof sub !== "string" || typeof jti !== "string") return "invalid";
      if (!(await store.isActive(sub, jti))) return "revoked";
      const nj = randomBytes(16).toString("base64url");
      await store.rotate(sub, jti, nj);
      const tok = jwt.sign({ sub, jti: nj }, refreshSecret, { issuer, expiresIn: "7d" });
      res.cookie("refresh_token", tok, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
      return "ok";
    } catch { return "invalid"; }
  };

  const deny = (res: Response, status: 401 | 403, code: ErrCode): void => {
    process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
    res.status(status).json({ error: code });
  };

  const protect = (): RequestHandler => async (req, res, next) => {
    const stateChanging = !["GET", "HEAD", "OPTIONS"].includes(req.method);
    if (stateChanging && !csrfCheck(req)) return deny(res, 403, "CSRF_MISMATCH");
    const auth = req.get("authorization");
    const m = auth ? auth.match(/^Bearer\s+(\S+)$/) : null;
    if (!m) return deny(res, 401, "AUTH_MISSING");
    const r = verifyToken(m[1]);
    if (!r.ok) return deny(res, 401, r.err);
    const refresh = (req.cookies as Record<string, string> | undefined)?.refresh_token;
    if (refresh) {
      const rr = await rotateRefresh(refresh, res);
      if (rr !== "ok") return deny(res, 401, rr === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE");
    }
    (req as Request & { user: unknown }).user = { sub: r.sub, roles: r.roles };
    next();
  };

  return { protect, verifyToken };
}

export const authMiddleware = (a: string, r: string, iss: string, s: Store): RequestHandler =>
  makeAuth(a, r, iss, s).protect();
