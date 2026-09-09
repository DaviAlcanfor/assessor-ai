export interface User {
  user_id: string;
  nome: string;
  email: string;
}

export interface ChatSummary {
  chat_id: string;
  title: string;
  updated_at: string;
}

export type Role = "user" | "assistant";

export interface Message {
  role: Role;
  content: string;
}

export type ToleranciaRisco = "baixa" | "media" | "alta";

export interface PerfilFinanceiro {
  renda_mensal: number;
  objetivo: string;
  tolerancia_risco: ToleranciaRisco;
  preferencias: string | null;
}
