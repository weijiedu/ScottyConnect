/** Shared event shape for UI lists and forms (camelCase). */
export interface StoredEvent {
  id: string
  title: string
  description: string
  date: string
  startTime: string
  endTime: string
  location: string
  capacity: number | null
  registeredCount: number | null
  status: 'draft' | 'published' | 'ended' | 'cancelled'
  ownerId: string
  createdAt: string
}

export interface EventFormData {
  title: string
  description: string
  date: string
  startTime: string
  endTime: string
  location: string
  capacity: string
}
