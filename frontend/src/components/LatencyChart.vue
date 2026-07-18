<script setup lang="ts">
import {
  CategoryScale,
  Chart,
  Filler,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from "chart.js";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { RawSample } from "../types/contracts";

Chart.register(CategoryScale, LineController, LineElement, PointElement, LinearScale, Tooltip, Filler);

const props = withDefaults(defineProps<{ samples: RawSample[]; mini?: boolean }>(), { mini: false });
const canvas = ref<HTMLCanvasElement | null>(null);
let chart: Chart | null = null;

const points = computed(() => props.samples.filter((item) => item.response_ms !== null).slice(props.mini ? -24 : -144));

function draw() {
  if (!canvas.value) return;
  chart?.destroy();
  Chart.getChart(canvas.value)?.destroy();
  const styles = getComputedStyle(document.documentElement);
  const cyan = styles.getPropertyValue("--cyan").trim() || "#32d3ff";
  const muted = styles.getPropertyValue("--text-muted").trim() || "#9eb2c8";
  chart = new Chart(canvas.value, {
    type: "line",
    data: {
      labels: points.value.map((item) => new Date(item.timestamp).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })),
      datasets: [{
        data: points.value.map((item) => item.response_ms),
        borderColor: cyan,
        backgroundColor: `${cyan}16`,
        borderWidth: props.mini ? 1.5 : 2,
        pointRadius: 0,
        tension: 0.35,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 350 },
      plugins: { legend: { display: false }, tooltip: { enabled: !props.mini, displayColors: false } },
      scales: props.mini ? { x: { display: false }, y: { display: false } } : {
        x: { ticks: { color: muted, maxTicksLimit: 7 }, grid: { display: false }, border: { display: false } },
        y: { beginAtZero: true, ticks: { color: muted, callback: (value) => `${value} ms` }, grid: { color: `${muted}18` }, border: { display: false } },
      },
    },
  });
}

onMounted(() => void nextTick(draw));
watch(() => props.samples, () => void nextTick(draw), { deep: true });
onBeforeUnmount(() => chart?.destroy());
</script>

<template>
  <div class="chart" :class="{ 'chart--mini': mini }">
    <canvas ref="canvas" :aria-label="mini ? 'Mini gráfico de latência' : 'Gráfico de latência das últimas 24 horas'" role="img" />
  </div>
</template>
