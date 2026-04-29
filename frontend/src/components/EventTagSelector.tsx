import { useEffect, useState } from 'react'
import { getAllTags, type Tag } from '../services/RecommendationService'
import '../styles/EventTagSelector.css'

interface EventTagSelectorProps {
  selectedTagIds: Set<string>
  onToggle: (tagId: string) => void
}

export default function EventTagSelector({
  selectedTagIds,
  onToggle,
}: EventTagSelectorProps) {
  const [allTags, setAllTags] = useState<Tag[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    ;(async () => {
      try {
        const tags = await getAllTags()
        if (!cancelled) setAllTags(tags)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load tags')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return <p className="event-tag-selector-loading">Loading tags…</p>
  }

  if (error) {
    return <p className="event-tag-selector-error">{error}</p>
  }

  if (allTags.length === 0) {
    return <p className="event-tag-selector-empty">No tags available.</p>
  }

  const sortedTags = [...allTags].sort((a, b) => {
    const aLabel = a.displayName?.trim() || a.slug
    const bLabel = b.displayName?.trim() || b.slug
    return aLabel.localeCompare(bLabel, undefined, { sensitivity: 'base' })
  })

  return (
    <div className="event-tag-selector">
      <p className="event-tag-selector-label">Tags (optional)</p>
      <div className="event-tag-pills" role="group" aria-label="Event tags">
        {sortedTags.map((tag) => {
          const active = selectedTagIds.has(tag.id)
          const label = tag.displayName?.trim() || tag.slug
          return (
            <button
              key={tag.id}
              type="button"
              role="checkbox"
              aria-checked={active}
              className={`event-tag-pill${active ? ' is-active' : ''}`}
              onClick={() => onToggle(tag.id)}
            >
              {label}
            </button>
          )
        })}
      </div>
      <p className="event-tag-count">{selectedTagIds.size} selected</p>
    </div>
  )
}
