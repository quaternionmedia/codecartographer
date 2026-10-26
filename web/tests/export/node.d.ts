// The few Node APIs the export harness uses, typed here. The web app's
// tsconfig checks tests/ against the DOM, and @types/node is not a dependency
// of a browser app; Playwright runs these files under Node regardless.

declare module 'node:fs' {
  export function mkdirSync(path: string, options?: { recursive?: boolean }): void;
  export function writeFileSync(path: string, data: string): void;
  export function readFileSync(path: string, encoding: 'utf8'): string;
  export function existsSync(path: string): boolean;
  export function rmSync(path: string, options?: { recursive?: boolean; force?: boolean }): void;
}

declare module 'node:path' {
  export function join(...parts: string[]): string;
}

declare const process: { env: Record<string, string | undefined> };
