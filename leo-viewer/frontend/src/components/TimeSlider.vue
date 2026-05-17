<template>
  <div class="hour-control">
    <svg
      class="icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>

    <input
      type="range"
      :value="selectedHour"
      min="0"
      max="23"
      step="1"
      :style="{ '--pct': pct }"
      @input="onHourInput"
      aria-label="Hour"
    />

    <div class="divider" />

    <span class="time">{{ selectedHour }}:00 (UTC)</span>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({ selectedHour: { type: Number, required: true } });
const emit = defineEmits(["update:selectedHour"]);

const pct = computed(() => Math.round((props.selectedHour / 23) * 100) + "%");

function onHourInput(e) {
  emit("update:selectedHour", parseInt(e.target.value));
}
</script>

<style scoped>
.hour-control {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 40px;
  padding: 0 16px 0 14px;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  width: 280px;
}

.icon {
  width: 16px;
  height: 16px;
  color: #9ca3af;
  flex-shrink: 0;
}

input[type="range"] {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: 2px;
  outline: none;
  border: none;
  background: none;
  background: linear-gradient(to right, #378add var(--pct), #e5e7eb var(--pct));
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #378add;
  cursor: pointer;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #378add;
}

.divider {
  width: 1px;
  height: 20px;
  background: #e5e7eb;
  flex-shrink: 0;
}

.time {
  font-size: 0.9rem;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
  width: 10ch;
  text-align: right;
  flex-shrink: 0;
}
</style>