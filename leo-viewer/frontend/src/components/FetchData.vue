<script lang="ts">
async function fetchGridPredictions(resolution: number = 2) {
  const response = await fetch(`/predicted_hex_res${resolution}.json`)
  return await response.json()
}

async function fetchDotPredictions() {
  const response = await fetch('/dot_predictions.json')
  return await response.json()
}

export default {}
export { fetchGridPredictions, fetchDotPredictions }
</script>
