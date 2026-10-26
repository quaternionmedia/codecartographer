/**
 * One test per subject in the manifest `codecarto show export` writes: each
 * draws the subject's views in the window and writes its show document and
 * pictures (`exporter.ts`). With no manifest there is nothing to draw.
 */

import { readFileSync } from 'node:fs';

import { test } from '@playwright/test';

import { exportSubject, type Manifest } from './exporter';

const path = process.env.SHOW_EXPORT_MANIFEST;
const manifest: Manifest | null = path ? JSON.parse(readFileSync(path, 'utf8')) : null;

for (const subject of manifest?.subjects ?? []) {
  test(subject.address, async ({ page }) => {
    await exportSubject(page, subject, manifest!);
  });
}
