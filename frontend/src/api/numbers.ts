import { API, json } from './client'

export type NumberWords = {
  words: string | null
  kind: 'number' | 'year' | 'ordinal' | null
}

// A number written in digits, in words in the language of the book ({words: null} when the text is not one number).
export const getNumberWords = (languageId: number, text: string) =>
  fetch(`${API}/numbers/spoken?languageId=${languageId}&text=${encodeURIComponent(text)}`).then((r) =>
    json<NumberWords>(r),
  )
