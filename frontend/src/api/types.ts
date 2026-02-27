export type ModelCategory = 'cloud' | 'self_hosted'

export interface ConfigFieldOption {
  label: string
  value: string
}

export interface ConfigField {
  key: string
  label: string
  input_type: 'text' | 'textarea' | 'number' | 'select' | 'checkbox' | 'slider'
  required: boolean
  default: string | number | boolean | null
  min?: number | null
  max?: number | null
  step?: number | null
  options: ConfigFieldOption[]
  placeholder?: string | null
  help_text?: string | null
}

export interface ModelCapabilities {
  streaming_available: boolean
  supports_speed: boolean
  supports_pitch: boolean
  supports_prompt_style: boolean
}

export interface ModelCatalogItem {
  model_id: string
  display_name: string
  provider: string
  category: ModelCategory
  capabilities: ModelCapabilities
  config_schema: ConfigField[]
  configured: boolean
  config_warnings: string[]
  runtime_alias?: string | null
}

export interface ModelCatalogResponse {
  models: ModelCatalogItem[]
}

export interface SynthesisResult {
  model_id: string
  success: boolean
  audio_base64?: string | null
  audio_url?: string | null
  latency_ms: number
  streaming_used: boolean
  error?: string | null
}

export interface SynthesizeResponse {
  result: SynthesisResult
}

export interface BatchSynthesizeResponse {
  results: SynthesisResult[]
  summary: {
    total: number
    success_count: number
    failure_count: number
    duration_ms: number
  }
}
