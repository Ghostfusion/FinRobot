// Version-history helpers shared by the report chrome.
//
// `priorVersions` lives here (not in the VersionDiffBanner component) because
// TWO callers need the same selection rule — the banner (which compares against
// a prior run) and the report page (which lists the "what changed" section in the
// rail only when such a run exists). Keeping it beside its consumer meant every
// test that mocks the banner component also had to re-declare the helper, and a
// missing stub silently turned the section-presence check into a crash.

import type { ArtifactSummaryV5 } from '../types/v5'

/** Prior versions of the SAME report type the diff can be taken against, in the
 *  timeline's own order (newest first where the backend supplies it). Empty →
 *  there is nothing to compare with, so no version-diff section exists. */
export function priorVersions(
  timeline: ArtifactSummaryV5[] | null | undefined,
  reportType: string,
  currentId: string,
): ArtifactSummaryV5[] {
  return (timeline ?? []).filter((a) => a.type === reportType && a.id !== currentId)
}
