/**
 * GraphbaseService
 *
 * Wraps the /db/* endpoints exposed by the graphbase submodule.
 * All methods return null / empty on any error rather than throwing
 * so callers can treat an unavailable graphbase as graceful degradation.
 *
 * The /db routes are only mounted when MONGODB_URI is set on the backend,
 * so a 404 on GET /db/ means graphbase is not configured — not a bug.
 */

export interface GraphbaseBookmark {
  name: string;
  url: string;
  layout: string;
  depth: number;
  extensions: string[];
  saved_at: number;
}

export interface GraphbaseSnapshotMeta {
  name: string;
  saved_at: number;
  meta?: { url?: string; layout?: string; nodeCount?: number };
}

export interface GraphbaseSnapshot extends GraphbaseSnapshotMeta {
  nodes: Array<{ id: string; [k: string]: unknown }>;
  edges: Array<{ source: string; target: string; [k: string]: unknown }>;
}

export const GraphbaseService = {
  /** Returns true when the /db/* router is reachable (MONGODB_URI is set). */
  async isAvailable(dbBase: string): Promise<boolean> {
    try {
      const r = await fetch(`${dbBase}/`, { signal: AbortSignal.timeout(2000) });
      return r.ok;
    } catch {
      return false;
    }
  },

  /** List all saved bookmarks. Returns [] when unavailable. */
  async listBookmarks(dbBase: string): Promise<GraphbaseBookmark[]> {
    try {
      const r = await fetch(`${dbBase}/bookmarks`);
      if (!r.ok) return [];
      return (await r.json()) as GraphbaseBookmark[];
    } catch {
      return [];
    }
  },

  /**
   * Save a bookmark. Silently upserts (replaces) if name already exists.
   * Returns true on success.
   */
  async saveBookmark(
    dbBase: string,
    name: string,
    url: string,
    layout: string,
    depth: number,
    extensions: string[],
  ): Promise<boolean> {
    try {
      const params = new URLSearchParams({
        name,
        url,
        layout,
        depth: String(depth),
        extensions: extensions.join(','),
      });
      const r = await fetch(`${dbBase}/bookmarks?${params}`, { method: 'POST' });
      return r.ok;
    } catch {
      return false;
    }
  },

  /** Delete a named bookmark. Returns true on success. */
  async deleteBookmark(dbBase: string, name: string): Promise<boolean> {
    try {
      const r = await fetch(`${dbBase}/bookmarks/${encodeURIComponent(name)}`, { method: 'DELETE' });
      return r.ok;
    } catch {
      return false;
    }
  },

  // ── Snapshot methods ──────────────────────────────────────────────────────

  /** List saved snapshots (metadata only, no node/edge payloads). */
  async listSnapshots(dbBase: string): Promise<GraphbaseSnapshotMeta[]> {
    try {
      const r = await fetch(`${dbBase}/snapshots`);
      if (!r.ok) return [];
      return (await r.json()) as GraphbaseSnapshotMeta[];
    } catch {
      return [];
    }
  },

  /** Save a full graph snapshot (nodes + edges + metadata). Returns true on success. */
  async saveSnapshot(
    dbBase: string,
    name: string,
    nodes: Array<{ id: string; [k: string]: unknown }>,
    edges: Array<{ source: string; target: string; [k: string]: unknown }>,
    meta: { url?: string; layout?: string; nodeCount?: number },
  ): Promise<boolean> {
    try {
      const r = await fetch(
        `${dbBase}/snapshots?name=${encodeURIComponent(name)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nodes, edges, meta }),
        },
      );
      return r.ok;
    } catch {
      return false;
    }
  },

  /** Load a full snapshot (nodes + edges) for instant replay. */
  async loadSnapshot(dbBase: string, name: string): Promise<GraphbaseSnapshot | null> {
    try {
      const r = await fetch(`${dbBase}/snapshots/${encodeURIComponent(name)}`);
      if (!r.ok) return null;
      return (await r.json()) as GraphbaseSnapshot;
    } catch {
      return null;
    }
  },

  /** Delete a named snapshot. Returns true on success. */
  async deleteSnapshot(dbBase: string, name: string): Promise<boolean> {
    try {
      const r = await fetch(`${dbBase}/snapshots/${encodeURIComponent(name)}`, { method: 'DELETE' });
      return r.ok;
    } catch {
      return false;
    }
  },
};
