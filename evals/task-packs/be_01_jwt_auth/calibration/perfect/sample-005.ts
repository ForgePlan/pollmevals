// source: own-authored 2026-05-26 by gogocat (license: MIT)
// perfect/sample-005 — branded token types + injectable clock.
// Distinct idiom: nominal typing via brand symbols, clock-injectable for tests.

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { Request, RequestHandler, Response } from "express";
import jwt from "jsonwebtoken";

declare const AccessTokenBrand: unique symbol;
declare const RefreshTokenBrand: unique symbol;
type AccessToken = string & { readonly [AccessTokenBrand]: true };
type RefreshToken = string & { readonly [RefreshTokenBrand]: true };

const asAccess = (s: string): AccessToken => s as AccessToken;
const asRefresh = (s: string): RefreshToken => s as RefreshToken;

interface Store {
  isActive(sub: string, jti: string): Promise<boolean>;
  rotate(sub: string, oldJti: string, newJti: string): Promise<void>;
}

export interface Opts {
  accessSecret: string;
  refreshSecret: string;
  issuer: string;
  refreshStore: Store;
  now?: () => number;
}

const STATE_CHANGE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function parseBearer(h: string | undefined): AccessToken | null {
  const m = h ? h.match(/^Bearer\s+(\S+)$/) : null;
  return m ? asAccess(m[1]) : null;
}

function verifyAccess(t: AccessToken, opts: Opts):
  | { kind: "ok"; sub: string; roles: readonly string[] }
  | { kind: "err"; code: string } {
  try {
    const clockTimestamp = opts.now ? Math.floor(opts.now() / 1000) : undefined;
    const p = jwt.verify(t, opts.accessSecret, {
      issuer: opts.issuer, algorithms: ["HS256"], clockTimestamp,
    });
    if (typeof p === "string" || !p) return { kind: "err", code: "AUTH_MALFORMED" };
    const sub = p.sub, roles = (p as { roles?: unknown }).roles;
    if (typeof sub !== "string") return { kind: "err", code: "AUTH_MALFORMED" };
    if (!Array.isArray(roles) || !roles.every((r): r is string => typeof r === "string")) {
      return { kind: "err", code: "AUTH_MALFORMED" };
    }
    return { kind: "ok", sub, roles: roles as readonly string[] };
  } catch (e) {
    const name = (e as { name?: string }).name;
    if (name === "TokenExpiredError") return { kind: "err", code: "AUTH_EXPIRED" };
    const msg = (e as { message?: string }).message ?? "";
    return {
      kind: "err",
      code: msg.startsWith("jwt issuer invalid") ? "AUTH_INVALID_ISSUER" : "AUTH_INVALID_SIGNATURE",
    };
  }
}

function csrfPass(req: Request): boolean {
  const h = req.get("x-csrf-token") ?? "";
  const c = (req.cookies as Record<string, string> | undefined)?.csrf_token ?? "";
  if (!h || !c || h.length !== c.length) return false;
  return timingSafeEqual(Buffer.from(h), Buffer.from(c));
}

async function rotateRefresh(t: RefreshToken, opts: Opts, res: Response):
  Promise<"ok" | "revoked" | "invalid"> {
  try {
    const p = jwt.verify(t, opts.refreshSecret, { issuer: opts.issuer });
    if (typeof p === "string" || !p) return "invalid";
    const { sub, jti } = p;
    if (typeof sub !== "string" || typeof jti !== "string") return "invalid";
    if (!(await opts.refreshStore.isActive(sub, jti))) return "revoked";
    const nj = randomBytes(16).toString("base64url");
    await opts.refreshStore.rotate(sub, jti, nj);
    const fresh = jwt.sign({ sub, jti: nj }, opts.refreshSecret, {
      issuer: opts.issuer, expiresIn: "7d",
    });
    res.cookie("refresh_token", fresh, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
    return "ok";
  } catch { return "invalid"; }
}

function emit(res: Response, status: 401 | 403, code: string): void {
  process.stderr.write(JSON.stringify({ ts: new Date().toISOString(), kind: "auth", code }) + "\n");
  res.status(status).json({ error: code });
}

export function authMiddleware(opts: Opts): RequestHandler {
  return async (req, res, next) => {
    if (STATE_CHANGE.has(req.method) && !csrfPass(req)) {
      return emit(res, 403, "CSRF_MISMATCH");
    }
    const tok = parseBearer(req.get("authorization"));
    if (!tok) return emit(res, 401, "AUTH_MISSING");
    const v = verifyAccess(tok, opts);
    if (v.kind === "err") return emit(res, 401, v.code);
    const refreshStr = (req.cookies as Record<string, string> | undefined)?.refresh_token;
    if (refreshStr) {
      const r = await rotateRefresh(asRefresh(refreshStr), opts, res);
      if (r !== "ok") return emit(res, 401, r === "revoked" ? "AUTH_REFRESH_REVOKED" : "AUTH_INVALID_SIGNATURE");
    }
    (req as Request & { user: { sub: string; roles: readonly string[] } }).user = {
      sub: v.sub, roles: v.roles,
    };
    next();
  };
}
