import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError, getPerfil, savePerfil } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import type { ToleranciaRisco } from "../types";

const CONTROL =
  "w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring";

const TOLERANCIAS: ToleranciaRisco[] = ["baixa", "media", "alta"];

export function PerfilPage() {
  const [renda, setRenda] = useState("");
  const [objetivo, setObjetivo] = useState("");
  const [tolerancia, setTolerancia] = useState<ToleranciaRisco | "">("");
  const [preferencias, setPreferencias] = useState("");

  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [status, setStatus] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  useEffect(() => {
    getPerfil()
      .then((perfil) => {
        if (!perfil) return;
        setRenda(String(perfil.renda_mensal));
        setObjetivo(perfil.objetivo);
        setTolerancia(perfil.tolerancia_risco);
        setPreferencias(perfil.preferencias ?? "");
      })
      .catch(() => setStatus({ tipo: "erro", texto: "Não consegui carregar o cadastro atual." }))
      .finally(() => setCarregando(false));
  }, []);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    if (salvando || tolerancia === "") return;

    setSalvando(true);
    setStatus(null);

    try {
      await savePerfil({
        renda_mensal: Number(renda),
        objetivo: objetivo.trim(),
        tolerancia_risco: tolerancia,
        preferencias: preferencias.trim() || null,
      });
      setStatus({ tipo: "ok", texto: "Perfil salvo. O assessor usa esses dados nas conversas." });
    } catch (err) {
      const texto =
        err instanceof ApiError ? err.message : "Não consegui falar com a API.";
      setStatus({ tipo: "erro", texto });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <Card className="mx-auto max-w-xl p-6">
        <header className="mb-6 flex items-baseline justify-between">
          <h1 className="font-display text-xl font-semibold text-foreground">Perfil financeiro</h1>
          <Link to="/chat" className="text-sm text-muted-foreground hover:text-foreground">
            voltar ao chat
          </Link>
        </header>

        <p className="mb-6 text-sm text-muted-foreground">
          Estes dados valem para todas as conversas — o assessor lê este cadastro quando precisa
          aconselhar. O chat não altera nada daqui.
        </p>

        {carregando ? (
          <p className="text-sm text-muted-foreground">Carregando...</p>
        ) : (
          <form onSubmit={salvar} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5 text-sm font-medium text-foreground">
              renda mensal
              <Input
                type="number"
                min="0"
                step="0.01"
                required
                value={renda}
                onChange={(e) => setRenda(e.target.value)}
                placeholder="4200"
              />
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-medium text-foreground">
              objetivo
              <Input
                type="text"
                maxLength={120}
                required
                value={objetivo}
                onChange={(e) => setObjetivo(e.target.value)}
                placeholder="juntar para uma viagem em dezembro"
              />
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-medium text-foreground">
              tolerância a risco
              <select
                required
                className={CONTROL}
                value={tolerancia}
                onChange={(e) => setTolerancia(e.target.value as ToleranciaRisco | "")}
              >
                <option value="" disabled>
                  selecione
                </option>
                {TOLERANCIAS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1.5 text-sm font-medium text-foreground">
              preferências
              <textarea
                rows={4}
                maxLength={2000}
                className={CONTROL}
                value={preferencias}
                onChange={(e) => setPreferencias(e.target.value)}
                placeholder="texto livre: planos, restrições e gostos em frases normais — ex.: não quero investimento agressivo"
              />
            </label>

            <div className="mt-2 flex items-center justify-between gap-4">
              <p
                className={`text-sm ${
                  status?.tipo === "erro"
                    ? "text-destructive"
                    : status?.tipo === "ok"
                      ? "text-foreground"
                      : "text-muted-foreground"
                }`}
              >
                {status?.texto ?? "nada salvo ainda nesta sessão"}
              </p>
              <Button type="submit" disabled={salvando}>
                {salvando ? "salvando..." : "salvar perfil"}
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
