import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('App error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-ink-900 flex items-center justify-center px-4">
          <div className="text-center font-mono">
            <div className="h-px w-16 bg-amber-500/40 mx-auto mb-6" />
            <p className="text-amber-500 text-xs tracking-widest mb-3">SYSTEM ERROR</p>
            <p className="text-slate-500 text-xs max-w-sm">
              {this.state.error?.message ?? 'An unexpected error occurred.'}
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-6 text-[10px] text-slate-600 hover:text-amber-500 tracking-widest transition-colors"
            >
              RETRY →
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
