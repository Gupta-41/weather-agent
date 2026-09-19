import { useEffect, useRef, useState } from "react";
import { strings } from "../i18n";

export default function Composer({ language, busy, disabled, onSend, voice }) {
  const t = strings(language);
  const [text, setText] = useState("");
  const inputRef = useRef(null);

  // While the microphone is open, show what it is hearing in the box.
  useEffect(() => {
    if (voice.listening && voice.transcript) setText(voice.transcript);
  }, [voice.listening, voice.transcript]);

  const send = (value) => {
    const question = (value ?? text).trim();
    if (!question || busy || disabled) return;
    setText("");
    onSend(question);
  };

  const toggleMic = () => {
    if (voice.listening) {
      voice.stopListening();
    } else {
      voice.startListening((finalText) => send(finalText));
    }
  };

  return (
    <div className="composer">
      {voice.supported && (
        <button
          type="button"
          className={`mic${voice.listening ? " is-live" : ""}`}
          onClick={toggleMic}
          aria-label={voice.listening ? t.stopListening : t.speak}
          title={voice.listening ? t.stopListening : t.speak}
          aria-pressed={voice.listening}
        >
          <span aria-hidden="true">{voice.listening ? "◼" : "🎙"}</span>
        </button>
      )}

      <input
        ref={inputRef}
        className="composer-input"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => event.key === "Enter" && send()}
        placeholder={voice.listening ? t.listening : t.askPlaceholder}
        disabled={disabled}
        aria-label={t.askPlaceholder}
      />

      <button
        type="button"
        className="composer-send"
        onClick={() => send()}
        disabled={busy || disabled || !text.trim()}
      >
        {busy ? t.thinking : t.ask}
      </button>
    </div>
  );
}
