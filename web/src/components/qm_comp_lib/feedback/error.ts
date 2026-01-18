import m from 'mithril';
import './error.css';

export interface ErrorDisplayAttrs {
  /** Error message to display */
  message: string | null;
  /** Optional title */
  title?: string;
  /** Retry callback */
  onRetry?: () => void;
  /** Dismiss callback */
  onDismiss?: () => void;
  /** Error severity */
  severity?: 'error' | 'warning' | 'info';
}

/**
 * Error display component
 * 
 * @example
 * m(ErrorDisplay, { 
 *   message: 'Failed to fetch repository',
 *   onRetry: () => fetchRepo(),
 *   onDismiss: () => clearError()
 * })
 */
export const ErrorDisplay: m.Component<ErrorDisplayAttrs> = {
  view(vnode) {
    const { 
      message, 
      title,
      onRetry, 
      onDismiss,
      severity = 'error'
    } = vnode.attrs;

    if (!message) return null;

    const icons = {
      error: '✕',
      warning: '⚠',
      info: 'ℹ',
    };

    return m(`.error-display.error-display--${severity}`, [
      m('.error-display__icon', icons[severity]),
      m('.error-display__content', [
        title && m('.error-display__title', title),
        m('.error-display__message', message),
      ]),
      m('.error-display__actions', [
        onRetry && m('button.error-display__btn', { onclick: onRetry }, '↻ Retry'),
        onDismiss && m('button.error-display__btn.error-display__btn--dismiss', { onclick: onDismiss }, '✕'),
      ]),
    ]);
  },
};

export interface ErrorBoundaryAttrs {
  /** Fallback content when error occurs */
  fallback?: m.Vnode | ((error: Error) => m.Vnode);
  /** Error handler callback */
  onError?: (error: Error) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Error boundary component - catches errors in child components
 * Note: Mithril doesn't have built-in error boundaries like React,
 * so this is a simplified implementation
 * 
 * @example
 * m(ErrorBoundary, { 
 *   fallback: m('div', 'Something went wrong'),
 *   onError: (err) => logError(err)
 * }, [
 *   m(SomeComponent)
 * ])
 */
export const ErrorBoundary: m.Component<ErrorBoundaryAttrs, ErrorBoundaryState> = {
  oninit(vnode) {
    vnode.state.error = null;
  },

  view(vnode) {
    const { fallback, onError } = vnode.attrs;
    const { error } = vnode.state;

    if (error) {
      if (typeof fallback === 'function') {
        return fallback(error);
      }
      
      return fallback || m(ErrorDisplay, {
        message: error.message || 'An unexpected error occurred',
        title: 'Error',
        onRetry: () => {
          vnode.state.error = null;
        },
      });
    }

    // Wrap children in try-catch during render
    try {
      return m('div.error-boundary', vnode.children);
    } catch (err) {
      const caughtError = err instanceof Error ? err : new Error(String(err));
      vnode.state.error = caughtError;
      onError?.(caughtError);
      return null;
    }
  },
};

/**
 * Toast notification for transient errors/messages
 */
export interface ToastAttrs {
  message: string;
  type?: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
  onClose?: () => void;
}

export const Toast: m.Component<ToastAttrs> = {
  oncreate(vnode) {
    const { duration = 5000, onClose } = vnode.attrs;
    if (duration > 0 && onClose) {
      setTimeout(onClose, duration);
    }
  },

  view(vnode) {
    const { message, type = 'info', onClose } = vnode.attrs;
    
    const icons = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ',
    };

    return m(`.toast.toast--${type}`, [
      m('span.toast__icon', icons[type]),
      m('span.toast__message', message),
      onClose && m('button.toast__close', { onclick: onClose }, '✕'),
    ]);
  },
};

export default ErrorDisplay;
