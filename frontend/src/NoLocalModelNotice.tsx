// What to say when translation is asked for offline and no local model is downloaded: one sentence, the same wherever it appears
// (the reader's translation panel, Settings -> Translation). The server's wording of the same notice is `translate.NO_LOCAL_MODEL`.
export function NoLocalModelNotice() {
  return (
    <>
      No local model installed. Offline, translation needs one: download it under <a href="#/settings/models">Models</a>, or turn off Work offline to translate online.
    </>
  )
}
