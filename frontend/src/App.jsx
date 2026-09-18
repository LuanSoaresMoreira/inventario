import { useCallback, useEffect, useState } from "react";

const apiBaseUrl = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const minimumEnvironmentKinds = [
  ["classroom", "Sala de aula"],
  ["laboratory", "Laboratório"],
  ["coordination", "Coordenação"],
  ["administrative", "Setor administrativo"],
  ["warehouse", "Almoxarifado"],
];
const equipmentKinds = [
  ["computer", "Computador"],
  ["projector", "Projetor"],
  ["air_conditioner", "Ar-condicionado"],
  ["remote_control", "Controle remoto"],
  ["other", "Outro"],
];
const equipmentStatuses = [
  ["active", "Ativo"],
  ["maintenance", "Em manutenção"],
  ["inactive", "Inativo"],
];

async function fetchJson(path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: "include",
    ...options,
  });

  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.status = response.status;
    try {
      const body = await response.json();
      error.detail = body.detail;
    } catch {
      error.detail = null;
    }
    throw error;
  }

  return response.status === 204 ? null : response.json();
}

function csrfToken() {
  const cookie = document.cookie
    .split("; ")
    .find((value) => value.startsWith("inventario_csrf="));
  return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

function labelFor(options, value) {
  return options.find(([option]) => option === value)?.[1] || value;
}

function publicEquipmentToken() {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/^\/public\/equipment\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function PublicReportPage({ token }) {
  const [form, setForm] = useState({ description: "", reporter_name: "", reporter_contact: "" });
  const [state, setState] = useState("idle");
  const [trackingToken, setTrackingToken] = useState("");

  async function submitReport(event) {
    event.preventDefault();
    setState("loading");
    try {
      const data = await fetchJson(`/api/public/equipment/${encodeURIComponent(token)}/occurrences`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: form.description,
          reporter_name: form.reporter_name || null,
          reporter_contact: form.reporter_contact || null,
        }),
      });
      setTrackingToken(data.tracking_token);
      setState("success");
    } catch {
      setState("error");
    }
  }

  return (
    <main className="page-shell public-page">
      <section className="catalog-panel public-panel" aria-labelledby="public-report-title">
        <p className="eyebrow">Comunicação institucional</p>
        <h1 id="public-report-title">Comunicar um problema</h1>
        <p className="intro">Descreva o problema observado. Não informe dados sensíveis ou prioridade; a equipe responsável fará a triagem.</p>
        {state === "success" ? (
          <div className="status-card status-success" role="status" aria-live="polite">
            Comunicação recebida. Guarde o identificador de acompanhamento: <strong>{trackingToken}</strong>
          </div>
        ) : (
          <form className="public-report-form" onSubmit={submitReport}>
            <label htmlFor="public-description">Descrição do problema<textarea id="public-description" required minLength={5} maxLength={2000} rows={6} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
            <label htmlFor="public-name">Seu nome (opcional)<input id="public-name" maxLength={160} autoComplete="name" value={form.reporter_name} onChange={(event) => setForm({ ...form, reporter_name: event.target.value })} /></label>
            <label htmlFor="public-contact">Contato (opcional)<input id="public-contact" maxLength={255} autoComplete="email" value={form.reporter_contact} onChange={(event) => setForm({ ...form, reporter_contact: event.target.value })} /></label>
            {state === "error" && <p className="form-error" role="alert">Não foi possível enviar agora. Tente novamente mais tarde.</p>}
            <button className="retry-button" type="submit" disabled={state === "loading"}>{state === "loading" ? "Enviando..." : "Enviar comunicação"}</button>
          </form>
        )}
      </section>
    </main>
  );
}

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [loginForm, setLoginForm] = useState({ auth_subject: "", password: "" });
  const [loginState, setLoginState] = useState("idle");
  const [loginError, setLoginError] = useState("");
  const [environments, setEnvironments] = useState([]);
  const [environmentEditId, setEnvironmentEditId] = useState(null);
  const [environmentActive, setEnvironmentActive] = useState("");
  const [environmentQuery, setEnvironmentQuery] = useState("");
  const [environmentMessage, setEnvironmentMessage] = useState("Carregando ambientes...");
  const [environmentForm, setEnvironmentForm] = useState({
    code: "",
    name: "",
    kind: "classroom",
    active: true,
    reason: "Cadastro no catálogo institucional",
  });
  const [equipment, setEquipment] = useState([]);
  const [equipmentEditId, setEquipmentEditId] = useState(null);
  const [equipmentFilters, setEquipmentFilters] = useState({
    search: "",
    kind: "",
    status: "",
    location_id: "",
  });
  const [equipmentOffset, setEquipmentOffset] = useState(0);
  const [equipmentTotal, setEquipmentTotal] = useState(0);
  const equipmentLimit = 20;
  const [equipmentMessage, setEquipmentMessage] = useState("Carregando equipamentos...");
  const [publicAccess, setPublicAccess] = useState(null);
  const [publicAccessEquipment, setPublicAccessEquipment] = useState(null);
  const [publicAccessMessage, setPublicAccessMessage] = useState("");
  const [movements, setMovements] = useState([]);
  const [movementForm, setMovementForm] = useState({ equipment_id: "", destination_environment_id: "", reason: "Movimentação institucional" });
  const [movementMessage, setMovementMessage] = useState("Selecione um equipamento para consultar a linha do tempo.");
  const [occurrences, setOccurrences] = useState([]);
  const [occurrenceFilter, setOccurrenceFilter] = useState({ status: "", priority: "" });
  const [occurrenceMessage, setOccurrenceMessage] = useState("Carregando ocorrências...");
  const [maintenances, setMaintenances] = useState([]);
  const [maintenanceForm, setMaintenanceForm] = useState({ equipment_id: "", occurrence_id: "", kind: "preventive", scheduled_for: "", reason: "Abertura de manutenção institucional" });
  const [maintenanceUpdateForm, setMaintenanceUpdateForm] = useState({ id: "", procedure: "", result: "", next_maintenance_on: "", reason: "Conclusão de manutenção institucional" });
  const [componentForm, setComponentForm] = useState({ maintenance_id: "", component_name: "", quantity: "1", observation: "", reason: "Registro de componente substituído" });
  const [maintenanceMessage, setMaintenanceMessage] = useState("Carregando manutenções...");
  const [dashboard, setDashboard] = useState(null);
  const [dashboardMessage, setDashboardMessage] = useState("Carregando indicadores...");
  const [plans, setPlans] = useState([]);
  const [planForm, setPlanForm] = useState({ year: String(new Date().getFullYear()), capacity: "10", reason: "Simulação do planejamento preventivo anual" });
  const [planningMessage, setPlanningMessage] = useState("Carregando planejamentos...");
  const [alerts, setAlerts] = useState([]);
  const [alertMessage, setAlertMessage] = useState("Carregando alertas...");
  const [report, setReport] = useState(null);
  const [reportMessage, setReportMessage] = useState("Carregando relatório...");
  const [warrantyForm, setWarrantyForm] = useState({ equipment_id: "", supplier: "", starts_on: "", ends_on: "", terms: "", reason: "Cadastro de garantia institucional" });
  const [costForm, setCostForm] = useState({ maintenance_id: "", amount: "", currency: "BRL", source: "", reference: "", note: "", reason: "Registro informativo de custo" });
  const [componentHistory, setComponentHistory] = useState([]);
  const [predictionPolicies, setPredictionPolicies] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [predictionMonitoring, setPredictionMonitoring] = useState(null);
  const [predictionMessage, setPredictionMessage] = useState("Carregando previsões...");
  const [equipmentForm, setEquipmentForm] = useState({
    kind: "computer",
    asset_tag: "",
    brand: "",
    model: "",
    location_id: "",
    status: "active",
    last_maintenance_on: "",
    next_maintenance_on: "",
    reason: "Cadastro no inventário institucional",
  });
  const [formState, setFormState] = useState("idle");
  const publicToken = publicEquipmentToken();
  const pageItems = [
    ["home", "Painel"],
    ["environments", "Ambientes"],
    ["equipment", "Equipamentos"],
    ["movements", "Movimentações"],
    ["occurrences", "Ocorrências"],
    ["maintenance", "Manutenções"],
    ["planning", "Planejamento"],
    ["alerts", "Alertas"],
    ["predictions", "Previsões"],
    ["reports", "Relatórios"],
  ];
  const [activePage, setActivePage] = useState(() => {
    if (typeof window === "undefined") return "home";
    const requestedPage = window.location.hash.replace(/^#/, "");
    return pageItems.some(([page]) => page === requestedPage) ? requestedPage : "home";
  });

  useEffect(() => {
    function syncPage() {
      const requestedPage = window.location.hash.replace(/^#/, "");
      setActivePage(pageItems.some(([page]) => page === requestedPage) ? requestedPage : "home");
    }
    window.addEventListener("hashchange", syncPage);
    return () => window.removeEventListener("hashchange", syncPage);
  }, []);

  function navigate(page) {
    window.location.hash = page === "home" ? "" : page;
    setActivePage(page);
  }

  function markSessionExpired() {
    setCurrentUser(null);
  }

  const checkSession = useCallback(async (signal) => {
    try {
      const data = await fetchJson("/api/auth/me", { signal });
      setCurrentUser(data.user);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) {
        markSessionExpired();
        return;
      }
      if (error.status === 403) {
        setLoginError("Seu usuário não tem permissão para acessar esta operação.");
        return;
      }
      setLoginError("Não foi possível verificar a sessão com segurança.");
    }
  }, []);

  const loadEnvironments = useCallback(async (signal, search = "", active) => {
    setEnvironmentMessage("Carregando ambientes...");
    const params = new URLSearchParams();
    if (search.trim()) params.set("search", search.trim());
    if (active) params.set("active", active);
    const query = params.toString() ? `?${params.toString()}` : "";
    try {
      const data = await fetchJson(`/api/environments${query}`, { signal });
      setEnvironments(data.items);
      setEnvironmentMessage(`${data.total} ambiente(s) encontrado(s).`);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) {
        markSessionExpired();
        setEnvironmentMessage("Faça login para consultar o catálogo de ambientes.");
        return;
      }
      if (error.status === 403) {
        setEnvironmentMessage("Seu usuário não tem permissão para consultar ambientes.");
        return;
      }
      setEnvironmentMessage("Não foi possível carregar o catálogo de ambientes.");
    }
  }, []);

  const loadEquipment = useCallback(async (signal, filters, offset = 0) => {
    setEquipmentMessage("Carregando equipamentos...");
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value && value.trim()) params.set(key, value.trim());
    });
    params.set("limit", String(equipmentLimit));
    params.set("offset", String(offset));
    try {
      const query = params.toString() ? `?${params.toString()}` : "";
      const data = await fetchJson(`/api/equipment${query}`, { signal });
      setEquipment(data.items);
      setEquipmentTotal(data.total);
      setEquipmentMessage(`${data.total} equipamento(s) encontrado(s).`);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) {
        markSessionExpired();
        setEquipmentMessage("Faça login para consultar o inventário de equipamentos.");
        return;
      }
      if (error.status === 403) {
        setEquipmentMessage("Seu usuário não tem permissão para consultar equipamentos.");
        return;
      }
      setEquipmentMessage("Não foi possível carregar o inventário de equipamentos.");
    }
  }, []);

  const loadMovements = useCallback(async (signal, equipmentId) => {
    if (!equipmentId) {
      setMovements([]);
      setMovementMessage("Selecione um equipamento para consultar a linha do tempo.");
      return;
    }
    setMovementMessage("Carregando linha do tempo...");
    try {
      const data = await fetchJson(`/api/equipment/${equipmentId}/movements`, { signal });
      setMovements(data.items);
      setMovementMessage(`${data.total} movimentação(ões) registrada(s).`);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) markSessionExpired();
      setMovementMessage("Não foi possível carregar a linha do tempo.");
    }
  }, []);

  const loadOccurrences = useCallback(async (signal, filters = occurrenceFilter) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    setOccurrenceMessage("Carregando ocorrências...");
    try {
      const query = params.toString() ? `?${params.toString()}` : "";
      const data = await fetchJson(`/api/occurrences${query}`, { signal });
      setOccurrences(data.items);
      setOccurrenceMessage(`${data.total} ocorrência(s) encontrada(s).`);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) markSessionExpired();
      setOccurrenceMessage("Não foi possível carregar as ocorrências.");
    }
  }, [occurrenceFilter]);

  const loadMaintenances = useCallback(async (signal) => {
    setMaintenanceMessage("Carregando manutenções...");
    try {
      const data = await fetchJson("/api/maintenances", { signal });
      setMaintenances(data.items);
      setMaintenanceMessage(`${data.total} manutenção(ões) encontrada(s).`);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) markSessionExpired();
      setMaintenanceMessage("Não foi possível carregar as manutenções.");
    }
  }, []);

  const loadDashboard = useCallback(async (signal) => {
    setDashboardMessage("Carregando indicadores...");
    try {
      const data = await fetchJson("/api/dashboard/summary", { signal });
      setDashboard(data);
      setDashboardMessage("Indicadores atualizados pelo backend.");
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) markSessionExpired();
      setDashboardMessage(error.status === 403 ? "Seu usuário não tem acesso ao painel gerencial." : "Não foi possível carregar os indicadores.");
    }
  }, []);

  const loadPlans = useCallback(async (signal) => {
    setPlanningMessage("Carregando planejamentos...");
    try {
      const data = await fetchJson("/api/maintenance-plans", { signal });
      setPlans(data.items);
      setPlanningMessage(`${data.total} planejamento(s) encontrado(s).`);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) markSessionExpired();
      setPlanningMessage(error.status === 403 ? "Seu usuário não tem acesso ao planejamento." : "Não foi possível carregar os planejamentos.");
    }
  }, []);

  const loadAlerts = useCallback(async (signal) => {
    setAlertMessage("Carregando alertas...");
    try {
      const data = await fetchJson("/api/alerts");
      setAlerts(data.items);
      setAlertMessage(`${data.total} alerta(s) encontrado(s).`);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) markSessionExpired();
      setAlertMessage(error.status === 403 ? "Seu usuário não tem acesso aos alertas." : "Não foi possível carregar os alertas.");
    }
  }, []);

  const loadReport = useCallback(async (signal) => {
    setReportMessage("Carregando relatório...");
    try {
      const [reportData, componentsData] = await Promise.all([
        fetchJson("/api/reports/inventory", { signal }),
        fetchJson("/api/components?limit=20", { signal }),
      ]);
      setReport(reportData);
      setComponentHistory(componentsData.items);
      setReportMessage("Relatório atualizado pelo backend.");
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) markSessionExpired();
      setReportMessage(error.status === 403 ? "Seu usuário não tem acesso aos relatórios." : "Não foi possível carregar o relatório.");
    }
  }, []);

  const loadPredictions = useCallback(async (signal) => {
    setPredictionMessage("Carregando previsões...");
    try {
      const [policiesData, predictionsData, monitoringData] = await Promise.all([
        fetchJson("/api/failure-predictions/policies", { signal }),
        fetchJson("/api/failure-predictions?limit=50", { signal }),
        fetchJson("/api/failure-predictions/monitoring", { signal }),
      ]);
      setPredictionPolicies(policiesData.items);
      setPredictions(predictionsData.items);
      setPredictionMonitoring(monitoringData);
      setPredictionMessage(`${predictionsData.total} recomendação(ões) carregada(s).`);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (error.status === 401) markSessionExpired();
      setPredictionMessage(error.status === 403 ? "Seu usuário não tem acesso às previsões." : "Não foi possível carregar as previsões.");
    }
  }, []);

  useEffect(() => {
    if (publicToken) return undefined;
    const controller = new AbortController();
    checkSession(controller.signal);
    loadEnvironments(controller.signal, "", "");
    loadEquipment(controller.signal, {}, 0);
    loadOccurrences(controller.signal, {});
    loadMaintenances(controller.signal);
    loadDashboard(controller.signal);
    loadPlans(controller.signal);
    loadAlerts(controller.signal);
    loadReport(controller.signal);
    loadPredictions(controller.signal);
    return () => controller.abort();
  }, [checkSession, loadEnvironments, loadEquipment, loadOccurrences, loadMaintenances, loadDashboard, loadPlans, loadAlerts, loadReport, loadPredictions, publicToken]);

  async function login(event) {
    event.preventDefault();
    setLoginState("loading");
    setLoginError("");
    try {
      const data = await fetchJson("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginForm),
      });
      setCurrentUser(data.user);
      setLoginForm({ auth_subject: "", password: "" });
      setLoginState("success");
      navigate("home");
      await Promise.all([
        loadEnvironments(undefined, environmentQuery, environmentActive),
        loadEquipment(undefined, equipmentFilters, equipmentOffset),
        loadOccurrences(undefined, occurrenceFilter),
        loadMaintenances(undefined),
        loadDashboard(undefined),
        loadPlans(undefined),
        loadAlerts(undefined),
        loadReport(undefined),
        loadPredictions(undefined),
      ]);
    } catch (error) {
      setLoginState("error");
      setLoginError("Não foi possível iniciar a sessão. Confira suas credenciais institucionais.");
    }
  }

  async function logout() {
    try {
      await fetchJson("/api/auth/logout", {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken() },
      });
    } catch {
      // A sessão também é removida da interface quando o servidor já a considera inválida.
    }
    setCurrentUser(null);
    setEnvironments([]);
    setEquipment([]);
    navigate("home");
  }

  async function createEnvironment(event) {
    event.preventDefault();
    setFormState("loading");
    try {
      await fetchJson(environmentEditId ? `/api/environments/${environmentEditId}` : "/api/environments", {
        method: environmentEditId ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify(environmentForm),
      });
      setFormState("success");
      setEnvironmentEditId(null);
      setEnvironmentForm({ code: "", name: "", kind: "classroom", active: true, reason: "Cadastro no catálogo institucional" });
      await loadEnvironments(undefined, environmentQuery, environmentActive);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setFormState(error.status === 409 ? "duplicate" : "error");
    }
  }

  function editEnvironment(environment) {
    setEnvironmentEditId(environment.id);
    setEnvironmentForm({
      code: environment.code,
      name: environment.name,
      kind: environment.kind,
      active: environment.active,
      reason: "Atualização do catálogo institucional",
    });
  }

  function cancelEnvironmentEdit() {
    setEnvironmentEditId(null);
    setEnvironmentForm({ code: "", name: "", kind: "classroom", active: true, reason: "Cadastro no catálogo institucional" });
  }

  async function createEquipment(event) {
    event.preventDefault();
    setFormState("loading");
    try {
      await fetchJson(equipmentEditId ? `/api/equipment/${equipmentEditId}` : "/api/equipment", {
        method: equipmentEditId ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({
          ...equipmentForm,
          asset_tag: equipmentForm.asset_tag || null,
          brand: equipmentForm.brand || null,
          model: equipmentForm.model || null,
          last_maintenance_on: equipmentForm.last_maintenance_on || null,
          next_maintenance_on: equipmentForm.next_maintenance_on || null,
        }),
      });
      setFormState("success");
      setEquipmentEditId(null);
      setEquipmentForm({ kind: "computer", asset_tag: "", brand: "", model: "", location_id: "", status: "active", last_maintenance_on: "", next_maintenance_on: "", reason: "Cadastro no inventário institucional" });
      await loadEquipment(undefined, equipmentFilters, equipmentOffset);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setFormState(error.status === 409 ? "duplicate" : "error");
    }
  }

  function editEquipment(item) {
    setEquipmentEditId(item.id);
    setEquipmentForm({
      kind: item.kind,
      asset_tag: item.asset_tag || "",
      brand: item.brand || "",
      model: item.model || "",
      location_id: item.location_id,
      status: item.status,
      last_maintenance_on: item.last_maintenance_on || "",
      next_maintenance_on: item.next_maintenance_on || "",
      reason: "Atualização do inventário institucional",
    });
  }

  function cancelEquipmentEdit() {
    setEquipmentEditId(null);
    setEquipmentForm({ kind: "computer", asset_tag: "", brand: "", model: "", location_id: "", status: "active", last_maintenance_on: "", next_maintenance_on: "", reason: "Cadastro no inventário institucional" });
  }

  async function inactivateEnvironment(environment) {
    setFormState("loading");
    try {
      await fetchJson(`/api/environments/${environment.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ active: false, reason: "Inativação pelo catálogo institucional" }),
      });
      setFormState("success");
      await loadEnvironments(undefined, environmentQuery, environmentActive);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setFormState(error.status === 403 ? "forbidden" : "error");
    }
  }

  async function inactivateEquipment(item) {
    setFormState("loading");
    try {
      await fetchJson(`/api/equipment/${item.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ status: "inactive", reason: "Inativação pelo inventário institucional" }),
      });
      setFormState("success");
      await loadEquipment(undefined, equipmentFilters, equipmentOffset);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setFormState(error.status === 403 ? "forbidden" : "error");
    }
  }

  async function loadPublicAccess(item) {
    try {
      const data = await fetchJson(`/api/equipment/${item.id}/public-access`);
      setPublicAccessEquipment(item);
      setPublicAccess(data);
      setPublicAccessMessage("");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPublicAccessMessage("Não foi possível carregar o link público.");
    }
  }

  async function changePublicAccess(action) {
    if (!publicAccessEquipment) return;
    try {
      const data = await fetchJson(`/api/equipment/${publicAccessEquipment.id}/public-access/${action}`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken() },
      });
      setPublicAccess(data);
      setPublicAccessMessage(action === "rotate" ? "Link anterior revogado e novo link gerado." : "Link público revogado.");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPublicAccessMessage(error.status === 403 ? "Operação não autorizada para este papel." : "Não foi possível alterar o link público.");
    }
  }

  async function createMovement(event) {
    event.preventDefault();
    try {
      await fetchJson(`/api/equipment/${movementForm.equipment_id}/movements`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({
          origin_environment_id: equipment.find((item) => item.id === movementForm.equipment_id)?.location_id,
          destination_environment_id: movementForm.destination_environment_id,
          reason: movementForm.reason,
        }),
      });
      setMovementMessage("Movimentação registrada com sucesso.");
      await Promise.all([
        loadMovements(undefined, movementForm.equipment_id),
        loadEquipment(undefined, equipmentFilters, equipmentOffset),
      ]);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setMovementMessage("Não foi possível registrar a movimentação.");
    }
  }

  function nextOccurrenceStatus(item) {
    return { open: "in_progress", in_progress: "resolved", resolved: "closed" }[item.status] || item.status;
  }

  async function advanceOccurrence(item) {
    const nextStatus = nextOccurrenceStatus(item);
    try {
      await fetchJson(`/api/occurrences/${item.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({
          status: nextStatus,
          resolution_reason: nextStatus === "closed" ? "Atendimento concluído pela equipe responsável." : null,
          reason: `Transição para ${nextStatus}`,
        }),
      });
      await loadOccurrences(undefined, occurrenceFilter);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setOccurrenceMessage("Não foi possível atualizar a ocorrência.");
    }
  }

  async function createMaintenance(event) {
    event.preventDefault();
    try {
      await fetchJson("/api/maintenances", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ ...maintenanceForm, occurrence_id: maintenanceForm.occurrence_id || null, scheduled_for: maintenanceForm.scheduled_for || null }),
      });
      setMaintenanceMessage("Manutenção aberta com sucesso.");
      await loadMaintenances(undefined);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setMaintenanceMessage("Não foi possível abrir a manutenção.");
    }
  }

  async function updateMaintenance(event) {
    event.preventDefault();
    try {
      await fetchJson(`/api/maintenances/${maintenanceUpdateForm.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({
          status: "completed",
          procedure: maintenanceUpdateForm.procedure,
          result: maintenanceUpdateForm.result,
          next_maintenance_on: maintenanceUpdateForm.next_maintenance_on || null,
          reason: maintenanceUpdateForm.reason,
        }),
      });
      setMaintenanceMessage("Manutenção concluída e inventário atualizado.");
      setMaintenanceUpdateForm({ id: "", procedure: "", result: "", next_maintenance_on: "", reason: "Conclusão de manutenção institucional" });
      await loadMaintenances(undefined);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setMaintenanceMessage("Não foi possível concluir a manutenção.");
    }
  }

  async function addComponent(event) {
    event.preventDefault();
    try {
      await fetchJson(`/api/maintenances/${componentForm.maintenance_id}/components`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ ...componentForm, quantity: Number(componentForm.quantity) }),
      });
      setMaintenanceMessage("Componente registrado no histórico.");
      setComponentForm({ maintenance_id: "", component_name: "", quantity: "1", observation: "", reason: "Registro de componente substituído" });
      await loadMaintenances(undefined);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setMaintenanceMessage("Não foi possível registrar o componente.");
    }
  }

  async function simulatePlan(event) {
    event.preventDefault();
    const monthlyCapacity = Number(planForm.capacity);
    const capacity_monthly = Object.fromEntries(Array.from({ length: 12 }, (_, index) => [String(index + 1), monthlyCapacity]));
    try {
      const data = await fetchJson("/api/maintenance-plans/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ year: Number(planForm.year), capacity_monthly, blackout_periods: [], reason: planForm.reason }),
      });
      setPlans((current) => [data, ...current]);
      setPlanningMessage("Simulação criada. Ela não altera agendas de manutenção até aprovação e publicação.");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPlanningMessage(error.status === 403 ? "Seu usuário não pode simular planejamentos." : "Não foi possível simular o planejamento.");
    }
  }

  async function changePlanStatus(plan, action) {
    try {
      const data = await fetchJson(`/api/maintenance-plans/${plan.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ reason: `${action === "approve" ? "Aprovação" : "Publicação"} humana do planejamento preventivo.` }),
      });
      setPlans((current) => current.map((item) => item.id === data.id ? data : item));
      setPlanningMessage(`Planejamento ${action === "approve" ? "aprovado" : "publicado"} com sucesso.`);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPlanningMessage("Não foi possível alterar o status do planejamento.");
    }
  }

  async function generateAlerts() {
    try {
      const data = await fetchJson("/api/alerts/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ upcoming_days: 30, reason: "Geração periódica de alertas de manutenção." }),
      });
      setAlerts(data.items);
      setAlertMessage(`${data.created} alerta(s) novo(s) gerado(s); reprocessamentos permanecem idempotentes.`);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setAlertMessage(error.status === 403 ? "Seu usuário não pode gerar alertas." : "Não foi possível gerar os alertas.");
    }
  }

  async function dispatchMockAlert(alert) {
    try {
      await fetchJson(`/api/alerts/${alert.id}/mock-dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ recipient_label: "ti-institucional-ficticio", reason: "Despacho controlado pelo mock de notificações." }),
      });
      await loadAlerts(undefined);
      setAlertMessage("Notificação registrada no provedor mock; nenhum e-mail real foi enviado.");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setAlertMessage("Não foi possível registrar a notificação mock.");
    }
  }

  async function createWarranty(event) {
    event.preventDefault();
    try {
      await fetchJson(`/api/equipment/${warrantyForm.equipment_id}/warranties`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ ...warrantyForm, ends_on: warrantyForm.ends_on || null }),
      });
      setWarrantyForm({ equipment_id: "", supplier: "", starts_on: "", ends_on: "", terms: "", reason: "Cadastro de garantia institucional" });
      setReportMessage("Garantia registrada sem alterar automaticamente a situação patrimonial.");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setReportMessage(error.status === 403 ? "Somente papéis autorizados podem registrar garantias." : "Não foi possível registrar a garantia.");
    }
  }

  async function createCost(event) {
    event.preventDefault();
    try {
      await fetchJson(`/api/maintenances/${costForm.maintenance_id}/costs`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ ...costForm, amount: costForm.amount.replace(",", ".") }),
      });
      setCostForm({ maintenance_id: "", amount: "", currency: "BRL", source: "", reference: "", note: "", reason: "Registro informativo de custo" });
      setReportMessage("Custo informativo registrado; o sistema não aprova nem paga despesas.");
      await loadReport(undefined);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setReportMessage(error.status === 403 ? "Somente o papel autorizado pode registrar custos." : "Não foi possível registrar o custo.");
    }
  }

  async function createPredictionPolicy() {
    try {
      const data = await fetchJson("/api/failure-predictions/policies", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({
          name: "baseline-falhas-institucional",
          version: 1,
          baseline_version: "deterministic-v1",
          horizon_days: 90,
          min_history_count: 2,
          min_confidence: 0.6,
          reason: "Criação controlada do baseline determinístico da SPEC-013.",
        }),
      });
      setPredictionPolicies((current) => [data, ...current]);
      setPredictionMessage("Baseline criado desabilitado. Avalie-o antes de ativar.");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPredictionMessage(error.status === 403 ? "Seu usuário não pode criar políticas." : "Não foi possível criar o baseline.");
    }
  }

  async function evaluatePredictionPolicy(policy) {
    try {
      await fetchJson("/api/failure-predictions/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({
          policy_id: policy.id,
          dataset_version: "synthetic-v1",
          approve_evaluation: true,
          reason: "Aprovação humana do conjunto sintético reproduzível da SPEC-013.",
        }),
      });
      await loadPredictions(undefined);
      setPredictionMessage("Avaliação reproduzível registrada; o baseline pode ser ativado explicitamente.");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPredictionMessage("Não foi possível avaliar o baseline.");
    }
  }

  async function changePredictionPolicy(policy, action) {
    try {
      await fetchJson(`/api/failure-predictions/policies/${policy.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ reason: `${action === "enable" ? "Ativação" : "Desativação"} humana da política de recomendações.` }),
      });
      await loadPredictions(undefined);
      setPredictionMessage(`Política ${action === "enable" ? "ativada" : "desativada"}; nenhuma agenda ou situação foi alterada.`);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPredictionMessage(error.status === 403 ? "Seu usuário não pode alterar a política." : "Não foi possível alterar a política.");
    }
  }

  async function runFailurePredictions(policy) {
    const action = policy.status === "enabled" ? "generate" : "simulate";
    try {
      const data = await fetchJson(`/api/failure-predictions/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ policy_id: policy.id, reason: "Execução controlada do baseline de recomendações." }),
      });
      setPredictions(data.items);
      setPredictionMessage(`${data.generated} recomendação(ões) nova(s); ${data.abstained} item(ns) em abstenção. Nenhuma mudança automática foi feita.`);
      await loadPredictions(undefined);
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPredictionMessage(error.status === 403 ? "Seu usuário não pode executar previsões." : "Não foi possível executar as previsões.");
    }
  }

  async function decideFailurePrediction(prediction, decision) {
    try {
      await fetchJson(`/api/failure-predictions/${prediction.id}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ decision, reason: `Decisão humana: ${decision}.` }),
      });
      await loadPredictions(undefined);
      setPredictionMessage("Decisão humana registrada na auditoria; o inventário não foi alterado.");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPredictionMessage("Não foi possível registrar a decisão humana.");
    }
  }

  async function notifyFailurePrediction(prediction) {
    try {
      await fetchJson(`/api/failure-predictions/${prediction.id}/mock-notify`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
        body: JSON.stringify({ confirm: true, recipient_label: "ti-institucional-ficticio", reason: "Confirmação humana da notificação mock." }),
      });
      setPredictionMessage("Notificação mock registrada; nenhum e-mail real foi enviado.");
    } catch (error) {
      if (error.status === 401) markSessionExpired();
      setPredictionMessage("Não foi possível registrar a notificação mock.");
    }
  }

  return (
    publicToken ? <PublicReportPage token={publicToken} /> : (
    <main className="page-shell">
      {currentUser && <nav className="app-nav" aria-label="Navegação principal">
        {pageItems.map(([page, label]) => <button key={page} className={`nav-button${activePage === page ? " active" : ""}`} type="button" aria-current={activePage === page ? "page" : undefined} onClick={() => navigate(page)}>{label}</button>)}
        <button className="nav-button nav-logout" type="button" onClick={logout}>Encerrar sessão</button>
      </nav>}

      {!currentUser && (
        <section className="catalog-panel login-panel" aria-labelledby="login-title">
          <p className="eyebrow">Acesso institucional</p>
          <h2 id="login-title">Entrar no inventário</h2>
          <p className="intro">Use suas credenciais institucionais. O acesso é validado pelo backend e não há cadastro público de contas.</p>
          <form className="login-form" onSubmit={login}>
            <label htmlFor="login-subject">Usuário institucional<input id="login-subject" name="auth_subject" autoComplete="username" required maxLength={255} value={loginForm.auth_subject} onChange={(event) => setLoginForm({ ...loginForm, auth_subject: event.target.value })} /></label>
            <label htmlFor="login-password">Senha<input id="login-password" name="password" type="password" autoComplete="current-password" required maxLength={1024} value={loginForm.password} onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })} /></label>
            {loginError && <p className="form-error" id="login-error" role="alert">{loginError}</p>}
            <button className="retry-button" type="submit" disabled={loginState === "loading"}>{loginState === "loading" ? "Entrando..." : "Entrar"}</button>
          </form>
        </section>
      )}

      {currentUser && (<>
      {activePage === "home" && <section className="catalog-panel dashboard-panel" aria-labelledby="dashboard-title">
        <p className="eyebrow">Painel institucional</p>
        <h2 id="dashboard-title">Visão geral</h2>
        <p className="intro">Indicadores calculados no backend, com data de referência e definições determinísticas.</p>
        <p className="catalog-message" role="status" aria-live="polite">{dashboardMessage}</p>
        {dashboard && <div className="dashboard-grid">
          <button className="dashboard-card" type="button" onClick={() => navigate("equipment")}><span>Total de equipamentos</span><strong>{dashboard.total_equipment}</strong><small>{dashboard.definitions.total_equipment}</small></button>
          <button className="dashboard-card" type="button" onClick={() => navigate("equipment")}><span>Em funcionamento</span><strong>{dashboard.functioning_equipment}</strong><small>{dashboard.definitions.functioning_equipment}</small></button>
          <button className="dashboard-card" type="button" onClick={() => navigate("maintenance")}><span>Em manutenção</span><strong>{dashboard.equipment_in_maintenance}</strong><small>{dashboard.definitions.equipment_in_maintenance}</small></button>
          <button className="dashboard-card" type="button" onClick={() => navigate("alerts")}><span>Manutenção atrasada</span><strong>{dashboard.overdue_maintenance}</strong><small>{dashboard.definitions.overdue_maintenance}</small></button>
          <button className="dashboard-card" type="button" onClick={() => navigate("occurrences")}><span>Ocorrências abertas</span><strong>{dashboard.open_occurrences}</strong><small>{dashboard.definitions.open_occurrences}</small></button>
          <button className="dashboard-card" type="button" onClick={() => navigate("planning")}><span>Próximas manutenções</span><strong>{dashboard.upcoming_maintenance}</strong><small>{dashboard.definitions.upcoming_maintenance}</small></button>
        </div>}
      </section>}

      {activePage === "environments" && <section className="catalog-panel" aria-labelledby="environment-title">
        <p className="eyebrow">Catálogo institucional</p>
        <h2 id="environment-title">Ambientes e localizações</h2>
        <p className="intro">Cadastre salas, laboratórios e setores sem apagar históricos patrimoniais.</p>
        <form className="environment-form" onSubmit={createEnvironment}>
          <div className="form-grid">
            <label htmlFor="environment-code">Código institucional<input id="environment-code" required maxLength={64} value={environmentForm.code} onChange={(event) => setEnvironmentForm({ ...environmentForm, code: event.target.value })} /></label>
            <label htmlFor="environment-name">Nome do ambiente<input id="environment-name" required maxLength={160} value={environmentForm.name} onChange={(event) => setEnvironmentForm({ ...environmentForm, name: event.target.value })} /></label>
            <label htmlFor="environment-kind">Tipo<input id="environment-kind" required maxLength={64} list="environment-kind-options" value={environmentForm.kind} onChange={(event) => setEnvironmentForm({ ...environmentForm, kind: event.target.value })} /><datalist id="environment-kind-options">{minimumEnvironmentKinds.map(([value, label]) => <option key={value} value={value} label={label} />)}</datalist></label>
            {environmentEditId && <label htmlFor="environment-active">Situação<select id="environment-active" value={environmentForm.active ? "true" : "false"} onChange={(event) => setEnvironmentForm({ ...environmentForm, active: event.target.value === "true" })}><option value="true">Ativo</option><option value="false">Inativo</option></select></label>}
            <label htmlFor="environment-reason">Justificativa<input id="environment-reason" required minLength={3} maxLength={500} value={environmentForm.reason} onChange={(event) => setEnvironmentForm({ ...environmentForm, reason: event.target.value })} /></label>
          </div>
          <div className="form-actions">
            <button className="retry-button" type="submit" disabled={formState === "loading"}>{environmentEditId ? "Salvar alterações" : "Cadastrar ambiente"}</button>
            {environmentEditId && <button className="secondary-button" type="button" onClick={cancelEnvironmentEdit}>Cancelar edição</button>}
          </div>
        </form>
        <form className="search-form" onSubmit={(event) => { event.preventDefault(); loadEnvironments(undefined, environmentQuery, environmentActive); }}>
          <label htmlFor="environment-search">Pesquisar por código, nome ou tipo</label>
          <div className="search-row"><input id="environment-search" value={environmentQuery} onChange={(event) => setEnvironmentQuery(event.target.value)} /><select id="environment-active-filter" aria-label="Filtrar por situação" value={environmentActive} onChange={(event) => setEnvironmentActive(event.target.value)}><option value="">Todas as situações</option><option value="true">Ativos</option><option value="false">Inativos</option></select><button className="secondary-button" type="submit">Pesquisar</button></div>
        </form>
        <p className="catalog-message" role="status" aria-live="polite">{environmentMessage}{formState === "duplicate" && " Código já cadastrado."}{formState === "forbidden" && " Operação não autorizada."}</p>
        <ul className="environment-list" aria-label="Ambientes cadastrados">{environments.map((environment) => <li key={environment.id} className="environment-item"><div><strong>{environment.code} — {environment.name}</strong><span>{environment.kind} · {environment.active ? "Ativo" : "Inativo"}</span></div><div className="item-actions"><button className="secondary-button" type="button" onClick={() => editEnvironment(environment)}>Editar</button>{environment.active && <button className="secondary-button" type="button" onClick={() => inactivateEnvironment(environment)}>Inativar</button>}</div></li>)}</ul>
       </section>}

       {activePage === "equipment" && <section className="catalog-panel" aria-labelledby="equipment-title">
        <p className="eyebrow">SPEC-004</p>
        <h2 id="equipment-title">Cadastro e inventário de equipamentos</h2>
        <p className="intro">Registre equipamentos, associe-os a um ambiente ativo e preserve o histórico de alterações.</p>
        <form className="equipment-form" onSubmit={createEquipment}>
          <div className="form-grid">
            <label htmlFor="equipment-kind">Tipo<select id="equipment-kind" required value={equipmentForm.kind} onChange={(event) => setEquipmentForm({ ...equipmentForm, kind: event.target.value })}>{equipmentKinds.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label htmlFor="equipment-asset-tag">Número de patrimônio (opcional)<input id="equipment-asset-tag" maxLength={80} value={equipmentForm.asset_tag} onChange={(event) => setEquipmentForm({ ...equipmentForm, asset_tag: event.target.value })} /></label>
            <label htmlFor="equipment-brand">Marca (opcional)<input id="equipment-brand" maxLength={100} value={equipmentForm.brand} onChange={(event) => setEquipmentForm({ ...equipmentForm, brand: event.target.value })} /></label>
            <label htmlFor="equipment-model">Modelo (opcional)<input id="equipment-model" maxLength={100} value={equipmentForm.model} onChange={(event) => setEquipmentForm({ ...equipmentForm, model: event.target.value })} /></label>
            <label htmlFor="equipment-location">Localização<select id="equipment-location" required value={equipmentForm.location_id} onChange={(event) => setEquipmentForm({ ...equipmentForm, location_id: event.target.value })}><option value="">Selecione um ambiente ativo</option>{environments.filter((environment) => environment.active).map((environment) => <option key={environment.id} value={environment.id}>{environment.code} — {environment.name}</option>)}</select></label>
            {equipmentEditId && <label htmlFor="equipment-status">Situação<select id="equipment-status" value={equipmentForm.status} onChange={(event) => setEquipmentForm({ ...equipmentForm, status: event.target.value })}>{equipmentStatuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>}
            <label htmlFor="equipment-last-maintenance">Última manutenção<input id="equipment-last-maintenance" type="date" value={equipmentForm.last_maintenance_on} onChange={(event) => setEquipmentForm({ ...equipmentForm, last_maintenance_on: event.target.value })} /></label>
            <label htmlFor="equipment-next-maintenance">Próxima manutenção<input id="equipment-next-maintenance" type="date" value={equipmentForm.next_maintenance_on} onChange={(event) => setEquipmentForm({ ...equipmentForm, next_maintenance_on: event.target.value })} /></label>
            <label htmlFor="equipment-reason">Justificativa<input id="equipment-reason" required minLength={3} maxLength={500} value={equipmentForm.reason} onChange={(event) => setEquipmentForm({ ...equipmentForm, reason: event.target.value })} /></label>
          </div>
          <div className="form-actions">
            <button className="retry-button" type="submit" disabled={formState === "loading"}>{equipmentEditId ? "Salvar alterações" : "Cadastrar equipamento"}</button>
            {equipmentEditId && <button className="secondary-button" type="button" onClick={cancelEquipmentEdit}>Cancelar edição</button>}
          </div>
        </form>
        <form className="equipment-filter-form" onSubmit={(event) => { event.preventDefault(); setEquipmentOffset(0); loadEquipment(undefined, equipmentFilters, 0); }}>
          <div className="form-grid">
            <label htmlFor="equipment-search">Pesquisar patrimônio, marca ou modelo<input id="equipment-search" value={equipmentFilters.search} onChange={(event) => setEquipmentFilters({ ...equipmentFilters, search: event.target.value })} /></label>
            <label htmlFor="equipment-filter-kind">Filtrar por tipo<select id="equipment-filter-kind" value={equipmentFilters.kind} onChange={(event) => setEquipmentFilters({ ...equipmentFilters, kind: event.target.value })}><option value="">Todos os tipos</option>{equipmentKinds.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label htmlFor="equipment-filter-status">Filtrar por situação<select id="equipment-filter-status" value={equipmentFilters.status} onChange={(event) => setEquipmentFilters({ ...equipmentFilters, status: event.target.value })}><option value="">Todas as situações</option>{equipmentStatuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label htmlFor="equipment-filter-location">Filtrar por localização<select id="equipment-filter-location" value={equipmentFilters.location_id} onChange={(event) => setEquipmentFilters({ ...equipmentFilters, location_id: event.target.value })}><option value="">Todas as localizações</option>{environments.map((environment) => <option key={environment.id} value={environment.id}>{environment.code} — {environment.name}</option>)}</select></label>
          </div>
          <button className="secondary-button" type="submit">Pesquisar inventário</button>
        </form>
        <p className="catalog-message" role="status" aria-live="polite">{equipmentMessage}{formState === "duplicate" && " Patrimônio já cadastrado."}{formState === "forbidden" && " Operação não autorizada."}</p>
        <div className="pagination-actions" aria-label="Paginação do inventário"><button className="secondary-button" type="button" disabled={equipmentOffset === 0} onClick={() => { const nextOffset = Math.max(0, equipmentOffset - equipmentLimit); setEquipmentOffset(nextOffset); loadEquipment(undefined, equipmentFilters, nextOffset); }}>Anterior</button><span>Exibindo {equipmentTotal === 0 ? 0 : equipmentOffset + 1}–{Math.min(equipmentOffset + equipmentLimit, equipmentTotal)} de {equipmentTotal}</span><button className="secondary-button" type="button" disabled={equipmentOffset + equipmentLimit >= equipmentTotal} onClick={() => { const nextOffset = equipmentOffset + equipmentLimit; setEquipmentOffset(nextOffset); loadEquipment(undefined, equipmentFilters, nextOffset); }}>Próxima</button></div>
        <ul className="equipment-list" aria-label="Equipamentos cadastrados">{equipment.map((item) => <li key={item.id} className="equipment-item"><div><strong>{item.asset_tag || "Sem patrimônio"} — {labelFor(equipmentKinds, item.kind)}</strong><span>{[item.brand, item.model].filter(Boolean).join(" · ") || "Sem marca/modelo"} · {labelFor(equipmentStatuses, item.status)} · {item.occurrence_count} ocorrência(s) · {item.maintenance_count} manutenção(ões)</span></div><div className="item-actions"><button className="secondary-button" type="button" onClick={() => editEquipment(item)}>Editar</button><button className="secondary-button" type="button" onClick={() => loadPublicAccess(item)}>Link/QR público</button>{item.status !== "inactive" && <button className="secondary-button" type="button" onClick={() => inactivateEquipment(item)}>Inativar</button>}</div></li>)}</ul>
        {publicAccess && publicAccessEquipment && <aside className="public-access-card" aria-labelledby="public-access-title"><h3 id="public-access-title">Comunicação pública — {publicAccessEquipment.asset_tag || "equipamento selecionado"}</h3><p className="catalog-message" role="status" aria-live="polite">{publicAccessMessage || (publicAccess.revoked ? "Este link está revogado." : "Compartilhe o link ou o QR Code para receber comunicações.")}</p><a href={publicAccess.public_url} target="_blank" rel="noreferrer">{publicAccess.public_url}</a><img className="public-qr" src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(publicAccess.qr_svg)}`} alt="QR Code para comunicação pública do equipamento" /><div className="form-actions"><button className="secondary-button" type="button" onClick={() => changePublicAccess("rotate")}>Rotacionar link</button>{!publicAccess.revoked && <button className="secondary-button" type="button" onClick={() => changePublicAccess("revoke")}>Revogar link</button>}</div></aside>}
       </section>}

       {activePage === "movements" && <section className="catalog-panel" aria-labelledby="movement-title">
        <p className="eyebrow">SPEC-005</p>
        <h2 id="movement-title">Movimentação e rastreabilidade</h2>
        <form className="equipment-form" onSubmit={createMovement}>
          <div className="form-grid">
            <label htmlFor="movement-equipment">Equipamento<select id="movement-equipment" required value={movementForm.equipment_id} onChange={(event) => { const equipmentId = event.target.value; setMovementForm({ ...movementForm, equipment_id: equipmentId, destination_environment_id: "" }); loadMovements(undefined, equipmentId); }}><option value="">Selecione um equipamento</option>{equipment.map((item) => <option key={item.id} value={item.id}>{item.asset_tag || item.id} — {labelFor(equipmentKinds, item.kind)}</option>)}</select></label>
            <label htmlFor="movement-destination">Destino ativo<select id="movement-destination" required value={movementForm.destination_environment_id} onChange={(event) => setMovementForm({ ...movementForm, destination_environment_id: event.target.value })}><option value="">Selecione o destino</option>{environments.filter((environment) => environment.active).map((environment) => <option key={environment.id} value={environment.id}>{environment.code} — {environment.name}</option>)}</select></label>
            <label htmlFor="movement-reason">Justificativa<input id="movement-reason" required minLength={3} maxLength={500} value={movementForm.reason} onChange={(event) => setMovementForm({ ...movementForm, reason: event.target.value })} /></label>
          </div>
          <button className="retry-button" type="submit">Registrar movimentação</button>
        </form>
        <p className="catalog-message" role="status" aria-live="polite">{movementMessage}</p>
        <ul className="equipment-list" aria-label="Linha do tempo de movimentações">{movements.map((movement) => <li key={movement.id} className="equipment-item"><div><strong>{movement.origin_environment_id} → {movement.destination_environment_id}</strong><span>{movement.reason} · ator {movement.moved_by_id} · {new Date(movement.created_at).toLocaleString()}</span></div></li>)}</ul>
       </section>}

       {activePage === "occurrences" && <section className="catalog-panel" aria-labelledby="occurrence-title">
        <p className="eyebrow">SPEC-007</p>
        <h2 id="occurrence-title">Ocorrências e chamados</h2>
        <form className="search-form" onSubmit={(event) => { event.preventDefault(); loadOccurrences(undefined, occurrenceFilter); }}>
          <div className="form-grid">
            <label htmlFor="occurrence-status">Status<select id="occurrence-status" value={occurrenceFilter.status} onChange={(event) => setOccurrenceFilter({ ...occurrenceFilter, status: event.target.value })}><option value="">Todos</option>{["open", "in_progress", "resolved", "closed"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
            <label htmlFor="occurrence-priority">Prioridade<select id="occurrence-priority" value={occurrenceFilter.priority} onChange={(event) => setOccurrenceFilter({ ...occurrenceFilter, priority: event.target.value })}><option value="">Todas</option>{["low", "normal", "high", "urgent"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          </div>
          <button className="secondary-button" type="submit">Filtrar ocorrências</button>
        </form>
        <p className="catalog-message" role="status" aria-live="polite">{occurrenceMessage}</p>
        <ul className="equipment-list" aria-label="Ocorrências cadastradas">{occurrences.map((item) => <li key={item.id} className="equipment-item"><div><strong>{item.status} · {item.priority}</strong><span>{item.description} · equipamento {item.equipment_id}</span></div>{item.status !== "closed" && <button className="secondary-button" type="button" onClick={() => advanceOccurrence(item)}>Avançar status</button>}</li>)}</ul>
       </section>}

       {activePage === "maintenance" && <section className="catalog-panel" aria-labelledby="maintenance-title">
        <p className="eyebrow">SPEC-008</p>
        <h2 id="maintenance-title">Manutenções e componentes</h2>
        <form className="equipment-form" onSubmit={createMaintenance}>
          <div className="form-grid">
            <label htmlFor="maintenance-equipment">Equipamento<select id="maintenance-equipment" required value={maintenanceForm.equipment_id} onChange={(event) => setMaintenanceForm({ ...maintenanceForm, equipment_id: event.target.value })}><option value="">Selecione um equipamento</option>{equipment.map((item) => <option key={item.id} value={item.id}>{item.asset_tag || item.id}</option>)}</select></label>
            <label htmlFor="maintenance-kind">Tipo<select id="maintenance-kind" value={maintenanceForm.kind} onChange={(event) => setMaintenanceForm({ ...maintenanceForm, kind: event.target.value })}><option value="preventive">Preventiva</option><option value="corrective">Corretiva</option></select></label>
            <label htmlFor="maintenance-occurrence">Ocorrência vinculada (opcional)<select id="maintenance-occurrence" value={maintenanceForm.occurrence_id} onChange={(event) => setMaintenanceForm({ ...maintenanceForm, occurrence_id: event.target.value })}><option value="">Nenhuma</option>{occurrences.filter((item) => item.equipment_id === maintenanceForm.equipment_id && item.status !== "closed").map((item) => <option key={item.id} value={item.id}>{item.priority} · {item.description.slice(0, 70)}</option>)}</select></label>
            <label htmlFor="maintenance-scheduled">Agendada para<input id="maintenance-scheduled" type="date" value={maintenanceForm.scheduled_for} onChange={(event) => setMaintenanceForm({ ...maintenanceForm, scheduled_for: event.target.value })} /></label>
            <label htmlFor="maintenance-reason">Justificativa<input id="maintenance-reason" required minLength={3} maxLength={500} value={maintenanceForm.reason} onChange={(event) => setMaintenanceForm({ ...maintenanceForm, reason: event.target.value })} /></label>
          </div>
          <button className="retry-button" type="submit">Abrir manutenção</button>
        </form>
        {maintenanceUpdateForm.id && <form className="equipment-form" onSubmit={updateMaintenance}><h3>Concluir manutenção</h3><div className="form-grid"><label htmlFor="maintenance-procedure">Procedimento realizado<textarea id="maintenance-procedure" required minLength={3} maxLength={5000} rows={4} value={maintenanceUpdateForm.procedure} onChange={(event) => setMaintenanceUpdateForm({ ...maintenanceUpdateForm, procedure: event.target.value })} /></label><label htmlFor="maintenance-result">Resultado<textarea id="maintenance-result" required minLength={3} maxLength={5000} rows={4} value={maintenanceUpdateForm.result} onChange={(event) => setMaintenanceUpdateForm({ ...maintenanceUpdateForm, result: event.target.value })} /></label><label htmlFor="maintenance-next-date">Próxima manutenção<input id="maintenance-next-date" type="date" value={maintenanceUpdateForm.next_maintenance_on} onChange={(event) => setMaintenanceUpdateForm({ ...maintenanceUpdateForm, next_maintenance_on: event.target.value })} /></label></div><button className="retry-button" type="submit">Concluir manutenção</button></form>}
        {componentForm.maintenance_id && <form className="equipment-form" onSubmit={addComponent}><h3>Registrar componente substituído</h3><div className="form-grid"><label htmlFor="component-name">Componente<input id="component-name" required maxLength={160} value={componentForm.component_name} onChange={(event) => setComponentForm({ ...componentForm, component_name: event.target.value })} /></label><label htmlFor="component-quantity">Quantidade<input id="component-quantity" type="number" min="1" max="100000" required value={componentForm.quantity} onChange={(event) => setComponentForm({ ...componentForm, quantity: event.target.value })} /></label><label htmlFor="component-observation">Observação<textarea id="component-observation" maxLength={2000} rows={3} value={componentForm.observation} onChange={(event) => setComponentForm({ ...componentForm, observation: event.target.value })} /></label></div><button className="retry-button" type="submit">Registrar componente</button></form>}
        <p className="catalog-message" role="status" aria-live="polite">{maintenanceMessage}</p>
        <ul className="equipment-list" aria-label="Manutenções cadastradas">{maintenances.map((item) => <li key={item.id} className="equipment-item"><div><strong>{item.kind} · {item.status}</strong><span>equipamento {item.equipment_id} · {item.components.length} componente(s)</span></div><div className="item-actions">{item.status === "planned" && <button className="secondary-button" type="button" onClick={async () => { await fetchJson(`/api/maintenances/${item.id}`, { method: "PATCH", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() }, body: JSON.stringify({ status: "in_progress", reason: "Início da manutenção" }) }); await loadMaintenances(undefined); }}>Iniciar</button>}{item.status === "in_progress" && <button className="secondary-button" type="button" onClick={() => setMaintenanceUpdateForm({ ...maintenanceUpdateForm, id: item.id })}>Concluir</button>}<button className="secondary-button" type="button" onClick={() => setComponentForm({ ...componentForm, maintenance_id: item.id })}>Componente</button></div></li>)}</ul>
       </section>}

       {activePage === "planning" && <section className="catalog-panel" aria-labelledby="planning-title">
         <p className="eyebrow">SPEC-009</p>
         <h2 id="planning-title">Planejamento preventivo anual</h2>
         <p className="intro">Simule uma distribuição determinística para computadores. A simulação não publica nem altera agendas automaticamente.</p>
         <form className="equipment-form" onSubmit={simulatePlan}>
           <div className="form-grid">
             <label htmlFor="plan-year">Ano<input id="plan-year" type="number" min="2020" max="2100" required value={planForm.year} onChange={(event) => setPlanForm({ ...planForm, year: event.target.value })} /></label>
             <label htmlFor="plan-capacity">Capacidade mensal<input id="plan-capacity" type="number" min="0" max="10000" required value={planForm.capacity} onChange={(event) => setPlanForm({ ...planForm, capacity: event.target.value })} /></label>
             <label htmlFor="plan-reason">Justificativa<input id="plan-reason" required minLength={3} maxLength={500} value={planForm.reason} onChange={(event) => setPlanForm({ ...planForm, reason: event.target.value })} /></label>
           </div>
           <button className="retry-button" type="submit">Simular planejamento</button>
         </form>
         <p className="catalog-message" role="status" aria-live="polite">{planningMessage}</p>
         <ul className="equipment-list" aria-label="Planejamentos preventivos">{plans.map((plan) => <li key={plan.id} className="equipment-item"><div><strong>{plan.year} · versão {plan.version} · {plan.status}</strong><span>{plan.summary?.planned || 0} planejado(s), {plan.summary?.conflicts || 0} conflito(s) · criado em {new Date(plan.created_at).toLocaleString()}</span></div><div className="item-actions">{plan.status === "simulated" && <button className="secondary-button" type="button" onClick={() => changePlanStatus(plan, "approve")}>Aprovar</button>}{plan.status === "approved" && <button className="secondary-button" type="button" onClick={() => changePlanStatus(plan, "publish")}>Publicar</button>}</div></li>)}</ul>
       </section>}

       {activePage === "alerts" && <section className="catalog-panel" aria-labelledby="alerts-title">
         <p className="eyebrow">SPEC-010</p>
         <h2 id="alerts-title">Alertas e notificações</h2>
         <p className="intro">Gere alertas de manutenção próxima ou vencida. O despacho usa somente o provedor mock e não envia e-mail real.</p>
         <button className="retry-button" type="button" onClick={generateAlerts}>Gerar alertas dos próximos 30 dias</button>
         <p className="catalog-message" role="status" aria-live="polite">{alertMessage}</p>
         <ul className="equipment-list" aria-label="Alertas de manutenção">{alerts.map((alert) => <li key={alert.id} className="equipment-item"><div><strong>{alert.kind === "overdue" ? "Atrasado" : "Próximo"} · {alert.status}</strong><span>equipamento {alert.equipment_id} · data {alert.due_on} · chave idempotente {alert.idempotency_key}</span></div>{alert.status === "open" && <button className="secondary-button" type="button" onClick={() => dispatchMockAlert(alert)}>Despachar mock</button>}</li>)}</ul>
       </section>}

       {activePage === "predictions" && <section className="catalog-panel" aria-labelledby="predictions-title">
         <p className="eyebrow">SPEC-013</p>
         <h2 id="predictions-title">Previsões e recomendações</h2>
         <p className="intro">O baseline é determinístico e falível. Resultados podem entrar em abstenção, exigem decisão humana e nunca alteram automaticamente o inventário, a agenda ou a prioridade.</p>
         <p className="catalog-message" role="status" aria-live="polite">{predictionMessage}</p>
         {predictionMonitoring && <div className="report-summary"><div><strong>{predictionMonitoring.recommendation_count}</strong><span>recomendações</span></div><div><strong>{predictionMonitoring.abstention_count}</strong><span>abstenções</span></div><div><strong>{predictionMonitoring.confirmed_count}</strong><span>confirmadas</span></div><div><strong>{predictionMonitoring.rejected_count}</strong><span>rejeitadas</span></div></div>}
         {predictionPolicies.length === 0 && currentUser.permissions?.includes("prediction:manage") && <button className="retry-button" type="button" onClick={createPredictionPolicy}>Criar baseline determinístico</button>}
         {predictionPolicies.map((policy) => <article key={policy.id} className="prediction-policy">
           <div className="prediction-policy-header"><div><h3>{policy.name} · v{policy.version}</h3><p>{policy.baseline_version} · janela {policy.horizon_days} dias · status {policy.status}</p></div><div className="item-actions">
             {currentUser.permissions?.includes("prediction:manage") && !policy.evaluation_approved && <button className="secondary-button" type="button" onClick={() => evaluatePredictionPolicy(policy)}>Avaliar baseline</button>}
             {currentUser.permissions?.includes("prediction:manage") && policy.evaluation_approved && policy.status !== "enabled" && <button className="secondary-button" type="button" onClick={() => changePredictionPolicy(policy, "enable")}>Ativar</button>}
             {currentUser.permissions?.includes("prediction:manage") && policy.status === "enabled" && <button className="secondary-button" type="button" onClick={() => changePredictionPolicy(policy, "disable")}>Desativar</button>}
             {currentUser.permissions?.includes("prediction:write") && <button className="secondary-button" type="button" onClick={() => runFailurePredictions(policy)}>{policy.status === "enabled" ? "Gerar recomendações" : "Simular recomendações"}</button>}
           </div></div>
           {policy.evaluation_summary && <p className="catalog-message">Avaliação {policy.evaluation_summary.metrics?.dataset_version || "synthetic-v1"}: precisão {policy.evaluation_summary.heuristic_precision ?? "n/d"}, recall {policy.evaluation_summary.heuristic_recall ?? "n/d"}, aprovada {policy.evaluation_approved ? "sim" : "não"}. Conjunto sintético, sem dados pessoais.</p>}
         </article>)}
         <h3 className="subsection-title">Recomendações auditáveis</h3>
         <ul className="equipment-list" aria-label="Recomendações de falha">{predictions.map((prediction) => <li key={prediction.id} className="equipment-item"><div><strong>{prediction.risk_level === "abstain" ? "Abstenção" : `Risco ${prediction.risk_level}`} · confiança {(prediction.confidence * 100).toFixed(0)}% · {prediction.status}</strong><span>equipamento {prediction.equipment_id} · score {(prediction.score * 100).toFixed(0)}% · {prediction.rationale.explanation}</span><small>Ocorrências: {prediction.feature_snapshot.occurrence_count} · corretivas: {prediction.feature_snapshot.corrective_maintenance_count} · próxima manutenção vencida: {prediction.feature_snapshot.maintenance_overdue ? "sim" : "não"}</small></div>{prediction.status === "recommended" && currentUser.permissions?.includes("prediction:write") && <div className="item-actions"><button className="secondary-button" type="button" onClick={() => decideFailurePrediction(prediction, "confirmed")}>Confirmar recomendação</button><button className="secondary-button" type="button" onClick={() => decideFailurePrediction(prediction, "rejected")}>Rejeitar</button></div>}{prediction.status === "confirmed" && currentUser.permissions?.includes("prediction:write") && <button className="secondary-button" type="button" onClick={() => notifyFailurePrediction(prediction)}>Notificar mock</button>}</li>)}</ul>
       </section>}

       {activePage === "reports" && <section className="catalog-panel" aria-labelledby="reports-title">
         <p className="eyebrow">SPEC-012</p>
         <h2 id="reports-title">Garantias, custos e relatórios</h2>
         <p className="intro">Registros financeiros são informativos. O sistema não autoriza compras, pagamentos ou despesas.</p>
         <div className="report-toolbar"><button className="secondary-button" type="button" onClick={() => loadReport(undefined)}>Atualizar relatório</button><a className="secondary-button report-link" href={`${apiBaseUrl}/api/reports/inventory.csv`} target="_blank" rel="noreferrer">Exportar CSV auditado</a></div>
         <p className="catalog-message" role="status" aria-live="polite">{reportMessage}</p>
         {report && <div className="report-summary"><div><strong>{report.equipment_count}</strong><span>equipamentos</span></div><div><strong>{report.maintenance_count}</strong><span>manutenções</span></div><div><strong>{report.component_count}</strong><span>componentes</span></div><div><strong>{report.warranty_count}</strong><span>garantias</span></div><div><strong>R$ {report.total_cost.toFixed(2)}</strong><span>custos informativos</span></div></div>}
         <form className="equipment-form" onSubmit={createWarranty}><h3>Registrar garantia</h3><div className="form-grid"><label htmlFor="warranty-equipment">Equipamento<select id="warranty-equipment" required value={warrantyForm.equipment_id} onChange={(event) => setWarrantyForm({ ...warrantyForm, equipment_id: event.target.value })}><option value="">Selecione</option>{equipment.map((item) => <option key={item.id} value={item.id}>{item.asset_tag || item.id}</option>)}</select></label><label htmlFor="warranty-supplier">Fornecedor<input id="warranty-supplier" required maxLength={160} value={warrantyForm.supplier} onChange={(event) => setWarrantyForm({ ...warrantyForm, supplier: event.target.value })} /></label><label htmlFor="warranty-start">Início<input id="warranty-start" type="date" required value={warrantyForm.starts_on} onChange={(event) => setWarrantyForm({ ...warrantyForm, starts_on: event.target.value })} /></label><label htmlFor="warranty-end">Fim<input id="warranty-end" type="date" value={warrantyForm.ends_on} onChange={(event) => setWarrantyForm({ ...warrantyForm, ends_on: event.target.value })} /></label><label htmlFor="warranty-terms">Condições<textarea id="warranty-terms" rows={3} maxLength={5000} value={warrantyForm.terms} onChange={(event) => setWarrantyForm({ ...warrantyForm, terms: event.target.value })} /></label></div><button className="retry-button" type="submit">Registrar garantia</button></form>
         <form className="equipment-form" onSubmit={createCost}><h3>Registrar custo informativo</h3><div className="form-grid"><label htmlFor="cost-maintenance">Manutenção<select id="cost-maintenance" required value={costForm.maintenance_id} onChange={(event) => setCostForm({ ...costForm, maintenance_id: event.target.value })}><option value="">Selecione</option>{maintenances.map((item) => <option key={item.id} value={item.id}>{item.kind} · {item.id}</option>)}</select></label><label htmlFor="cost-amount">Valor<input id="cost-amount" required inputMode="decimal" value={costForm.amount} onChange={(event) => setCostForm({ ...costForm, amount: event.target.value })} /></label><label htmlFor="cost-currency">Moeda<input id="cost-currency" required maxLength={3} value={costForm.currency} onChange={(event) => setCostForm({ ...costForm, currency: event.target.value.toUpperCase() })} /></label><label htmlFor="cost-source">Origem<input id="cost-source" required maxLength={255} value={costForm.source} onChange={(event) => setCostForm({ ...costForm, source: event.target.value })} /></label><label htmlFor="cost-reference">Referência<input id="cost-reference" maxLength={255} value={costForm.reference} onChange={(event) => setCostForm({ ...costForm, reference: event.target.value })} /></label><label htmlFor="cost-note">Observação<textarea id="cost-note" rows={3} maxLength={2000} value={costForm.note} onChange={(event) => setCostForm({ ...costForm, note: event.target.value })} /></label></div><button className="retry-button" type="submit">Registrar custo</button></form>
         <h3 className="subsection-title">Histórico de componentes</h3><ul className="equipment-list" aria-label="Histórico de componentes">{componentHistory.map((item) => <li key={item.id} className="equipment-item"><div><strong>{item.component_name} · quantidade {item.quantity}</strong><span>manutenção {item.maintenance_id} · equipamento {item.equipment_id} · {item.observation || "Sem observação"}</span></div></li>)}</ul>
       </section>}
       </>)}
    </main>
    )
  );
}

export default App;
