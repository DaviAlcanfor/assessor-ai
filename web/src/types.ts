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

export type NodeName =
  | "roteador_node"
  | "financeiro_node"
  | "agenda_node"
  | "faq_node"
  | "orquestrador_node"
  | "guardrail_entrada_node"
  | "guardrail_saida_node";

export type Route = "financeiro" | "agenda" | "faq" | "fim";

export type ExecutionEvent =
  | { type: "run_started" }
  | { type: "node_started"; node: NodeName }
  | { type: "route_selected"; route: Route }
  | { type: "node_finished"; node: NodeName }
  | { type: "answer_ready"; content: string }
  | { type: "run_finished" }
  | { type: "run_failed"; message: string };

export type ToleranciaRisco = "baixa" | "media" | "alta";

export interface PerfilFinanceiro {
  renda_mensal: number;
  objetivo: string;
  tolerancia_risco: ToleranciaRisco;
  preferencias: string | null;
}
