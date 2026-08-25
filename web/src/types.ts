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
