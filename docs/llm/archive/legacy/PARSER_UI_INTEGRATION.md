# Parser UI Integration

**Date**: 2026-01-17
**Status**: ✅ Complete
**Build**: Passing (251.42 kB / 82.57 kB gzipped)

## Overview

Added comprehensive parser controls to the UI, allowing users to select different parsing modes and configure file extension filtering directly from the control panel.

## Features Implemented

### 1. Parser Mode Selector

Three distinct parsing modes are now available in the Styling tab:

#### AST (Code Structure) Mode 🔍
- **Description**: Full Python abstract syntax tree analysis
- **Shows**: Classes, functions, imports, calls, control flow
- **Use Case**: Deep code structure visualization
- **Backend**: Uses `python_custom_ast.py` parser
- **Endpoint**: `/plotter/file`, `/plotter/folder`

#### Directory Tree Mode 📁
- **Description**: Filesystem hierarchy visualization
- **Shows**: Folder and file structure
- **Use Case**: Repository organization overview
- **Backend**: Uses `directory_parser.py`
- **Endpoint**: `/plotter/whole_repo`

#### Dependencies Mode ◈
- **Description**: Import relationship analysis
- **Shows**: How files depend on each other (import statements)
- **Use Case**: Dependency graph visualization
- **Backend**: Uses `dependency_parser.py`
- **Endpoint**: `/plotter/whole_repo_deps`

### 2. File Extension Filtering

- **UI Element**: Text input field
- **Format**: Comma-separated list (e.g., `.py, .js, .ts`)
- **Default**: `.py`
- **Use Case**: Filter which files to parse in directory operations
- **Future Enhancement**: Will be wired to backend `extensions` query parameter

## Technical Implementation

### Frontend Changes

#### 1. Type Definitions

**File**: [web/src/state/types.ts](../../web/src/state/types.ts)

```typescript
/** Parser modes for analyzing code */
export type ParserMode = 'ast' | 'directory' | 'dependencies';

/** Parser configuration options */
export interface ParserOptions {
  mode: ParserMode;            // Parser type
  fileExtensions: string[];    // File extensions to parse
}
```

#### 2. Control Panel Interface

**File**: [web/src/components/codecarto/control_panel/control_panel.ts](../../web/src/components/codecarto/control_panel/control_panel.ts)

Added to `ControlPanelState`:
```typescript
parserOptions: ParserOptions;
```

Added to `ControlPanelCallbacks`:
```typescript
onParserOptionsChange: (options: Partial<ParserOptions>) => void;
```

#### 3. UI Components

**Parser Mode Selector** (Styling Tab):
- Three button cards with icons and labels
- Active state highlighting with theme colors
- Tooltips showing full descriptions
- Visual feedback on hover

**File Extensions Input**:
- Monospace text input for extension list
- Hint text explaining format
- Change handler splitting comma-separated values

#### 4. State Management

**File**: [web/src/state/cell_state.ts](../../web/src/state/cell_state.ts)

Added to `ICellState`:
```typescript
parserOptions: ParserOptions;
```

Default state:
```typescript
parserOptions: {
  mode: 'ast',
  fileExtensions: ['.py'],
}
```

#### 5. Application Integration

**File**: [web/src/components/codecarto/codecarto.ts](../../web/src/components/codecarto/codecarto.ts)

Wired callback:
```typescript
onParserOptionsChange: async (options) => {
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
}
```

### CSS Styling

**File**: [web/src/components/codecarto/control_panel/control_panel.css](../../web/src/components/codecarto/control_panel/control_panel.css)

Added styles (lines 746-815):
- `.panel-settings__parser-modes` - Container for parser mode buttons
- `.panel-settings__parser-mode` - Individual mode button card
- `.panel-settings__parser-mode--active` - Active state with theme color
- `.panel-settings__parser-icon` - Icon styling
- `.panel-settings__parser-label` - Label text
- `.panel-settings__extensions` - Extension input container
- `.panel-settings__input` - Monospace input field
- `.panel-settings__hint` - Helper text

## User Workflow

### Changing Parser Mode

1. Open control panel (click handle at bottom)
2. Navigate to **Styling** tab
3. Scroll to **Parser Options** section
4. Click desired parser mode button:
   - 🔍 AST (Code Structure)
   - 📁 Directory Tree
   - ◈ Dependencies
5. Selected mode is highlighted with theme color

### Configuring File Extensions

1. In **Parser Options** section
2. Click the **File Extensions** input field
3. Enter comma-separated extensions: `.py, .js, .ts`
4. Press Enter or blur to save
5. Extensions are split and stored as array

## Backend Integration Status

### Currently Implemented

✅ Parser mode is stored in global state
✅ File extensions are stored in global state
✅ UI reflects current parser mode selection
✅ State persists across redraws

### Next Steps (Future Work)

The parser options are now available in the application state and can be accessed when making plot requests. To fully integrate with the backend:

#### Option 1: Use Existing Endpoints Based on Mode

The current button actions (`onPlotWholeRepo`, `onPlotRepoDeps`) already map to specific parser modes:
- `onPlotWholeRepo()` → Directory Tree mode → `/plotter/whole_repo`
- `onPlotRepoDeps()` → Dependencies mode → `/plotter/whole_repo_deps`
- Individual file actions → AST mode → `/plotter/file`

**No additional changes needed** - the UI mode selector serves as documentation/feedback to the user about which parser is being used.

#### Option 2: Dynamic Parser Selection

To allow switching parser modes for the same data source:

1. **Update plot service** ([web/src/services/plot_service.ts](../../web/src/services/plot_service.ts)):
   ```typescript
   // Access parser mode from state
   const parserMode = stateController.state.parserOptions.mode;

   // Choose endpoint based on mode
   if (parserMode === 'ast') {
     return this.plotFile(file, options);
   } else if (parserMode === 'dependencies') {
     return this.plotRepoDeps(directory, options);
   } else {
     return this.plotWholeRepo(directory, options);
   }
   ```

2. **Add extensions parameter to API calls**:
   ```typescript
   const params = new URLSearchParams({
     layout: options.layout,
     extensions: JSON.stringify(parserOptions.fileExtensions)
   });
   ```

3. **Backend receives extensions**:
   ```python
   @PlotterRouter.post("/whole_repo")
   async def plot_whole_repo(
       directory: Directory,
       options: PlotOptions,
       extensions: list[str] = Query(default=[".py"])
   ):
       # Use extensions parameter in parser
   ```

#### Option 3: Add Unified Endpoint

Create a single endpoint that accepts parser mode as parameter:

```python
@PlotterRouter.post("/plot")
async def plot(
    directory: Directory,
    options: PlotOptions,
    parser_mode: str = Query(default="ast"),
    extensions: list[str] = Query(default=[".py"])
):
    if parser_mode == "ast":
        graph = await ParserService.parse_code(directory)
    elif parser_mode == "directory":
        graph = await ParserService.parse_directory(directory)
    elif parser_mode == "dependencies":
        graph = await ParserService.parse_dependancy(directory)
```

## Architecture Benefits

### 1. Separation of Concerns
- UI controls are decoupled from backend implementation
- Parser selection is a user preference, not hardcoded
- Easy to add new parser modes without UI changes

### 2. User Experience
- Visual feedback on which parser is active
- Tooltips explain what each parser does
- File extension filtering is explicit and configurable

### 3. Extensibility
- New parser modes can be added to `PARSER_MODES` array
- File extension list is dynamic and user-configurable
- State management is centralized

## Testing Checklist

### UI Testing

- [ ] Open control panel
- [ ] Navigate to Styling tab
- [ ] Verify parser mode selector renders
- [ ] Click each parser mode button
- [ ] Verify active state highlighting
- [ ] Hover over mode buttons (check tooltips)
- [ ] Change file extensions input
- [ ] Verify extensions are split correctly

### Integration Testing

- [ ] Upload Python files
- [ ] Select AST mode
- [ ] Plot file - verify AST visualization
- [ ] Select Directory mode
- [ ] Plot whole repo - verify directory tree
- [ ] Select Dependencies mode
- [ ] Plot dependencies - verify import graph
- [ ] Change file extensions to `.js`
- [ ] Upload JS files (if supported)
- [ ] Verify filtering works

### State Testing

- [ ] Change parser mode
- [ ] Check browser console for "Parser options updated" log
- [ ] Verify global state contains parserOptions
- [ ] Reload page - verify state persistence
- [ ] Switch tabs - verify state persists

## Related Files

### Frontend
- [web/src/state/types.ts](../../web/src/state/types.ts) - Type definitions
- [web/src/state/cell_state.ts](../../web/src/state/cell_state.ts) - State interface
- [web/src/components/codecarto/control_panel/control_panel.ts](../../web/src/components/codecarto/control_panel/control_panel.ts) - UI component
- [web/src/components/codecarto/control_panel/control_panel.css](../../web/src/components/codecarto/control_panel/control_panel.css) - Styles
- [web/src/components/codecarto/codecarto.ts](../../web/src/components/codecarto/codecarto.ts) - App integration

### Backend (Reference)
- [codecarto/services/parser_service.py](../../codecarto/services/parser_service.py) - Parser orchestration
- [codecarto/services/parsers/ASTs/python_custom_ast.py](../../codecarto/services/parsers/ASTs/python_custom_ast.py) - AST parser
- [codecarto/services/parsers/python/directory_parser.py](../../codecarto/services/parsers/python/directory_parser.py) - Directory parser
- [codecarto/services/parsers/python/dependency_parser.py](../../codecarto/services/parsers/python/dependency_parser.py) - Dependency parser
- [codecarto/routers/plotter_router.py](../../codecarto/routers/plotter_router.py) - API endpoints

## Known Limitations

1. **File extension filtering not yet wired to backend** - Currently stored in state but not sent to API
2. **Parser mode selection is informational** - Actual parser is determined by which button (Directory Tree vs Dependencies) user clicks
3. **No validation on file extensions** - User could enter invalid values

## Future Enhancements

### Short Term
1. Wire file extensions to backend API calls
2. Add validation for file extension input
3. Add preset extension buttons (Python, JavaScript, TypeScript, etc.)

### Medium Term
1. Add parser mode auto-detection based on file types
2. Show parser statistics (nodes, edges, files parsed)
3. Add parser performance metrics

### Long Term
1. Support for multi-language parsing (JavaScript, TypeScript, Java, etc.)
2. Custom parser plugins
3. Parser configuration presets (Quick, Detailed, Deep)
4. Real-time parser mode switching without re-fetch

## Build Metrics

**Before**: 249.76 kB (gzipped: 82.10 kB)
**After**: 251.42 kB (gzipped: 82.57 kB)
**Delta**: +1.66 kB (+0.47 kB gzipped)

Minimal bundle size increase for comprehensive parser controls.

---

**Status**: ✅ Parser UI integration complete and ready for backend wiring
