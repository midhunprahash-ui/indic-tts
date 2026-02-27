import type { ModelCatalogItem } from '../api/types'
import { getModelParts } from '../utils/modelDisplay'

interface ModelSidebarProps {
  model?: ModelCatalogItem
  config: Record<string, unknown>
  onChange: (key: string, value: unknown) => void
}

function renderInput(
  modelId: string,
  field: ModelCatalogItem['config_schema'][number],
  value: unknown,
  onChange: (value: unknown) => void,
) {
  const id = `${modelId}-${field.key}`

  if (field.input_type === 'textarea') {
    return (
      <textarea
        id={id}
        value={typeof value === 'string' ? value : ''}
        onChange={(event) => onChange(event.target.value)}
        placeholder={field.placeholder || ''}
      />
    )
  }

  if (field.input_type === 'select') {
    return (
      <select id={id} value={String(value ?? '')} onChange={(event) => onChange(event.target.value)}>
        {field.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    )
  }

  if (field.input_type === 'slider') {
    return (
      <div className="slider-wrap">
        <input
          id={id}
          type="range"
          min={field.min ?? undefined}
          max={field.max ?? undefined}
          step={field.step ?? undefined}
          value={Number(value ?? field.default ?? 0)}
          onChange={(event) => onChange(Number(event.target.value))}
        />
        <span>{Number(value ?? field.default ?? 0).toFixed(2)}</span>
      </div>
    )
  }

  if (field.input_type === 'number') {
    return (
      <input
        id={id}
        type="number"
        min={field.min ?? undefined}
        max={field.max ?? undefined}
        step={field.step ?? undefined}
        value={Number(value ?? field.default ?? 0)}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    )
  }

  if (field.input_type === 'checkbox') {
    return (
      <input
        id={id}
        type="checkbox"
        checked={Boolean(value)}
        onChange={(event) => onChange(event.target.checked)}
      />
    )
  }

  return (
    <input
      id={id}
      type="text"
      value={String(value ?? '')}
      onChange={(event) => onChange(event.target.value)}
      placeholder={field.placeholder || ''}
    />
  )
}

export function ModelSidebar({ model, config, onChange }: ModelSidebarProps) {
  if (!model) {
    return <aside className="sidebar">Select a model tab.</aside>
  }

  const { providerLabel, modelLabel } = getModelParts(model)

  return (
    <aside className="sidebar">
      <h2>{modelLabel}</h2>
      <p className="meta">
        Provider: {providerLabel} · {model.category === 'cloud' ? 'Cloud API' : 'Self-hosted'}
      </p>
      {!model.configured ? (
        <div className="warning-box">
          <strong>Not configured</strong>
          <ul>
            {model.config_warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="field-list">
        {model.config_schema.map((field) => (
          <label className="field" key={field.key} htmlFor={`${model.model_id}-${field.key}`}>
            <span>{field.label}</span>
            {renderInput(model.model_id, field, config[field.key], (value) => onChange(field.key, value))}
            {field.help_text ? <small>{field.help_text}</small> : null}
          </label>
        ))}
      </div>
    </aside>
  )
}
