/**
 * UrlInput Component
 *
 * GitHub repository URL input form
 */
import m from 'mithril';
import { Button } from '../../../components/qm_comp_lib/form';

export interface UrlInputAttrs {
  url: string;
  isLoading: boolean;
  onUrlChange: (url: string) => void;
  onFetch: () => void;
}

export const UrlInput: m.Component<UrlInputAttrs> = {
  view(vnode) {
    const { url, isLoading, onUrlChange, onFetch } = vnode.attrs;

    return m('.url-input', [
      m('input.url-input__field', {
        type: 'text',
        placeholder: 'Enter GitHub repository URL...',
        value: url,
        oninput: (e: Event) => {
          const target = e.target as HTMLInputElement;
          onUrlChange(target.value);
        },
        onkeypress: (e: KeyboardEvent) => {
          if (e.key === 'Enter' && url && !isLoading) {
            onFetch();
          }
        },
      }),
      m(Button, {
        label: isLoading ? 'Fetching...' : 'Fetch',
        disabled: !url || isLoading,
        loading: isLoading,
        onClick: onFetch,
      }),
    ]);
  },
};
