<template>
  <div class="date-picker" ref="pickerRef">
    <div
      class="trigger"
      :class="{ open: isOpen }"
      @click="toggle"
      role="combobox"
      :aria-expanded="isOpen"
      aria-haspopup="listbox"
      tabindex="0"
      @keydown="onTriggerKeydown"
    >
      <span class="trigger-left">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <path d="M16 2v4M8 2v4M3 10h18" />
        </svg>
        <span class="trigger-label">{{ selectedLabel }}</span>
      </span>
      <svg
        class="chevron"
        :class="{ open: isOpen }"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        aria-hidden="true"
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </div>

    <Transition name="dropdown">
      <div
        v-if="isOpen"
        class="dropdown"
        role="listbox"
        :aria-label="'Select date'"
        ref="dropdownRef"
      >
        <div
          v-for="(d, i) in allowedDates"
          :key="d"
          class="option"
          :class="{ selected: d === selectedDate }"
          role="option"
          :aria-selected="d === selectedDate"
          :tabindex="isOpen ? 0 : -1"
          @click="select(d)"
          @keydown="(e) => onOptionKeydown(e, i)"
        >
          <span>{{ formatDate(d) }}</span>
          <svg
            v-if="d === selectedDate"
            class="check"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <path d="M5 13l4 4L19 7" />
          </svg>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: null,
  },
  allowedDates: {
    type: Array,
    required: true,
    // Expects ISO date strings: ['2026-05-12', '2026-05-13', ...]
  },
})

const emit = defineEmits(['update:modelValue', 'change'])

const pickerRef = ref(null)
const dropdownRef = ref(null)
const isOpen = ref(false)

const selectedDate = computed(() => props.modelValue ?? props.allowedDates[0] ?? null)

const selectedLabel = computed(() =>
  selectedDate.value ? formatDate(selectedDate.value) : 'Select a date'
)

function formatDate(isoString) {
  const date = new Date(isoString + 'T00:00:00')
  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

function toggle() {
  isOpen.value = !isOpen.value
}

function select(date) {
  emit('update:modelValue', date)
  emit('change', date)
  isOpen.value = false
}

function close() {
  isOpen.value = false
}

function onTriggerKeydown(e) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    toggle()
  } else if (e.key === 'Escape') {
    close()
  } else if (e.key === 'ArrowDown' && isOpen.value) {
    e.preventDefault()
    dropdownRef.value?.querySelector('.option')?.focus()
  }
}

function onOptionKeydown(e, index) {
  const options = dropdownRef.value?.querySelectorAll('.option')
  if (!options) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    options[Math.min(index + 1, options.length - 1)]?.focus()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (index === 0) pickerRef.value?.querySelector('.trigger')?.focus()
    else options[index - 1]?.focus()
  } else if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    select(props.allowedDates[index])
  } else if (e.key === 'Escape') {
    close()
    pickerRef.value?.querySelector('.trigger')?.focus()
  }
}

function onClickOutside(e) {
  if (pickerRef.value && !pickerRef.value.contains(e.target)) {
    close()
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<style scoped>
.date-picker {
  position: relative;
  width: 150px;
  font-family: inherit;
  font-size: 0.9em;
}

.trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  height: 40px;
  cursor: pointer;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  color: #111827;
  user-select: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  outline: none;
}

.trigger:hover {
  border-color: #9ca3af;
}

.trigger:focus-visible {
  border-color: #378add;
  box-shadow: 0 0 0 3px rgba(55, 138, 221, 0.2);
}

.trigger.open {
  border-color: #378add;
  box-shadow: 0 0 0 3px rgba(55, 138, 221, 0.2);
}

.trigger-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #374151;
}

.trigger-label {
  color: #111827;
  font-weight: 400;
}

.icon {
  width: 16px;
  height: 16px;
  color: #6b7280;
  flex-shrink: 0;
}

.chevron {
  width: 16px;
  height: 16px;
  color: #9ca3af;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.chevron.open {
  transform: rotate(180deg);
}

.dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow-x: hidden;
  overflow-y: auto;
  max-height: 220px;
  z-index: 50;
}

.option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  cursor: pointer;
  color: #111827;
  transition: background 0.1s;
  outline: none;
}

.option:not(:last-child) {
  border-bottom: 1px solid #f3f4f6;
}

.option:hover,
.option:focus-visible {
  background: #f9fafb;
}

.option.selected {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 400;
}

.option.selected:hover,
.option.selected:focus-visible {
  background: #dbeafe;
}

.check {
  width: 15px;
  height: 15px;
  color: #2563eb;
  flex-shrink: 0;
}

/* Dropdown transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>