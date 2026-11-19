import { useEffect, useState } from 'react'
import { X } from 'lucide-react'

export default function ProfileDialog({ user, busy, error, onClose, onSave }) {
  const [name, setName] = useState(user.name)
  const [email, setEmail] = useState(user.email)
  useEffect(() => { setName(user.name); setEmail(user.email) }, [user])
  return <div className="account-overlay" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section className="account-dialog profile-dialog" role="dialog" aria-modal="true" aria-labelledby="profile-heading">
      <button className="account-close" onClick={onClose} aria-label="Close"><X size={18}/></button>
      <div className="account-eyebrow">ACCOUNT SETTINGS</div><h2 id="profile-heading">Your profile</h2><p className="account-intro">Update the details attached to your account.</p>
      <form className="account-form" onSubmit={event => { event.preventDefault(); onSave({ name, email }) }}>
        <label>Display name<input value={name} onChange={event => setName(event.target.value)} maxLength={80} required/></label>
        <label>Email address<input type="email" value={email} onChange={event => setEmail(event.target.value)} maxLength={254} required/></label>
        {error && <div className="account-error" role="alert">{error}</div>}
        <button className="account-submit" disabled={busy}>{busy ? 'Saving…' : 'Save changes'}</button>
      </form>
    </section>
  </div>
}
