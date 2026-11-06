import { AddLanguages } from './AddLanguages'
import { notify } from './notices'

// Settings -> Languages -> Add languages.
export function AddLanguagesPage() {
  return (
    <>
      <div className="title-row">
        <h1>Add languages</h1>
        <a href="#/settings/languages" className="button secondary">
          Back
        </a>
      </div>
      <AddLanguages
        onAdded={(names) => {
          notify(`Added ${names.join(', ')}`)
          window.location.hash = '#/settings/languages'
        }}
      />
      <p className="muted">
        <a href="#/settings/languages/new">Add a language that is not in the list…</a>
      </p>
    </>
  )
}
