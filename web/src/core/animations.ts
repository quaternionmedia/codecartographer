import { animate, stagger, createTimeline } from 'animejs';
import type { JSAnimation } from 'animejs';

// Matches animejs's own DOMTargetsParam (string | DOMTarget | NodeList, or
// an array of those) — animate() genuinely accepts a plain array of
// elements (e.g. Array.from(...).filter(...)), not just a single Element
// or a live NodeList.
type AnimationTarget = string | Element | Element[] | NodeList;

/** Reusable animation presets for consistent UI polish */
export const animations = {
  /** Fade in element with optional slide */
  fadeIn: (
    target: AnimationTarget,
    options?: {
      duration?: number;
      delay?: number;
      translateY?: number;
    }
  ) => {
    const { duration = 300, delay = 0, translateY = 20 } = options || {};
    return animate(target, {
      opacity: [0, 1],
      translateY: [translateY, 0],
      duration,
      delay,
      ease: 'outQuad',
    });
  },

  /** Fade out element */
  fadeOut: (
    target: AnimationTarget,
    options?: { duration?: number }
  ) => {
    const { duration = 200 } = options || {};
    return animate(target, {
      opacity: [1, 0],
      duration,
      ease: 'inQuad',
    });
  },

  /** Slide navigation panel in/out */
  slideNav: (
    target: AnimationTarget,
    isOpen: boolean,
    side: 'left' | 'right'
  ) => {
    const translateX =
      side === 'left'
        ? isOpen
          ? ['-100%', '0%']
          : ['0%', '-100%']
        : isOpen
        ? ['100%', '0%']
        : ['0%', '100%'];

    return animate(target, {
      translateX,
      duration: 350,
      ease: 'outCubic',
    });
  },

  /** Stagger children for list animations */
  staggerIn: (
    target: AnimationTarget,
    options?: {
      delay?: number;
      staggerDelay?: number;
    }
  ) => {
    const { delay = 0, staggerDelay = 50 } = options || {};
    return animate(target, {
      opacity: [0, 1],
      translateY: [15, 0],
      delay: stagger(staggerDelay, { start: delay }),
      duration: 300,
      ease: 'outQuad',
    });
  },

  /** Button press feedback */
  buttonPress: (target: AnimationTarget) => {
    return animate(target, {
      scale: [1, 0.95, 1],
      duration: 150,
      ease: 'inOutQuad',
    });
  },

  /** Loading pulse animation */
  pulse: (target: AnimationTarget) => {
    return animate(target, {
      opacity: [0.5, 1],
      scale: [0.98, 1],
      duration: 800,
      alternate: true,
      loop: true,
      ease: 'inOutSine',
    });
  },

  /** Graph node entrance animation */
  graphNodeEntrance: (target: AnimationTarget) => {
    return animate(target, {
      scale: [0, 1],
      opacity: [0, 1],
      delay: stagger(10),
      duration: 400,
      ease: 'outElastic(1, .6)',
    });
  },

  /** Shake for error feedback */
  shake: (target: AnimationTarget) => {
    return animate(target, {
      translateX: [0, -10, 10, -10, 10, 0],
      duration: 400,
      ease: 'inOutQuad',
    });
  },

  /** Expand/collapse for folder toggle */
  expandCollapse: (target: AnimationTarget, isExpanding: boolean) => {
    return animate(target, {
      height: isExpanding ? [0, (target as Element).scrollHeight || 'auto'] : [(target as Element).scrollHeight || 'auto', 0],
      opacity: isExpanding ? [0, 1] : [1, 0],
      duration: 250,
      ease: 'outQuad',
    });
  },

  /** Tooltip appear */
  tooltipIn: (target: AnimationTarget) => {
    return animate(target, {
      opacity: [0, 1],
      scale: [0.9, 1],
      duration: 150,
      ease: 'outQuad',
    });
  },

  /** Tooltip disappear */
  tooltipOut: (target: AnimationTarget) => {
    return animate(target, {
      opacity: [1, 0],
      scale: [1, 0.9],
      duration: 100,
      ease: 'inQuad',
    });
  },
};

/** Animation controller for managing active animations */
export class AnimationController {
  private activeAnimations: Map<string, JSAnimation> = new Map();

  play(id: string, animation: JSAnimation) {
    // Stop existing animation with same ID
    this.stop(id);
    this.activeAnimations.set(id, animation);
    return animation;
  }

  stop(id: string) {
    const existing = this.activeAnimations.get(id);
    if (existing) {
      existing.pause();
      this.activeAnimations.delete(id);
    }
  }

  stopAll() {
    this.activeAnimations.forEach((anim) => anim.pause());
    this.activeAnimations.clear();
  }

  isPlaying(id: string): boolean {
    return this.activeAnimations.has(id);
  }
}

export const animationController = new AnimationController();
