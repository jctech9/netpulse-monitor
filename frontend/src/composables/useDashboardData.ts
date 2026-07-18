import { onBeforeUnmount, onMounted, ref } from "vue";
import { fetchDashboard } from "../services/data";
import type { DashboardData } from "../types/contracts";

export function useDashboardData(refreshMs = 60_000) {
  const data = ref<DashboardData | null>(null);
  const loading = ref(true);
  const refreshing = ref(false);
  const error = ref<string | null>(null);
  let timer: number | undefined;
  let controller: AbortController | undefined;

  async function load(background = false) {
    controller?.abort();
    controller = new AbortController();
    if (background) refreshing.value = true;
    else loading.value = true;
    try {
      data.value = await fetchDashboard(controller.signal);
      error.value = null;
    } catch (caught) {
      if ((caught as Error).name !== "AbortError") {
        error.value = caught instanceof Error ? caught.message : "Falha inesperada ao carregar os dados.";
      }
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  }

  onMounted(() => {
    void load();
    timer = window.setInterval(() => void load(true), refreshMs);
  });
  onBeforeUnmount(() => {
    controller?.abort();
    if (timer) window.clearInterval(timer);
  });

  return { data, loading, refreshing, error, load };
}
