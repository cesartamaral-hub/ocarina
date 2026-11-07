// A run of digits on the page (the parser does not count it as a word): "1995", "3", "2,5", "1.250", "3e".
export const isNumberText = (text: string): boolean =>
  /^\d[\d.,  ]*\d?(?:e|er|ste|de|ème)?$/.test(text.trim()) && /\d/.test(text)

// The words of a number written out, to look up one by one: "negentien honderd vijfennegentig" has three.
export const wordsOf = (written: string): string[] => [...new Set(written.split(/[\s-]+/).filter(Boolean))]
