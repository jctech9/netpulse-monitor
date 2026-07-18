import type { DashboardData, HistoryDocument, IncidentsDocument, StatusDocument } from "../types/contracts";

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function assertBase(value: unknown, name: string): asserts value is Record<string, unknown> {
  if (!isObject(value) || value.schema_version !== 1 || typeof value.generated_at !== "string") {
    throw new Error(`${name} possui formato incompatível.`);
  }
}

export function parseDocuments(status: unknown, history: unknown, incidents: unknown): DashboardData {
  assertBase(status, "status.json");
  assertBase(history, "history.json");
  assertBase(incidents, "incidents.json");
  if (!Array.isArray(status.monitors) || typeof status.counts !== "object") {
    throw new Error("status.json não contém monitores válidos.");
  }
  if (!isObject(history.monitors)) {
    throw new Error("history.json não contém histórico válido.");
  }
  if (!Array.isArray(incidents.incidents)) {
    throw new Error("incidents.json não contém incidentes válidos.");
  }
  return {
    status: status as unknown as StatusDocument,
    history: history as unknown as HistoryDocument,
    incidents: incidents as unknown as IncidentsDocument,
  };
}

async function fetchJson(file: string, signal?: AbortSignal): Promise<unknown> {
  const base = import.meta.env.BASE_URL;
  const url = `${base}data/${file}?v=${Date.now()}`;
  const response = await fetch(url, { cache: "no-store", signal });
  if (!response.ok) throw new Error(`Não foi possível carregar ${file} (HTTP ${response.status}).`);
  return response.json();
}

export async function fetchDashboard(signal?: AbortSignal): Promise<DashboardData> {
  const [status, history, incidents] = await Promise.all([
    fetchJson("status.json", signal),
    fetchJson("history.json", signal),
    fetchJson("incidents.json", signal),
  ]);
  return parseDocuments(status, history, incidents);
}
