/**
 * rad — the session. This is the whole inbound API.
 *
 * Implements §2 of the rad host integration standard. A host supplies CONTENT
 * (`resolve`) and STATE (`onIntent`); rad owns the geometry and the state
 * machine and owns nothing else. Nothing on this surface takes a scene, an
 * element, or a store — which is why rad cannot reach a host's scene. That is
 * a property of the surface, not a promise about discipline.
 *
 * Ported from quaternionmedia/rad @ d362abd, standard §2.
 */
import type {
  Effect,
  Geometry,
  InputEvent,
  MachineState,
  MenuContext,
  MenuSpec,
  RingView,
} from './core/types.js';
import { GEOM, fitRing } from './core/geometry.js';
import { assertRing, createMachine, step } from './core/machine.js';

export interface SessionOptions {
  /**
   * The host owns the vocabulary for its own domain. Called once per open and
   * never cached, so a menu is always current with host state.
   */
  resolve: (context: MenuContext) => MenuSpec;
  /**
   * The host applies the intent. rad has already forgotten the menu by the
   * time this is called, so an intent cannot be mistaken for a live handle.
   */
  onIntent: (intent: { action: string; context: MenuContext; itemId: string }) => void;
  /** Optional. Carries highlight, open, submenu, back and cancel. */
  onEffect?: (effect: Effect) => void;
  /** Optional per-session geometry overrides. */
  geometry?: Partial<Geometry>;
}

export interface Session {
  readonly isOpen: boolean;
  readonly view: RingView | null;
  openAt(context: MenuContext, viewport: { width: number; height: number }, mode?: 'idle' | 'tracking'): Effect[];
  input(ev: InputEvent): Effect[];
  close(): Effect[];
}

export function createSession(opts: SessionOptions): Session {
  const { resolve, onIntent, onEffect = () => {}, geometry } = opts;
  if (typeof resolve !== 'function') {
    throw new TypeError('rad: a host must supply resolve(context) → MenuSpec');
  }
  if (typeof onIntent !== 'function') {
    throw new TypeError('rad: a host must supply onIntent(intent)');
  }

  let machine: MachineState | null = null;
  let ctx: MenuContext | null = null;
  let geom: Geometry | null = null;

  function dispatch(ev: InputEvent): Effect[] {
    if (!machine) return [];
    const fx = step(machine, ev);
    for (const f of fx) {
      if (f.t === 'commit') {
        const item = f.item;
        const context = ctx as MenuContext;
        machine = null;
        ctx = null;
        // The intent is plain data: a verb, the context it applies to, and the
        // item id that produced it. Nothing here is a closure, which is what
        // lets a host serialize, queue, replay or send it over a wire.
        onIntent({ action: item.action ?? item.id, context, itemId: item.id });
      } else {
        if (f.t === 'cancel') {
          machine = null;
          ctx = null;
        }
        onEffect(f);
      }
    }
    return fx;
  }

  return {
    get isOpen() {
      return machine !== null;
    },

    get view(): RingView | null {
      if (!machine) return null;
      const top = machine.stack[machine.stack.length - 1];
      return {
        title: top.title ?? null,
        items: top.items.map((i) => ({
          id: i.id,
          label: i.label ?? '',
          swatch: i.swatch ?? null,
          enabled: i.enabled !== false,
          destructive: !!i.destructive,
          hasChildren: !!i.children,
        })),
        highlight: machine.highlight,
        depth: machine.stack.length,
        geometry: geom,
      };
    },

    openAt(context, viewport, mode = 'idle') {
      const spec = resolve(context);
      assertRing(spec.items, spec.title || 'root');
      geom = { ...GEOM, ...fitRing(viewport.width, viewport.height), ...(geometry ?? {}) };
      ctx = context;
      machine = createMachine(spec, geom);
      if (mode === 'tracking') {
        machine.status = 'pending';
        return dispatch({ type: 'longpress' });
      }
      return dispatch({ type: 'open' });
    },

    input(ev) {
      return dispatch(ev);
    },

    close() {
      return dispatch({ type: 'close' });
    },
  };
}
