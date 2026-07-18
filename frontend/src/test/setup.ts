import { vi } from "vitest";

vi.mock("chart.js", () => {
  class FakeChart {
    static register() {}
    static getChart() { return undefined; }
    destroy() {}
  }
  return {
    Chart: FakeChart,
    CategoryScale: {},
    Filler: {},
    LineController: {},
    LineElement: {},
    LinearScale: {},
    PointElement: {},
    Tooltip: {},
  };
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
