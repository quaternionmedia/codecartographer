import m from 'mithril';
import './loading.css';

export interface LoadingAttrs {
  /** Whether loading state is active */
  isLoading: boolean;
  /** Optional message to display */
  message?: string;
  /** Size variant */
  size?: 'small' | 'medium' | 'large';
  /** Whether to show as overlay */
  overlay?: boolean;
}

/**
 * Loading spinner component with optional message
 * 
 * @example
 * // Basic usage
 * m(Loading, { isLoading: true })
 * 
 * // With message
 * m(Loading, { isLoading: true, message: 'Fetching repository...' })
 * 
 * // As overlay
 * m(Loading, { isLoading: true, overlay: true })
 */
export const Loading: m.Component<LoadingAttrs> = {
  view(vnode) {
    const { 
      isLoading, 
      message = 'Loading...', 
      size = 'medium',
      overlay = false 
    } = vnode.attrs;

    if (!isLoading) return null;

    const spinner = m(`.loading.loading--${size}`, [
      m('.loading__spinner', [
        m('.loading__spinner-ring'),
        m('.loading__spinner-ring'),
        m('.loading__spinner-ring'),
      ]),
      message && m('.loading__message', message),
    ]);

    if (overlay) {
      return m('.loading-overlay', spinner);
    }

    return spinner;
  },
};

/**
 * Inline loading indicator for buttons or small areas
 */
export const LoadingInline: m.Component<{ isLoading: boolean }> = {
  view(vnode) {
    if (!vnode.attrs.isLoading) return null;
    return m('span.loading-inline', [
      m('span.loading-inline__dot'),
      m('span.loading-inline__dot'),
      m('span.loading-inline__dot'),
    ]);
  },
};

export default Loading;
