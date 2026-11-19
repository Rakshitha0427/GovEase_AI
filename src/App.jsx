import { useEffect, useRef, useState } from 'react'
import { ArrowDown, ArrowLeft, ArrowUp, AudioLines, Bookmark, Check, ChevronDown, CircleHelp, FileText, Globe2, Landmark, Leaf, Menu, Mic, MoreHorizontal, Paperclip, Plus, Search, ShieldCheck, Sparkles, GraduationCap, UserRound, X } from 'lucide-react'
import AuthModal from './features/account/AuthModal.jsx'
import ProfileDialog from './features/account/ProfileDialog.jsx'
import ProfileMenu, { initials } from './features/account/ProfileMenu.jsx'
import ConversationHistory from './features/history/ConversationHistory.jsx'
import './features/account/account.css'

async function apiRequest(url, options = {}) {
  const response = await fetch(url, { credentials: 'same-origin', ...options, headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers } })
  const data = response.status === 204 ? null : await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data?.detail || 'The request could not be completed.')
  return data
}

const starters = [
  { icon: GraduationCap, title: 'Find scholarships', text: 'I am a college student in Karnataka. What scholarships could I explore?' },
  { icon: Leaf, title: 'Support for farmers', text: 'What government support is available for farmers?' },
  { icon: FileText, title: 'Understand a document', text: 'I want to upload a government PDF and understand it.' },
  { icon: CircleHelp, title: 'Check eligibility', text: 'How do I find out if I may qualify for a scheme?' },
]

function MessageText({ text }) {
  return <div className="message-copy">{text.split(/\n/).map((line, i) => {
    if (line.startsWith('### ')) return <h3 key={i}>{line.slice(4)}</h3>
    if (line.startsWith('## ')) return <h3 key={i}>{line.slice(3)}</h3>
    if (line.startsWith('- ')) return <div className="rich-list" key={i}>• {inline(line.slice(2))}</div>
    if (/^\d+\. /.test(line)) return <div className="rich-list" key={i}>{inline(line)}</div>
    if (!line.trim()) return <div className="line-space" key={i} />
    return <p key={i}>{inline(line)}</p>
  })}</div>
}
function inline(text) {
  return text.split(/(\*\*.*?\*\*|\[.*?\]\(.*?\))/g).map((part, i) => {
    const link = part.match(/^\[(.*?)\]\((.*?)\)$/)
    if (link) return <a href={link[2]} target="_blank" rel="noreferrer" key={i}>{link[1]}</a>
    if (part.startsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>
    return part
  })
}

export default function App() {
  const hour = new Date().getHours()
  const greeting = hour < 5 || hour >= 21 ? 'Good night' : hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [language, setLanguage] = useState('English')
  const [languageOpen, setLanguageOpen] = useState(false)
  const [file, setFile] = useState(null)
  const [document, setDocument] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [mode, setMode] = useState('demo')
  const [user, setUser] = useState(null)
  const [conversations, setConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [accountModal, setAccountModal] = useState(null)
  const [accountError, setAccountError] = useState('')
  const [accountBusy, setAccountBusy] = useState(false)
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const [profileDialogOpen, setProfileDialogOpen] = useState(false)
  const endRef = useRef(null)
  const inputRef = useRef(null)
  const fileRef = useRef(null)

  useEffect(() => { fetch('/api/health').then(r => r.json()).then(d => setMode(d.mode)).catch(() => {}) }, [])
  useEffect(() => {
    let mounted = true
    apiRequest('/api/auth/me').then(account => {
      if (!mounted) return
      setUser(account)
      return apiRequest('/api/conversations').then(items => { if (mounted) setConversations(items) })
    }).catch(() => {})
    return () => { mounted = false }
  }, [])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const refreshConversations = async () => {
    if (!user) { setConversations([]); return }
    try { setConversations(await apiRequest('/api/conversations')) } catch { setConversations([]) }
  }
  const newChat = () => { setMessages([]); setDocument(null); setFile(null); setInput(''); setActiveConversationId(null); inputRef.current?.focus() }
  const submitAccount = async ({ mode: action, name, email, password }) => {
    setAccountBusy(true); setAccountError('')
    try {
      const account = await apiRequest(`/api/auth/${action}`, { method: 'POST', body: JSON.stringify({ name, email, password }) })
      setUser(account); setAccountModal(null); setAccountError(''); newChat()
      setConversations(await apiRequest('/api/conversations'))
    } catch (error) { setAccountError(error.message) } finally { setAccountBusy(false) }
  }
  const signOut = async () => {
    try { await apiRequest('/api/auth/logout', { method: 'POST' }) } catch {}
    setUser(null); setConversations([]); setProfileMenuOpen(false); newChat()
  }
  const saveProfile = async values => {
    setAccountBusy(true); setAccountError('')
    try { const account = await apiRequest('/api/auth/profile', { method: 'PATCH', body: JSON.stringify(values) }); setUser(account); setProfileDialogOpen(false) }
    catch (error) { setAccountError(error.message) } finally { setAccountBusy(false) }
  }
  const openConversation = async id => {
    try {
      const conversation = await apiRequest(`/api/conversations/${id}`)
      setMessages(conversation.messages); setActiveConversationId(conversation.id); setDocument(null); setFile(null); setSidebarOpen(false)
    } catch (error) { window.alert(error.message) }
  }
  const renameConversation = async (id, title) => {
    try { await apiRequest(`/api/conversations/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }); await refreshConversations() }
    catch (error) { window.alert(error.message) }
  }
  const deleteConversation = async id => {
    if (!window.confirm('Delete this conversation and its saved messages?')) return
    try { await apiRequest(`/api/conversations/${id}`, { method: 'DELETE' }); if (activeConversationId === id) newChat(); await refreshConversations() }
    catch (error) { window.alert(error.message) }
  }
  const send = async (value = input) => {
    const message = value.trim()
    if ((!message && !file) || loading) return
    const userMsg = { role: 'user', content: message || `Please summarize ${file.name}.`, file: file?.name }
    setMessages(prev => [...prev, userMsg]); setInput(''); setLoading(true)
    let attached = document
    if (file) {
      try {
        const form = new FormData(); form.append('file', file)
        const response = await fetch('/api/documents', { method: 'POST', body: form })
        const result = await response.json()
        if (!response.ok) throw new Error(result.detail || 'Could not read the PDF.')
        attached = result; setDocument(result); setFile(null)
      } catch (err) {
        setMessages(prev => [...prev, { role: 'assistant', content: `I couldn’t read that PDF: ${err.message}` }]); setLoading(false); return
      }
    }
    try {
      const prior = messages.slice(-10).map(m => ({ role: m.role, content: m.content }))
      const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, language, history: prior, document: attached, conversation_id: activeConversationId }), credentials: 'same-origin' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'The assistant could not respond.')
      setMode(result.mode || 'demo')
      if (result.conversation_id) { setActiveConversationId(result.conversation_id); refreshConversations() }
      setMessages(prev => [...prev, { role: 'assistant', content: result.answer, sources: result.sources }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `I couldn’t reach the assistant just now. ${err.message} Please try again.` }])
    } finally { setLoading(false) }
  }

  const onKeyDown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }

  return <div className="app-shell">
    {sidebarOpen && <button className="mobile-scrim" onClick={() => setSidebarOpen(false)} aria-label="Close menu" />}
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <div className="brand-row"><div className="brand-mark"><Landmark size={18} strokeWidth={2.2} /></div><span>GovEase<span className="brand-ai"> AI</span></span><button className="icon-btn sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><X size={18}/></button></div>
      <button className="new-chat" onClick={newChat}><Plus size={17}/><span>New conversation</span><span className="shortcut">⌘ K</span></button>
      <div className="sidebar-label">YOUR SPACE</div>
      {user ? <ConversationHistory items={conversations} activeId={activeConversationId} onOpen={openConversation} onRename={renameConversation} onDelete={deleteConversation}/> : <div className="history-empty"><div className="history-icon"><Bookmark size={16}/></div><p>Your conversations<br/>will appear here</p><button className="history-signin" onClick={() => setAccountModal('signup')}>Create an account to save chats</button></div>}
      <div className="sidebar-bottom">
        <div className="trust-card"><div className="trust-icon"><ShieldCheck size={17}/></div><div><strong>Grounded in trust</strong><span>Official sources, clearly linked.</span></div><ChevronDown size={15} className="trust-chevron"/></div>
        <button className="profile-row" onClick={() => setProfileMenuOpen(value => !value)}><div className="avatar">{user ? initials(user.name) : <UserRound size={16}/>}</div><div className="profile-text"><strong>{user?.name || 'Guest'}</strong><span>{user?.email || 'Exploring GovEase AI'}</span></div><MoreHorizontal size={19} className="profile-more"/></button>
        {profileMenuOpen && <ProfileMenu user={user} onClose={() => setProfileMenuOpen(false)} onEdit={() => { setProfileMenuOpen(false); setAccountError(''); setProfileDialogOpen(true) }} onLogout={signOut} onSignIn={() => { setProfileMenuOpen(false); setAccountError(''); setAccountModal('login') }} />}
      </div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="icon-btn menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu"><Menu size={19}/></button><div className="breadcrumb"><span>Workspace</span><span className="crumb-sep">/</span><strong>{conversations.find(item => item.id === activeConversationId)?.title || 'New conversation'}</strong></div></div><div className="topbar-actions"><span className={`mode-pill ${mode === 'gemini' ? 'mode-live' : ''}`}><span className="mode-dot"/>{mode === 'gemini' ? 'AI connected' : 'Preview mode'}</span><button className="lang-btn" onClick={() => setLanguageOpen(v => !v)}><Globe2 size={16}/><span>{language}</span><ChevronDown size={14}/></button>{languageOpen && <div className="language-menu">{['English', 'हिन्दी', 'ಕನ್ನಡ'].map(lang => <button key={lang} onClick={() => { setLanguage(lang); setLanguageOpen(false) }}>{lang}{language === lang && <Check size={15}/>}</button>)}</div>}<button className="avatar top-avatar" aria-label="Account" onClick={() => setProfileMenuOpen(value => !value)}>{user ? initials(user.name) : <UserRound size={16}/>}</button></div></header>

      <section className={`conversation ${messages.length ? 'conversation-active' : ''}`}>
        {messages.length === 0 ? <div className="welcome-wrap"><div className="welcome-content"><div className="welcome-orb"><Sparkles size={22}/></div><div className="eyebrow"><span/> YOUR GOVERNMENT SERVICES COMPANION</div><h1>{greeting}.<br/><span>What can I help you with?</span></h1><p className="welcome-sub">Find the right scheme, understand what you qualify for, and take your next step with confidence.</p>
          <div className="starter-grid">{starters.map(({ icon: Icon, title, text }) => <button className="starter-card" key={title} onClick={() => send(text)}><span className="starter-icon"><Icon size={17}/></span><span className="starter-title">{title}</span><span className="starter-arrow"><ArrowUp size={14}/></span><span className="starter-desc">{text}</span></button>)}</div>
          <div className="welcome-note"><ShieldCheck size={15}/><span>Thoughtful answers, with official sources to help you verify.</span></div></div></div>
        : <div className="message-list">{messages.map((m, i) => <div className={`message-row ${m.role}`} key={i}>{m.role === 'assistant' ? <div className="assistant-avatar"><Landmark size={15}/></div> : null}<div className="message-inner"><div className="message-meta">{m.role === 'assistant' ? <><strong>GovEase AI</strong><span className="meta-dot">·</span><span>Just now</span></> : <><strong>You</strong><span className="meta-dot">·</span><span>Just now</span></>}</div>{m.file && <div className="attached-file"><FileText size={15}/>{m.file}</div>}{m.role === 'assistant' ? <MessageText text={m.content}/> : <div className="user-content">{m.content}</div>}{m.sources?.length > 0 && <div className="source-strip"><span className="source-heading"><ShieldCheck size={13}/> SOURCES</span>{m.sources.slice(0, 3).map((s, j) => <a href={s.url} target="_blank" rel="noreferrer" key={j}>{s.title}<ArrowUp size={11}/></a>)}</div>}</div></div>)}{loading && <div className="message-row assistant"><div className="assistant-avatar"><Landmark size={15}/></div><div className="message-inner"><div className="message-meta"><strong>GovEase AI</strong><span className="meta-dot">·</span><span>Thinking</span></div><div className="typing"><i/><i/><i/></div></div></div>}<div ref={endRef}/></div>}
      </section>

      <div className="composer-dock"><div className="composer-wrap">{file && <div className="file-chip"><FileText size={14}/><span>{file.name}</span><button onClick={() => setFile(null)} aria-label="Remove file"><X size={14}/></button></div>}{document && !file && <div className="doc-context"><Check size={13}/> {document.filename} added to this conversation <button onClick={() => setDocument(null)}>Remove</button></div>}<div className="composer"><textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKeyDown} placeholder="Ask about a scheme, service, or document..." rows={1} aria-label="Message GovEase AI"/><div className="composer-tools"><div className="tool-left"><button className="composer-tool" onClick={() => fileRef.current?.click()} aria-label="Attach a PDF"><Paperclip size={17}/><span>Attach PDF</span></button><input ref={fileRef} type="file" accept="application/pdf,.pdf" hidden onChange={e => setFile(e.target.files?.[0] || null)}/><span className="tool-divider"/><button className="composer-tool voice-btn" aria-label="Voice input (coming soon)" title="Voice input coming soon"><Mic size={16}/></button></div><div className="tool-right"><span className="enter-hint">↵ <span>to send</span></span><button className={`send-btn ${input.trim() || file ? 'send-ready' : ''}`} onClick={() => send()} disabled={loading || (!input.trim() && !file)} aria-label="Send message"><ArrowUp size={17}/></button></div></div></div><div className="disclaimer">GovEase AI can make mistakes. Verify important details with the official source.</div></div></div>
    </main>
    {accountModal && <AuthModal key={accountModal} initialMode={accountModal} busy={accountBusy} error={accountError} onClose={() => { setAccountModal(null); setAccountError('') }} onSubmit={submitAccount} onModeChange={() => setAccountError('')}/>}
    {profileDialogOpen && user && <ProfileDialog user={user} busy={accountBusy} error={accountError} onClose={() => { setProfileDialogOpen(false); setAccountError('') }} onSave={saveProfile}/>}
  </div>
}
