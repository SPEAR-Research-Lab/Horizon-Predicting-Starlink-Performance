<script lang="ts">
const base = import.meta.env.BASE_URL

async function fetchGridPredictions(resolution: number = 2) {
  const singleUrl = `${base}predicted_hex_res${resolution}.json`
  const singleResp = await fetch(singleUrl)
  if (singleResp.ok) {
    return await singleResp.json()
  }

  const merged: Record<string, any> = {}
  for (let i = 1; i <= 4; i++) {
    const partUrl = `${base}predicted_hex_res${resolution}_part${i}.json`
    const resp = await fetch(partUrl)
    if (!resp.ok) break
    const chunk = await resp.json()
    Object.assign(merged, chunk)
  }
  return merged
}

async function fetchDotPredictions() {
  const response = await fetch(`${base}dot_predictions.json`)
  return await response.json()
}

export default {}
export { fetchGridPredictions, fetchDotPredictions }
</script>
