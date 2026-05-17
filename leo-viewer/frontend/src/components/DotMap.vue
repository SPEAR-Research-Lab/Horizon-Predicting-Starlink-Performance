<template>
  <div>
    <Legend :colorLegend="colorLegend" title="Network Quality" />
    <MapControls
      :controls="controls"
      @update:controls="emit('update:controls', $event)"
    />
    <div id="dot-map" class="map-container"></div>
    <TooltipCard
      :show="tooltip.show"
      :x="tooltip.x"
      :y="tooltip.y"
      :data="tooltip.data"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, nextTick } from 'vue'
import maplibregl, { Map } from 'maplibre-gl'
import Legend from './Legend.vue'
import MapControls from './MapControls.vue'
import TooltipCard from './TooltipCard.vue'
import { fetchDotPredictions } from './FetchData.vue'

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

const dotData = ref<any[]>([])

const tooltip = reactive({
  show: false,
  x: 0,
  y: 0,
  data: {} as Record<string, any>,
})

let map: Map | null = null
let dotLayerAdded = false

async function loadDotData() {
  dotData.value = await fetchDotPredictions()
  if (!Array.isArray(dotData.value)) dotData.value = []
  const dates = [...new Set(dotData.value.map((d) => d.Date))].sort()
  const currentDate = props.controls.selectedDate
  emit('update:controls', {
    ...props.controls,
    allowedDates: dates,
    selectedDate: dates.includes(currentDate) ? currentDate : (dates[0] ?? currentDate),
  })
}

function makeDotGeoJSON() {
  const features = dotData.value
    .filter((d) => d.Date === props.controls.selectedDate && Number(d.Hour) === Number(props.controls.selectedHour))
    .map((d, i) => ({
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
      map!.addSource('dot-predictions', { type: 'geojson', data: makeDotGeoJSON() })
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
      if (!e.features?.length) { tooltip.show = false; return }
      const p = e.features[0].properties
      tooltip.data = {
        lat: p.lat,
        lon: p.lon,
        date: p.Date ?? p.date,
        hour: p.Hour ?? p.hour,
        latency: p.Pred_Latency,
        throughput: p.Pred_Throughput,
        sat_density: p.sat_density,
      }
      tooltip.x = e.originalEvent.x + 15
      tooltip.y = e.originalEvent.y + 15
      tooltip.show = true
    })
    map!.on('mouseleave', 'dot-layer', () => { tooltip.show = false })
    map!.on('touchstart', () => { tooltip.show = false })
    map!.on('movestart', () => { tooltip.show = false })

    watch(() => [props.controls.selectedDate, props.controls.selectedHour], updateDotsLayer)
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
</style>