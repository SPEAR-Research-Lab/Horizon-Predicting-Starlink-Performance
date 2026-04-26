<script lang="ts">
const backendRoot = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function fetchGridPredictions(resolution: number = 2) {
  const response = await fetch(`${backendRoot}/api/predictions/grids?resolution=${resolution}`)
  return await response.json()
}

async function fetchDotPredictions() {
  const response = await fetch(`${backendRoot}/api/predictions/city`)
  return await response.json()
}

export { fetchGridPredictions, fetchDotPredictions }
</script>
