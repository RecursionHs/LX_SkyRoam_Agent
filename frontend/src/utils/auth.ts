import { message } from 'antd';
// 简单的JWT Token存储与携带工具
export const TOKEN_KEY = 'auth_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}


export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  // 默认JSON头
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json');
  }
  let response: Response;
  try {
    response = await fetch(input, { ...init, headers });
  } catch (e: any) {
    try {
      const GUARD_KEY = 'network_error_notice_guard';
      const now = Date.now();
      const last = Number(sessionStorage.getItem(GUARD_KEY) || 0);
      if (now - last > 3000) {
        sessionStorage.setItem(GUARD_KEY, String(now));
        message.error('网络异常或操作过于频繁被阻止，请稍后再试');
      }
    } catch {}
    const err: any = new Error('网络异常或操作过于频繁被阻止，请稍后再试');
    err.status = -1;
    throw err;
  }
  if (response.status === 401) {
    // 防止在登录/注册页造成刷新循环；并清理过期令牌
    const path = window.location.pathname || '';
    const onAuthPage = path.startsWith('/login') || path.startsWith('/register');
    if (!onAuthPage) {
      try { clearToken(); } catch {}
      const GUARD_KEY = 'auth_redirect_guard';
      const now = Date.now();
      const last = Number(sessionStorage.getItem(GUARD_KEY) || 0);
      if (now - last > 2000) {
        sessionStorage.setItem(GUARD_KEY, String(now));
        window.location.href = '/login';
      }
    }
  }
  if (response.status === 429) {
    try {
      const GUARD_KEY = 'rate_limit_notice_guard';
      const now = Date.now();
      const last = Number(sessionStorage.getItem(GUARD_KEY) || 0);
      if (now - last > 3000) {
        sessionStorage.setItem(GUARD_KEY, String(now));
        message.warning('操作过于频繁，请稍后再试');
      }
    } catch {}
  }
  return response;
}

export async function fetchJson<T = any>(input: RequestInfo | URL, init: RequestInit = {}): Promise<T> {
  const res = await authFetch(input, init);
  if (!res.ok) {
    if (res.status === 429) {
      const err: any = new Error('操作过于频繁，请稍后再试');
      err.status = 429;
      throw err;
    }
    const err: any = new Error(`请求失败: ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}
