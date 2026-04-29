import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import StorageUtil from '../common/StorageUtil'
import { getEvent, apiEventToStored } from '../services/LifecycleService'
import { apiUrl } from '../services/Config'
import { loadEvents } from './CreateEventPage'
import type { StoredEvent } from '../types/event'
import '../styles/TaskBoard.css'

interface TaskNode {
  id: string
  event_id: string
  parent_id: string | null
  title: string
  description: string
  status: string
  assigned_to: string | null
  assigned_to_username: string | null
  contribution: string | null
  created_by: string
  progress: number
  children: TaskNode[]
  created_at: string
  updated_at: string
}

type ModalMode =
  | { kind: 'create'; parentId: string | null }
  | { kind: 'edit'; task: TaskNode }
  | { kind: 'contribute'; task: TaskNode }
  | null

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  claimed: 'Claimed',
  completed: 'Completed',
  closed: 'Closed',
  unavailable: 'Unavailable',
}

function mkHeaders(ev: StoredEvent | null): HeadersInit {
  const token = StorageUtil.getToken() ?? ''
  const h: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  }
  if (ev) {
    h['X-Event-Owner-Id'] = ev.ownerId
    h['X-Event-Status'] = ev.status
  }
  return h
}

export default function TaskBoardPage() {
  const { eventId } = useParams<{ eventId: string }>()
  const navigate = useNavigate()
  const user = StorageUtil.getUser()
  const userId = user.id ?? ''

  const [event, setEvent] = useState<StoredEvent | null>(null)
  const [tasks, setTasks] = useState<TaskNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState<ModalMode>(null)

  const isOwner = event?.ownerId === userId
  const eventStatus = event?.status ?? 'draft'
  const canCreateTask = isOwner && (eventStatus === 'draft' || eventStatus === 'published')
  const canEdit = isOwner && (eventStatus === 'draft' || eventStatus === 'published')
  const canClaim = eventStatus === 'published'
  const canContribute = eventStatus === 'published'

  const loadTaskTree = useCallback(async (ev: StoredEvent | null) => {
    if (!eventId) return
    try {
      const res = await fetch(apiUrl(`/api/tasks/events/${eventId}`), {
        headers: mkHeaders(ev),
      })
      const data = await res.json()
      if (res.ok) {
        setTasks(data.tasks ?? [])
        setError('')
      } else {
        setError(data.message ?? 'Failed to load tasks')
      }
    } catch {
      setError('Network error — could not load tasks')
    } finally {
      setLoading(false)
    }
  }, [eventId, userId])

  useEffect(() => {
    let cancelled = false

    async function loadEventAndTasks() {
      if (!eventId) return
      setLoading(true)
      setError('')

      let ev: StoredEvent | null = loadEvents().find((e) => e.id === eventId) ?? null

      if (!ev) {
        try {
          const apiEv = await getEvent(eventId)
          ev = apiEventToStored(apiEv)
        } catch (e) {
          if (!cancelled) {
            setError(e instanceof Error ? e.message : 'Failed to load event')
          }
        }
      }

      if (cancelled) return
      setEvent(ev)
      await loadTaskTree(ev)
    }

    loadEventAndTasks()
    return () => {
      cancelled = true
    }
  }, [eventId, loadTaskTree])

  function overallProgress(): number {
    if (tasks.length === 0) return 0
    const total = tasks.reduce((s, t) => s + t.progress, 0)
    return Math.round(total / tasks.length)
  }

  async function handleCreate(title: string, description: string, parentId: string | null) {
    if (!eventId) return

    try {
      const res = await fetch(apiUrl(`/api/tasks/events/${eventId}`), {
        method: 'POST',
        headers: mkHeaders(event),
        body: JSON.stringify({ title, description, parent_id: parentId }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.message ?? 'Failed to create task')
        return
      }
    } catch {
      setError('Network error')
      return
    }

    setModal(null)
    await loadTaskTree(event)
  }

  async function handleUpdate(taskId: string, title: string, description: string) {
    try {
      const res = await fetch(apiUrl(`/api/tasks/${taskId}`), {
        method: 'PUT',
        headers: mkHeaders(event),
        body: JSON.stringify({ title, description }),
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.message ?? 'Failed to update task')
        return
      }
    } catch {
      setError('Network error')
      return
    }

    setModal(null)
    await loadTaskTree(event)
  }

  async function handleDelete(taskId: string) {
    if (!confirm('Delete this task and all its sub-tasks?')) return

    try {
      const res = await fetch(apiUrl(`/api/tasks/${taskId}`), {
        method: 'DELETE',
        headers: mkHeaders(event),
      })
      const data = await res.json()
      
      if (!res.ok) {
        setError(data.message ?? 'Failed to delete task')
        return
      }
    } catch {
      setError('Network error')
      return
    }

    await loadTaskTree(event)
  }

  async function handleClaim(taskId: string) {
    try {
      const res = await fetch(apiUrl(`/api/tasks/${taskId}/claim`), {
        method: 'POST',
        headers: mkHeaders(event),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.message ?? 'Failed to claim task')
        return
      }
    } catch {
      setError('Network error')
      return
    }
    await loadTaskTree(event)
  }

  async function handleUnclaim(taskId: string) {
    try {
      const res = await fetch(apiUrl(`/api/tasks/${taskId}/claim`), {
        method: 'DELETE',
        headers: mkHeaders(event),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.message ?? 'Failed to unclaim task')
        return
      }
    } catch {
      setError('Network error')
      return
    }
    await loadTaskTree(event)
  }

  async function handleContribute(taskId: string, contribution: string) {
    try {
      const res = await fetch(apiUrl(`/api/tasks/${taskId}/contribute`), {
        method: 'POST',
        headers: mkHeaders(event),
        body: JSON.stringify({ contribution }),
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.message ?? 'Failed to submit contribution')

        return
      }
    } catch {
      setError('Network error')

      return
    }

    setModal(null)
    await loadTaskTree(event)
  }

  const pct = overallProgress()

  return (
    <div className="tb-page">
      <header className="tb-header">
        <div className="tb-header-inner">
          <button className="tb-back" onClick={() => navigate('/my-events')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Back to My Events
          </button>
        </div>
      </header>

      <main className="tb-content">
        <h1 className="tb-title">Task Board</h1>
        <p className="tb-subtitle">{event?.title ?? 'Event'}</p>

        {error && <div className="tb-error">{error}</div>}

        {/* Overall progress */}
        <div className="tb-progress-section">
          <div className="tb-progress-header">
            <span className="tb-progress-label">Overall Progress</span>
            <span className="tb-progress-pct">{pct}%</span>
          </div>
          <div className="tb-progress-track">
            <div className="tb-progress-fill" style={{ width: `${pct}%` }} />
          </div>
        </div>

        {/* Toolbar */}
        <div className="tb-toolbar">
          <h2 className="tb-toolbar-title">Tasks</h2>
          {canCreateTask && (
            <button className="tb-add-btn" onClick={() => setModal({ kind: 'create', parentId: null })}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
              Add Task
            </button>
          )}
        </div>

        {/* Task tree */}
        {loading ? (
          <div className="tb-loading">Loading tasks...</div>
        ) : tasks.length === 0 ? (
          <div className="tb-empty">
            <p>No tasks yet.{canCreateTask ? ' Create the first one!' : ''}</p>
          </div>
        ) : (
          <div className="tb-tree">
            {tasks.map((t) => (
              <TaskNodeItem
                key={t.id}
                node={t}
                userId={userId}
                isOwner={isOwner}
                canEdit={canEdit}
                canCreateTask={canCreateTask}
                canClaim={canClaim}
                canContribute={canContribute}
                onAddSub={(parentId) => setModal({ kind: 'create', parentId })}
                onEdit={(task) => setModal({ kind: 'edit', task })}
                onDelete={handleDelete}
                onClaim={handleClaim}
                onUnclaim={handleUnclaim}
                onContribute={(task) => setModal({ kind: 'contribute', task })}
              />
            ))}
          </div>
        )}
      </main>

      <footer className="tb-footer">
        <p>ScottyConnect · Carnegie Mellon University</p>
      </footer>

      {/* Modals */}
      {modal?.kind === 'create' && (
        <CreateTaskModal
          parentId={modal.parentId}
          onSubmit={handleCreate}
          onClose={() => setModal(null)}
        />
      )}
      {modal?.kind === 'edit' && (
        <EditTaskModal
          task={modal.task}
          onSubmit={handleUpdate}
          onClose={() => setModal(null)}
        />
      )}
      {modal?.kind === 'contribute' && (
        <ContributeModal
          task={modal.task}
          onSubmit={handleContribute}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  )
}

interface TaskNodeProps {
  node: TaskNode
  userId: string
  isOwner: boolean
  canEdit: boolean
  canCreateTask: boolean
  canClaim: boolean
  canContribute: boolean
  onAddSub: (parentId: string) => void
  onEdit: (task: TaskNode) => void
  onDelete: (taskId: string) => void
  onClaim: (taskId: string) => void
  onUnclaim: (taskId: string) => void
  onContribute: (task: TaskNode) => void
}

function TaskNodeItem({
  node, userId, isOwner, canEdit, canCreateTask, canClaim, canContribute,
  onAddSub, onEdit, onDelete, onClaim, onUnclaim, onContribute,
}: TaskNodeProps) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.children.length > 0
  const isLeaf = !hasChildren
  const statusCls = `tb-status tb-status-${node.status}`
  const isMyClaim = node.assigned_to === userId

  return (
    <div className="tb-node">
      <div className="tb-node-header">
        {hasChildren ? (
          <button
            className={`tb-expand-btn ${expanded ? 'expanded' : ''}`}
            onClick={() => setExpanded(!expanded)}
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        ) : (
          <span style={{ width: 24, flexShrink: 0 }} />
        )}

        <div className="tb-node-info">
          <p className="tb-node-title">
            {node.title}
            {node.assigned_to && (
              <span className="tb-assigned">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                {isMyClaim ? 'You' : (node.assigned_to_username ?? node.assigned_to.slice(0, 8))}
              </span>
            )}
          </p>
          {node.description && <p className="tb-node-desc">{node.description}</p>}
        </div>

        <div className="tb-node-meta">
          {hasChildren && (
            <div className="tb-node-progress">
              <div className="tb-node-progress-fill" style={{ width: `${Math.round(node.progress)}%` }} />
            </div>
          )}
          <span className={statusCls}>{STATUS_LABELS[node.status] ?? node.status}</span>
        </div>
      </div>

      {/* Contribution display */}
      {node.contribution && (
        <div className="tb-contribution">
          <div className="tb-contribution-label">Contribution</div>
          <div className="tb-contribution-box">{node.contribution}</div>
        </div>
      )}

      {/* Action buttons */}
      <div className="tb-node-actions">
        {canCreateTask && (
          <button className="tb-btn tb-btn-secondary" onClick={() => onAddSub(node.id)}>
            + Sub-task
          </button>
        )}
        {canEdit && node.status !== 'claimed' && node.status !== 'completed' && (
          <button className="tb-btn tb-btn-secondary" onClick={() => onEdit(node)}>
            Edit
          </button>
        )}
        {canEdit && (
          <button className="tb-btn tb-btn-danger" onClick={() => onDelete(node.id)}>
            Delete
          </button>
        )}
        {canClaim && isLeaf && node.status === 'open' && (
          <button className="tb-btn tb-btn-claim" onClick={() => onClaim(node.id)}>
            Claim
          </button>
        )}
        {canContribute && isMyClaim && node.status === 'claimed' && (
          <button className="tb-btn tb-btn-contribute" onClick={() => onContribute(node)}>
            Submit Contribution
          </button>
        )}
        {canClaim && isLeaf && node.status === 'claimed' && (isMyClaim || isOwner) && (
          <button className="tb-btn tb-btn-secondary" onClick={() => onUnclaim(node.id)}>
            Cancel Claim
          </button>
        )}
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div className="tb-children">
          {node.children.map((child) => (
            <TaskNodeItem
              key={child.id}
              node={child}
              userId={userId}
              isOwner={isOwner}
              canEdit={canEdit}
              canCreateTask={canCreateTask}
              canClaim={canClaim}
              canContribute={canContribute}
              onAddSub={onAddSub}
              onEdit={onEdit}
              onDelete={onDelete}
              onClaim={onClaim}
              onUnclaim={onUnclaim}
              onContribute={onContribute}
            />
          ))}
        </div>
      )}
    </div>
  )
}


function CreateTaskModal({
  parentId,
  onSubmit,
  onClose,
}: {
  parentId: string | null
  onSubmit: (title: string, desc: string, parentId: string | null) => void
  onClose: () => void
}) {
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')
  const valid = title.trim().length > 0

  return (
    <div className="tb-modal-overlay" onClick={onClose}>
      <div className="tb-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="tb-modal-title">{parentId ? 'Add Sub-task' : 'Create Task'}</h2>
        <div className="tb-modal-field">
          <label className="tb-modal-label">Title *</label>
          <input
            className="tb-modal-input"
            placeholder="Task title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
        </div>
        <div className="tb-modal-field">
          <label className="tb-modal-label">Description</label>
          <textarea
            className="tb-modal-textarea"
            placeholder="Optional description..."
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
          />
        </div>
        <div className="tb-modal-actions">
          <button
            className="tb-modal-btn tb-modal-btn-primary"
            disabled={!valid}
            onClick={() => onSubmit(title.trim(), desc.trim(), parentId)}
          >
            Create
          </button>
          <button className="tb-modal-btn tb-modal-btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}


function EditTaskModal({
  task,
  onSubmit,
  onClose,
}: {
  task: TaskNode
  onSubmit: (taskId: string, title: string, desc: string) => void
  onClose: () => void
}) {
  const [title, setTitle] = useState(task.title)
  const [desc, setDesc] = useState(task.description)
  const valid = title.trim().length > 0

  return (
    <div className="tb-modal-overlay" onClick={onClose}>
      <div className="tb-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="tb-modal-title">Edit Task</h2>
        <div className="tb-modal-field">
          <label className="tb-modal-label">Title *</label>
          <input
            className="tb-modal-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
        </div>
        <div className="tb-modal-field">
          <label className="tb-modal-label">Description</label>
          <textarea
            className="tb-modal-textarea"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
          />
        </div>
        <div className="tb-modal-actions">
          <button
            className="tb-modal-btn tb-modal-btn-primary"
            disabled={!valid}
            onClick={() => onSubmit(task.id, title.trim(), desc.trim())}
          >
            Save
          </button>
          <button className="tb-modal-btn tb-modal-btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}


function ContributeModal({
  task,
  onSubmit,
  onClose,
}: {
  task: TaskNode
  onSubmit: (taskId: string, contribution: string) => void
  onClose: () => void
}) {
  const [text, setText] = useState('')
  const valid = text.trim().length > 0

  return (
    <div className="tb-modal-overlay" onClick={onClose}>
      <div className="tb-modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="tb-modal-title">Submit Contribution</h2>
        <p style={{ fontSize: '0.875rem', color: 'var(--iron-gray)', margin: '0 0 14px' }}>
          Describe what you did for "{task.title}"
        </p>
        <div className="tb-modal-field">
          <label className="tb-modal-label">Contribution *</label>
          <textarea
            className="tb-modal-textarea"
            placeholder="Describe your contribution..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            autoFocus
          />
        </div>
        <div className="tb-modal-actions">
          <button
            className="tb-modal-btn tb-modal-btn-primary"
            disabled={!valid}
            onClick={() => onSubmit(task.id, text.trim())}
          >
            Submit
          </button>
          <button className="tb-modal-btn tb-modal-btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
