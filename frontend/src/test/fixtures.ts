import type { DashboardData } from "../types/contracts";

export const fixtureData: DashboardData = {
  status: {
    schema_version: 1,
    generated_at: "2026-07-18T15:00:00Z",
    last_successful_update: "2026-07-18T15:00:00Z",
    timezone: "America/Sao_Paulo",
    demo: false,
    overall_status: "degraded",
    overall_uptime_24h: 99.5,
    counts: { up: 1, degraded: 1, down: 1, maintenance: 1, unknown: 1 },
    open_incidents: 1,
    monitors: ["up", "degraded", "down", "maintenance", "unknown"].map((status, index) => ({
      id: `service_${index}`,
      name: `Serviço ${index + 1}`,
      group: index < 2 ? "Web" : "Infra",
      type: index === 1 ? "tls" : "http",
      description: "Serviço público de teste.",
      target: "https://example.com",
      status: status as "up" | "degraded" | "down" | "maintenance" | "unknown",
      response_ms: status === "down" ? null : 123.4 + index,
      last_checked_at: "2026-07-18T15:00:00Z",
      detail: "Verificação concluída",
      uptime_24h: 99.5,
      uptime_30d: 99.9,
      metadata: index === 1 ? { days_remaining: 19, issuer: "CA", subject: "example.com", expires_at: "2026-08-06T15:00:00Z" } : {},
    })),
  },
  history: {
    schema_version: 1,
    generated_at: "2026-07-18T15:00:00Z",
    demo: false,
    monitors: Object.fromEntries(Array.from({ length: 5 }, (_, index) => [`service_${index}`, {
      raw: [
        { timestamp: "2026-07-18T14:50:00Z", status: "up", response_ms: 120 },
        { timestamp: "2026-07-18T15:00:00Z", status: index === 2 ? "down" : "up", response_ms: index === 2 ? null : 125 },
      ],
      hourly: [],
    }])),
  },
  incidents: {
    schema_version: 1,
    generated_at: "2026-07-18T15:00:00Z",
    demo: false,
    incidents: [{
      id: "incident_1",
      monitor_id: "service_2",
      started_at: "2026-07-18T14:30:00Z",
      ended_at: null,
      cause: "Timeout",
      duration_seconds: null,
      status: "open",
      message: "Investigando indisponibilidade.",
    }],
  },
};
