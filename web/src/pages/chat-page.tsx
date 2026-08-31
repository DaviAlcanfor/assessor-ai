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
  // Chat que está de fato em tela agora. handleSend guarda o resultado de sendMessage contra
  // isso antes de aplicar em setMessages — sem essa checagem, trocar de conversa (sidebar ou
  // "Nova conversa") enquanto uma resposta ainda está a caminho faz a resposta da conversa
  // antiga aparecer grudada na conversa nova/diferente que está em tela quando ela chega.
  const activeChatIdRef = useRef(chatId);

  useEffect(() => {
    activeChatIdRef.current = chatId;

    if (skipNextFetchRef.current) {
      skipNextFetchRef.current = false;
      return;
    }

    if (!chatId) {
      setMessages([]);
      return;
    }

    // Cancela aplicar o resultado se o efeito rodar de novo antes de resolver (troca rápida
    // entre chats na sidebar) — sem isso, um fetch mais antigo que resolve depois de um mais
    // novo sobrescreve as mensagens certas com as do chat errado.
    let cancelado = false;

    getMessages(chatId)
      .then((msgs) => {
        if (!cancelado) setMessages(msgs);
      })
      .catch(() => {
        if (!cancelado) setMessages([]);
      });

    return () => {
      cancelado = true;
    };
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
          activeChatIdRef.current = id;
          skipNextFetchRef.current = true;
          setSidebarRefresh((n) => n + 1);
          navigate(`/chat/${id}`, { replace: true });
        }

        const resposta = await sendMessage(id, content);
        if (activeChatIdRef.current !== id) return;
        setMessages((prev) => [...prev, { role: "assistant", content: resposta.content }]);
        setSidebarRefresh((n) => n + 1);
      } catch (err) {
        if (activeChatIdRef.current !== id) return;
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
      {/* pr-64 espelha a largura da sidebar → mx-auto interno centraliza no centro da tela, não da área restante */}
      <div ref={mainRef} className="flex flex-1 flex-col xl:pr-64">
        <MessageList messages={messages} pensando={pensando} />
        <ChatInput onSend={handleSend} disabled={pensando} />
      </div>
    </div>
  );
}
