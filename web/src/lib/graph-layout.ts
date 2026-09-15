import type { NodeName } from "../types";

// Layout fixo espelhando o grafo em builder.py — não dá pra derivar isso do backend sem expor a
// topologia via API, e ela muda raramente o bastante pra valer hardcodear.
export const NODE_META: Record<NodeName, { x: number; y: number; label: string }> = {
  guardrail_entrada_node: { x: 500, y: 70, label: "entrada" },
  roteador_node: { x: 500, y: 230, label: "roteador" },
  financeiro_node: { x: 190, y: 400, label: "financeiro" },
  agenda_node: { x: 500, y: 400, label: "agenda" },
  faq_node: { x: 810, y: 400, label: "faq" },
  orquestrador_node: { x: 345, y: 560, label: "orquestrador" },
  guardrail_saida_node: { x: 500, y: 700, label: "saída" },
};

export const GRAPH_EDGES: [NodeName, NodeName][] = [
  ["guardrail_entrada_node", "roteador_node"],
  ["roteador_node", "financeiro_node"],
  ["roteador_node", "agenda_node"],
  ["roteador_node", "faq_node"],
  ["financeiro_node", "orquestrador_node"],
  ["agenda_node", "orquestrador_node"],
  ["orquestrador_node", "guardrail_saida_node"],
  ["faq_node", "guardrail_saida_node"],
];

export const VIEWBOX = "0 0 1000 760";
