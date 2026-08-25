import { useCallback, useEffect, useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useNavigate, useParams } from "react-router";
import { createChat, getMessages, sendMessage } from "../lib/api";
import { ChatInput } from "../components/chat/chat-input";
import { MessageList } from "../components/chat/message-list";
import { Sidebar } from "../components/sidebar/sidebar";
import type { Message } from "../types";

export function ChatPage() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [pensando, setPensando] = useState(false);
  const [sidebarRefresh, setSidebarRefresh] = useState(0);
  const mainRef = useRef<HTMLDivElement>(null);
  // Evita que o refetch disparado por navigate() (logo abaixo de createChat) sobrescreva as
  // mensagens otimistas já em tela antes da resposta do Assessor chegar e ser persistida.
  const skipNextFetchRef = useRef(false);

  useEffect(() => {
    if (skipNextFetchRef.current) {
      skipNextFetchRef.current = false;
      return;
    }

    if (!chatId) {
      setMessages([]);
      return;
    }

    getMessages(chatId)
      .then(setMessages)
      .catch(() => setMessages([]));
  }, [chatId]);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();

      mm.add({ reduceMotion: "(prefers-reduced-motion: reduce)" }, (context) => {
        const { reduceMotion } = context.conditions as { reduceMotion: boolean };

        gsap.from(mainRef.current, {
          autoAlpha: 0,
          duration: reduceMotion ? 0 : 0.3,
          ease: "power2.out",
        });
      });
    },
    { scope: mainRef },
  );

  const handleSend = useCallback(
    async (content: string) => {
      let id = chatId;

      setMessages((prev) => [...prev, { role: "user", content }]);
      setPensando(true);

      try {
        if (!id) {
          const created = await createChat();
          id = created.chat_id;
          skipNextFetchRef.current = true;
          setSidebarRefresh((n) => n + 1);
          navigate(`/chat/${id}`, { replace: true });
        }

        const resposta = await sendMessage(id, content);
        setMessages((prev) => [...prev, { role: "assistant", content: resposta.content }]);
        setSidebarRefresh((n) => n + 1);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: err instanceof Error ? err.message : "Erro ao enviar mensagem.",
          },
        ]);
      } finally {
        setPensando(false);
      }
    },
    [chatId, navigate],
  );

  return (
    <div className="flex h-screen">
      <Sidebar refreshKey={sidebarRefresh} />
      <div ref={mainRef} className="flex flex-1 flex-col">
        <MessageList messages={messages} pensando={pensando} />
        <ChatInput onSend={handleSend} disabled={pensando} />
      </div>
    </div>
  );
}
