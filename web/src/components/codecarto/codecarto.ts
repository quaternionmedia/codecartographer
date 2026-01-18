import m from 'mithril';

import { ICell } from '../../state/cell_state';
import { StateController } from '../../state/state_controller';
import { createActions, AppActions } from '../../state/actions';
import { Directory, RawFile, RawFolder, RepoInfo } from '../models/source';

import { ControlPanel, ControlPanelState, ControlPanelCallbacks, ControlPanelContent } from './control_panel';
import { Plot } from '../../features/graph';

import './codecarto.css';

/** The Code Cartographer app component - returns a Mithril closure component */
export const CodeCarto = (getCell: () => ICell): m.Component => {
  // Get initial cell for setting up actions (they need cell.update)
  const initialCell = getCell();
  const appState = new StateController(initialCell);
  const actions: AppActions = createActions(appState);

  // Local uploaded files storage (not in global state yet)
  let uploadedFiles: RawFile[] = [];

  // Track last plot action for re-executing when layout changes
  let lastPlotAction: (() => Promise<void>) | null = null;

  // Control panel local state - persists across redraws
  let panelState: ControlPanelState = {
    isOpen: false,
    activeTab: 'code',
    codeSourceMode: 'upload',
    repoUrl: '',
    currentTheme: 'terminal',
    isLoading: false,
    statusMessage: 'Ready',
    panelHeight: 300,
    graphStyling: {
      layout: 'spring_layout',
      enablePhysics: true,
      chargeStrength: -100,
      linkDistance: 55,
      nodeSize: 5,
      nodeOpacity: 1.0,
      nodeBorderWidth: 1.5,
      edgeWidth: 1.0,
      edgeOpacity: 1.0,
      showNodeLabels: true,
      showEdgeLabels: false,
      labelSize: 10,
      labelColor: '#333333',
    },
    parserOptions: {
      mode: 'ast',
      fileExtensions: ['.py'],
    },
  };

  // Helper to update panel state and trigger redraw
  const updatePanelState = (updates: Partial<ControlPanelState>) => {
    panelState = { ...panelState, ...updates };
    m.redraw();
  };

  // Control panel callbacks - fully wired
  const panelCallbacks: ControlPanelCallbacks = {
    // Demo
    onDemo: async () => {
      updatePanelState({ isLoading: true, statusMessage: 'Loading demo...' });

      // Store this action for re-execution when layout changes
      lastPlotAction = async () => {
        await actions.plot.loadDemo();
      };

      try {
        await lastPlotAction();
        updatePanelState({ isLoading: false, statusMessage: 'Ready' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: 'Error loading demo' });
      }
    },
    
    // Repository - fetch
    onRepoSubmit: async (url: string) => {
      updatePanelState({ isLoading: true, statusMessage: 'Fetching repository...' });
      try {
        await actions.repo.fetchRepository(url);
        updatePanelState({ isLoading: false, statusMessage: 'Repository loaded' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: 'Error fetching repository' });
      }
    },
    
    // Repository - click file in tree
    onRepoFileClick: async (url: string) => {
      updatePanelState({ isLoading: true, statusMessage: 'Plotting file...' });
      try {
        await actions.plot.plotUrlFile(url);
        updatePanelState({ isLoading: false, statusMessage: 'Ready' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: 'Error plotting file' });
      }
    },
    
    // Repository - plot whole directory
    onPlotWholeRepo: async () => {
      const repoContent = appState.repo.content;
      if (repoContent && repoContent.size > 0) {
        updatePanelState({ isLoading: true, statusMessage: 'Plotting directory tree...' });

        // Store this action for re-execution when layout changes
        lastPlotAction = async () => {
          const content = appState.repo.content;
          if (content && content.size > 0) {
            await actions.plot.plotWholeRepo(content);
          }
        };

        try {
          await lastPlotAction();
          updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch (error) {
          updatePanelState({ isLoading: false, statusMessage: 'Error plotting repository' });
        }
      }
    },
    
    // Repository - plot dependencies
    onPlotRepoDeps: async () => {
      const repoContent = appState.repo.content;
      if (repoContent && repoContent.size > 0) {
        updatePanelState({ isLoading: true, statusMessage: 'Plotting dependencies...' });

        // Store this action for re-execution when layout changes
        lastPlotAction = async () => {
          const content = appState.repo.content;
          if (content && content.size > 0) {
            await actions.plot.plotRepoDeps(content);
          }
        };

        try {
          await lastPlotAction();
          updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch (error) {
          updatePanelState({ isLoading: false, statusMessage: 'Error plotting dependencies' });
        }
      }
    },
    
    // Upload - file upload handler
    onFileUpload: (files: FileList) => {
      updatePanelState({ isLoading: true, statusMessage: 'Processing files...' });
      
      const newFiles: RawFile[] = [];
      let processed = 0;
      
      Array.from(files).forEach(file => {
        // Check if file already exists
        const exists = uploadedFiles.some(f => f.name === file.name);
        if (exists) {
          processed++;
          if (processed === files.length) {
            updatePanelState({ isLoading: false, statusMessage: `${newFiles.length} new file(s) added` });
          }
          return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target?.result as string;
          const newFile = new RawFile(file.name, file.size, content, file.webkitRelativePath || file.name);
          newFiles.push(newFile);
          uploadedFiles.push(newFile);
          processed++;
          
          // Update state when all files are processed
          if (processed === files.length) {
            // Also update the global state for consistency
            appState.update({
              local: {
                content: new Directory(
                  new RepoInfo(),
                  uploadedFiles.length,
                  new RawFolder('uploads', 0, uploadedFiles)
                ),
              },
            });
            updatePanelState({ isLoading: false, statusMessage: `${newFiles.length} file(s) added` });
          }
        };
        reader.readAsText(file);
      });
    },
    
    // Upload - click uploaded file
    onUploadedFileClick: async (file: RawFile) => {
      updatePanelState({ isLoading: true, statusMessage: 'Plotting file...' });

      // Store this action for re-execution when layout changes
      lastPlotAction = async () => {
        await actions.plot.plotUploadedFile(file);
      };

      try {
        await lastPlotAction();
        updatePanelState({ isLoading: false, statusMessage: 'Ready' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: 'Error plotting file' });
      }
    },

    // Upload - plot all uploaded files
    onPlotAllUploads: async () => {
      if (uploadedFiles.length > 0) {
        updatePanelState({ isLoading: true, statusMessage: 'Plotting all files...' });

        // Store this action for re-execution when layout changes
        lastPlotAction = async () => {
          if (uploadedFiles.length > 0) {
            // For now, plot the first file - TODO: implement multi-file plotting
            await actions.plot.plotUploadedFile(uploadedFiles[0]);
          }
        };

        try {
          await lastPlotAction();
          updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch (error) {
          updatePanelState({ isLoading: false, statusMessage: 'Error plotting files' });
        }
      }
    },
    
    // Settings - theme change
    onThemeChange: (theme: string) => {
      // Theme is handled by CSS variables via data-theme attribute in control panel
    },

    // Graph styling change
    onGraphStylingChange: async (options) => {
      const oldLayout = panelState.graphStyling.layout;
      const newLayout = options.layout;

      // Update local panel state for UI
      updatePanelState({
        graphStyling: { ...panelState.graphStyling, ...options }
      });

      // Update global state so it's available to the renderer
      const currentCell = getCell();
      const currentState = currentCell.state;
      currentCell.update({
        graphStyling: { ...currentState.graphStyling, ...options }
      });

      // If layout changed, trigger a re-fetch from backend
      if (newLayout && newLayout !== oldLayout && lastPlotAction) {
        updatePanelState({ isLoading: true, statusMessage: 'Applying new layout...' });
        try {
          await lastPlotAction();
          updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch (error) {
          updatePanelState({ isLoading: false, statusMessage: 'Error applying layout' });
        }
        return;
      }

      // For other styling changes, just re-render with existing data
      if (currentState.graphData) {
        actions.plot.createGraphVnode();
        m.redraw();
      }
    },

    // Parser options change
    onParserOptionsChange: async (options) => {
      const oldMode = panelState.parserOptions.mode;
      const newMode = options.mode;

      // Update local panel state for UI
      updatePanelState({
        parserOptions: { ...panelState.parserOptions, ...options }
      });

      // Update global state so it's available to plot actions
      const currentCell = getCell();
      const currentState = currentCell.state;
      currentCell.update({
        parserOptions: { ...currentState.parserOptions, ...options }
      });

      console.log('Parser options updated:', { ...panelState.parserOptions, ...options });

      // If parser mode changed, trigger a re-fetch from backend with new mode
      if (newMode && newMode !== oldMode && lastPlotAction) {
        updatePanelState({ isLoading: true, statusMessage: `Parsing with ${newMode} mode...` });
        try {
          await lastPlotAction();
          updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch (error) {
          updatePanelState({ isLoading: false, statusMessage: `Error parsing with ${newMode} mode` });
        }
      }
    },
  };

  // Build content for control panel
  const getContent = (): ControlPanelContent => ({
    repoDirectory: appState.repo.content,
    uploadedFiles: uploadedFiles,
  });

  // Return a closure component - view is called on each redraw, but closures are preserved
  return {
    view: () => {
      // Get fresh state from cell on each render
      const currentCell = getCell();
      const currentState = currentCell.state;
      
      // Build header
      const header = m('div.codecarto__header', [
        m('h1.codecarto__title', [
          m('span.codecarto__title-icon', '◈'),
          'Code Cartographer',
        ]),
        m('p.codecarto__subtitle', 'Visualize code architecture and dependencies'),
      ]);

      // Main content area - use fresh graphContent from current state
      const mainContent = m('div.codecarto__main', [
        m(Plot, { graphs: currentState.graphContent }),
      ]);

      // Control panel - update content with fresh repo data
      const content: ControlPanelContent = {
        repoDirectory: currentState.repo.content,
        uploadedFiles: uploadedFiles,
      };
      
      const controlPanel = ControlPanel(
        panelState,
        panelCallbacks,
        updatePanelState,
        content
      );

      return m('div.codecarto', [
        header,
        mainContent,
        controlPanel,
      ]);
    },
  };
};
