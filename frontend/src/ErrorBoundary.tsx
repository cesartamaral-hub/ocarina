import { Component, type ReactNode } from 'react'

// A screen that throws while rendering would otherwise take the whole window with it (React unmounts the tree).
// This keeps the header and shows a way out; the page is rendered again once the address changes.
export class ErrorBoundary extends Component<{ children: ReactNode; resetKey: string }, { error: Error | null }> {
  state: { error: Error | null; key: string } = {
    error: null,
    key: this.props.resetKey,
  }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  static getDerivedStateFromProps(props: { resetKey: string }, state: { key: string }) {
    return props.resetKey !== state.key ? { error: null, key: props.resetKey } : null
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <section className="card" role="alert">
        <h2>Something went wrong on this page</h2>
        <p className="muted">{this.state.error.message}</p>
        <p>
          <a href="#/">Back to Books</a>
        </p>
      </section>
    )
  }
}
