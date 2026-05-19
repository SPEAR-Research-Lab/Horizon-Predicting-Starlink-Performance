<template>
  <div>
    <div class="mobile-toggle-wrapper">
      <button class="mobile-toggle" @click="open = !open">
        <svg class="icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" 
            fill="none" stroke="currentColor" stroke-width="2" 
            stroke-linecap="round" stroke-linejoin="round" 
            aria-hidden="true" style="flex-shrink: 0;">
          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
          <line x1="9" y1="3" x2="9" y2="18"/>
          <line x1="15" y1="6" x2="15" y2="21"/>
        </svg>
        Controls
      </button>
    </div>
    <div
      v-if="!isMobile || open"
      class="map-controls"
    >
      <DatePicker
        :model-value="controls.selectedDate"
        :allowed-dates="controls.allowedDates"
        @update:model-value="emit('update:controls', { ...controls, selectedDate: $event })"
      />

      <TimeSlider
        :selected-hour="controls.selectedHour"
        @update:selected-hour="emit('update:controls', { ...controls, selectedHour: $event })"
      />

      <span v-if="resolution" class="res-badge">
        H3 res {{ resolution }}
      </span>
    </div>

    <!-- optional backdrop -->
    <div v-if="isMobile && open" class="backdrop" @click="open = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import DatePicker from './DatePicker.vue'
import TimeSlider from './TimeSlider.vue'

interface Controls {
  selectedDate: string
  selectedHour: number
  allowedDates: string[]
}

const props = defineProps<{
  controls: Controls
  resolution?: number | null
}>()

const emit = defineEmits<{
  'update:controls': [controls: Controls]
}>()

const open = ref(false)

const isMobile = ref(false)

const checkMobile = () => {
  isMobile.value = window.innerWidth <= 850
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.map-controls {
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 1100;
  display: flex;
  align-items: center;
  gap: 10px;
  background: white;
  padding: 8px 12px;
  border-radius: 12px;
  box-shadow: 0 0 12px rgba(0, 0, 0, 0.16);
}

.res-badge {
  background: color-mix(in srgb, #337ab7 15%, transparent);
  color: #185FA5;
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 1em;
  font-weight: 500;
  max-width: 90px;
  text-align: center;
  border: none;
}

.mobile-toggle-wrapper {
  top: 1rem;
  left: 1rem;
  height: 40px;
  z-index: 1100;
  background: white;
  border: 1px solid #ccc;
  border-radius: 8px;
  padding: 5px;
  display: none;
  position: absolute;
  box-shadow: 0 0 12px rgba(0, 0, 0, 0.16);
}

.mobile-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82em;
  font-weight: 400;
  padding: 5px 10px;
  background: #f4f4f5;
  border: 1px solid #a1a1aa;
  color: #18181b;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.mobile-toggle:hover {
  background: #e4e4e7;
  border-color: #71717a;
}

.icon {
  width: 16px;
  height: 16px;
  color: currentColor;
  flex-shrink: 0;
}

.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.2);
  z-index: 999;
}

@media (max-width: 850px) {
  .map-controls {
    position: absolute;
    top: 60px;
    left: 10px;
    right: 10px;
    flex-direction: column;
    align-items: stretch;
    width: max-content;
  }

  .mobile-toggle-wrapper {
    display: block;
  }
}
</style>