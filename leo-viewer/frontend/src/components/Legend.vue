<template>
  <div class="legend-container" :class="{ collapsed }">
    <div class="legend-header" @click="collapsed = !collapsed">
      <span class="legend-title">{{ title }}</span>
      <span class="collapse-btn" :class="{ rotated: collapsed }">
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M1 3.5L5 7L9 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
    </div>

    <div v-show="!collapsed" class="legend-body">
      <div class="legend-row" v-for="item in colorLegend" :key="item.label">
        <span class="legend-color" :style="{ background: item.color }"></span>
        <span>{{ item.label }}</span>
      </div>
      <span class="info-trigger" @click="showInfo = true">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <circle cx="6" cy="6" r="5.5" stroke="currentColor"/>
          <path d="M6 5.5V9M6 3.5V4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
        About this data
      </span>
    </div>

    <Teleport to="body">
      <Transition name="popup">
        <div v-if="showInfo" class="popup-backdrop" @click.self="showInfo = false">
          <div class="popup">
            <div class="popup-header">
              <span class="popup-title">{{ title ?? 'Legend' }}</span>
              <button class="popup-close" @click="showInfo = false" aria-label="Close">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                </svg>
              </button>
            </div>

            <div class="popup-body">
              <p v-if="extraInfo" class="popup-extra">{{ extraInfo }}</p>

              <div class="popup-metrics">
                <div class="popup-metric">
                  <span class="metric-name">Latency</span>
                  <span class="metric-desc">Network delay measured in milliseconds. Lower values indicate a more responsive connection.</span>
                </div>
                <div class="popup-metric">
                  <span class="metric-name">Throughput</span>
                  <span class="metric-desc">Data transfer rate in Mbps. Higher values indicate faster speeds.</span>
                </div>
                <div v-if="showSatDensity" class="popup-metric">
                  <span class="metric-name">Sat Density</span>
                  <span class="metric-desc">Number of LEO satellites visible from this location at the recorded time.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  colorLegend: { color: string; label: string }[]
  title?: string
  showSatDensity?: boolean
  extraInfo?: string
}>()

const showInfo = ref(false)
const collapsed = ref(window.innerWidth < 850)
</script>

<style scoped>
.legend-container {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.97);
  border-radius: 10px;
  padding: 10px 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.13);
  z-index: 1001;
  min-width: 148px;
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
  gap: 10px;
  user-select: none;
}
.legend-title {
  font-weight: 600;
  font-size: 0.88em;
  color: #18181b;
}
.collapse-btn {
  color: #a1a1aa;
  display: flex;
  transition: transform 0.2s ease;
}
.collapse-btn.rotated {
  transform: rotate(-180deg);
}
.legend-body {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.83em;
  color: #3f3f46;
  padding: 1px 0;
}
.legend-color {
  width: 18px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
  border: 1px solid rgba(0,0,0,0.1);
}
.info-trigger {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 6px;
  font-size: 0.78em;
  color: #71717a;
  cursor: pointer;
  transition: color 0.15s;
  line-height: 1;
}
.info-trigger:hover {
  color: #18181b;
}

.popup-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 16px;
}
.popup {
  background: #fff;
  border-radius: 14px;
  width: 100%;
  max-width: 340px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}
.popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 14px;
  border-bottom: 1px solid #f4f4f5;
}
.popup-title {
  font-weight: 600;
  font-size: 0.95em;
  color: #18181b;
}
.popup-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: #f4f4f5;
  border-radius: 50%;
  cursor: pointer;
  color: #71717a;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}
.popup-close:hover {
  background: #e4e4e7;
  color: #18181b;
}
.popup-body {
  padding: 16px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.popup-extra {
  font-size: 0.85em;
  color: #52525b;
  margin: 0;
  line-height: 1.5;
}
.popup-metrics {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.popup-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.metric-name {
  font-size: 0.82em;
  font-weight: 600;
  color: #18181b;
}
.metric-desc {
  font-size: 0.8em;
  color: #71717a;
  line-height: 1.45;
}

.popup-enter-active,
.popup-leave-active {
  transition: opacity 0.18s ease;
}
.popup-enter-active .popup,
.popup-leave-active .popup {
  transition: transform 0.18s ease, opacity 0.18s ease;
}
.popup-enter-from,
.popup-leave-to {
  opacity: 0;
}
.popup-enter-from .popup,
.popup-leave-to .popup {
  transform: scale(0.96) translateY(6px);
  opacity: 0;
}

@media (max-width: 850px) {
  .legend-container {
    bottom: 10px;
    left: 10px;
  }
}
</style>