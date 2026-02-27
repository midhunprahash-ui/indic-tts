import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from '../App'
import * as api from '../api/client'

vi.mock('../api/client', () => ({
  fetchCatalog: vi.fn(),
  synthesizeOne: vi.fn(),
  synthesizeBatch: vi.fn(),
}))

describe('Batch synthesis partial failures', () => {
  it('shows success audio and error independently per model', async () => {
    vi.mocked(api.fetchCatalog).mockResolvedValue({
      models: [
        {
          model_id: 'model-a',
          display_name: 'Model A',
          provider: 'test',
          category: 'cloud',
          capabilities: {
            streaming_available: true,
            supports_speed: false,
            supports_pitch: false,
            supports_prompt_style: false,
          },
          config_schema: [],
          configured: true,
          config_warnings: [],
          runtime_alias: null,
        },
        {
          model_id: 'model-b',
          display_name: 'Model B',
          provider: 'test',
          category: 'self_hosted',
          capabilities: {
            streaming_available: false,
            supports_speed: false,
            supports_pitch: false,
            supports_prompt_style: true,
          },
          config_schema: [],
          configured: true,
          config_warnings: [],
          runtime_alias: null,
        },
      ],
    })

    vi.mocked(api.synthesizeBatch).mockResolvedValue({
      results: [
        {
          model_id: 'model-a',
          success: true,
          audio_url: 'http://localhost:8000/tts/audio/mock.mp3',
          audio_base64: null,
          latency_ms: 120,
          streaming_used: true,
          error: null,
        },
        {
          model_id: 'model-b',
          success: false,
          audio_url: null,
          audio_base64: null,
          latency_ms: 80,
          streaming_used: false,
          error: 'Model not configured',
        },
      ],
      summary: {
        total: 2,
        success_count: 1,
        failure_count: 1,
        duration_ms: 210,
      },
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getAllByText('Model A').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Model B').length).toBeGreaterThan(0)
    })

    fireEvent.click(screen.getByRole('button', { name: 'Speak on selected models' }))

    await waitFor(() => {
      expect(screen.getByText('Model not configured')).toBeInTheDocument()
    })

    const audio = document.querySelector('audio')
    expect(audio).toBeInTheDocument()
  })
})
