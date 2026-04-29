import { useEffect, useState } from 'react'
import { getAllTags, getUserTags, setUserTags, type Tag } from '../services/RecommendationService'

interface RecommendationSettingsModalProps {
  isOpen: boolean
  userId: string
  onClose: () => void
  onSaved?: (tagIds: string[]) => void
}

function tagLabel(tag: Tag): string {
  return tag.displayName?.trim() || tag.slug
}

export default function RecommendationSettingsModal({
  isOpen,
  userId,
  onClose,
  onSaved,
}: RecommendationSettingsModalProps) {
  const [allTags, setAllTags] = useState<Tag[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Reset and load when opening.
  useEffect(() => {
    if (!isOpen) return
    let cancelled = false
    setError('')
    setLoading(true)
    ;(async () => {
      try {
        const [tags, userTagIds] = await Promise.all([
          getAllTags(),
          getUserTags(userId),
        ])
        if (cancelled) return
        setAllTags(tags)
        setSelected(new Set(userTagIds))
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load tags')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [isOpen, userId])

  // Escape closes.
  useEffect(() => {
    if (!isOpen) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  function toggle(tagId: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(tagId)) {
        next.delete(tagId)
      } else {
        next.add(tagId)
      }
      return next
    })
  }

  async function handleSave() {
    setSaving(true)
    setError('')
    try {
      const saved = await setUserTags(userId, Array.from(selected))
      onSaved?.(saved)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save tags')
    } finally {
      setSaving(false)
    }
  }

  const sortedTags = [...allTags].sort((a, b) =>
    tagLabel(a).localeCompare(tagLabel(b), undefined, { sensitivity: 'base' }),
  )

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div
        className="settings-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="settings-modal-head">
          <h2 id="settings-modal-title" className="settings-modal-title">
            Your interests
          </h2>
          <button
            type="button"
            className="settings-modal-close"
            aria-label="Close"
            onClick={onClose}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </header>

        <p className="settings-modal-desc">
          Select tags that describe you. We'll use these to recommend events that match your interests.
        </p>

        {loading && <p className="settings-modal-desc">Loading tags…</p>}

        {!loading && sortedTags.length === 0 && !error && (
          <p className="settings-modal-desc">No tags available.</p>
        )}

        {!loading && sortedTags.length > 0 && (
          <div
            className="settings-tag-grid"
            role="group"
            aria-label="Available tags"
          >
            {sortedTags.map((tag) => {
              const active = selected.has(tag.id)
              return (
                <button
                  key={tag.id}
                  type="button"
                  role="checkbox"
                  aria-checked={active}
                  className={`settings-tag-pill${active ? ' is-active' : ''}`}
                  onClick={() => toggle(tag.id)}
                >
                  {tagLabel(tag)}
                </button>
              )
            })}
          </div>
        )}

        {!loading && (
          <p className="settings-modal-desc settings-tag-count">
            {selected.size} selected
          </p>
        )}

        {error && (
          <p className="settings-modal-error" role="alert">
            {error}
          </p>
        )}

        <footer className="settings-modal-actions">
          <button
            type="button"
            className="settings-modal-btn settings-modal-btn-ghost"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            type="button"
            className="settings-modal-btn settings-modal-btn-primary"
            onClick={handleSave}
            disabled={saving || loading}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </footer>
      </div>
    </div>
  )
}
