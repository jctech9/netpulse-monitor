<script setup lang="ts">
import type { MonitorStatus } from "../types/contracts";
import { statusLabels } from "../utils/format";

defineProps<{ status: MonitorStatus }>();
</script>

<template>
  <span class="status-badge" :class="`is-${status}`">
    <span class="status-dot" aria-hidden="true" />
    {{ statusLabels[status] }}
  </span>
</template>
