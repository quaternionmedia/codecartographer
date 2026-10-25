/**
 * An unread folder in the Files panel, reading itself on a click.
 *
 * Pure, so it compiles under `tsconfig.pure.json` and is asserted under
 * `node --test`; `folder.ts` holds the state and the markup.
 */

/** What a folder holds while it reads itself. */
export interface StubState {
  isOpen: boolean;
  isLoading: boolean;
}

/**
 * Open the folder and read it, once: a click while it is loading asks
 * nothing. `read` resolves true when it put the folder's contents in the tree.
 *
 * **THE SPINNER ENDS WHEN THE READ DOES, HOWEVER IT ENDS.** It ended only when
 * contents arrived, so a read that failed -- GitHub's unauthenticated limit, a
 * submodule's path, which the server answers with `GithubNoDataError` -- spun
 * for good, and a folder still loading is never read again. A read that
 * failed, or put nothing in the tree, closes the folder, so it is drawn unread
 * again and the next click reads it again.
 */
export async function readStub(
  state: StubState,
  read: () => Promise<boolean>,
  redraw: () => void,
): Promise<void> {
  if (state.isLoading) return;
  state.isOpen = true;
  state.isLoading = true;
  redraw();
  let filled = false;
  try {
    filled = (await read()) === true;
  } catch {
    filled = false;
  }
  state.isLoading = false;
  if (!filled) state.isOpen = false;
  redraw();
}
