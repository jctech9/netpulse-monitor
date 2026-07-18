import { fireEvent, render, screen } from "@testing-library/vue";
import { ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fixtureData } from "./test/fixtures";
import type { DashboardData } from "./types/contracts";

const dashboard = {
  data: ref<DashboardData | null>(fixtureData),
  loading: ref(false),
  refreshing: ref(false),
  error: ref<string | null>(null),
  load: vi.fn(),
};

vi.mock("./composables/useDashboardData", () => ({ useDashboardData: () => dashboard }));
import App from "./App.vue";

describe("painel NetPulse", () => {
  beforeEach(() => {
    dashboard.data.value = fixtureData;
    dashboard.loading.value = false;
    dashboard.error.value = null;
    localStorage.clear();
  });

  it("exibe resumo, cards e incidente", () => {
    render(App);
    expect(screen.getByRole("heading", { name: "Operação parcialmente degradada" })).toBeTruthy();
    expect(screen.getAllByRole("button", { name: /Abrir detalhes/ })).toHaveLength(5);
    expect(screen.getByText("Investigando indisponibilidade.")).toBeTruthy();
  });

  it("filtra por estado usando KPI", async () => {
    render(App);
    await fireEvent.click(screen.getByRole("button", { name: /OFFLINE/ }));
    expect(screen.getByRole("button", { name: "Abrir detalhes de Serviço 3" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Abrir detalhes de Serviço 1" })).toBeNull();
  });

  it("alterna tema com label acessível", async () => {
    render(App);
    const toggle = screen.getByRole("button", { name: "Ativar tema claro" });
    await fireEvent.click(toggle);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("mostra erro quando não há dados", () => {
    dashboard.data.value = null;
    dashboard.error.value = "Falha controlada";
    render(App);
    expect(screen.getByRole("heading", { name: "Não foi possível carregar o painel." })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeTruthy();
  });
});
