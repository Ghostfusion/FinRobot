// coverageStore — UI-only state for the Coverage archive: which group is open,
// card density, and the card-sort choice. The authoritative coverage data
// (groups, members, overview) lives in the backend SQLite store and is fetched
// via TanStack Query (useCoverage); localStorage here holds ONLY view-state.

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { CoverageSort } from '../components/coverage/coverageSort'

export type CoverageDensity = 'comfort' | 'compact'

interface CoverageUiState {
  selectedGroupId: string | null
  // Card density — a global view preference (not per-group), persisted.
  density: CoverageDensity
  // Card-sort choice. null = the page's DEFAULT_SORT (needs-attention desc), so a
  // fresh store has no opinion. The page runs the persisted value through
  // normaliseCoverageSort on read, so a stale key degrades to the default rather
  // than an unsorted wall.
  sort: CoverageSort | null
  setSelectedGroup: (id: string | null) => void
  setDensity: (density: CoverageDensity) => void
  setSort: (sort: CoverageSort | null) => void
}

export const useCoverageStore = create<CoverageUiState>()(
  persist(
    (set) => ({
      selectedGroupId: null,
      density: 'comfort',
      sort: null,
      setSelectedGroup: (id) => set({ selectedGroupId: id }),
      setDensity: (density) => set({ density }),
      setSort: (sort) => set({ sort }),
    }),
    {
      name: 'finrobot-coverage-ui',
      storage: createJSONStorage(() => localStorage),
      // Persist only durable view preferences.
      partialize: (s) => ({
        selectedGroupId: s.selectedGroupId,
        density: s.density,
        sort: s.sort,
      }),
    },
  ),
)
