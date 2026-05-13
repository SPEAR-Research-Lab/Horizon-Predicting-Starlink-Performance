<template>
  <div>
    <Legend :colorLegend="colorLegend" title="Network Quality" />
    <div class="controls" v-if="allowedDates.length && selectedDate">
      <select v-model="selectedDate">
        <option v-for="d in allowedDates" :key="d" :value="d">{{ d }}</option>
      </select>
      <input type="range" v-model.number="selectedHour" min="0" max="23" step="1" />
      <span>{{ selectedHour }}:00</span>
    </div>
    <div id="dot-map" class="map-container"></div>
    <div v-if="tooltip.show" :style="tooltip.style" class="dot-tooltip">
      <div><b>{{ tooltip.data.Date }} {{ tooltip.data.Hour }}:00</b></div>
      <div>Lat: {{ tooltip.data.lat }}</div>
      <div>Lon: {{ tooltip.data.lon }}</div>
      <div>Latency: {{ Number(tooltip.data.Pred_Latency).toFixed(1) }} ms</div>
      <div>Throughput: {{ Number(tooltip.data.Pred_Throughput).toFixed(1) }} Mbps</div>
      <div v-if="tooltip.data.sat_density">SatDensity: {{ tooltip.data.sat_density }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, nextTick } from 'vue'
import maplibregl, { Map } from 'maplibre-gl'
import Legend from './Legend.vue'
import { fetchDotPredictions } from './FetchData.vue'

const colorLegend = [
  { color: '#1a9850', label: 'Excellent' },
  { color: '#91cf60', label: 'Good' },
  { color: '#d9ef8b', label: 'Fair' },
  { color: '#fee08b', label: 'Average' },
  { color: '#fc8d59', label: 'Bad' },
  { color: '#d73027', label: 'Very Bad' },
  { color: '#800026', label: 'Extreme/Unusable' },
]

const dotData = ref<any[]>([])
const allowedDates = ref<string[]>([])
const selectedDate = ref('')
const selectedHour = ref(0)

const tooltip = reactive({
  show: false,
  style: {
    position: 'fixed' as const,
    left: '0px',
    top: '0px',
    zIndex: 10000,
    pointerEvents: 'none' as const,
    background: '#fff',
    color: '#222',
    border: '1px solid #aaa',
    borderRadius: '8px',
    padding: '10px',
    fontSize: '1em',
    boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
  },
  data: {} as any,
})

let map: Map | null = null
let dotLayerAdded = false

async function loadDotData() {
  dotData.value = await fetchDotPredictions()
  if (!Array.isArray(dotData.value)) dotData.value = []
  allowedDates.value = [...new Set(dotData.value.map((d) => d.Date))].sort()
  selectedDate.value = allowedDates.value[0] || ''
}

function getDotsForCurrentTime() {
  return dotData.value.filter((d) => d.Date === selectedDate.value && Number(d.Hour) === Number(selectedHour.value))
}

function makeDotGeoJSON() {
  const features = getDotsForCurrentTime().map((d, i) => ({
    type: 'Feature',
    geometry: {
      type: 'Point',
      coordinates: [Number(d.lon || d.Longitude), Number(d.lat || d.Latitude)],
    },
    properties: { ...d, color: d.color || '#ccc', id: i },
  }))
  return { type: 'FeatureCollection', features }
}

function updateDotsLayer() {
  if (!map) return
  const source = map.getSource('dot-predictions') as maplibregl.GeoJSONSource
  if (source) source.setData(makeDotGeoJSON())
}

onMounted(async () => {
  await loadDotData()
  await nextTick()

  map = new maplibregl.Map({
    container: 'dot-map',
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    center: [0, 20],
    zoom: 2,
  })
  map.dragRotate.disable()
  map.keyboard.disableRotation()
  map.touchZoomRotate.disableRotation()

  map.on('load', () => {
    if (!dotLayerAdded) {
      map!.addSource('dot-predictions', {
        type: 'geojson',
        data: makeDotGeoJSON(),
      })
      map!.addLayer({
        id: 'dot-layer',
        type: 'circle',
        source: 'dot-predictions',
        paint: {
          'circle-radius': 7,
          'circle-color': ['get', 'color'],
          'circle-opacity': 0.9,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
        },
      })
      dotLayerAdded = true
    }

    map!.on('mousemove', 'dot-layer', (e) => {
      if (!e.features?.length) {
        tooltip.show = false
        return
      }
      tooltip.data = e.features[0].properties
      const { x, y } = e.originalEvent
      tooltip.style.left = x + 15 + 'px'
      tooltip.style.top = y + 15 + 'px'
      tooltip.show = true
    })
    map!.on('mouseleave', 'dot-layer', () => {
      tooltip.show = false
    })

    watch([selectedDate, selectedHour], updateDotsLayer)
  })
})
</script>

<style scoped>
.map-container {
  width: 100vw;
  height: 100vh;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 0;
}
.controls {
  position: absolute;
  top: 10px;
  left: 10px;
  background: white;
  padding: 10px;
  border-radius: 8px;
  z-index: 1;
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
  font-family: sans-serif;
  display: flex;
  gap: 10px;
  align-items: center;
}
.dot-tooltip {
  pointer-events: none;
  min-width: 170px;
  white-space: nowrap;
}
</style>
