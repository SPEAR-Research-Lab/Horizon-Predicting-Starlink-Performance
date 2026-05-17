<template>
  <div>
    <Legend :colorLegend="colorLegend" title="Network Quality" />
    <MapControls
      :controls="controls"
      :resolution="currentResolution"
      @update:controls="emit('update:controls', $event)"
    />
    <div v-if="loading" class="loading-overlay">Loading...</div>
    <div id="grid-map" class="map-container"></div>
    <div v-if="tooltip.show" :style="tooltip.style" class="dot-tooltip">
      <div><b>{{ tooltip.data.date }} {{ tooltip.data.hour }}:00</b></div>
      <div>Lat: {{ tooltip.data.lat }}</div>
      <div>Lon: {{ tooltip.data.lon }}</div>
      <div>Latency: {{ Number(tooltip.data.latency).toFixed(1) }} ms</div>
      <div>Throughput: {{ Number(tooltip.data.throughput).toFixed(1) }} Mbps</div>
      <div v-if="tooltip.data.sat_density !== undefined">
        SatDensity: {{ tooltip.data.sat_density }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Legend from './Legend.vue'
import MapControls from './MapControls.vue'
import { fetchGridPredictions } from './FetchData.vue'
import { ref, reactive, watch, onMounted, nextTick } from 'vue'
import maplibregl, { Map } from 'maplibre-gl'
import * as h3 from 'h3-js'

interface Controls {
  selectedDate: string
  selectedHour: number
  allowedDates: string[]
}

const props = defineProps<{ controls: Controls }>()
const emit = defineEmits<{ 'update:controls': [controls: Controls] }>()

const colorLegend = [
  { color: '#1a9850', label: 'Excellent' },
  { color: '#91cf60', label: 'Good' },
  { color: '#d9ef8b', label: 'Fair' },
  { color: '#fee08b', label: 'Average' },
  { color: '#fc8d59', label: 'Bad' },
  { color: '#d73027', label: 'Very Bad' },
  { color: '#800026', label: 'Extreme/Unusable' },
]

const tooltip = reactive({
  show: false,
  style: {
    position: 'fixed' as const,
    left: '0px', top: '0px',
    zIndex: 10000, pointerEvents: 'none' as const,
    background: '#fff', color: '#222',
    border: '1px solid #aaa', borderRadius: '8px',
    padding: '10px', fontSize: '1em',
    boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
  },
  data: {} as any,
})

const predictionsByRes = ref<Record<number, Record<string, any[]>>>({})
const currentResolution = ref(2)
const loading = ref(false)

let map: Map
let mapLoaded = false
let zoomDebounceTimer: ReturnType<typeof setTimeout> | null = null

function getResolutionForZoom(zoom: number): number {
  if (zoom < 4) return 2
  if (zoom < 7) return 3
  return 4
}

async function loadResolution(res: number) {
  if (predictionsByRes.value[res]) return
  loading.value = true
  try {
    predictionsByRes.value[res] = await fetchGridPredictions(res)
  } finally {
    loading.value = false
  }
}

function extractDates(resData: Record<string, any[]>) {
  const dates = new Set<string>()
  Object.values(resData).forEach((arr) => arr.forEach((rec: any) => dates.add(rec.date)))
  return Array.from(dates).sort()
}

function getPrediction(resData: Record<string, any[]>, h3Index: string, date: string, hour: number) {
  const preds = resData[h3Index]
  if (!preds) return null
  return preds.find((p) => p.date === date && Number(p.hour) === Number(hour))
}

function fixAntimeridian(coords: [number, number][]): [number, number][][] {
  let crosses = false
  for (let i = 1; i < coords.length; i++) {
    if (Math.abs(coords[i - 1][0] - coords[i][0]) > 180) { crosses = true; break }
  }
  if (!crosses) return [[...coords, coords[0]]]
  const west: [number, number][] = []
  const east: [number, number][] = []
  coords.forEach(([lng, lat]) => { if (lng < 0) west.push([lng, lat]); else east.push([lng, lat]) })
  return [[...west, west[0]], [...east, east[0]]]
}

function makeGeoJSON() {
  const resData = predictionsByRes.value[currentResolution.value]
  if (!resData) return { type: 'FeatureCollection', features: [] }
  const features = Object.keys(resData)
    .map((h3Index) => {
      const pred = getPrediction(resData, h3Index, props.controls.selectedDate, props.controls.selectedHour)
      if (!pred) return null
      const boundary = h3.cellToBoundary(h3Index, true)
      const rings = fixAntimeridian(boundary)
      return {
        type: 'Feature',
        geometry: { type: 'MultiPolygon', coordinates: rings.map((ring) => [ring]) },
        properties: { h3Index, ...pred, color: pred.color },
      }
    })
    .filter(Boolean)
  return { type: 'FeatureCollection', features }
}

function updateLayer() {
  if (!mapLoaded) return
  const source = map.getSource('prediction-grid') as maplibregl.GeoJSONSource
  if (source) source.setData(makeGeoJSON())
}

onMounted(async () => {
  await loadResolution(2)

  const resData = predictionsByRes.value[2]
  if (resData) {
    const dates = extractDates(resData)
    const currentDate = props.controls.selectedDate
    emit('update:controls', {
      ...props.controls,
      allowedDates: dates,
      selectedDate: dates.includes(currentDate) ? currentDate : (dates[0] ?? currentDate),
    })
  }

  await nextTick()

  map = new maplibregl.Map({
    container: 'grid-map',
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    center: [0, 20],
    zoom: 2,
  })
  map.dragRotate.disable()
  map.keyboard.disableRotation()
  map.touchZoomRotate.disableRotation()

  map.on('load', () => {
    mapLoaded = true

    map.addSource('prediction-grid', { type: 'geojson', data: makeGeoJSON() })
    map.addLayer({
      id: 'prediction-layer',
      type: 'fill',
      source: 'prediction-grid',
      paint: {
        'fill-color': ['get', 'color'],
        'fill-opacity': 0.5,
        'fill-outline-color': '#333',
      },
    })

    map.on('mousemove', 'prediction-layer', (e) => {
      if (!e.features?.length) { tooltip.show = false; return }
      tooltip.data = e.features[0].properties
      const { x, y } = e.originalEvent
      tooltip.style.left = x + 15 + 'px'
      tooltip.style.top = y + 15 + 'px'
      tooltip.show = true
    })
    map.on('mouseleave', 'prediction-layer', () => { tooltip.show = false })

    map.on('zoomend', () => {
      if (zoomDebounceTimer) clearTimeout(zoomDebounceTimer)
      zoomDebounceTimer = setTimeout(async () => {
        const newRes = getResolutionForZoom(map.getZoom())
        if (newRes !== currentResolution.value) {
          currentResolution.value = newRes
          await loadResolution(newRes)
          updateLayer()
        }
      }, 300)
    })

    map.on('moveend', () => { updateLayer() })

    updateLayer()
    watch(() => [props.controls.selectedDate, props.controls.selectedHour], updateLayer)
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
.loading-overlay {
  position: fixed;
  top: 70px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 8px 20px;
  border-radius: 8px;
  z-index: 9999;
  font-family: sans-serif;
}
.dot-tooltip {
  pointer-events: none;
  min-width: 170px;
  white-space: nowrap;
}
</style>