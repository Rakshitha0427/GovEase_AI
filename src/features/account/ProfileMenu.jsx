import { LogOut, Settings, UserRound, X } from 'lucide-react'

export function initials(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map(part => part[0]?.toUpperCase() || '').join('') || 'G'
}

export default function ProfileMenu({ user, onClose, onEdit, onLogout, onSignIn }) {
  return <div className="account-menu-wrap">
    <button className="account-menu-scrim" onClick={onClose} aria-label="Close account menu"/>
    <div className="account-menu" role="menu">
      <div className="account-menu-user"><div className="account-avatar">{user ? initials(user.name) : <UserRound size={16}/>}</div><div><strong>{user?.name || 'Guest'}</strong><span>{user?.email || 'Sign in to save your chats'}</span></div><button className="account-menu-x" onClick={onClose} aria-label="Close"><X size={15}/></button></div>
      <div className="account-menu-separator"/>
      {user ? <>
        <button role="menuitem" onClick={onEdit}><Settings size={15}/> Profile settings</button>
        <button role="menuitem" onClick={onLogout}><LogOut size={15}/> Sign out</button>
      </> : <button role="menuitem" onClick={onSignIn}><UserRound size={15}/> Sign in or create account</button>}
    </div>
  </div>
}
