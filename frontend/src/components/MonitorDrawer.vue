<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { Incident, MonitorHistory, MonitorSummary } from "../types/contracts";
import { formatDate, formatLatency, formatUptime } from "../utils/format";
import AvailabilityStrip from "./AvailabilityStrip.vue";
import IncidentTimeline from "./IncidentTimeline.vue";
import LatencyChart from "./LatencyChart.vue";
import StatusBadge from "./StatusBadge.vue";

defineProps<{ monitor: MonitorSummary; history: MonitorHistory; incidents: Incident[]; monitors: MonitorSummary[]; timezone: string }>();
const emit = defineEmits<{ close: [] }>();
const closeButton = ref<HTMLButtonElement | null>(null);

function keydown(event: KeyboardEvent) {
  if (event.key === "Escape") emit("close");
}

onMounted(() => {
  document.body.classList.add("drawer-open");
  document.addEventListener("keydown", keydown);
  closeButton.value?.focus();
});
onBeforeUnmount(() => {
  document.body.classList.remove("drawer-open");
  document.removeEventListener("keydown", keydown);
});
</script>

<template>
  <div class="drawer-layer" role="presentation" @mousedown.self="emit('close')">
    <aside
      class="drawer"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="`drawer-title-${monitor.id}`"
    >
      <header class="drawer__header">
        <div>
          <p class="eyebrow">
            {{ monitor.group }} · {{ monitor.type.toUpperCase() }}
          </p>
          <h2 :id="`drawer-title-${monitor.id}`">
            {{ monitor.name }}
          </h2>
        </div>
        <button
          ref="closeButton"
          class="icon-button"
          type="button"
          aria-label="Fechar detalhes"
          @click="emit('close')"
        >
          ×
        </button>
      </header>
      <div class="drawer__content">
        <div class="drawer__status">
          <StatusBadge :status="monitor.status" />
          <span>{{ monitor.detail }}</span>
        </div>
        <p class="drawer__description">
          {{ monitor.description }}
        </p>
        <code class="target">{{ monitor.target }}</code>

        <div class="drawer__metrics">
          <div><span>Resposta</span><strong>{{ formatLatency(monitor.response_ms) }}</strong></div>
          <div><span>Disponibilidade 24h</span><strong>{{ formatUptime(monitor.uptime_24h) }}</strong></div>
          <div><span>Disponibilidade 30d</span><strong>{{ formatUptime(monitor.uptime_30d) }}</strong></div>
        </div>

        <section class="drawer-section">
          <div class="section-heading compact">
            <div>
              <p class="eyebrow">
                Telemetria
              </p><h3>Latência nas últimas 24 horas</h3>
            </div>
          </div>
          <LatencyChart :samples="history.raw" />
          <AvailabilityStrip :samples="history.raw" :blocks="48" />
        </section>

        <section v-if="monitor.type === 'tls' && monitor.metadata.days_remaining" class="certificate-panel">
          <div><span>Dias restantes</span><strong>{{ monitor.metadata.days_remaining }}</strong></div>
          <dl>
            <div><dt>Emissor</dt><dd>{{ monitor.metadata.issuer }}</dd></div>
            <div><dt>Assunto</dt><dd>{{ monitor.metadata.subject }}</dd></div>
            <div><dt>Validade</dt><dd>{{ formatDate(String(monitor.metadata.expires_at), timezone, true) }}</dd></div>
          </dl>
        </section>

        <section class="drawer-section">
          <div class="section-heading compact">
            <div>
              <p class="eyebrow">
                Registro
              </p><h3>Incidentes deste monitor</h3>
            </div>
          </div>
          <IncidentTimeline
            :incidents="incidents"
            :monitors="monitors"
            :timezone="timezone"
            compact
          />
        </section>
      </div>
    </aside>
  </div>
</template>
