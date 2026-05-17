<template>
  <div v-if="show" ref="tooltipEl" :style="positionStyle" class="tooltip-card">
    <div class="tooltip-header">{{ data.date }} {{ data.hour }}:00</div>
    <div class="tooltip-row"><span class="tooltip-label">Lat</span><span>{{ data.lat }}</span></div>
    <div class="tooltip-row"><span class="tooltip-label">Lon</span><span>{{ data.lon }}</span></div>
    <div class="tooltip-row"><span class="tooltip-label">Latency</span><span>{{ Number(data.latency).toFixed(1) }} ms</span></div>
    <div class="tooltip-row"><span class="tooltip-label">Throughput</span><span>{{ Number(data.throughput).toFixed(1) }} Mbps</span></div>
    <div v-if="data.sat_density !== undefined" class="tooltip-row">
      <span class="tooltip-label">Sat Density</span><span>{{ data.sat_density }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'

const props = defineProps<{
  show: boolean
  x: number
  y: number
  data: Record<string, any>
}>()

const OFFSET = 12 // px gap from cursor

const tooltipEl = ref<HTMLElement | null>(null)
const tooltipWidth = ref(200)
const tooltipHeight = ref(120)

watch(
  () => [props.show, props.x, props.y],
  async ([visible]) => {
    if (visible) {
      await nextTick()
      if (tooltipEl.value) {
        tooltipWidth.value = tooltipEl.value.offsetWidth
        tooltipHeight.value = tooltipEl.value.offsetHeight
      }
    }
  }
)

const positionStyle = computed(() => {
  const vw = window.innerWidth
  const vh = window.innerHeight

  let left = props.x + OFFSET
  let top = props.y + OFFSET

  if (left + tooltipWidth.value > vw - OFFSET) {
    left = props.x - tooltipWidth.value - OFFSET
  }

  if (top + tooltipHeight.value > vh - OFFSET) {
    top = props.y - tooltipHeight.value - OFFSET
  }

  left = Math.max(OFFSET, Math.min(left, vw - tooltipWidth.value - OFFSET))
  top  = Math.max(OFFSET, Math.min(top,  vh - tooltipHeight.value - OFFSET))

  return {
    position: 'fixed' as const,
    left: left + 'px',
    top: top + 'px',
    pointerEvents: 'none' as const,
    zIndex: 10000,
  }
})
</script>

<style scoped>
.tooltip-card {
  min-width: 180px;
  white-space: nowrap;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 0.82em;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.tooltip-header {
  font-weight: 600;
  margin-bottom: 6px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  color: #18181b;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 0;
  color: #18181b;
}

.tooltip-label {
  color: #71717a;
  font-weight: 500;
}
</style>