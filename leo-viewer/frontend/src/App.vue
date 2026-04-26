<template>
  <div>
    <div class="topbar">
      <button @click="view = 'grid'" :class="{ active: view === 'grid' }">Grid Map</button>
      <button @click="view = 'dots'" :class="{ active: view === 'dots' }">Dot Map</button>
    </div>
    <GridMap v-if="view === 'grid'" />
    <DotMap v-if="view === 'dots'" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import GridMap from './components/GridMap.vue'
import DotMap from './components/DotMap.vue'
const view = ref('grid')
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
}

.topbar {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  background: white;
  padding: 10px 20px;
  border-radius: 12px;
  box-shadow: 0 0 12px rgba(0, 0, 0, 0.16);
  display: flex;
  gap: 20px;
}

.topbar button {
  font-size: 1.1em;
  background: #fafbfc;
  border: 1px solid #ccc;
  border-radius: 8px;
  padding: 7px 18px;
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
</style>
