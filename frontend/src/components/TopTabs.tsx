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
    <section className="tab-group" aria-label={title}>
      <h3>{title}</h3>
      <div className="provider-groups">
        {providerGroups.map((group) => (
          <div className="provider-group" key={group.provider}>
            <p className="provider-title">{group.provider}</p>
            <div className="tab-list">
              {group.models.map((model) => {
                const active = model.model_id === activeModelId
                const selected = selectedModelIds.includes(model.model_id)
                const { modelLabel } = getModelParts(model)
                return (
                  <button
                    key={model.model_id}
                    type="button"
                    className={`model-tab ${active ? 'active' : ''} ${model.configured ? '' : 'unconfigured'}`.trim()}
                    onClick={() => onSelectTab(model.model_id)}
                  >
                    <span>{modelLabel}</span>
                    {!model.configured ? <small className="mini-warning">Not configured</small> : null}
                    <input
                      aria-label={`Select ${model.display_name}`}
                      type="checkbox"
                      checked={selected}
                      onChange={() => onToggleSelected(model.model_id)}
                      onClick={(event) => event.stopPropagation()}
                    />
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
    <div className="top-tabs">
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
