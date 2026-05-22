import { useEffect, useState, useRef } from "react"
import ProfileSelectCard from "../components/ProfileSelectCard"
import "../styles/Interview.css"

const BASE = "http://localhost:5000"

const PHASE = {
  SELECT:    "select",
  READY:     "ready",
  QUESTION:  "question",
  REVIEWING: "reviewing",
  REPORT:    "report",
}

// Sarvam bulbul:v3 speakers
const SARVAM_SPEAKERS = [
  { value: "sumit",    label: "Sumit (Male)"   },
  { value: "arvind",   label: "Arvind (Male)"  },
  { value: "amol",     label: "Amol (Male)"    },
  { value: "meera",    label: "Meera (Female)" },
  { value: "anushka",  label: "Anushka (Female)" },
  { value: "advithi",  label: "Advithi (Female)" },
]

// ── Browser-side WAV encoder ─────────────────────────────────────────────────
async function blobToWav(audioBlob) {
  const arrayBuffer = await audioBlob.arrayBuffer()
  const audioCtx    = new AudioContext()
  const decoded     = await audioCtx.decodeAudioData(arrayBuffer)
  await audioCtx.close()

  const TARGET_SR = 16000
  const offCtx    = new OfflineAudioContext(1, Math.ceil(decoded.duration * TARGET_SR), TARGET_SR)
  const src       = offCtx.createBufferSource()
  src.buffer      = decoded
  src.connect(offCtx.destination)
  src.start(0)
  const resampled = await offCtx.startRendering()
  const samples   = resampled.getChannelData(0)

  const dataLen = samples.length * 2
  const buf     = new ArrayBuffer(44 + dataLen)
  const view    = new DataView(buf)
  const str     = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)) }

  str(0, "RIFF");  view.setUint32(4, 36 + dataLen, true)
  str(8, "WAVE");  str(12, "fmt ")
  view.setUint32(16, 16, true);  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true);   view.setUint32(24, TARGET_SR, true)
  view.setUint32(28, TARGET_SR * 2, true); view.setUint16(32, 2, true)
  view.setUint16(34, 16, true);  str(36, "data"); view.setUint32(40, dataLen, true)

  for (let i = 0, off = 44; i < samples.length; i++, off += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
  }
  return new Blob([buf], { type: "audio/wav" })
}

// ─────────────────────────────────────────────────────────────────────────────

export default function Interview() {
  const [profiles,        setProfiles]        = useState([])
  const [selectedProfile, setSelectedProfile] = useState(null)

  const [phase,        setPhase]        = useState(PHASE.SELECT)
  const [sessionId,    setSessionId]    = useState(null)
  const [questions,    setQuestions]    = useState([])
  const [currentQ,     setCurrentQ]     = useState(0)
  const [answers,      setAnswers]      = useState([])
  const [report,       setReport]       = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [statusMsg,    setStatusMsg]    = useState("")
  const [numQuestions, setNumQuestions] = useState(3)
  const [speaker,      setSpeaker]      = useState("sumit")

  const [speaking,        setSpeaking]        = useState(false)
  const [countdown,       setCountdown]       = useState(null)
  const [recording,       setRecording]       = useState(false)
  const [useTextMode,     setUseTextMode]     = useState(false)
  const [textAnswer,      setTextAnswer]      = useState("")
  const [shownTranscript, setShownTranscript] = useState("")

  const audioRef       = useRef(null)
  const mediaRecRef    = useRef(null)
  const chunksRef      = useRef([])
  const countdownTimer = useRef(null)
  const phaseRef       = useRef(PHASE.SELECT)

  useEffect(() => { phaseRef.current = phase }, [phase])

  useEffect(() => {
    fetch(`${BASE}/api/profiles/analyzed`)
      .then(r => r.json())
      .then(setProfiles)
      .catch(() => {})
  }, [])

  const question = questions[currentQ] || null

  // ── Auto-play Sarvam TTS audio when question changes ──────────────────────
  useEffect(() => {
    if (phase !== PHASE.QUESTION || !question) return
    clearCountdown()
    stopRecording()
    setShownTranscript("")

    if (question.audio_url && audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = `${BASE}${question.audio_url}`
      audioRef.current.load()
      audioRef.current.play()
        .then(() => { setSpeaking(true); setStatusMsg("Interviewer is speaking…") })
        .catch(() => setStatusMsg("Click ▶ to hear the question, then record your answer."))
    } else {
      setStatusMsg("Read the question above, then record your answer.")
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question, phase])

  useEffect(() => {
    return () => { clearCountdown(); stopRecording() }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Audio element handlers ─────────────────────────────────────────────────
  const onAudioEnd = () => {
    setSpeaking(false)
    if (!useTextMode && phaseRef.current === PHASE.QUESTION) startCountdown()
  }

  const onAudioError = () => {
    setSpeaking(false)
    setStatusMsg("Audio unavailable — read the question and record your answer.")
  }

  const replayQuestion = () => {
    if (!question?.audio_url || !audioRef.current || recording) return
    clearCountdown()
    audioRef.current.currentTime = 0
    audioRef.current.play()
      .then(() => { setSpeaking(true); setStatusMsg("Interviewer is speaking…") })
      .catch(console.error)
  }

  // ── Countdown → auto-start recording ──────────────────────────────────────
  const startCountdown = () => {
    let val = 3
    setCountdown(val)
    setStatusMsg(`Your turn in ${val}…`)
    countdownTimer.current = setInterval(() => {
      val -= 1
      if (val > 0) { setCountdown(val); setStatusMsg(`Your turn in ${val}…`) }
      else { clearCountdown(); if (phaseRef.current === PHASE.QUESTION) startRecordingMic() }
    }, 1000)
  }

  const clearCountdown = () => {
    clearInterval(countdownTimer.current)
    countdownTimer.current = null
    setCountdown(null)
  }

  // ── MediaRecorder + WAV conversion → Sarvam STT ───────────────────────────
  const getSupportedMime = () => {
    const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"]
    return types.find(t => MediaRecorder.isTypeSupported(t)) || ""
  }

  const startRecordingMic = async () => {
    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = getSupportedMime()
      const mr       = new MediaRecorder(stream, mimeType ? { mimeType } : {})
      chunksRef.current  = []
      chunksRef.mimeType = mr.mimeType
      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.start(250)
      mediaRecRef.current = mr
      setRecording(true)
      setStatusMsg("Recording… speak your answer, then click Stop")
    } catch {
      setUseTextMode(true)
      setStatusMsg("Microphone unavailable — type your answer below")
    }
  }

  const stopRecording = () => {
    if (!mediaRecRef.current) return
    try {
      mediaRecRef.current.stream.getTracks().forEach(t => t.stop())
      mediaRecRef.current.stop()
    } catch (_) {}
    mediaRecRef.current = null
    setRecording(false)
  }

  const stopAndSubmit = () => {
    if (!mediaRecRef.current) return
    const mr = mediaRecRef.current
    mr.onstop = async () => {
      const mime    = chunksRef.mimeType || "audio/webm"
      const rawBlob = new Blob(chunksRef.current, { type: mime })
      if (rawBlob.size < 500) {
        setStatusMsg("Recording too short — please try again")
        setPhase(PHASE.QUESTION)
        return
      }
      setPhase(PHASE.REVIEWING)
      setStatusMsg("Converting audio…")
      let wavBlob
      try { wavBlob = await blobToWav(rawBlob) }
      catch (e) { console.error("[WAV]", e); wavBlob = rawBlob }
      setStatusMsg("Transcribing & evaluating…")
      await submitAudioBlob(wavBlob)
    }
    stopRecording()
  }

  const submitAudioBlob = async (wavBlob) => {
    const form = new FormData()
    form.append("session_id",      sessionId)
    form.append("question_number", question.number)
    form.append("audio",           wavBlob, "answer.wav")
    try {
      const res  = await fetch(`${BASE}/api/interview/submit-answer`, { method: "POST", body: form })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      if (data.stt_error || !data.transcript) {
        console.warn("[STT]", data.stt_error || "empty transcript")
        setPhase(PHASE.QUESTION)
        setStatusMsg(data.stt_error
          ? `Transcription failed: ${data.stt_error}. Retry or switch to text mode.`
          : "Could not hear your answer — retry or switch to text mode.")
        return
      }
      setShownTranscript(data.transcript)
      recordAnswer(data)
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`)
      setPhase(PHASE.QUESTION)
    }
  }

  const submitTextAnswer = async () => {
    const text = textAnswer.trim()
    if (!text) return
    clearCountdown(); stopRecording()
    setPhase(PHASE.REVIEWING)
    setStatusMsg("Evaluating answer…")
    setShownTranscript(text)
    try {
      const res  = await fetch(`${BASE}/api/interview/submit-answer`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, question_number: question.number, text_answer: text }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      recordAnswer(data)
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`)
      setPhase(PHASE.QUESTION)
    }
  }

  const recordAnswer = (data) => {
    setAnswers(prev => [...prev, data])
    setTextAnswer("")
    const nextIdx = currentQ + 1
    if (nextIdx < questions.length) { setCurrentQ(nextIdx); setPhase(PHASE.QUESTION) }
    else finalizeInterview()
  }

  const startInterview = async () => {
    if (!selectedProfile) return
    setLoading(true)
    setStatusMsg("Generating questions & preparing audio…")
    try {
      const res  = await fetch(`${BASE}/api/interview/start`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_url:   selectedProfile.profile_url,
          num_questions: numQuestions,
          speaker,
        }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setSessionId(data.session_id)
      setQuestions(data.questions)
      setCurrentQ(0)
      setAnswers([])
      setPhase(PHASE.QUESTION)
      setStatusMsg("")
    } catch (err) {
      setStatusMsg(`Error: ${err.message}`)
    }
    setLoading(false)
  }

  const finalizeInterview = async () => {
    setPhase(PHASE.REVIEWING)
    setStatusMsg("Generating final report…")
    try {
      const res  = await fetch(`${BASE}/api/interview/finalize`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      })
      const data = await res.json()
      setReport(data)
      setPhase(PHASE.REPORT)
      setStatusMsg("")
    } catch (err) {
      setStatusMsg(`Finalize error: ${err.message}`)
    }
  }

  const reset = () => {
    if (audioRef.current) audioRef.current.pause()
    clearCountdown(); stopRecording()
    setPhase(PHASE.SELECT);  setSelectedProfile(null)
    setSessionId(null);      setQuestions([]);   setCurrentQ(0)
    setAnswers([]);           setReport(null);    setStatusMsg("")
    setTextAnswer("");        setShownTranscript("")
    setSpeaking(false);       setRecording(false)
  }

  const recColor = (rec) => {
    if (!rec) return ""
    if (rec.includes("Strong Hire")) return "rec-green"
    if (rec.includes("Hire"))        return "rec-blue"
    if (rec.includes("Hold"))        return "rec-amber"
    return "rec-red"
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="interview-page">

      {/* Hidden audio element for Sarvam TTS playback */}
      <audio ref={audioRef} onEnded={onAudioEnd} onError={onAudioError} style={{ display: "none" }} />

      {/* ════════ LEFT PANEL ════════ */}
      <div className="interview-left">

        {(phase === PHASE.SELECT || phase === PHASE.READY) && (
          <>
            <h2>Agentic Interview</h2>

            <div className="interview-config">
              <label className="config-label">Number of questions</label>
              <div className="q-selector">
                {[3, 5, 7].map(n => (
                  <button key={n} className={`q-btn ${numQuestions === n ? "active" : ""}`}
                    onClick={() => setNumQuestions(n)}>{n}</button>
                ))}
              </div>

              <label className="config-label" style={{ marginTop: 4 }}>Interviewer voice</label>
              <select
                className="voice-select"
                value={speaker}
                onChange={e => setSpeaker(e.target.value)}
              >
                {SARVAM_SPEAKERS.map(v => (
                  <option key={v.value} value={v.value}>{v.label}</option>
                ))}
              </select>

              <div className="mode-toggle">
                <label>
                  <input type="checkbox" checked={useTextMode}
                    onChange={e => setUseTextMode(e.target.checked)} />
                  <span>Text mode (no microphone)</span>
                </label>
              </div>
            </div>

            {selectedProfile && (
              <div className="selected-info">
                <span className="selected-label">Interviewing</span>
                <span className="selected-name">{selectedProfile.name}</span>
              </div>
            )}

            <button className="run-btn" onClick={startInterview}
              disabled={!selectedProfile || loading}>
              {loading ? "Preparing…" : "Start Interview"}
            </button>
            {statusMsg && <p className="status-msg">{statusMsg}</p>}
          </>
        )}

        {phase === PHASE.QUESTION && question && (
          <div className="question-panel">
            <div className="q-progress">
              {questions.map((_, i) => (
                <div key={i}
                  className={`q-dot ${i < currentQ ? "done" : i === currentQ ? "active" : ""}`} />
              ))}
            </div>
            <div className="q-counter">Question {currentQ + 1} of {questions.length}</div>

            <div className={`q-card ${speaking ? "q-card--speaking" : ""}`}>
              {speaking && (
                <div className="speaker-badge">
                  <span className="speaker-wave">🎙</span> Interviewer speaking
                </div>
              )}
              <p className="q-text">{question.text}</p>
              {question.audio_url && (
                <button className="play-btn" onClick={replayQuestion}
                  disabled={speaking || recording}>
                  {speaking ? "▶ Speaking…" : "↺ Replay"}
                </button>
              )}
            </div>

            {statusMsg && (
              <p className={`status-msg ${countdown != null ? "status-countdown" : ""}`}>
                {statusMsg}
              </p>
            )}

            {useTextMode ? (
              <div className="answer-box">
                <textarea className="answer-textarea"
                  placeholder="Type your answer here…"
                  value={textAnswer} onChange={e => setTextAnswer(e.target.value)}
                  rows={5} disabled={speaking} />
                <button className="run-btn" onClick={submitTextAnswer}
                  disabled={!textAnswer.trim() || speaking}>Submit Answer</button>
              </div>
            ) : (
              <div className="mic-controls">
                {!recording ? (
                  <button className="mic-btn start" onClick={startRecordingMic}
                    disabled={speaking || countdown != null}>
                    <span className="mic-icon">🎙</span>
                    {countdown != null ? `Starting in ${countdown}…`
                      : speaking ? "Wait for question…" : "Start Recording"}
                  </button>
                ) : (
                  <button className="mic-btn stop" onClick={stopAndSubmit}>
                    <span className="mic-icon recording-pulse">⏹</span> Stop &amp; Submit
                  </button>
                )}
                <button className="text-fallback-link"
                  onClick={() => { clearCountdown(); stopRecording(); setUseTextMode(true) }}>
                  Switch to text mode
                </button>
              </div>
            )}
          </div>
        )}

        {phase === PHASE.REVIEWING && (
          <div className="reviewing-panel">
            <div className="spinner" />
            <p className="status-msg">{statusMsg || "Evaluating…"}</p>
            {shownTranscript && (
              <div className="transcript-box reviewing-transcript">
                <span className="transcript-label">Your answer</span>
                <p className="transcript-text">{shownTranscript}</p>
              </div>
            )}
          </div>
        )}

        {phase === PHASE.REPORT && report && (
          <div className="report-panel">
            <h2>Interview Report</h2>
            <div className="report-hero">
              <div className="score-ring">
                <svg viewBox="0 0 80 80">
                  <circle cx="40" cy="40" r="34" fill="none" stroke="#e5e7eb" strokeWidth="7"/>
                  <circle cx="40" cy="40" r="34" fill="none" stroke="#5E5ADB" strokeWidth="7"
                    strokeDasharray={`${(report.overall_score / 100) * 213.6} 213.6`}
                    strokeLinecap="round" transform="rotate(-90 40 40)" />
                </svg>
                <span className="score-number">{Math.round(report.overall_score)}</span>
              </div>
              <div className="report-meta">
                <div className="report-name">{report.candidate_name}</div>
                <div className={`rec-badge ${recColor(report.recommendation)}`}>
                  {report.recommendation}
                </div>
                <p className="report-summary">{report.summary}</p>
              </div>
            </div>
            <div className="qa-breakdown">
              <h3>Q&amp;A Breakdown</h3>
              {report.qa_breakdown?.map((qa, i) => (
                <div key={i} className="qa-item">
                  <div className="qa-header">
                    <span className="qa-q">Q{i + 1}. {qa.question}</span>
                    <span className="qa-score">{qa.score}/10</span>
                  </div>
                  <p className="qa-answer">{qa.answer || <em>No answer</em>}</p>
                  <div className="qa-tags">
                    {qa.red_flags?.map((f, j) => <span key={j} className="flag-tag">{f}</span>)}
                  </div>
                  <p className="qa-strength">{qa.strengths}</p>
                </div>
              ))}
            </div>
            <button className="run-btn outline" onClick={reset}>New Interview</button>
          </div>
        )}
      </div>

      {/* ════════ RIGHT PANEL ════════ */}
      {(phase === PHASE.SELECT || phase === PHASE.READY) && (
        <div className="interview-right">
          <h3>Select Candidate</h3>
          <div className="profile-grid">
            {profiles.map(p => (
              <ProfileSelectCard key={p.id} profile={p}
                selected={selectedProfile?.id === p.id}
                onSelect={p => { setSelectedProfile(p); setPhase(PHASE.READY) }} />
            ))}
          </div>
        </div>
      )}

      {(phase === PHASE.QUESTION || phase === PHASE.REVIEWING) && answers.length > 0 && (
        <div className="interview-right">
          <h3>Live Scores</h3>
          <div className="live-scores">
            {answers.map((a, i) => (
              <div key={i} className="live-score-item">
                <span className="ls-q">Q{a.question_number}</span>
                <div className="ls-bar-wrap">
                  <div className="ls-bar" style={{ width: `${(a.evaluation?.score || 0) * 10}%` }} />
                </div>
                <span className="ls-score">{a.evaluation?.score ?? "—"}/10</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
