export type MonitorStatus = "unknown" | "up" | "degraded" | "down" | "maintenance";
export type OverallStatus = "operational" | "degraded" | "major_outage" | "unknown";

export interface MonitorSummary {
  id: string;
  name: string;
  group: string;
  type: "http" | "json" | "keyword" | "dns" | "tcp" | "tls";
  description: string;
  target: string;
  status: MonitorStatus;
  response_ms: number | null;
  last_checked_at: string | null;
  detail: string;
  uptime_24h: number | null;
  uptime_30d: number | null;
  metadata: Record<string, unknown>;
}

export interface StatusDocument {
  schema_version: 1;
  generated_at: string;
  last_successful_update: string;
  timezone: string;
  demo: boolean;
  overall_status: OverallStatus;
  overall_uptime_24h: number | null;
  counts: Record<MonitorStatus, number>;
  open_incidents: number;
  monitors: MonitorSummary[];
}

export interface RawSample {
  timestamp: string;
  status: MonitorStatus;
  response_ms: number | null;
}

export interface HourlySample {
  timestamp: string;
  status: MonitorStatus;
  avg_ms: number | null;
  min_ms: number | null;
  max_ms: number | null;
  sample_count: number;
  status_counts: Partial<Record<MonitorStatus, number>>;
}

export interface MonitorHistory {
  raw: RawSample[];
  hourly: HourlySample[];
}

export interface HistoryDocument {
  schema_version: 1;
  generated_at: string;
  demo: boolean;
  monitors: Record<string, MonitorHistory>;
}

export interface Incident {
  id: string;
  monitor_id: string;
  started_at: string;
  ended_at: string | null;
  cause: string;
  duration_seconds: number | null;
  status: "open" | "resolved";
  message: string;
}

export interface IncidentsDocument {
  schema_version: 1;
  generated_at: string;
  demo: boolean;
  incidents: Incident[];
}

export interface DashboardData {
  status: StatusDocument;
  history: HistoryDocument;
  incidents: IncidentsDocument;
}
