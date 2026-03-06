import useSWR from 'swr'
import { apiJson } from '@/lib/api-client'

export type ContainerInfo = {
  id: string
  name: string
  cpu_percent: number
  memory_mb: number
  status: string
  // Legacy fields used by ContainerList component (optional)
  image?: string
  created?: number
  labels?: Record<string, string>
}

export function useContainers() {
  const { data, error, isLoading } = useSWR<{ containers: ContainerInfo[] }>(
    '/api/containers',
    apiJson,
    { refreshInterval: 3000 }
  )

  return {
    containers: (data?.containers ?? []) as ContainerInfo[],
    error,
    isLoading,
  }
}
