import { useCallback, useMemo, useState } from 'react'
import { fetchCatalog, synthesizeBatch, synthesizeOne } from '../api/client'
import type { ModelCatalogItem, SynthesisResult } from '../api/types'

export type ModelStatus = 'idle' | 'queued' | 'running' | 'success' | 'error'

export interface ModelRunState {
  status: ModelStatus
  result?: SynthesisResult
}

type ConfigMap = Record<string, Record<string, unknown>>

function buildDefaults(models: ModelCatalogItem[]): ConfigMap {
  const map: ConfigMap = {}
  for (const model of models) {
    map[model.model_id] = {}
    for (const field of model.config_schema) {
      map[model.model_id][field.key] = field.default
    }
  }
  return map
}

export function usePlaygroundStore() {
  const [models, setModels] = useState<ModelCatalogItem[]>([])
  const [activeModelId, setActiveModelId] = useState<string>('')
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([])
  const [text, setText] = useState<string>('Vanakkam! This is Tanglish text-to-speech testing.')
  const [modelConfigs, setModelConfigs] = useState<ConfigMap>({})
  const [results, setResults] = useState<Record<string, ModelRunState>>({})
  const [loadingCatalog, setLoadingCatalog] = useState(false)
  const [globalError, setGlobalError] = useState<string | null>(null)

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true)
    setGlobalError(null)
    try {
      const response = await fetchCatalog()
      setModels(response.models)
      if (response.models.length > 0) {
        setActiveModelId(response.models[0].model_id)
      }
      setSelectedModelIds(response.models.map((m) => m.model_id))
      setModelConfigs(buildDefaults(response.models))

      const initialResults: Record<string, ModelRunState> = {}
      for (const model of response.models) {
        initialResults[model.model_id] = { status: 'idle' }
      }
      setResults(initialResults)
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : 'Failed to load model catalog')
    } finally {
      setLoadingCatalog(false)
    }
  }, [])

  const setModelConfig = useCallback((modelId: string, key: string, value: unknown) => {
    setModelConfigs((prev) => ({
      ...prev,
      [modelId]: {
        ...(prev[modelId] || {}),
        [key]: value,
      },
    }))
  }, [])

  const toggleSelectedModel = useCallback((modelId: string) => {
    setSelectedModelIds((prev) =>
      prev.includes(modelId) ? prev.filter((id) => id !== modelId) : [...prev, modelId],
    )
  }, [])

  const runSingle = useCallback(async () => {
    if (!activeModelId || !text.trim()) {
      return
    }

    const activeModelMeta = models.find((model) => model.model_id === activeModelId)
    if (activeModelMeta && !activeModelMeta.configured) {
      setResults((prev) => ({
        ...prev,
        [activeModelId]: {
          status: 'error',
          result: {
            model_id: activeModelId,
            success: false,
            latency_ms: 0,
            streaming_used: false,
            error:
              activeModelMeta.config_warnings.join('; ') ||
              'Model is not configured. Add required environment variables.',
          },
        },
      }))
      return
    }

    setResults((prev) => ({
      ...prev,
      [activeModelId]: { status: 'running' },
    }))

    try {
      const response = await synthesizeOne({
        model_id: activeModelId,
        text,
        config_overrides: modelConfigs[activeModelId] || {},
        prefer_streaming: true,
      })

      const status: ModelStatus = response.result.success ? 'success' : 'error'
      setResults((prev) => ({
        ...prev,
        [activeModelId]: { status, result: response.result },
      }))
    } catch (error) {
      setResults((prev) => ({
        ...prev,
        [activeModelId]: {
          status: 'error',
          result: {
            model_id: activeModelId,
            success: false,
            latency_ms: 0,
            streaming_used: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          },
        },
      }))
    }
  }, [activeModelId, modelConfigs, models, text])

  const runBatch = useCallback(async () => {
    const modelIds = selectedModelIds.length > 0 ? selectedModelIds : activeModelId ? [activeModelId] : []
    if (modelIds.length === 0 || !text.trim()) {
      return
    }

    const modelMap = new Map(models.map((model) => [model.model_id, model]))
    const runnableModelIds: string[] = []
    const notConfiguredModelIds: string[] = []
    for (const id of modelIds) {
      const meta = modelMap.get(id)
      if (meta && !meta.configured) {
        notConfiguredModelIds.push(id)
      } else {
        runnableModelIds.push(id)
      }
    }

    setResults((prev) => {
      const next = { ...prev }
      for (const id of runnableModelIds) {
        next[id] = { status: 'queued' }
      }
      for (const id of notConfiguredModelIds) {
        const meta = modelMap.get(id)
        next[id] = {
          status: 'error',
          result: {
            model_id: id,
            success: false,
            latency_ms: 0,
            streaming_used: false,
            error:
              meta?.config_warnings.join('; ') ||
              'Model is not configured. Add required environment variables.',
          },
        }
      }
      return next
    })

    if (runnableModelIds.length === 0) {
      return
    }

    setResults((prev) => {
      const next = { ...prev }
      for (const id of runnableModelIds) {
        next[id] = { status: 'running' }
      }
      return next
    })

    try {
      const perModelConfig: Record<string, Record<string, unknown>> = {}
      for (const id of modelIds) {
        perModelConfig[id] = modelConfigs[id] || {}
      }

      const response = await synthesizeBatch({
        model_ids: runnableModelIds,
        text,
        per_model_config: perModelConfig,
        prefer_streaming: true,
      })

      setResults((prev) => {
        const next = { ...prev }
        for (const result of response.results) {
          next[result.model_id] = {
            status: result.success ? 'success' : 'error',
            result,
          }
        }
        return next
      })
    } catch (error) {
      setResults((prev) => {
        const next = { ...prev }
        for (const id of runnableModelIds) {
          next[id] = {
            status: 'error',
            result: {
              model_id: id,
              success: false,
              latency_ms: 0,
              streaming_used: false,
              error: error instanceof Error ? error.message : 'Batch request failed',
            },
          }
        }
        return next
      })
    }
  }, [activeModelId, modelConfigs, models, selectedModelIds, text])

  const activeModel = useMemo(
    () => models.find((model) => model.model_id === activeModelId),
    [activeModelId, models],
  )

  return {
    models,
    activeModel,
    activeModelId,
    selectedModelIds,
    text,
    modelConfigs,
    results,
    loadingCatalog,
    globalError,
    setActiveModelId,
    toggleSelectedModel,
    setText,
    setModelConfig,
    loadCatalog,
    runSingle,
    runBatch,
  }
}
