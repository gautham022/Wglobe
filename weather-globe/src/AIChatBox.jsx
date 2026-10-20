import React, { useState, useRef, useEffect } from 'react'
import { Send, Bot, X, Loader2, Sparkles, Mic, MicOff, Volume2, VolumeX } from 'lucide-react'
import './AIChatBox.css'
import { API_URL } from './config';

const SUGGESTIONS = [
  'Will it rain today?',
  'What should I wear?',
  'Is the UV dangerous?',
  'Compare Paris and Tokyo',
]

function getSpeechRecognition() {
  const w = typeof window !== 'undefined' ? window : {}
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

function AIChatBox({ city, weather, variant = 'floating' }) {
  const isDocked = variant === 'docked'
  const [open, setOpen] = useState(isDocked ? true : false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [listening, setListening] = useState(false)
  const [speakReplies, setSpeakReplies] = useState(false)
  const messagesEndRef = useRef(null)
  const recognitionRef = useRef(null)
  const pendingVoiceSubmit = useRef(false)
  const transcriptRef = useRef('')

  useEffect(() => {
    if (open) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, open])

  // Clean up speech recognition when the box closes
  useEffect(() => () => recognitionRef.current?.stop(), [])

  function speak(text) {
    if (!speakReplies || !('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.05
    utterance.pitch = 1
    window.speechSynthesis.speak(utterance)
  }

  function stopSpeaking() {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel()
  }

  function send(message) {
    const trimmed = message.trim()
    if (!trimmed || isLoading) return

    const userMessage = { text: trimmed, isUser: true }
    const updatedHistory = messages.map((m) => ({
      role: m.isUser ? 'user' : 'assistant',
      content: m.text,
    }))

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setError(null)
    setIsLoading(true)

    fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: trimmed,
        city: city || null,
        weather: weather || null,
        history: updatedHistory,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed (${res.status})`)
        return res.json()
      })
      .then((data) => {
        setMessages((prev) => [...prev, { text: data.reply, isUser: false }])
        speak(data.reply)
      })
      .catch((err) => {
        console.error('Chat request failed:', err)
        setError("Couldn't reach the weather assistant. Try again in a moment.")
      })
      .finally(() => setIsLoading(false))
  }

  function handleSubmit(e) {
    e?.preventDefault()
    send(input)
  }

  function toggleMic() {
    const Recognition = getSpeechRecognition()
    if (!Recognition) {
      setError('Voice input is not supported in this browser. Try Chrome or Edge.')
      return
    }
    if (listening) {
      recognitionRef.current?.stop()
      return
    }
    stopSpeaking()
    const recognition = new Recognition()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      setInput(transcript)
      pendingVoiceSubmit.current = true
    }
    recognition.onend = () => {
      setListening(false)
      if (pendingVoiceSubmit.current) {
        pendingVoiceSubmit.current = false
        send(transcriptRef.current)
      }
    }
    recognition.onerror = (event) => {
      setListening(false)
      if (event.error === 'not-allowed') {
        setError('Microphone permission denied. Allow mic access to talk to the assistant.')
      }
    }
    recognitionRef.current = recognition
    pendingVoiceSubmit.current = false
    transcriptRef.current = ''
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      transcriptRef.current = transcript
      setInput(transcript)
      pendingVoiceSubmit.current = true
    }
    setListening(true)
    recognition.start()
  }

  return (
    <>
      {!isDocked && (
        <button
          className="ai-chat-toggle"
          onClick={() => setOpen((prev) => !prev)}
          aria-label={open ? 'Close weather assistant' : 'Open weather assistant'}
        >
          {open ? <X size={22} /> : <Bot size={24} />}
        </button>
      )}

      {open && (
        <div className={`ai-chatbox ${isDocked ? 'ai-chatbox--docked' : ''}`}>
          <div className="ai-chatbox__header">
            <div className="ai-chatbox__header-left">
              <Sparkles size={16} className="ai-chatbox__icon" />
              <span>Wglobe Assistant</span>
            </div>
            <div className="ai-chatbox__header-right">
              {city && <span className="ai-chatbox__context-chip">{city}</span>}
              <button
                type="button"
                className={`ai-chatbox__icon-btn ${speakReplies ? 'ai-chatbox__icon-btn--active' : ''}`}
                onClick={() => {
                  if (speakReplies) stopSpeaking()
                  setSpeakReplies((v) => !v)
                }}
                title={speakReplies ? 'Mute spoken replies' : 'Speak replies out loud'}
                aria-label={speakReplies ? 'Mute spoken replies' : 'Speak replies out loud'}
              >
                {speakReplies ? <Volume2 size={15} /> : <VolumeX size={15} />}
              </button>
            </div>
          </div>

          <div className="ai-chatbox__messages">
            {messages.length === 0 ? (
              <div className="ai-chatbox__empty">
                <Sparkles size={30} className="ai-chatbox__icon ai-chatbox__icon--large" />
                <p className="ai-chatbox__empty-title">Ask me about the weather</p>
                <p className="ai-chatbox__empty-sub">
                  {city
                    ? `E.g. "Will it rain tomorrow in ${city}?" or "Should I carry an umbrella?"`
                    : 'Search a city on the globe, then ask me anything about its weather.'}
                </p>
                <div className="ai-chatbox__suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className="ai-chatbox__suggestion-chip"
                      onClick={() => send(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`ai-chatbox__bubble-row ${
                      msg.isUser ? 'ai-chatbox__bubble-row--user' : ''
                    }`}
                  >
                    <div
                      className={`ai-chatbox__bubble ${
                        msg.isUser ? 'ai-chatbox__bubble--user' : 'ai-chatbox__bubble--bot'
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="ai-chatbox__bubble-row">
                    <div className="ai-chatbox__bubble ai-chatbox__bubble--bot ai-chatbox__typing">
                      <span className="ai-chatbox__dot" />
                      <span className="ai-chatbox__dot" />
                      <span className="ai-chatbox__dot" />
                    </div>
                  </div>
                )}
              </>
            )}
            {error && <div className="ai-chatbox__error">{error}</div>}
            <div ref={messagesEndRef} />
          </div>

          <form className="ai-chatbox__input-row" onSubmit={handleSubmit}>
            <button
              type="button"
              className={`ai-chatbox__send ai-chatbox__mic ${
                listening ? 'ai-chatbox__mic--listening' : ''
              }`}
              onClick={toggleMic}
              title={listening ? 'Stop listening' : 'Ask with your voice'}
              aria-label={listening ? 'Stop listening' : 'Ask with your voice'}
              disabled={isLoading}
            >
              {listening ? <MicOff size={16} /> : <Mic size={16} />}
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={listening ? 'Listening...' : 'Type your message...'}
              className="ai-chatbox__input"
            />
            <button
              type="submit"
              className="ai-chatbox__send"
              disabled={!input.trim() || isLoading}
            >
              {isLoading ? (
                <Loader2 size={18} className="ai-chatbox__spin" />
              ) : (
                <Send size={18} />
              )}
            </button>
          </form>
        </div>
      )}
    </>
  )
}

export default AIChatBox
