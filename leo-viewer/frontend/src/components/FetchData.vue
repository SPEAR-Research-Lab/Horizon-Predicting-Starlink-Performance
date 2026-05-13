<script lang="ts">
const base = import.meta.env.BASE_URL

async function fetchGridPredictions(resolution: number = 2) {
  const response = await fetch(`${base}predicted_hex_res${resolution}.json`)
  return await response.json()
}

async function fetchDotPredictions() {
  const response = await fetch(`${base}dot_predictions.json`)
  return await response.json()
}

export default {}
export { fetchGridPredictions, fetchDotPredictions }
</script>
