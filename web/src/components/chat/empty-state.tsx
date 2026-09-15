import { useMemo, useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { loadUser } from "../../lib/storage";

const SAUDACOES = [
  "Olá, {nome}!",
  "E aí, {nome}, tudo certo?",
  "Bem-vindo de volta, {nome}.",
  "Oi, {nome}! No que posso ajudar?",
  "Fala, {nome}!",
  "Pronto pra começar, {nome}?",
];

const SUBTITULOS = [
  "Pergunte sobre suas finanças, sua agenda ou tire dúvidas.",
  "Posso ajudar com investimentos, compromissos ou dúvidas rápidas.",
  "Manda a pergunta que eu chamo o especialista certo.",
  "Sobre dinheiro, agenda ou dúvidas gerais — pode perguntar.",
];

function pick(lista: string[]): string {
  return lista[Math.floor(Math.random() * lista.length)];
}

export function EmptyState() {
  const containerRef = useRef<HTMLDivElement>(null);
  const nome = loadUser()?.nome ?? "você";

  const saudacao = useMemo(() => pick(SAUDACOES).replace("{nome}", nome), [nome]);
  const subtitulo = useMemo(() => pick(SUBTITULOS), []);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();

      mm.add({ reduceMotion: "(prefers-reduced-motion: reduce)" }, (context) => {
        const { reduceMotion } = context.conditions as { reduceMotion: boolean };

        gsap
          .timeline({ defaults: { ease: "power3.out" } })
          .from(".empty-title", {
            autoAlpha: 0,
            y: reduceMotion ? 0 : 16,
            duration: reduceMotion ? 0 : 0.6,
          })
          .from(
            ".empty-subtitle",
            {
              autoAlpha: 0,
              y: reduceMotion ? 0 : 10,
              duration: reduceMotion ? 0 : 0.5,
            },
            "-=0.3",
          );
      });
    },
    { scope: containerRef },
  );

  return (
    <div ref={containerRef} className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center">
      <h1 className="empty-title font-display text-3xl font-semibold text-foreground">{saudacao}</h1>
      <p className="empty-subtitle text-sm text-muted-foreground">{subtitulo}</p>
    </div>
  );
}
