<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import DashboardSkeleton from "./components/DashboardSkeleton.vue";
import IncidentTimeline from "./components/IncidentTimeline.vue";
import MonitorCard from "./components/MonitorCard.vue";
import MonitorDrawer from "./components/MonitorDrawer.vue";
import { useDashboardData } from "./composables/useDashboardData";
import type { MonitorStatus, MonitorSummary } from "./types/contracts";
import { formatDate, formatUptime, overallLabels, relativeTime, statusLabels } from "./utils/format";

const { data, loading, refreshing, error, load } = useDashboardData();
const theme = ref<"dark" | "light">("dark");
const group = ref("all");
const type = ref("all");
const status = ref<"all" | MonitorStatus>("all");
const selected = ref<MonitorSummary | null>(null);

const groups = computed(() => [...new Set(data.value?.status.monitors.map((item) => item.group) ?? [])].sort());
const types = computed(() => [...new Set(data.value?.status.monitors.map((item) => item.type) ?? [])].sort());
const filteredMonitors = computed(() => (data.value?.status.monitors ?? []).filter((monitor) =>
  (group.value === "all" || monitor.group === group.value) &&
  (type.value === "all" || monitor.type === type.value) &&
  (status.value === "all" || monitor.status === status.value),
));
const selectedHistory = computed(() => selected.value && data.value ? data.value.history.monitors[selected.value.id] ?? { raw: [], hourly: [] } : { raw: [], hourly: [] });
const selectedIncidents = computed(() => selected.value && data.value ? data.value.incidents.incidents.filter((item) => item.monitor_id === selected.value?.id) : []);

const healthTone = computed(() => data.value?.status.overall_status ?? "unknown");
const uptimeNumber = computed(() => data.value?.status.overall_uptime_24h ?? 0);
const uptimeStyle = computed(() => ({ "--uptime-angle": `${Math.min(100, Math.max(0, uptimeNumber.value)) * 3.6}deg` }));

function setTheme(value: "dark" | "light") {
  theme.value = value;
  document.documentElement.dataset.theme = value;
  document.documentElement.style.colorScheme = value;
  localStorage.setItem("netpulse-theme", value);
}

function toggleTheme() {
  setTheme(theme.value === "dark" ? "light" : "dark");
}

function clearFilters() {
  group.value = "all";
  type.value = "all";
  status.value = "all";
}

onMounted(() => {
  const saved = localStorage.getItem("netpulse-theme");
  const preferred = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  setTheme(saved === "light" || saved === "dark" ? saved : preferred);
});

watch(data, () => {
  if (selected.value && data.value) {
    selected.value = data.value.status.monitors.find((item) => item.id === selected.value?.id) ?? null;
  }
});
</script>

<template>
  <a class="skip-link" href="#main-content">Pular para o conteúdo</a>
  <div class="ambient ambient--one" aria-hidden="true" />
  <div class="ambient ambient--two" aria-hidden="true" />

  <header class="topbar">
    <a class="brand" href="#" aria-label="NetPulse, início">
      <span class="brand-mark" aria-hidden="true"><i /><i /><i /></span>
      <span><strong>NetPulse</strong><small>NETWORK OBSERVATORY</small></span>
    </a>
    <div class="topbar__status" aria-live="polite">
      <span class="live-indicator" :class="{ active: !error }" aria-hidden="true" />
      <span>
        <strong>{{ error ? "Dados indisponíveis" : "Monitoramento ativo" }}</strong>
        <small v-if="data">Atualizado {{ relativeTime(data.status.generated_at) }}</small>
        <small v-else>Conectando à telemetria</small>
      </span>
    </div>
    <div class="topbar__actions">
      <span v-if="refreshing" class="refreshing" role="status">Sincronizando…</span>
      <button
        class="icon-button theme-toggle"
        type="button"
        :aria-label="theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'"
        @click="toggleTheme"
      >
        <span aria-hidden="true">{{ theme === "dark" ? "☼" : "◐" }}</span>
      </button>
      <a
        class="github-link"
        href="https://github.com/jctech9/netpulse-monitor"
        target="_blank"
        rel="noreferrer"
      >
        <span aria-hidden="true">⌘</span><span class="github-link__text">GitHub</span><span aria-hidden="true">↗</span>
      </a>
    </div>
  </header>

  <main id="main-content" class="shell">
    <DashboardSkeleton v-if="loading && !data" />

    <section v-else-if="error && !data" class="load-state load-state--error">
      <span class="load-state__icon" aria-hidden="true">!</span>
      <p class="eyebrow">
        Falha de telemetria
      </p>
      <h1>Não foi possível carregar o painel.</h1>
      <p>{{ error }}</p>
      <button class="primary-button" type="button" @click="load()">
        Tentar novamente
      </button>
    </section>

    <template v-else-if="data">
      <div v-if="data.status.demo" class="demo-banner" role="note">
        <span aria-hidden="true">◆</span>
        Dados de demonstração — serão substituídos pela primeira execução real do workflow.
      </div>

      <section class="overview" :class="`tone-${healthTone}`">
        <div class="overview__copy">
          <div class="overview__kicker">
            <span /> SAÚDE DA REDE · ÚLTIMAS 24 HORAS
          </div>
          <h1>{{ overallLabels[data.status.overall_status] }}</h1>
          <p>
            {{ data.status.overall_status === "operational" ? "Todos os serviços acompanhados responderam dentro dos parâmetros esperados." : "Detectamos condições que exigem atenção. Consulte os serviços e incidentes abaixo." }}
          </p>
          <div class="overview__meta">
            <span><i aria-hidden="true" /> {{ data.status.monitors.length }} serviços acompanhados</span>
            <span>Fuso {{ data.status.timezone }}</span>
          </div>
        </div>
        <div
          class="uptime-orbit"
          :style="uptimeStyle"
          role="img"
          :aria-label="`Disponibilidade geral de ${formatUptime(data.status.overall_uptime_24h)}`"
        >
          <div class="uptime-orbit__inner">
            <strong>{{ formatUptime(data.status.overall_uptime_24h) }}</strong>
            <span>DISPONIBILIDADE</span>
          </div>
          <span class="orbit-dot" aria-hidden="true" />
        </div>
      </section>

      <section class="kpi-grid" aria-label="Resumo dos estados">
        <button class="kpi-card kpi-card--up" type="button" @click="status = 'up'">
          <span class="kpi-card__icon" aria-hidden="true">↗</span><span><small>ONLINE</small><strong>{{ data.status.counts.up }}</strong><em>Operando normalmente</em></span>
        </button>
        <button class="kpi-card kpi-card--degraded" type="button" @click="status = 'degraded'">
          <span class="kpi-card__icon" aria-hidden="true">≈</span><span><small>INSTÁVEL</small><strong>{{ data.status.counts.degraded }}</strong><em>Requer atenção</em></span>
        </button>
        <button class="kpi-card kpi-card--down" type="button" @click="status = 'down'">
          <span class="kpi-card__icon" aria-hidden="true">↓</span><span><small>OFFLINE</small><strong>{{ data.status.counts.down }}</strong><em>Falha confirmada</em></span>
        </button>
        <a class="kpi-card kpi-card--incidents" href="#incidents">
          <span class="kpi-card__icon" aria-hidden="true">◎</span><span><small>INCIDENTES</small><strong>{{ data.status.open_incidents }}</strong><em>Em andamento</em></span>
        </a>
      </section>

      <section class="monitors-section">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              TELEMETRIA
            </p><h2>Serviços monitorados</h2><p>Resposta, disponibilidade e sinais recentes por destino.</p>
          </div>
          <div class="filters" aria-label="Filtros de monitores">
            <label><span class="sr-only">Filtrar por grupo</span><select v-model="group"><option value="all">Todos os grupos</option><option v-for="item in groups" :key="item" :value="item">{{ item }}</option></select></label>
            <label><span class="sr-only">Filtrar por tipo</span><select v-model="type"><option value="all">Todos os tipos</option><option v-for="item in types" :key="item" :value="item">{{ item.toUpperCase() }}</option></select></label>
            <label><span class="sr-only">Filtrar por estado</span><select v-model="status"><option value="all">Todos os estados</option><option v-for="(label, key) in statusLabels" :key="key" :value="key">{{ label }}</option></select></label>
          </div>
        </div>

        <div v-if="filteredMonitors.length" class="monitor-grid">
          <MonitorCard
            v-for="monitor in filteredMonitors"
            :key="monitor.id"
            :monitor="monitor"
            :history="data.history.monitors[monitor.id] ?? { raw: [], hourly: [] }"
            :timezone="data.status.timezone"
            @open="selected = $event"
          />
        </div>
        <div v-else class="load-state load-state--empty">
          <span class="load-state__icon" aria-hidden="true">◇</span>
          <h3>Nenhum serviço corresponde aos filtros.</h3>
          <p>Ajuste os critérios para voltar a visualizar a telemetria.</p>
          <button class="secondary-button" type="button" @click="clearFilters">
            Limpar filtros
          </button>
        </div>
      </section>

      <section id="incidents" class="incidents-section">
        <div class="section-heading">
          <div>
            <p class="eyebrow">
              LINHA DO TEMPO
            </p><h2>Incidentes recentes</h2><p>Eventos confirmados, resolução e duração registrada.</p>
          </div>
          <span class="incident-counter"><i />{{ data.status.open_incidents }} em andamento</span>
        </div>
        <IncidentTimeline :incidents="data.incidents.incidents" :monitors="data.status.monitors" :timezone="data.status.timezone" />
      </section>
    </template>
  </main>

  <footer class="footer">
    <div><strong>NetPulse</strong><span>Python · asyncio · Vue · GitHub Actions</span></div>
    <p v-if="data">
      Dados gerados em {{ formatDate(data.status.generated_at, data.status.timezone, true) }} · Monitoramento periódico, não em tempo real.
    </p>
  </footer>

  <MonitorDrawer
    v-if="selected && data"
    :monitor="selected"
    :history="selectedHistory"
    :incidents="selectedIncidents"
    :monitors="data.status.monitors"
    :timezone="data.status.timezone"
    @close="selected = null"
  />
</template>
