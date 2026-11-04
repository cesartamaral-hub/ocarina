import { useEffect, useMemo, useRef, useState } from 'react'
import { getSentences, type BookSentences, type ReaderPage } from '../api'
import type { Playable } from '../media'
import { wordTime } from '../wordTime'

// Keeps the reader in step with the book's generated audio.
//
// Sentences that contain a word, in page order, line up one to one with the generated audio's
// sentences for the same page (both come from Lute's parser). If the counts differ, the text
// was edited after the audio was made, so following switches itself off (aligned = false).
export function useAudioFollow(bookId: number, page: ReaderPage | null, follow: boolean, version = 0) {
  const audioRef = useRef<Playable | null>(null)
  const [audioInfo, setAudioInfo] = useState<BookSentences | null>(null)
  const [playing, setPlaying] = useState<number | null>(null)

  useEffect(() => {
    getSentences(bookId).then(setAudioInfo, () => setAudioInfo(null))
  }, [bookId, version]) // another audio version has other timings (or none)

  const timings = audioInfo?.hasTimings ? audioInfo.sentences : null
  // Where each sentence starts, for the J and L keys.
  const starts = useMemo(() => (timings ? timings.map((t) => t.start).filter((s): s is number => s !== undefined) : null), [timings])
  const wordSentences = useMemo(
    () => page?.paragraphs.flat().filter((s) => s.some((i) => i.isWord)).map((s) => s[0].sentence) ?? [],
    [page],
  )
  const pageTimings = useMemo(
    () => (timings && page ? timings.filter((t) => t.page === page.page) : []),
    [timings, page],
  )
  const aligned = timings !== null && pageTimings.length > 0 && pageTimings.length === wordSentences.length

  // Where in the audio a sentence (by its number on the page) starts.
  const startOf = (sentence: number) => (aligned ? pageTimings[wordSentences.indexOf(sentence)]?.start : undefined)

  // Where in the audio a word is said (see wordTime.ts).
  function wordStartOf(sentence: number, charsBefore: number, chars: number) {
    const i = aligned ? wordSentences.indexOf(sentence) : -1
    const start = pageTimings[i]?.start
    return start === undefined ? undefined : wordTime(start, pageTimings[i + 1]?.start, charsBefore, chars)
  }

  function onAudioTime(t: number) {
    if (!timings || !page) return
    let idx = -1
    timings.forEach((s, i) => {
      if (s.start !== undefined && s.start <= t) idx = i
    })
    const entry = idx >= 0 ? timings[idx] : null
    if (!entry) return setPlaying(null)
    if (entry.page !== page.page) {
      setPlaying(null)
      if (follow && audioRef.current && !audioRef.current.paused) {
        window.location.hash = `#/book/${bookId}/read/${entry.page}`
      }
      return
    }
    setPlaying(aligned ? (wordSentences[pageTimings.indexOf(entry)] ?? null) : null)
  }

  useEffect(() => {
    if (playing === null || !audioRef.current || audioRef.current.paused) return
    document.querySelector(`[data-sent="${playing}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [playing])

  function playAt(seconds: number) {
    const el = audioRef.current
    if (!el) return
    el.currentTime = seconds
    el.play()
  }

  return { audioRef, audioInfo, timings, starts, aligned, firstStart: pageTimings[0]?.start, startOf, wordStartOf, playing, onAudioTime, playAt }
}
