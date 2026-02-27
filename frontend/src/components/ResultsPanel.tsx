import type { ModelCatalogItem } from '../api/types'
import type { ModelRunState } from '../state/usePlaygroundStore'
import { StatusCard } from './StatusCard'

interface ResultsPanelProps {
  models: ModelCatalogItem[]
  results: Record<string, ModelRunState>
}

export function ResultsPanel({ models, results }: ResultsPanelProps) {
  return (
    <section className="results">
      <h2>Model Outputs</h2>
      <div className="results-grid">
        {models.map((model) => (
          <StatusCard
            key={model.model_id}
            model={model}
            state={results[model.model_id] || { status: 'idle' }}
          />
        ))}
      </div>
    </section>
  )
}
