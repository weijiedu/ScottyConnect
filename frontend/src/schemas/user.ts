import { snakeToCamel } from '../services/ServiceUtils'

export type UserRole = 'STUDENT' | 'ALUMNI'

export interface PublicUser {
  id: string | null
  username: string
  email: string
  verified: boolean
  role: UserRole
  bio: string
  tags: string[]
  createdAt: string
  updatedAt: string
}

export function apiUserFromSnake(raw: Record<string, unknown>): PublicUser {
  const user = snakeToCamel(raw) as Record<string, unknown>
  return {
    id: (user.id as string | null) ?? null,
    username: user.username as string,
    email: user.email as string,
    verified: user.verified as boolean,
    role: user.role as UserRole,
    bio: (user.bio as string) ?? '',
    tags: (user.tags as string[]) ?? [],
    createdAt: (user.createdAt as string) ?? '',
    updatedAt: (user.updatedAt as string) ?? '',
  }
}
