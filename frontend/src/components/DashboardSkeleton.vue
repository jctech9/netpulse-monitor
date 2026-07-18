<template>
  <div class="skeleton-page" aria-label="Carregando painel" role="status">
    <div class="skeleton skeleton--hero" />
    <div class="skeleton-grid">
      <div v-for="item in 4" :key="item" class="skeleton skeleton--kpi" />
    </div>
    <div class="skeleton-cards">
      <div v-for="item in 6" :key="item" class="skeleton skeleton--card" />
    </div>
    <span class="sr-only">Carregando dados de monitoramento…</span>
  </div>
</template>
