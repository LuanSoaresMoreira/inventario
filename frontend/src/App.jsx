import { useCallback, useEffect, useState } from "react";

const apiBaseUrl = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

function App() {
  const [health, setHealth] = useState({ state: "loading", message: "Verificando a API..." });

  const checkApi = useCallback(async (signal) => {
    setHealth({ state: "loading", message: "Verificando a API..." });

    try {
      const response = await fetch(`${apiBaseUrl}/api/health`, { signal });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setHealth({ state: "success", message: `API disponível (${data.service})` });
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }

      setHealth({
        state: "error",
        message: "Não foi possível conectar à API. Verifique se o backend está em execução.",
      });
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    checkApi(controller.signal);

    return () => controller.abort();
  }, [checkApi]);

  return (
    <main className="page-shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Inventário institucional</p>
        <h1 id="page-title">Base do sistema pronta para evoluir.</h1>
        <p className="intro">
          O frontend React está conectado à API FastAPI para validar o ambiente local.
        </p>

        <div className={`status-card status-${health.state}`} role="status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          <span>{health.message}</span>
        </div>

        <button className="retry-button" type="button" onClick={() => checkApi()}>
          Verificar novamente
        </button>
      </section>
    </main>
  );
}

export default App;
