import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchDashboard, parseDocuments } from "./data";
import { fixtureData } from "../test/fixtures";

describe("contrato de dados", () => {
  afterEach(() => vi.restoreAllMocks());

  it("analisa os três documentos válidos", () => {
    const result = parseDocuments(fixtureData.status, fixtureData.history, fixtureData.incidents);
    expect(result.status.monitors).toHaveLength(5);
  });

  it("rejeita schema incompatível", () => {
    expect(() => parseDocuments({ ...fixtureData.status, schema_version: 2 }, fixtureData.history, fixtureData.incidents)).toThrow("incompatível");
  });

  it("carrega JSONs usando o caminho base e cache busting", async () => {
    const documents = [fixtureData.status, fixtureData.history, fixtureData.incidents];
    const fetchMock = vi.spyOn(globalThis, "fetch");
    documents.forEach((document) => fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(document), { status: 200 })));
    const result = await fetchDashboard();
    expect(result.status.overall_status).toBe("degraded");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[0][0])).toContain("data/status.json?v=");
  });
});
