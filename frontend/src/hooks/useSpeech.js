import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Voice in and voice out, using the browser's own Web Speech API.
 *
 * Nothing is uploaded and no key is needed — recognition runs wherever the
 * browser runs it, which on Chrome means Google's service and on Safari means
 * on-device. Support is uneven, so `supported` drives whether we show the
 * microphone at all rather than letting it fail silently.
 */

const Recognition =
  typeof window !== "undefined" &&
  (window.SpeechRecognition || window.webkitSpeechRecognition);

export function useSpeech(speechTag = "en-IN") {
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState(null);

  const recognitionRef = useRef(null);
  const onFinalRef = useRef(null);

  const supported = Boolean(Recognition);
  const canSpeak =
    typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => {
    if (!supported) return undefined;

    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = speechTag;

    recognition.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) {
          const text = result[0].transcript.trim();
          setTranscript(text);
          onFinalRef.current?.(text);
        } else {
          interim += result[0].transcript;
        }
      }
      if (interim) setTranscript(interim);
    };

    recognition.onerror = (event) => {
      setError(event.error);
      setListening(false);
    };
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [supported, speechTag]);

  const startListening = useCallback((onFinal) => {
    if (!recognitionRef.current) return;
    onFinalRef.current = onFinal;
    setTranscript("");
    setError(null);
    try {
      recognitionRef.current.start();
      setListening(true);
    } catch {
      // start() throws if it is already running; treat that as already-on.
      setListening(true);
    }
  }, []);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  const speak = useCallback(
    (text) => {
      if (!canSpeak || !text) return;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = speechTag;
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(utterance);
    },
    [canSpeak, speechTag]
  );

  const stopSpeaking = useCallback(() => {
    if (!canSpeak) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [canSpeak]);

  useEffect(() => () => canSpeak && window.speechSynthesis.cancel(), [canSpeak]);

  return {
    supported,
    canSpeak,
    listening,
    speaking,
    transcript,
    error,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  };
}
