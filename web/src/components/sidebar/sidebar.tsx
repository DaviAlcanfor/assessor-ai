import { useEffect, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useNavigate, useParams } from "react-router";
import { listChats } from "../../lib/api";
import { loadUser } from "../../lib/storage";
import type { ChatSummary } from "../../types";
import { Button } from "../ui/button";

export function Sidebar({ refreshKey }: { refreshKey: number }) {
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { chatId } = useParams();
  const user = loadUser();

  useEffect(() => {
    listChats()
      .then(setChats)
      .catch(() => setChats([]));
  }, [refreshKey]);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();

      mm.add({ reduceMotion: "(prefers-reduced-motion: reduce)" }, (context) => {
        const { reduceMotion } = context.conditions as { reduceMotion: boolean };

        gsap.from(".chat-list-item", {
          autoAlpha: 0,
          y: 8,
          stagger: reduceMotion ? 0 : 0.04,
          duration: reduceMotion ? 0 : 0.3,
          ease: "power2.out",
        });
      });
    },
    { scope: containerRef, dependencies: [chats.length] },
  );

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <div className="p-3">
        <Button className="w-full" onClick={() => navigate("/chat")}>
          Nova conversa
        </Button>
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto px-2">
        {chats.map((chat) => (
          <button
            key={chat.chat_id}
            onClick={() => navigate(`/chat/${chat.chat_id}`)}
            className={`chat-list-item block w-full truncate rounded-md px-3 py-2 text-left text-sm hover:bg-accent/10 ${
              chat.chat_id === chatId ? "bg-accent/15 font-medium" : ""
            }`}
          >
            {chat.title}
          </button>
        ))}
      </div>

      {user && (
        <div className="border-t border-sidebar-border p-3 text-sm text-muted-foreground">
          {user.nome}
        </div>
      )}
    </aside>
  );
}
