/**
 * Repository Feature Module
 *
 * The GitHub repository service. Its component and state slices were a
 * migration begun and not finished -- nothing outside this barrel imported
 * them -- and are gone; the application's repository state lives in
 * `state/cell_state.ts` and its panels in `layout/panels/`.
 */

export { RepoService } from './services/repo_service';
