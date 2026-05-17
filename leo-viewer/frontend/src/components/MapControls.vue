<template>
  <div>
    <button class="mobile-toggle" @click="open = !open">
      Controls
    </button>
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
  z-index: 1000;
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
  border: none;
}

.mobile-toggle {
  display: none;
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 1100;
  background: white;
  border: 1px solid #ccc;
  padding: 8px 12px;
  border-radius: 10px;
  box-shadow: 0 0 12px rgba(0,0,0,0.15);
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
  }

  .mobile-toggle {
    display: block;
  }
}
</style>