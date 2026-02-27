interface TextComposerProps {
  text: string
  onTextChange: (text: string) => void
  onSpeak: () => Promise<void>
  onSpeakBatch: () => Promise<void>
}

export function TextComposer({ text, onTextChange, onSpeak, onSpeakBatch }: TextComposerProps) {
  return (
    <section className="composer">
      <h2>Input Text</h2>
      <textarea
        value={text}
        onChange={(event) => onTextChange(event.target.value)}
        placeholder="Type Tanglish or Tamil/English text here..."
      />
      <div className="action-row">
        <button type="button" onClick={() => void onSpeak()}>
          Speak
        </button>
        <button type="button" className="secondary" onClick={() => void onSpeakBatch()}>
          Speak on selected models
        </button>
      </div>
    </section>
  )
}
