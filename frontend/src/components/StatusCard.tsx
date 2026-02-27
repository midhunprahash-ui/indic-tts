import type { ModelCatalogItem } from '../api/types'
import type { ModelRunState } from '../state/usePlaygroundStore'
import { getModelParts } from '../utils/modelDisplay'

interface StatusCardProps {
  model: ModelCatalogItem
  state: ModelRunState
}

function toAudioSrc(state: ModelRunState): string | undefined {
  if (!state.result?.success) {
    return undefined
  }
  if (state.result.audio_url) {
    return state.result.audio_url
  }
  if (state.result.audio_base64) {
    return `data:audio/wav;base64,${state.result.audio_base64}`
  }
  return undefined
}

export function StatusCard({ model, state }: StatusCardProps) {
  const audioSrc = toAudioSrc(state)
  const { providerLabel, modelLabel } = getModelParts(model)

  return (
    <article className={`status-card ${state.status}`}>
      <header>
        <div>
          <p className="provider-chip">{providerLabel}</p>
          <h4>{modelLabel}</h4>
        </div>
        <span className={`pill ${state.status}`}>{state.status}</span>
      </header>
      <p className="card-meta">
        Latency: {state.result?.latency_ms ?? 0}ms · Streaming: {state.result?.streaming_used ? 'yes' : 'no'}
      </p>
      {audioSrc ? <audio controls src={audioSrc} /> : null}
      {state.result?.error ? <p className="error-text">{state.result.error}</p> : null}
    </article>
  )
}
