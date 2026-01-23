import m from 'mithril';
import './form.css';

/**
 * Input Component
 */
export interface InputAttrs {
  value: string;
  onchange: (value: string) => void;
  placeholder?: string;
  type?: 'text' | 'email' | 'password' | 'url' | 'search';
  disabled?: boolean;
  error?: string | null;
  label?: string;
  id?: string;
  onkeydown?: (e: KeyboardEvent) => void;
  autofocus?: boolean;
}

export const Input: m.Component<InputAttrs> = {
  view(vnode) {
    const {
      value,
      onchange,
      placeholder,
      type = 'text',
      disabled = false,
      error,
      label,
      id,
      onkeydown,
      autofocus,
    } = vnode.attrs;

    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

    return m('.form-input', { class: error ? 'form-input--error' : '' }, [
      label && m('label.form-input__label', { for: inputId }, label),
      m('input.form-input__field', {
        id: inputId,
        type,
        value,
        placeholder,
        disabled,
        autofocus,
        oninput: (e: InputEvent) => onchange((e.target as HTMLInputElement).value),
        onkeydown,
      }),
      error && m('.form-input__error', error),
    ]);
  },
};

/**
 * Button Component
 */
export interface ButtonAttrs {
  onclick?: (e: MouseEvent) => void;
  disabled?: boolean;
  variant?: 'default' | 'primary' | 'danger' | 'ghost';
  size?: 'small' | 'medium' | 'large';
  loading?: boolean;
  icon?: string;
  type?: 'button' | 'submit' | 'reset';
}

export const Button: m.Component<ButtonAttrs> = {
  view(vnode) {
    const {
      onclick,
      disabled = false,
      variant = 'default',
      size = 'medium',
      loading = false,
      icon,
      type = 'button',
    } = vnode.attrs;

    const classes = [
      'form-btn',
      `form-btn--${variant}`,
      `form-btn--${size}`,
      loading ? 'form-btn--loading' : '',
    ].filter(Boolean).join(' ');

    return m('button', {
      class: classes,
      onclick,
      disabled: disabled || loading,
      type,
    }, [
      loading && m('span.form-btn__spinner'),
      icon && !loading && m('span.form-btn__icon', icon),
      m('span.form-btn__text', vnode.children),
    ]);
  },
};

/**
 * Select Component
 */
export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectAttrs {
  value: string;
  options: SelectOption[];
  onchange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  label?: string;
  id?: string;
}

export const Select: m.Component<SelectAttrs> = {
  view(vnode) {
    const {
      value,
      options,
      onchange,
      placeholder,
      disabled = false,
      label,
      id,
    } = vnode.attrs;

    const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;

    return m('.form-select', [
      label && m('label.form-select__label', { for: selectId }, label),
      m('select.form-select__field', {
        id: selectId,
        value,
        disabled,
        onchange: (e: Event) => onchange((e.target as HTMLSelectElement).value),
      }, [
        placeholder && m('option', { value: '', disabled: true }, placeholder),
        ...options.map(opt =>
          m('option', { value: opt.value, disabled: opt.disabled }, opt.label)
        ),
      ]),
      m('span.form-select__arrow', '▼'),
    ]);
  },
};

/**
 * Toggle/Switch Component
 */
export interface ToggleAttrs {
  checked: boolean;
  onchange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
  id?: string;
}

export const Toggle: m.Component<ToggleAttrs> = {
  view(vnode) {
    const {
      checked,
      onchange,
      label,
      disabled = false,
      id,
    } = vnode.attrs;

    const toggleId = id || `toggle-${Math.random().toString(36).substr(2, 9)}`;

    return m('.form-toggle', { class: disabled ? 'form-toggle--disabled' : '' }, [
      m('input.form-toggle__input', {
        id: toggleId,
        type: 'checkbox',
        checked,
        disabled,
        onchange: (e: Event) => onchange((e.target as HTMLInputElement).checked),
      }),
      m('label.form-toggle__track', { for: toggleId }, [
        m('span.form-toggle__thumb'),
      ]),
      label && m('label.form-toggle__label', { for: toggleId }, label),
    ]);
  },
};

/**
 * Textarea Component
 */
export interface TextareaAttrs {
  value: string;
  onchange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
  label?: string;
  id?: string;
  maxlength?: number;
}

export const Textarea: m.Component<TextareaAttrs> = {
  view(vnode) {
    const {
      value,
      onchange,
      placeholder,
      disabled = false,
      rows = 4,
      label,
      id,
      maxlength,
    } = vnode.attrs;

    const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;

    return m('.form-textarea', [
      label && m('label.form-textarea__label', { for: textareaId }, label),
      m('textarea.form-textarea__field', {
        id: textareaId,
        value,
        placeholder,
        disabled,
        rows,
        maxlength,
        oninput: (e: InputEvent) => onchange((e.target as HTMLTextAreaElement).value),
      }),
      maxlength && m('.form-textarea__counter', `${value.length}/${maxlength}`),
    ]);
  },
};

export default { Input, Button, Select, Toggle, Textarea };
