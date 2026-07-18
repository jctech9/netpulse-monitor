<script setup lang="ts">
import { computed } from "vue";
import type { MonitorStatus, RawSample } from "../types/contracts";
import { statusLabels } from "../utils/format";

const props = withDefaults(defineProps<{ samples: RawSample[]; blocks?: number }>(), { blocks: 36 });

const cells = computed<{ status: MonitorStatus; count: number }[]>(() => {
  if (!props.samples.length) return Array.from({ length: props.blocks }, () => ({ status: "unknown", count: 0 }));
  const size = Math.max(1, Math.ceil(props.samples.length / props.blocks));
  const groups = [];
  for (let index = 0; index < props.samples.length; index += size) {
    const slice = props.samples.slice(index, index + size);
    const priority = ["down", "degraded", "maintenance", "up", "unknown"] as const;
    const status = priority.find((candidate) => slice.some((item) => item.status === candidate)) ?? "unknown";
    groups.push({ status, count: slice.length });
  }
  return groups.slice(-props.blocks);
});
</script>

<template>
  <div class="availability-strip" role="img" aria-label="Faixa de disponibilidade recente">
    <span
      v-for="(cell, index) in cells"
      :key="index"
      class="availability-cell"
      :class="`is-${cell.status}`"
      :title="`${statusLabels[cell.status]} · ${cell.count || 'sem'} amostra(s)`"
    />
  </div>
</template>
