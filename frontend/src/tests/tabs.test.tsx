import { render, screen, waitFor } from '@testing-library/react'
import App from '../App'
import * as api from '../api/client'

vi.mock('../api/client', () => ({
  fetchCatalog: vi.fn(),
  synthesizeOne: vi.fn(),
  synthesizeBatch: vi.fn(),
}))

describe('Top tabs', () => {
  it('renders cloud and self-hosted tab groups from catalog', async () => {
    vi.mocked(api.fetchCatalog).mockResolvedValue({
      models: [
        {
          model_id: 'sarvam:bulbul:v2',
          display_name: 'Sarvam AI - bulbul:v2',
          provider: 'sarvam',
          category: 'cloud',
          capabilities: {
            streaming_available: true,
            supports_speed: true,
            supports_pitch: true,
            supports_prompt_style: false,
          },
          config_schema: [],
          configured: true,
          config_warnings: [],
          runtime_alias: null,
        },
        {
          model_id: 'ai4bharat/indic-parler-tts',
          display_name: 'ai4bharat/indic-parler-tts',
          provider: 'huggingface-local',
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

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Cloud Models')).toBeInTheDocument()
      expect(screen.getByText('Self-hosted Models')).toBeInTheDocument()
    })

    expect(screen.getAllByText('Sarvam AI').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Ai4bharat').length).toBeGreaterThan(0)
    expect(screen.getAllByText('bulbul:v2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('indic-parler-tts').length).toBeGreaterThan(0)
  })
})
