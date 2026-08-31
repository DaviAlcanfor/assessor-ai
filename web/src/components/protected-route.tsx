import { useEffect, useState, type ReactNode } from "react";
import { listUsers } from "../lib/api";
import { loadUser, saveUser } from "../lib/storage";

/**
 * Modo dev, sem auth de verdade: se ninguém "entrou" ainda, pega um usuário aleatório da API
 * e persiste no localStorage. Só funciona com API_KEY_AUTH_ENABLED=false (interfaces/api/auth.py).
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const [pronto, setPronto] = useState(() => loadUser() !== null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (pronto) return;
    listUsers()
      .then((users) => {
        if (users.length === 0) throw new Error("Nenhum usuário cadastrado na API.");
        const u = users[Math.floor(Math.random() * users.length)];
        saveUser({ user_id: u.user_id, nome: u.nome });
        setPronto(true);
      })
      .catch((e: unknown) => setErro(e instanceof Error ? e.message : "Erro ao carregar usuário."));
  }, [pronto]);

  if (erro) return <p className="p-6 text-sm text-destructive">{erro}</p>;
  if (!pronto) return <p className="p-6 text-muted-foreground">Entrando...</p>;
  return <>{children}</>;
}
