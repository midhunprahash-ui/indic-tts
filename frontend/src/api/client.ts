import type {
  BatchSynthesizeResponse,
  ModelCatalogResponse,
  SynthesizeResponse,
} from './types'

const API_BASE = import.meta.env.VITE_BACKEND_BASE_URL || 'http://localhost:8000'

export async function fetchCatalog(): Promise<ModelCatalogResponse> {
  const response = await fetch(`${API_BASE}/models/catalog`)
  if (!response.ok) {
    throw new Error(`Failed to fetch catalog: ${response.status}`)
  }
  return response.json()
}

export async function synthesizeOne(input: {
  model_id: string
  text: string
  config_overrides: Record<string, unknown>
  prefer_streaming: boolean
}): Promise<SynthesizeResponse> {
  const response = await fetch(`${API_BASE}/tts/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })

  if (!response.ok) {
    throw new Error(`Synthesize failed: ${response.status}`)
  }
  return response.json()
}

export async function synthesizeBatch(input: {
  model_ids: string[]
  text: string
  per_model_config: Record<string, Record<string, unknown>>
  prefer_streaming: boolean
}): Promise<BatchSynthesizeResponse> {
  const response = await fetch(`${API_BASE}/tts/synthesize-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })

  if (!response.ok) {
    throw new Error(`Batch synthesize failed: ${response.status}`)
  }
  return response.json()
}
