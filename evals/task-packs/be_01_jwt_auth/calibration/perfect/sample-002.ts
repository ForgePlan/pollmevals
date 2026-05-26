// source: own-authored 2026-05-26 by gogocat (license: MIT)
// perfect/sample-002 — class-based AuthService with DI via constructor.
// Distinct idiom: object-oriented, services and methods.

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response } from "express";
import jwt, { type JwtPayload } from "jsonwebtoken";

interface IStore {
  isActive(sub: string, jti: string): Promise<boolean>;
  rotate(sub: string, oldJti: string, newJti: string): Promise<void>;
}

export class AuthService {
  constructor(
    private readonly accessSecret: string,
    private readonly refreshSecret: string,
    private readonly issuer: string,
    private readonly store: IStore,
  ) {}

  middleware(): RequestHandler {
    return async (req, res, next) => {
      if (this.unsafe(req.method) && !this.csrf(req)) return this.deny(res, 403, "CSRF_MISMATCH");
      const tok = this.bearer(req.get("authorization"));
      if (!tok) return this.deny(res, 401, "AUTH_MISSING");
      const claims = this.verify(tok);
      if ("err" in claims) return this.deny(res, 401, claims.err);
      const refresh = (req.cookies as Record<string, string> | undefined)?.refresh_token;
      if (refresh) {
        const r = await this.rotateRefresh(refresh, res);
        if (r !== "ok") return this.deny(res, 401, r === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE");
      }
      (req as Request & { user: { sub: string; roles: readonly string[] } }).user = {
        sub: claims.sub, roles: claims.roles,
      };
      next();
    };
  }

  private unsafe = (m: string): boolean => !["GET", "HEAD", "OPTIONS"].includes(m);

  private csrf(req: Request): boolean {
    const h = req.get("x-csrf-token") ?? "";
    const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
    if (!h || !c || h.length !== c.length) return false;
    return timingSafeEqual(Buffer.from(h), Buffer.from(c));
  }

  private bearer(h: string | undefined): string | null {
    const m = h ? h.match(/^Bearer\s+(\S+)$/) : null;
    return m ? m[1] : null;
  }

  private verify(token: string):
    | { sub: string; roles: readonly string[] }
    | { err: "AUTH_EXPIRED" | "AUTH_INVALID_ISSUER" | "AUTH_INVALID_SIGNATURE" | "AUTH_MALFORMED" } {
    try {
      const p = jwt.verify(token, this.accessSecret, { issuer: this.issuer, algorithms: ["HS256"] });
      if (typeof p === "string" || !p) return { err: "AUTH_MALFORMED" };
      const ok = this.narrow(p);
      return ok ?? { err: "AUTH_MALFORMED" };
    } catch (e) {
      const name = (e as { name?: string }).name;
      if (name === "TokenExpiredError") return { err: "AUTH_EXPIRED" };
      const msg = (e as { message?: string }).message ?? "";
      return { err: msg.startsWith("jwt issuer invalid") ? "AUTH_INVALID_ISSUER" : "AUTH_INVALID_SIGNATURE" };
    }
  }

  private narrow(p: JwtPayload): { sub: string; roles: readonly string[] } | null {
    const sub = p.sub, roles = (p as { roles?: unknown }).roles;
    if (typeof sub !== "string") return null;
    if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) return null;
    return { sub, roles: roles as readonly string[] };
  }

  private async rotateRefresh(cookie: string, res: Response): Promise<"ok" | "revoked" | "invalid"> {
    try {
      const p = jwt.verify(cookie, this.refreshSecret, { issuer: this.issuer });
      if (typeof p === "string" || !p) return "invalid";
      const { sub, jti } = p;
      if (typeof sub !== "string" || typeof jti !== "string") return "invalid";
      if (!(await this.store.isActive(sub, jti))) return "revoked";
      const next = randomBytes(16).toString("base64url");
      await this.store.rotate(sub, jti, next);
      const tok = jwt.sign({ sub, jti: next }, this.refreshSecret, { issuer: this.issuer, expiresIn: "7d" });
      res.cookie("refresh_token", tok, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
      return "ok";
    } catch { return "invalid"; }
  }

  private deny(res: Response, status: 401 | 403, code: string): void {
    process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
    res.status(status).json({ error: code });
  }
}

export const authMiddleware = (a: string, r: string, iss: string, s: IStore): RequestHandler =>
  new AuthService(a, r, iss, s).middleware();
