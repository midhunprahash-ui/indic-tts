import type { ModelCatalogItem } from '../api/types'

function titleCase(input: string): string {
  return input
    .split(/[_\-]/g)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ')
}

export function getModelParts(model: ModelCatalogItem): { providerLabel: string; modelLabel: string } {
  if (model.display_name.includes(' - ')) {
    const [providerLabel, modelLabel] = model.display_name.split(' - ', 2)
    return { providerLabel, modelLabel }
  }

  if (model.category === 'self_hosted' && model.model_id.includes('/')) {
    const [provider, ...rest] = model.model_id.split('/')
    return {
      providerLabel: titleCase(provider),
      modelLabel: rest.join('/'),
    }
  }

  return {
    providerLabel: titleCase(model.provider),
    modelLabel: model.display_name,
  }
}
