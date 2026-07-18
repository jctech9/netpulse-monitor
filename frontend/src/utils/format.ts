import type { MonitorStatus, OverallStatus } from "../types/contracts";

export const statusLabels: Record<MonitorStatus, string> = {
  up: "Online",
  degraded: "Instável",
  down: "Offline",
  maintenance: "Manutenção",
  unknown: "Sem dados",
};

export const overallLabels: Record<OverallStatus, string> = {
  operational: "Todos os sistemas operacionais",
  degraded: "Operação parcialmente degradada",
  major_outage: "Indisponibilidade generalizada",
  unknown: "Aguardando dados válidos",
};

export function formatLatency(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  if (value >= 1000) return `${(value / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} s`;
  return `${Math.round(value).toLocaleString("pt-BR")} ms`;
}

export function formatUptime(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 3 })}%`;
}

export function formatDate(value: string | null, timezone: string, includeDate = false): string {
  if (!value) return "Aguardando";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Data inválida";
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: timezone,
    day: includeDate ? "2-digit" : undefined,
    month: includeDate ? "short" : undefined,
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function relativeTime(value: string | null): string {
  if (!value) return "nunca";
  const diff = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "agora";
  if (minutes < 60) return `há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `há ${hours} h`;
  return `há ${Math.floor(hours / 24)} d`;
}

export function formatDuration(seconds: number | null, started?: string): string {
  const actual = seconds ?? (started ? Math.max(0, (Date.now() - new Date(started).getTime()) / 1000) : 0);
  const minutes = Math.round(actual / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}
