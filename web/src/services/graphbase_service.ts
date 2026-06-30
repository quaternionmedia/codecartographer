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

export interface GraphbaseHistoryMeta {
  url_hash: string;
  url: string;
  captured_at: number;
  meta?: { layout?: string; nodeCount?: number };
}

export interface GraphbaseHistoryEntry extends GraphbaseHistoryMeta {
  nodes: Array<{ id: string; [k: string]: unknown }>;
  edges: Array<{ source: string; target: string; [k: string]: unknown }>;
}

/** SHA-256 URL hash (first 16 hex chars) matching CacheService's repo-key scheme. */
async function urlHash(url: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(url));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
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

  // ── History methods ───────────────────────────────────────────────────────

  /** Append a history entry for the given URL. Returns true on success. */
  async appendHistory(
    dbBase: string,
    url: string,
    nodes: Array<{ id: string; [k: string]: unknown }>,
    edges: Array<{ source: string; target: string; [k: string]: unknown }>,
    meta: { layout?: string; nodeCount?: number },
  ): Promise<boolean> {
    try {
      const params = new URLSearchParams({ url });
      const r = await fetch(`${dbBase}/history?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges, meta }),
      });
      return r.ok;
    } catch {
      return false;
    }
  },

  /** List history metadata for a URL (no node/edge payloads). */
  async listHistory(dbBase: string, url: string): Promise<GraphbaseHistoryMeta[]> {
    try {
      const hash = await urlHash(url);
      const r = await fetch(`${dbBase}/history/${hash}`);
      if (!r.ok) return [];
      return (await r.json()) as GraphbaseHistoryMeta[];
    } catch {
      return [];
    }
  },

  /** Retrieve a specific history entry (full data). */
  async getHistoryEntry(
    dbBase: string,
    urlHash: string,
    capturedAt: number,
  ): Promise<GraphbaseHistoryEntry | null> {
    try {
      const r = await fetch(`${dbBase}/history/${urlHash}/${capturedAt}`);
      if (!r.ok) return null;
      return (await r.json()) as GraphbaseHistoryEntry;
    } catch {
      return null;
    }
  },

  /** Delete a specific history entry. Returns true on success. */
  async deleteHistoryEntry(dbBase: string, urlHash: string, capturedAt: number): Promise<boolean> {
    try {
      const r = await fetch(`${dbBase}/history/${urlHash}/${capturedAt}`, { method: 'DELETE' });
      return r.ok;
    } catch {
      return false;
    }
  },
};
