import { useEffect, useRef, useState, type FormEvent } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { useNavigate } from "react-router";
import { createUser, listUsers } from "../lib/api";
import { saveUser } from "../lib/storage";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import type { User } from "../types";

/**
 * Tela de dev, não de auth de verdade — sem senha, só escolhe qual user_id vai no header
 * X-User-Id. Só funciona com API_KEY_AUTH_ENABLED=false no backend (interfaces/api/auth.py).
 */
export function LoginPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const { contextSafe } = useGSAP({ scope: rootRef });

  useEffect(() => {
    listUsers()
      .then(setUsers)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Erro ao carregar usuários."))
      .finally(() => setLoading(false));
  }, []);

  const entrar = contextSafe((user: User) => {
    saveUser({ user_id: user.user_id, nome: user.nome });

    const mm = gsap.matchMedia();
    mm.add({ reduceMotion: "(prefers-reduced-motion: reduce)" }, (context) => {
      const { reduceMotion } = context.conditions as { reduceMotion: boolean };

      gsap.to(rootRef.current, {
        autoAlpha: 0,
        duration: reduceMotion ? 0 : 0.25,
        ease: "power2.in",
        onComplete: () => navigate("/chat"),
      });
    });
  });

  function entrarAleatorio() {
    if (users.length === 0) return;
    entrar(users[Math.floor(Math.random() * users.length)]);
  }

  async function criar(e: FormEvent) {
    e.preventDefault();
    try {
      const user = await createUser(nome, email);
      entrar(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível criar o usuário.");
    }
  }

  return (
    <main
      ref={rootRef}
      className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center gap-8 px-4 py-12"
    >
      <h1 className="font-display text-3xl font-bold">Assessor.AI</h1>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading ? (
        <p className="text-muted-foreground">Carregando usuários...</p>
      ) : (
        <>
          <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
            {users.map((user) => (
              <Card key={user.user_id} className="flex items-center justify-between p-4">
                <div>
                  <p className="font-medium">{user.nome}</p>
                  <p className="text-sm text-muted-foreground">{user.email}</p>
                </div>
                <Button variant="secondary" onClick={() => entrar(user)}>
                  Entrar
                </Button>
              </Card>
            ))}
          </div>

          {users.length > 0 && (
            <Button variant="ghost" onClick={entrarAleatorio}>
              Entrar com um aleatório
            </Button>
          )}
        </>
      )}

      <Card className="w-full max-w-sm p-6">
        <h2 className="mb-4 font-display text-lg font-semibold">Criar novo</h2>
        <form className="flex flex-col gap-3" onSubmit={criar}>
          <Input placeholder="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
          <Input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Button type="submit">Criar e entrar</Button>
        </form>
      </Card>
    </main>
  );
}
