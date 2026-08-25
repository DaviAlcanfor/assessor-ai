import { useRef } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

export function ThinkingDots() {
  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();

      mm.add({ reduceMotion: "(prefers-reduced-motion: reduce)" }, (context) => {
        const { reduceMotion } = context.conditions as { reduceMotion: boolean };
        if (reduceMotion) return;

        gsap.to(".thinking-dot", {
          y: -4,
          duration: 0.4,
          ease: "power1.inOut",
          repeat: -1,
          yoyo: true,
          stagger: { each: 0.15, repeat: -1, yoyo: true },
        });
      });
    },
    { scope: containerRef },
  );

  return (
    <div ref={containerRef} className="flex items-center gap-1 px-4 py-2" aria-label="Pensando">
      <span className="thinking-dot h-2 w-2 rounded-full bg-primary" />
      <span className="thinking-dot h-2 w-2 rounded-full bg-primary" />
      <span className="thinking-dot h-2 w-2 rounded-full bg-primary" />
    </div>
  );
}
