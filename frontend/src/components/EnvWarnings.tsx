import type { ModelCatalogItem } from '../api/types'

interface EnvWarningsProps {
  models: ModelCatalogItem[]
}

export function EnvWarnings({ models }: EnvWarningsProps) {
  const unconfigured = models.filter((model) => !model.configured)
  if (unconfigured.length === 0) {
    return null
  }

  return (
    <section className="env-warnings" aria-label="Environment warnings">
      <details>
        <summary>
          <strong>{unconfigured.length} model(s) not configured.</strong> Expand for required env vars.
        </summary>
        <ul>
          {unconfigured.map((model) => (
            <li key={model.model_id}>
              {model.display_name}: {model.config_warnings.join(', ')}
            </li>
          ))}
        </ul>
      </details>
    </section>
  )
}
