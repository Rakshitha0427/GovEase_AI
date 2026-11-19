import { useState } from 'react'
import { ArrowRight, Landmark, X } from 'lucide-react'

export default function AuthModal({ initialMode = 'login', busy, error, onClose, onSubmit, onModeChange }) {
  const [mode, setMode] = useState(initialMode)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const changeMode = next => { setMode(next); onModeChange(next) }
  const submit = event => {
    event.preventDefault()
    onSubmit({ mode, name, email, password })
  }

  return <div className="account-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section className="account-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-heading">
      <button className="account-close" onClick={onClose} aria-label="Close"><X size={18}/></button>
      <div className="account-brand"><span><Landmark size={18}/></span> GovEase AI</div>
      <div className="account-eyebrow">YOUR SERVICES, ALL IN ONE PLACE</div>
      <h2 id="auth-heading">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2>
      <p className="account-intro">{mode === 'login' ? 'Sign in to continue your conversations.' : 'Save your conversations and make GovEase yours.'}</p>
      <form onSubmit={submit} className="account-form">
        {mode === 'signup' && <label>Your name<input autoComplete="name" value={name} onChange={event => setName(event.target.value)} maxLength={80} required placeholder="Your full name"/></label>}
        <label>Email address<input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} maxLength={254} required placeholder="you@example.com"/></label>
        <label>Password<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} minLength={mode === 'signup' ? 10 : 1} maxLength={128} required placeholder={mode === 'signup' ? 'At least 10 characters' : 'Your password'}/></label>
        {error && <div className="account-error" role="alert">{error}</div>}
        <button className="account-submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}<ArrowRight size={16}/></button>
      </form>
      <div className="account-switch">{mode === 'login' ? <>New to GovEase? <button onClick={() => changeMode('signup')}>Create an account</button></> : <>Already have an account? <button onClick={() => changeMode('login')}>Sign in</button></>}</div>
      <div className="account-privacy">Your account details are stored securely and used only to provide your GovEase account.</div>
    </section>
  </div>
}
