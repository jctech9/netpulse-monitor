<script setup lang="ts">
import type { MonitorHistory, MonitorSummary } from "../types/contracts";
import { formatDate, formatLatency, formatUptime } from "../utils/format";
import AvailabilityStrip from "./AvailabilityStrip.vue";
import LatencyChart from "./LatencyChart.vue";
import StatusBadge from "./StatusBadge.vue";

defineProps<{ monitor: MonitorSummary; history: MonitorHistory; timezone: string }>();
const emit = defineEmits<{ open: [monitor: MonitorSummary] }>();
</script>

<template>
  <article class="monitor-card" :class="`accent-${monitor.status}`">
    <header class="monitor-card__header">
      <div>
        <p class="eyebrow">
          {{ monitor.group }}
        </p>
        <h3>{{ monitor.name }}</h3>
      </div>
      <StatusBadge :status="monitor.status" />
    </header>

    <div class="monitor-card__signal">
      <div>
        <span class="metric-label">Resposta atual</span>
        <strong>{{ formatLatency(monitor.response_ms) }}</strong>
      </div>
      <span class="type-chip">{{ monitor.type.toUpperCase() }}</span>
    </div>

    <LatencyChart :samples="history.raw" mini />
    <AvailabilityStrip :samples="history.raw" :blocks="28" />

    <dl class="monitor-card__stats">
      <div><dt>Disponibilidade 24h</dt><dd>{{ formatUptime(monitor.uptime_24h) }}</dd></div>
      <div><dt>Últimos 30 dias</dt><dd>{{ formatUptime(monitor.uptime_30d) }}</dd></div>
    </dl>

    <footer class="monitor-card__footer">
      <span>Verificado às {{ formatDate(monitor.last_checked_at, timezone) }}</span>
      <button type="button" :aria-label="`Abrir detalhes de ${monitor.name}`" @click="emit('open', monitor)">
        Detalhes <span aria-hidden="true">↗</span>
      </button>
    </footer>
  </article>
</template>
