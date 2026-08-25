import { cn } from "../../lib/cn";
import type { Message } from "../../types";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] whitespace-pre-wrap rounded-lg px-4 py-2 text-sm",
          isUser ? "bg-accent text-accent-foreground" : "bg-primary text-primary-foreground",
        )}
      >
        {message.content}
      </div>
    </div>
  );
}
