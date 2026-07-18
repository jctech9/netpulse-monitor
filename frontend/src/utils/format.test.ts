import { describe, expect, it } from "vitest";
import { formatDate, formatDuration, formatLatency, formatUptime } from "./format";

describe("formatação pt-BR", () => {
  it("formata latência e uptime", () => {
    expect(formatLatency(184.4)).toBe("184 ms");
    expect(formatLatency(1250)).toContain("1,3 s");
    expect(formatLatency(null)).toBe("—");
    expect(formatUptime(99.987)).toBe("99,987%");
  });

  it("formata data no fuso configurado", () => {
    expect(formatDate("2026-07-18T15:00:00Z", "America/Sao_Paulo", true)).toMatch(/12:00/);
  });

  it("formata duração", () => {
    expect(formatDuration(1020)).toBe("17 min");
    expect(formatDuration(5400)).toBe("1 h 30 min");
  });
});
