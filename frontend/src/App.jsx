import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import AlertsPanel from "./components/AlertsPanel";
import Composer from "./components/Composer";
import LanguagePicker from "./components/LanguagePicker";
import Message from "./components/Message";
import SavedLocations from "./components/SavedLocations";
import { api } from "./api";
import { strings } from "./i18n";
import { useSpeech } from "./hooks/useSpeech";

const FALLBACK_LANGUAGES = [
  { code: "en", native: "English", speech_tag: "en-IN" },
];

const STORED_LANGUAGE = "weathergpt.language";
const ALERT_POLL_MS = 60_000;

let nextId = 1;
const newId = () => `m${nextId++}`;

export default function App() {
  const [languages, setLanguages] = useState(FALLBACK_LANGUAGES);
  const [language, setLanguage] = useState(
    () => localStorage.getItem(STORED_LANGUAGE) || "en"
  );

  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);

  const [locations, setLocations] = useState([]);
  const [locationError, setLocationError] = useState(null);

  const [alerts, setAlerts] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRunAt, setLastRunAt] = useState(null);

  const [health, setHealth] = useState(null);
  const [offline, setOffline] = useState(false);
  const [readingId, setReadingId] = useState(null);

  const t = strings(language);
  const endRef = useRef(null);

  const speechTag = useMemo(
    () => languages.find((l) => l.code === language)?.speech_tag || "en-IN",
    [languages, language]
  );
  const speech = useSpeech(speechTag);

  useEffect(() => {
    localStorage.setItem(STORED_LANGUAGE, language);
  }, [language]);

  // --- loading -------------------------------------------------------------

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const [langs, status] = await Promise.all([api.languages(), api.health()]);
        if (cancelled) return;
        setLanguages(langs.languages);
        setHealth(status);
        setOffline(false);
      } catch {
        if (!cancelled) setOffline(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const loadLocations = useCallback(async () => {
    try {
      const body = await api.locations();
      setLocations(body.locations);
    } catch {
      /* the offline banner already says this */
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      const body = await api.alerts(language, true);
      setAlerts(body.alerts);
      setLastRunAt(body.scheduler?.last_run_at || null);
    } catch {
      /* same */
    }
  }, [language]);

  useEffect(() => {
    loadLocations();
  }, [loadLocations]);

  useEffect(() => {
    loadAlerts();
    const timer = setInterval(loadAlerts, ALERT_POLL_MS);
    return () => clearInterval(timer);
  }, [loadAlerts]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  // --- chat ----------------------------------------------------------------

  const send = useCallback(
    async (question) => {
      const history = messages
        .filter((m) => !m.error)
        .slice(-10)
        .map(({ role, content }) => ({ role, content }));

      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "user", content: question },
      ]);
      setBusy(true);

      try {
        const body = await api.chat(question, history, language);
        setMessages((prev) => [
          ...prev,
          {
            id: newId(),
            role: "assistant",
            content: body.reply,
            trace: body.trace,
          },
        ]);
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          {
            id: newId(),
            role: "assistant",
            content: error.status === 503 ? t.noKey : error.message,
            error: true,
          },
        ]);
      } finally {
        setBusy(false);
      }
    },
    [messages, language, t.noKey]
  );

  // --- locations and alerts ------------------------------------------------

  const addLocation = useCallback(
    async (place) => {
      setLocationError(null);
      try {
        await api.saveLocation(place, language);
        await Promise.all([loadLocations(), loadAlerts()]);
        return true;
      } catch (error) {
        setLocationError(error.message);
        return false;
      }
    },
    [language, loadLocations, loadAlerts]
  );

  const removeLocation = useCallback(
    async (id) => {
      setLocationError(null);
      try {
        await api.deleteLocation(id);
        await Promise.all([loadLocations(), loadAlerts()]);
      } catch (error) {
        setLocationError(error.message);
      }
    },
    [loadLocations, loadAlerts]
  );

  const dismissAlert = useCallback(async (id) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
    try {
      await api.acknowledgeAlert(id);
    } catch {
      /* it will come back on the next poll if this failed */
    }
  }, []);

  const refreshAlerts = useCallback(async () => {
    setRefreshing(true);
    try {
      const result = await api.refreshAlerts();
      setLastRunAt(result.ran_at);
      await loadAlerts();
    } catch {
      /* same */
    } finally {
      setRefreshing(false);
    }
  }, [loadAlerts]);

  // --- speech --------------------------------------------------------------

  const messageSpeech = {
    canSpeak: speech.canSpeak,
    speaking: speech.speaking,
    readingId,
    read: (id, text) => {
      setReadingId(id);
      speech.speak(text);
    },
    stop: () => {
      setReadingId(null);
      speech.stopSpeaking();
    },
  };

  useEffect(() => {
    if (!speech.speaking) setReadingId(null);
  }, [speech.speaking]);

  const unreadCount = alerts.length;
  const chatDisabled = offline;

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-title">
          <h1>WeatherGPT</h1>
          <p>{t.tagline}</p>
        </div>

        <div className="masthead-controls">
          {unreadCount > 0 && (
            <span className="alert-count" aria-label={`${unreadCount} ${t.alerts}`}>
              {unreadCount}
            </span>
          )}
          <LanguagePicker
            languages={languages}
            value={language}
            onChange={setLanguage}
            language={language}
          />
        </div>
      </header>

      {(offline || health?.llm_configured === false) && (
        <p className="banner">{offline ? t.offline : t.noKey}</p>
      )}

      <main className="layout">
        <section className="conversation" aria-label="Conversation">
          <div className="thread">
            {messages.length === 0 ? (
              <div className="empty">
                <h2>{t.emptyTitle}</h2>
                <p>{t.emptyBody}</p>
                <ul className="suggestions">
                  {t.suggestions.map((suggestion) => (
                    <li key={suggestion}>
                      <button
                        type="button"
                        className="suggestion"
                        onClick={() => send(suggestion)}
                        disabled={chatDisabled}
                      >
                        {suggestion}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              messages.map((message) => (
                <Message
                  key={message.id}
                  message={message}
                  language={language}
                  speech={messageSpeech}
                />
              ))
            )}

            {busy && <p className="pending">{t.thinking}</p>}
            <div ref={endRef} />
          </div>

          <Composer
            language={language}
            busy={busy}
            disabled={chatDisabled}
            onSend={send}
            voice={speech}
          />

          {speech.error && <p className="voice-note">{t.voiceUnsupported}</p>}
        </section>

        <aside className="sidebar">
          <AlertsPanel
            language={language}
            alerts={alerts}
            onDismiss={dismissAlert}
            onRefresh={refreshAlerts}
            refreshing={refreshing}
            lastRunAt={lastRunAt}
          />
          <SavedLocations
            language={language}
            locations={locations}
            onAdd={addLocation}
            onRemove={removeLocation}
            error={locationError}
          />
        </aside>
      </main>
    </div>
  );
}
