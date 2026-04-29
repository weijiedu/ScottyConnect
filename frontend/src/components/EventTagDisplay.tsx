import { useEffect, useState } from 'react'
import { getAllTags, type Tag } from '../services/RecommendationService'
import '../styles/EventTagDisplay.css'

// Module-level cache so multiple instances share a single fetch.
let tagsCache: Promise<Tag[]> | null = null

function loadTagsCached(): Promise<Tag[]> {
  if (!tagsCache) {
    tagsCache = getAllTags().catch((err) => {
      // Clear the cache on failure so the next render can retry.
      tagsCache = null
      throw err
    })
  }
  return tagsCache
}

interface EventTagDisplayProps {
  tagIds: string[]
  /** Max number of tags to show inline before collapsing into a "+N" pill. */
  limit?: number
}

export default function EventTagDisplay({ tagIds, limit = 3 }: EventTagDisplayProps) {
  const [tagMap, setTagMap] = useState<Record<string, Tag>>({})

  useEffect(() => {
    let cancelled = false
    loadTagsCached()
      .then((tags) => {
        if (cancelled) return
        const map: Record<string, Tag> = {}
        for (const t of tags) map[t.id] = t
        setTagMap(map)
      })
      .catch(() => {
        /* Silent fail — tags just render blank. */
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (!tagIds || tagIds.length === 0) return null

  const visible = tagIds.slice(0, limit)
  const hidden = tagIds.length > limit ? tagIds.length - limit : 0

  return (
    <div className="event-tag-display">
      {visible.map((id) => {
        const tag = tagMap[id]
        const label = tag ? tag.displayName?.trim() || tag.slug : '…'
        return (
          <span key={id} className="event-tag-display-pill">
            {label}
          </span>
        )
      })}
      {hidden > 0 && (
        <span className="event-tag-display-more">+{hidden}</span>
      )}
    </div>
  )
}
