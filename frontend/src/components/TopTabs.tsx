import type { ModelCatalogItem } from '../api/types'
import { getModelParts } from '../utils/modelDisplay'

interface TopTabsProps {
  models: ModelCatalogItem[]
  activeModelId: string
  selectedModelIds: string[]
  onSelectTab: (modelId: string) => void
  onToggleSelected: (modelId: string) => void
}

interface CategoryTabsProps {
  title: string
  items: ModelCatalogItem[]
  activeModelId: string
  selectedModelIds: string[]
  onSelectTab: (modelId: string) => void
  onToggleSelected: (modelId: string) => void
}

function groupByProvider(items: ModelCatalogItem[]): Array<{ provider: string; models: ModelCatalogItem[] }> {
  const groups = new Map<string, ModelCatalogItem[]>()
  for (const item of items) {
    const { providerLabel } = getModelParts(item)
    const current = groups.get(providerLabel) || []
    current.push(item)
    groups.set(providerLabel, current)
  }
  return Array.from(groups.entries()).map(([provider, models]) => ({ provider, models }))
}

function CategoryTabs({
  title,
  items,
  activeModelId,
  selectedModelIds,
  onSelectTab,
  onToggleSelected,
}: CategoryTabsProps) {
  const providerGroups = groupByProvider(items)

  return (
    <section className="model-group" aria-label={title}>
      <div className="model-group-head">
        <h3>{title}</h3>
        <span>{items.length}</span>
      </div>
      <div className="provider-groups">
        {providerGroups.map((group) => (
          <div className="provider-group" key={group.provider}>
            <p className="provider-title">{group.provider}</p>
            <div className="model-list">
              {group.models.map((model) => {
                const active = model.model_id === activeModelId
                const selected = selectedModelIds.includes(model.model_id)
                const { modelLabel } = getModelParts(model)
                return (
                  <button
                    key={model.model_id}
                    type="button"
                    className={`model-row ${active ? 'active' : ''} ${model.configured ? '' : 'unconfigured'}`.trim()}
                    onClick={() => onSelectTab(model.model_id)}
                  >
                    <span className="model-row-title">{modelLabel}</span>
                    <input
                      aria-label={`Select ${model.display_name}`}
                      type="checkbox"
                      checked={selected}
                      onChange={() => onToggleSelected(model.model_id)}
                      onClick={(event) => event.stopPropagation()}
                    />
                    {!model.configured ? <small className="mini-warning">Not configured</small> : null}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export function TopTabs(props: TopTabsProps) {
  const cloudModels = props.models.filter((model) => model.category === 'cloud')
  const selfHostedModels = props.models.filter((model) => model.category === 'self_hosted')

  return (
    <div className="model-browser">
      <div className="model-browser-head">
        <h2>Models</h2>
        <p>Click row to edit config. Checkbox controls batch run.</p>
      </div>
      <CategoryTabs
        title="Cloud Models"
        items={cloudModels}
        activeModelId={props.activeModelId}
        selectedModelIds={props.selectedModelIds}
        onSelectTab={props.onSelectTab}
        onToggleSelected={props.onToggleSelected}
      />
      <CategoryTabs
        title="Self-hosted Models"
        items={selfHostedModels}
        activeModelId={props.activeModelId}
        selectedModelIds={props.selectedModelIds}
        onSelectTab={props.onSelectTab}
        onToggleSelected={props.onToggleSelected}
      />
    </div>
  )
}
