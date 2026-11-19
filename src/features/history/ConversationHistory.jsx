import { useState } from 'react'
import { Check, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'

export default function ConversationHistory({ items, activeId, onOpen, onRename, onDelete }) {
  const [editingId, setEditingId] = useState(null)
  const [title, setTitle] = useState('')
  const [menuId, setMenuId] = useState(null)

  const beginRename = item => { setEditingId(item.id); setTitle(item.title); setMenuId(null) }
  const saveRename = async event => {
    event.preventDefault()
    if (title.trim()) await onRename(editingId, title.trim())
    setEditingId(null)
  }

  if (!items.length) return <div className="history-empty"><div className="history-icon">⌁</div><p>Your saved conversations<br/>will appear here</p></div>
  return <div className="history-list">
    {items.map(item => <div className={`history-item ${activeId === item.id ? 'history-item-active' : ''}`} key={item.id}>
      {editingId === item.id ? <form className="history-rename" onSubmit={saveRename}><input autoFocus value={title} onChange={event => setTitle(event.target.value)} maxLength={100}/><button type="submit" aria-label="Save title"><Check size={14}/></button></form> : <>
        <button className="history-open" onClick={() => onOpen(item.id)} title={item.title}>{item.title}</button>
        <button className="history-more" onClick={() => setMenuId(menuId === item.id ? null : item.id)} aria-label="Conversation options"><MoreHorizontal size={16}/></button>
        {menuId === item.id && <div className="history-actions"><button onClick={() => beginRename(item)}><Pencil size={13}/>Rename</button><button onClick={() => { setMenuId(null); onDelete(item.id) }}><Trash2 size={13}/>Delete</button></div>}
      </>}
    </div>)}
  </div>
}
