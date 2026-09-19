import TraceTape from "./TraceTape";
import { strings } from "../i18n";

export default function Message({ message, language, speech }) {
  const t = strings(language);
  const isUser = message.role === "user";
  const isReading = speech?.speaking && speech.readingId === message.id;

  return (
    <article className={`message is-${message.role}`}>
      <div className="message-body">
        {message.error ? (
          <p className="message-error">{message.content}</p>
        ) : (
          <p>{message.content}</p>
        )}

        {!isUser && !message.error && speech?.canSpeak && (
          <button
            type="button"
            className="message-speak"
            onClick={() =>
              isReading ? speech.stop() : speech.read(message.id, message.content)
            }
            aria-label={isReading ? t.stopReading : t.readAloud}
            title={isReading ? t.stopReading : t.readAloud}
          >
            {isReading ? "◼" : "▶"}
          </button>
        )}
      </div>

      {message.trace && <TraceTape trace={message.trace} language={language} />}
    </article>
  );
}
