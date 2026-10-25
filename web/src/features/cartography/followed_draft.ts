/**
 * What a field that names a shown value holds: what the person typed, until
 * the value it names changes -- from anywhere -- and then that value.
 *
 * **THE CARGO PANEL'S WORKSPACE FIELD IS THE CASE.** The panel shows the
 * reading of `cargoPath`, and `cargoPath` is set from outside the panel too: a
 * bundled example's click reads its workspace. A draft taken once, when the
 * panel was made, stayed empty or held an earlier path while the example's
 * crates were shown under it, so "read" did nothing or read the old path over
 * them. A change to the value now replaces an edit not yet read, so the field
 * names what the panel shows; between changes, an edit stands.
 *
 * Compiled by `tsconfig.pure.json` and asserted under `node --test`.
 */
export class FollowedDraft {
  private followed: string;
  private text: string;

  constructor(current: string) {
    this.followed = current;
    this.text = current;
  }

  /** What the field holds while the value it names is `current`. */
  shown(current: string): string {
    if (current !== this.followed) {
      this.followed = current;
      this.text = current;
    }
    return this.text;
  }

  /** The person typed `text`. */
  edit(text: string): void {
    this.text = text;
  }
}
