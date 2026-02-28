import { useEffect } from 'react'
import { EnvWarnings } from './components/EnvWarnings'
import { ModelSidebar } from './components/ModelSidebar'
import { ResultsPanel } from './components/ResultsPanel'
import { TextComposer } from './components/TextComposer'
import { TopTabs } from './components/TopTabs'
import { usePlaygroundStore } from './state/usePlaygroundStore'
import './styles.css'

function App() {
  const {
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
  } = usePlaygroundStore()

  useEffect(() => {
    void loadCatalog()
  }, [loadCatalog])

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Tanglish TTS Playground</h1>
        <p>Left: all models · Middle: input and outputs · Right: selected model settings.</p>
      </header>

      {globalError ? <div className="error-banner">{globalError}</div> : null}
      <EnvWarnings models={models} />

      {loadingCatalog ? (
        <p>Loading model catalog...</p>
      ) : (
        <main className="workspace-layout">
          <section className="models-column">
            <TopTabs
              models={models}
              activeModelId={activeModelId}
              selectedModelIds={selectedModelIds}
              onSelectTab={setActiveModelId}
              onToggleSelected={toggleSelectedModel}
            />
          </section>

          <section className="middle-column">
            <TextComposer text={text} onTextChange={setText} onSpeak={runSingle} onSpeakBatch={runBatch} />
            <ResultsPanel models={models} results={results} />
          </section>

          <ModelSidebar
            model={activeModel}
            config={activeModel ? modelConfigs[activeModel.model_id] || {} : {}}
            onChange={(key, value) => {
              if (activeModel) {
                setModelConfig(activeModel.model_id, key, value)
              }
            }}
          />
        </main>
      )}
    </div>
  )
}

export default App
