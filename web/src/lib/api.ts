import type { ChatSummary, Message, PerfilFinanceiro, User } from "../types";
import { loadUser } from "./storage";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const user = loadUser();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(user ? { "X-User-Id": user.user_id } : {}),
    ...init?.headers,
  };

  const res = await fetch(path, { ...init, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(body?.detail ?? `Erro ${res.status}`, res.status);
  }

  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

export function listUsers(): Promise<User[]> {
  return request("/v1/users");
}

export function listChats(): Promise<ChatSummary[]> {
  return request("/v1/chats");
}

export function createChat(): Promise<{ chat_id: string }> {
  return request("/v1/chats", { method: "POST" });
}

export function getMessages(chatId: string): Promise<Message[]> {
  return request(`/v1/chats/${chatId}/messages`);
}

export function sendMessage(
  chatId: string,
  content: string,
): Promise<{ chat_id: string; content: string }> {
  return request(`/v1/chats/${chatId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function getPerfil(): Promise<PerfilFinanceiro | null> {
  try {
    return await request<PerfilFinanceiro>("/v1/perfil");
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

export function savePerfil(perfil: PerfilFinanceiro): Promise<PerfilFinanceiro> {
  return request("/v1/perfil", { method: "PUT", body: JSON.stringify(perfil) });
}
