<template>
  <div class="legend-container" :class="{ collapsed }">
    <div class="legend-header" @click="collapsed = !collapsed">
      <span class="legend-title">{{ title }}</span>
      <span class="collapse-btn">{{ collapsed ? "▲" : "▼" }}</span>
    </div>
    <div v-show="!collapsed" class="legend-body">
      <div class="legend-row" v-for="item in colorLegend" :key="item.label">
        <span class="legend-color" :style="{ background: item.color }"></span>
        <span>{{ item.label }}</span>
      </div>
      <span class="info-icon" @click="showInfo = true">ⓘ Info</span>
    </div>
    <div v-if="showInfo" class="legend-popup" @click.self="showInfo = false">
      <div class="legend-popup-inner">
        <b>Legend info</b>
        <p v-if="extraInfo">{{ extraInfo }}</p>
        <ul>
          <li><b>Latency</b>: Delay in ms (lower is better)</li>
          <li><b>Throughput</b>: Mbps (higher is better)</li>
          <li v-if="showSatDensity">
            <b>SatDensity</b>: Number of visible LEO satellites
          </li>
        </ul>
        <button @click="showInfo = false" class="close-btn">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
  colorLegend: { color: string; label: string }[];
  title?: string;
  showSatDensity?: boolean;
  extraInfo?: string;
}>();

const showInfo = ref(false);
const collapsed = ref(window.innerWidth < 850);
</script>

<style scoped>
.legend-container {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.97);
  border-radius: 8px;
  padding: 10px 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.17);
  z-index: 1001;
  min-width: 140px;
  font-family: sans-serif;
}
.legend-container.collapsed {
  padding: 8px 12px;
}
.legend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  gap: 8px;
}
.legend-title {
  font-weight: bold;
  font-size: 0.95em;
}
.collapse-btn {
  font-size: 0.75em;
  color: #666;
}
.legend-body {
  margin-top: 6px;
}
.info-icon {
  cursor: pointer;
  font-size: 0.85em;
  color: #337ab7;
  margin-top: 6px;
  display: inline-block;
}
.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 3px 0;
  font-size: 0.88em;
}
.legend-color {
  width: 20px;
  height: 12px;
  border-radius: 3px;
  border: 1px solid #888;
}
.legend-popup {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.legend-popup-inner {
  background: #fff;
  border-radius: 10px;
  padding: 18px 24px;
  min-width: 280px;
  max-width: 90vw;
  box-shadow: 0 6px 40px rgba(0, 0, 0, 0.2);
  font-size: 1em;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.legend-popup ul {
  margin: 0 0 10px 20px;
  padding: 0;
  font-size: 0.95em;
}
.close-btn {
  align-self: flex-end;
  padding: 5px 13px;
  border: none;
  background: #337ab7;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95em;
}

@media (max-width: 850px) {
  .legend-container {
    bottom: 10px;
    left: 10px;
    padding: 8px 10px;
    font-size: 0.92em;
  }
  .legend-row {
    font-size: 0.85em;
    color: #222;
  }
  .legend-title {
    font-size: 0.9em;
  }
}
</style>
