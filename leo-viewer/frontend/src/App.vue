<template>
  <div>
    <div class="topbar">
      <button @click="view = 'grid'" :class="{ active: view === 'grid' }">Grid Map</button>
      <button @click="view = 'dots'" :class="{ active: view === 'dots' }">Dot Map</button>
    </div>
    <GridMap
      v-if="view === 'grid'"
      :controls="controls"
      @update:controls="controls = $event"
    />
    <DotMap
      v-if="view === 'dots'"
      :controls="controls"
      @update:controls="controls = $event"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GridMap from './components/GridMap.vue'
import DotMap from './components/DotMap.vue'

const view = ref('grid')

const controls = ref({
  selectedDate: new Date().toISOString().slice(0, 10),
  selectedHour: new Date().getUTCHours(),
  allowedDates: [] as string[],
})
</script>

<style>
html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  overflow: hidden;
  color: black;
}

.topbar {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  background: white;
  padding: 8px 16px;
  border-radius: 12px;
  box-shadow: 0 0 12px rgba(0, 0, 0, 0.16);
  display: flex;
  gap: 12px;
}

@media (max-width: 1400px) {
  .topbar {
    left: auto;
    right: 1rem;
    transform: none;
  }
}

.topbar button {
  font-size: 1em;
  background: #fafbfc;
  border: 1px solid #ccc;
  border-radius: 8px;
  padding: 6px 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.topbar button:hover {
  background: #e0e0e0;
}

.topbar button.active {
  background: #e0e0e0;
  border-color: #999;
}

@media (max-width: 850px) {
  .topbar {
    top: 10px;
    right: 10px;
    padding: 6px 10px;
    gap: 8px;
  }

  .topbar button {
    font-size: 0.82em;
    padding: 5px 10px;
  }
}
</style>