import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { speakLive, stopLive, type ReaderPage } from '../api'
import { notify } from '../notices'
import { readableSentences, startIndex } from './readAloud'

// Reads the page aloud with the Mac voice, one sentence at a time, and says which sentence is being read so the reader can mark it.
// At the end of the page it turns to the next one and goes on, unless that is the last page.
export function useReadAloud(page: ReaderPage | null, bookId: number, rate: number, onStart?: () => void) {
  const [sentence, setSentence] = useState<number | null>(null)
  const [state, setState] = useState<'idle' | 'reading' | 'paused'>('idle')
  const run = useRef(0) // the latest start: a loop from an earlier one stops itself
  const goOn = useRef(false) // reading was running when the page turned itself
  const rateRef = useRef(rate)
  useEffect(() => {
    rateRef.current = rate
  }, [rate])
  const sentences = useMemo(() => (page ? readableSentences(page) : []), [page])
  const pageNumber = page?.page
  const pageCount = page?.pageCount ?? 0
  const languageId = page?.language.id

  const read = useCallback(
    async (from?: number) => {
      if (languageId === undefined) return
      const mine = ++run.current
      onStart?.()
      setState('reading')
      for (let i = startIndex(sentences, from); i < sentences.length; i++) {
        if (mine !== run.current) return
        setSentence(sentences[i].id)
        try {
          const done = await speakLive(sentences[i].text, languageId, rateRef.current)
          if (!done.finished || mine !== run.current) return // stopped, paused, or another start took over
        } catch (e) {
          if (mine === run.current) {
            notify((e as Error).message, 6000)
            setState('idle')
            setSentence(null)
          }
          return
        }
      }
      if (mine !== run.current) return
      if (pageNumber !== undefined && pageNumber < pageCount) {
        goOn.current = true
        window.location.hash = `#/book/${bookId}/read/${pageNumber + 1}`
      } else {
        setState('idle')
        setSentence(null)
      }
    },
    [languageId, sentences, pageNumber, pageCount, bookId, onStart],
  )

  // The page turned itself: carry on from its top.
  useEffect(() => {
    if (goOn.current && sentences.length > 0) {
      goOn.current = false
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void read()
    }
  }, [sentences, read])

  const stop = useCallback(() => {
    run.current++
    goOn.current = false
    setState('idle')
    setSentence(null)
    stopLive().catch(() => undefined)
  }, [])

  const pause = useCallback(() => {
    run.current++
    setState('paused')
    stopLive().catch(() => undefined)
  }, [])

  const resume = useCallback(() => void read(sentence ?? undefined), [read, sentence])

  // Leaving the page (or the book) ends the reading.
  useEffect(
    () => () => {
      run.current++
      stopLive().catch(() => undefined)
    },
    [],
  )

  return { sentence, state, read, pause, resume, stop }
}
