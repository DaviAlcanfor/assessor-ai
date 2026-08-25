import { useState, type FormEvent } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (content: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue("");
  }

  return (
    <form onSubmit={submit} className="flex gap-2 border-t border-border p-4">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Escreva sua mensagem..."
        disabled={disabled}
      />
      <Button type="submit" disabled={disabled || !value.trim()}>
        Enviar
      </Button>
    </form>
  );
}
