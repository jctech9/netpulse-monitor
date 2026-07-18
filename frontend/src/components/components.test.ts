import { fireEvent, render, screen } from "@testing-library/vue";
import { describe, expect, it } from "vitest";
import AvailabilityStrip from "./AvailabilityStrip.vue";
import MonitorCard from "./MonitorCard.vue";
import StatusBadge from "./StatusBadge.vue";
import { fixtureData } from "../test/fixtures";

describe("componentes essenciais", () => {
  it.each(["up", "degraded", "down", "maintenance", "unknown"] as const)("mostra estado %s com texto", (status) => {
    render(StatusBadge, { props: { status } });
    expect(screen.getByText(/Online|Instável|Offline|Manutenção|Sem dados/)).toBeTruthy();
  });

  it("renderiza faixa com label acessível", () => {
    render(AvailabilityStrip, { props: { samples: fixtureData.history.monitors.service_0.raw, blocks: 10 } });
    expect(screen.getByRole("img", { name: /Faixa de disponibilidade/ })).toBeTruthy();
  });

  it("abre detalhes pelo botão acessível", async () => {
    const monitor = fixtureData.status.monitors[0];
    const view = render(MonitorCard, {
      props: { monitor, history: fixtureData.history.monitors.service_0, timezone: fixtureData.status.timezone },
    });
    await fireEvent.click(screen.getByRole("button", { name: `Abrir detalhes de ${monitor.name}` }));
    expect(view.emitted().open).toHaveLength(1);
    expect(screen.getByText("123 ms")).toBeTruthy();
  });
});
