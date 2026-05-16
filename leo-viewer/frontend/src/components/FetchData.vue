<script lang="ts">
const base = import.meta.env.BASE_URL

async function fetchGridPredictions(resolution: number = 2) {
  const singleUrl = `${base}predicted_hex_res${resolution}.json`
  try {
    const singleResp = await fetch(singleUrl)
    if (singleResp.ok && singleResp.headers.get('content-type')?.includes('json')) {
      return await singleResp.json()
    }
  } catch {}

  const merged: Record<string, any> = {}
  for (let i = 1; i <= 4; i++) {
    const partUrl = `${base}predicted_hex_res${resolution}_part${i}.json`
    try {
      const resp = await fetch(partUrl)
      if (!resp.ok) break
      const chunk = await resp.json()
      Object.assign(merged, chunk)
    } catch { break }
  }
  return Object.keys(merged).length > 0 ? merged : {}
}

async function fetchDotPredictions() {
  const response = await fetch(`${base}dot_predictions.json`)
  if (!response.ok) return []
  return await response.json()
}

export default {}
export { fetchGridPredictions, fetchDotPredictions }
</script>
