<template>
  <div class="legend-container">
    <div class="legend-title">
      <span>{{ title }}</span>
      <span class="info-icon" @click="showInfo = true">ⓘ</span>
    </div>
    <div class="legend-row" v-for="item in colorLegend" :key="item.label">
      <span class="legend-color" :style="{background: item.color}"></span>
      <span>{{ item.label }}</span>
    </div>
    <div v-if="showInfo" class="legend-popup">
      <div class="legend-popup-inner">
        <b>Legend info</b>
        <p v-if="extraInfo">{{ extraInfo }}</p>
        <ul>
          <li><b>Latency</b>: Delay in ms (lower is better)</li>
          <li><b>Jitter</b>: Variation in latency (ms, lower is better)</li>
          <li><b>Loss</b>: Packet loss % (lower is better)</li>
          <li><b>Throughput</b>: Mbps (higher is better)</li>
          <li v-if="showSatDensity"><b>SatDensity</b>: Number of visible LEO satellites</li>
        </ul>
        <button @click="showInfo = false" class="close-btn">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  colorLegend: { color: string, label: string }[]
  title?: string
  showSatDensity?: boolean
  extraInfo?: string
}>()

const showInfo = ref(false)
</script>

<style scoped>
.legend-container {
  margin-bottom: 35px;
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255,255,255,0.97);
  border-radius: 8px;
  padding: 12px 18px 10px 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.17);
  z-index: 1001;
  min-width: 150px;
  font-family: sans-serif;
}
.legend-title {
  font-weight: bold;
  font-size: 1.07em;
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 7px;
}
.info-icon {
  cursor: pointer;
  font-size: 1.1em;
  color: #337ab7;
  user-select: none;
}
.legend-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 2px 0;
}
.legend-color {
  width: 22px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid #888;
  margin-right: 4px;
}
.legend-popup {
  position: fixed;
  top: 20%;
  left: 50%;
  transform: translate(-50%, 0);
  background: #fff;
  border: 1.5px solid #444;
  border-radius: 10px;
  padding: 18px 24px;
  z-index: 2000;
  min-width: 320px;
  box-shadow: 0 6px 40px rgba(0,0,0,0.20);
  font-size: 1.08em;
}
.legend-popup-inner {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.legend-popup ul {
  margin: 0 0 10px 20px;
  padding: 0;
  font-size: 0.98em;
}
.close-btn {
  margin-top: 8px;
  align-self: flex-end;
  padding: 5px 13px;
  border: none;
  background: #337ab7;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1em;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}

</style>
