import { RequestHandler } from './request_handler';
import { Directory } from '../components/models/source';
import { logger } from '../core/logger';

type PlotRequestBody = Record<string, unknown> | FormData;

export interface StreamMeta {
  nodeCount: number;
  edgeCount: number;
  layout: string;
  from_cache?: boolean;
}
export interface StreamNode { id: string; x?: number; y?: number; [k: string]: unknown; }
export interface StreamEdge { source: string; target: string; [k: string]: unknown; }

export interface StreamCallbacks {
  onMeta: (meta: StreamMeta) => void;
  onNode: (node: StreamNode, index: number) => void;
  onEdge: (edge: StreamEdge) => void;
  onDone: (elapsed_ms: number, from_cache?: boolean) => void;
  onError: (msg: string) => void;
  /** Called on 'fetching' events (stream-url only): status message updates before nodes arrive. */
  onFetching?: (message: string) => void;
}

export class PlotService {
  /** Load demo data from backend. */
  public static async loadDemo(
    plotterUrl: string,
    layout: string = 'Spring',
    parseMode: string = 'directory'
  ): Promise<unknown> {
    const body = {
      options: {
        palette_id: '0',
        layout: layout,
        type: 'd3',
        parse_by: parseMode,
      },
    };
    const data = await this.sendPlotRequest(plotterUrl, '/demo', body);
    if (typeof data === 'string') {
      logger.error('Error loading demo');
      return null;
    }
    return data;
  }

  /**
   * Convert GraphData JSON to pre-rendered HTML for Notebook renderer.
   * Sends graph data to backend which renders it using gravis and returns HTML.
   */
  public static async renderToHtml(
    plotterUrl: string,
    graphData: unknown,
    layout: string = 'Spring'
  ): Promise<{ 'text/html': string } | null> {
    const body = {
      graph_data: graphData,
      options: {
        layout: layout,
      },
    };
    const data = await this.sendPlotRequest(plotterUrl, '/render/html', body);
    if (typeof data === 'string' || !data) {
      logger.error('Error rendering to HTML');
      return null;
    }
    // RequestHandler already extracts responseData.results, so data IS the results object
    // Expected format: { "text/html": "<html>..." }
    const result = data as { 'text/html'?: string };
    if (result['text/html']) {
      return { 'text/html': result['text/html'] };
    }
    logger.error('Invalid response format from renderToHtml:', data);
    return null;
  }

  /** Fetch the registered language extensions from the backend. */
  public static async fetchLanguages(
    parseUrl: string
  ): Promise<Record<string, string[]> | null> {
    const data = await RequestHandler.getRequest(`${parseUrl}/languages`) as Record<string, unknown> | null;
    return (data?.['languages'] as Record<string, string[]>) ?? null;
  }

  /** Parse a directory using the unified schema (depth-based hierarchy). */
  public static async plotUnified(
    parseUrl: string,
    directory: Directory,
    depth: number = 2,
    extensions: string[] | null = null,
    layout: string = 'Spring',
    mode?: string
  ): Promise<unknown> {
    const url = `${parseUrl}/unified`;
    const body: Record<string, unknown> = {
      directory: {
        info: directory.info,
        size: directory.size,
        root: directory.root,
        is_partial: directory.is_partial,
      },
      depth,
      layout,
    };
    if (extensions) {
      body['extensions'] = extensions;
    }
    if (mode) {
      body['mode'] = mode;
    }
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      logger.error('Error plotUnified');
      return null;
    }
    return data;
  }

  /** Expand a single file node to reveal its symbols. */
  public static async expandNode(
    parseUrl: string,
    directory: Directory,
    nodeId: string,
    depth: number = 2
  ): Promise<unknown> {
    const url = `${parseUrl}/expand`;
    const body = {
      directory: {
        info: directory.info,
        size: directory.size,
        root: directory.root,
        is_partial: directory.is_partial,
      },
      node_id: nodeId,
      depth,
    };
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      logger.error('Error expandNode');
      return null;
    }
    return data;
  }

  /**
   * Read an SSE response body and dispatch (eventType, payload) to onEvent
   * as each complete `event: ...\ndata: ...\n\n` frame arrives. Shared by
    * streamUnified/streamFromUrl so each only needs to define
   * its request body and its event-type dispatch.
   */
  private static async _consumeSSE(
    resp: Response,
    onEvent: (eventType: string, payload: any) => void,
  ): Promise<void> {
    if (!resp.body) return;
    const reader = resp.body.pipeThrough(new TextDecoderStream()).getReader();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += value;

      // Parse complete SSE events (terminated by double newline)
      const parts = buf.split('\n\n');
      buf = parts.pop() ?? '';

      for (const part of parts) {
        const lines = part.trim().split('\n');
        let eventType = 'message';
        let dataStr = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7).trim();
          if (line.startsWith('data: '))  dataStr  = line.slice(6).trim();
        }
        if (!dataStr) continue;

        try {
          onEvent(eventType, JSON.parse(dataStr));
        } catch {
          // ignore malformed events
        }
      }
    }
  }

  /**
   * Stream a parse result via POST + SSE.
   * Returns a cancel function; call it to abort the stream.
   */
  static streamUnified(
    parseUrl: string,
    directory: Directory,
    opts: {
      depth?: number;
      extensions?: string[] | null;
      layout?: string;
      mode?: string;
    },
    callbacks: StreamCallbacks
  ): () => void {
    const controller = new AbortController();
    const { depth = 2, extensions = null, layout = 'Spring', mode } = opts;

    const body: Record<string, unknown> = {
      directory: {
        info: directory.info,
        size: directory.size,
        root: directory.root,
        is_partial: directory.is_partial,
      },
      depth,
      layout,
    };
    if (extensions) body['extensions'] = extensions;
    if (mode)       body['mode'] = mode;

    let nodeIndex = 0;

    (async () => {
      try {
        const resp = await fetch(`${parseUrl}/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
          body: JSON.stringify(body),
          signal: controller.signal,
        });

        if (!resp.ok || !resp.body) {
          callbacks.onError(`HTTP ${resp.status}`);
          return;
        }

        await this._consumeSSE(resp, (eventType, payload) => {
          switch (eventType) {
            case 'meta':  callbacks.onMeta(payload as StreamMeta); break;
            case 'node':  callbacks.onNode(payload as StreamNode, nodeIndex++); break;
            case 'edge':  callbacks.onEdge(payload as StreamEdge); break;
            case 'done':  callbacks.onDone(payload.elapsed_ms ?? 0, payload.from_cache); break;
            case 'error': callbacks.onError(payload.message ?? 'Stream error'); break;
          }
        });
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;  // cancelled
        callbacks.onError(String(err));
      }
    })();

    return () => controller.abort();
  }

  /**
   * Stream a parse result directly from a GitHub URL (two-phase: structure first, symbols second).
   * Returns a cancel function; call it to abort.
   */
  static streamFromUrl(
    parseUrl: string,
    githubUrl: string,
    opts: {
      depth?: number;
      extensions?: string[] | null;
      layout?: string;
      mode?: string;
    },
    callbacks: StreamCallbacks
  ): () => void {
    const controller = new AbortController();
    const { depth = 2, extensions = null, layout = 'Spring', mode } = opts;

    const body: Record<string, unknown> = { url: githubUrl, depth, layout };
    if (extensions) body['extensions'] = extensions;
    if (mode)       body['mode'] = mode;

    let nodeIndex = 0;

    (async () => {
      try {
        const resp = await fetch(`${parseUrl}/stream-url`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
          body: JSON.stringify(body),
          signal: controller.signal,
        });

        if (!resp.ok || !resp.body) {
          callbacks.onError(`HTTP ${resp.status}`);
          return;
        }

        await this._consumeSSE(resp, (eventType, payload) => {
          switch (eventType) {
            case 'fetching': callbacks.onFetching?.(payload.message ?? ''); break;
            case 'meta':  callbacks.onMeta(payload as StreamMeta); break;
            case 'node':  callbacks.onNode(payload as StreamNode, nodeIndex++); break;
            case 'edge':  callbacks.onEdge(payload as StreamEdge); break;
            case 'done':  callbacks.onDone(payload.elapsed_ms ?? 0, payload.from_cache); break;
            case 'error': callbacks.onError(payload.message ?? 'Stream error'); break;
            // 'phase' events are informational — ignored silently
          }
        });
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return;
        callbacks.onError(String(err));
      }
    })();

    return () => controller.abort();
  }

  /** Plot the content of the selected file. */
  private static async sendPlotRequest(
    plotterUrl: string,
    endpoint: string,
    body: PlotRequestBody
  ): Promise<unknown> {
    const url = `${plotterUrl}${endpoint}`;
    logger.debug('PlotService.sendPlotRequest - sending to:', url, 'body:', body);
    const data = await RequestHandler.postRequest(url, body);
    logger.debug('PlotService.sendPlotRequest - response:', data);
    if (typeof data === 'string') {
      logger.error('Error sendPlotRequest - got string response');
      return null;
    }
    return data;
  }
}
