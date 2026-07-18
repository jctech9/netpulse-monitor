<script setup lang="ts">
import type { Incident, MonitorSummary } from "../types/contracts";
import { formatDate, formatDuration } from "../utils/format";

defineProps<{ incidents: Incident[]; monitors: MonitorSummary[]; timezone: string; compact?: boolean }>();

function monitorName(id: string, monitors: MonitorSummary[]) {
  return monitors.find((item) => item.id === id)?.name ?? id;
}
</script>

<template>
  <div v-if="incidents.length" class="timeline" :class="{ 'timeline--compact': compact }">
    <article
      v-for="incident in incidents"
      :key="incident.id"
      class="timeline-item"
      :class="`is-${incident.status}`"
    >
      <span class="timeline-item__marker" aria-hidden="true" />
      <div class="timeline-item__body">
        <div class="timeline-item__top">
          <div>
            <span class="incident-state">{{ incident.status === "open" ? "Em andamento" : "Resolvido" }}</span>
            <h3>{{ monitorName(incident.monitor_id, monitors) }}</h3>
          </div>
          <time :datetime="incident.started_at">{{ formatDate(incident.started_at, timezone, true) }}</time>
        </div>
        <p>{{ incident.message }}</p>
        <div class="timeline-item__meta">
          <span>{{ incident.cause }}</span>
          <span>Duração: {{ formatDuration(incident.duration_seconds, incident.started_at) }}</span>
        </div>
      </div>
    </article>
  </div>
  <div v-else class="empty-inline">
    <span aria-hidden="true">✓</span>
    <p>Nenhum incidente registrado neste período.</p>
  </div>
</template>
