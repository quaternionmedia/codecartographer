# Control Panel Tutorial Flow

## Overview

The control panel has been redesigned as an **in-situ tutorial** that guides users through the visualization process from left to right. Each tab is numbered and builds on the previous step.

## Tab Flow (Left to Right)

### 1. Source 📁
**Purpose**: Choose where to get your code
**Required Fields**:
- Source mode (Upload / Repository)
- Demo button OR file upload OR repo URL

**Help Text**: "Choose where to get your code"

**User Actions**:
- Click "Try Demo" for instant visualization
- Upload local files (.py, .js, etc.)
- Enter GitHub repository URL

**Next Step**: Once data is loaded, move to Parse tab →

---

### 2. Parse 🔍
**Purpose**: Define how to analyze the code
**Required Fields**:
- Parser mode (AST / Directory / Dependencies)

**Optional Fields**:
- File extensions filter

**Help Text**: "Define how to analyze the code"

**Parser Modes**:
- **AST (Abstract Syntax Tree)**: Analyze code structure (functions, classes, variables)
- **Directory**: Visualize file/folder hierarchy
- **Dependencies**: Show import relationships between modules

**Next Step**: Code is parsed, move to Layout tab →

---

### 3. Layout ◈
**Purpose**: Arrange nodes in space
**Required Fields**:
- Layout algorithm

**Optional Fields**:
- Physics simulation (on/off)
- Charge strength (repulsion force)
- Link distance (edge length)

**Help Text**: "Arrange nodes in space"

**Layout Algorithms**:
- **Spring**: Force-directed, organic clustering
- **Spectral**: Mathematical eigenvalue-based
- **Kamada-Kawai**: Energy minimization
- **Circular**: Nodes in a circle
- **Spiral**: Spiral pattern
- **Random**: Random positioning
- **Shell**: Concentric circles
- **Sorted Square**: Grid-based

**Next Step**: Nodes are positioned, move to Visual tab →

---

### 4. Visual ✦
**Purpose**: Style the appearance
**Required Fields**:
- Renderer (D3.js / Gravis / Notebook)

**Optional Fields**:
- Node settings (size, opacity, labels, border)
- Edge settings (width, opacity, labels)
- Label settings (size, color)

**Help Text**: "Style the appearance"

**Renderer Options**:
- **D3.js (Force-directed)**: Interactive with custom node shapes, box selection, radial menu
- **Gravis (vis-network)**: Classic network visualization with physics
- **Notebook (iframe)**: Pre-rendered HTML (for demos)

**All renderers work with all graph types** - users can switch freely!

**Node Controls**:
- Show labels (toggle)
- Size (2-30px)
- Opacity (0.1-1.0)
- Border width (0.5-5px)

**Edge Controls**:
- Show labels (toggle)
- Width (0.5-5px)
- Opacity (0.1-1.0)

**Next Step**: Styling complete, optionally adjust Theme →

---

### 5. Theme 🎨
**Purpose**: Overall color scheme
**Required Fields**:
- Theme selection

**Help Text**: "Overall color scheme"

**Available Themes**:
- **Terminal** (default): Green on black, hacker aesthetic
- **Light**: Bright, clean, professional
- **Cyberpunk**: Magenta/cyan, futuristic
- **Ocean**: Blues/teals, calm
- **Sunset**: Oranges/warm tones
- **Forest**: Greens, natural
- **Noir**: Black & white, minimalist
- **Candy**: Pink/turquoise, playful

**Next Step**: Visualization complete! ✨

---

## Progressive Disclosure

### Required vs Optional Fields

**Required fields** (top of each tab):
- Must be set for visualization to work
- Clearly labeled
- Defaults provided

**Optional fields** (below required):
- Fine-tuning and customization
- Can be skipped by beginners
- Advanced users can tweak

### Field Organization

Each tab follows this structure:

```
┌─────────────────────────┐
│ [Tab Help Text]         │  ← Brief explanation of tab purpose
├─────────────────────────┤
│ REQUIRED FIELDS         │
│ - Primary action        │  ← What user MUST do
│ - Key setting           │
├─────────────────────────┤
│ [Section Header]        │
│ OPTIONAL FIELDS         │
│ - Fine-tuning option 1  │  ← Advanced customization
│ - Fine-tuning option 2  │
│ [...]                   │
└─────────────────────────┘
```

## Tutorial Flow Examples

### Beginner Path (Minimal Clicks)

1. **Source** → Click "Try Demo"
2. **Visual** → Select renderer (optional, D3 is default)
3. Done! ✨

**Result**: Instant visualization with sensible defaults

---

### Intermediate Path (Upload & Customize)

1. **Source** → Upload .py file
2. **Parse** → Select "AST" (default)
3. **Layout** → Try "Spectral" instead of "Spring"
4. **Visual** → Increase node size, enable labels
5. Done! ✨

**Result**: Custom visualization of uploaded code

---

### Advanced Path (Full Customization)

1. **Source** → Enter GitHub repo URL
2. **Parse** → Select "Dependencies", add `.py,.js` extensions
3. **Layout** → Use "Kamada-Kawai", adjust charge strength
4. **Visual** → Switch to "Gravis" renderer, tune all visual settings
5. **Theme** → Change to "Ocean" theme
6. Done! ✨

**Result**: Highly customized professional visualization

---

## Help Text Strategy

### Tab-Level Help
Each tab has concise help text in the tab definition:
```typescript
{
  id: 'source',
  label: '1. Source',
  icon: '📁',
  helpText: 'Choose where to get your code'
}
```

### Field-Level Help
Individual settings have contextual help:
```typescript
m('div.panel-settings__help-text',
  state.selectedRenderer === 'd3' &&
  'Interactive force-directed graph with custom shapes'
)
```

### Progressive Hints
- Beginners see only required fields and primary actions
- Advanced options are grouped below with clear labels
- Settings show current values (e.g., "Size: 6px")

## Renderer Flexibility

### Key Feature: All Renderers Handle All Data

**Before** (restrictive):
```typescript
// D3 only handled data with type='d3'
// Gravis only handled data with type='gravis'
// Users were locked into one renderer per data source
```

**After** (flexible):
```typescript
// ALL renderers can handle gJGF graph data
// Users can switch renderers freely via dropdown
// Same graph, different visualization style
```

### User Benefit

Users can now:
1. Load **any graph** (demo, upload, repo)
2. Try **all three renderers** with same data
3. Pick their **favorite visualization style**

Example:
```
Upload Python file
  → Parse as AST
  → Try D3 (custom shapes, radial menu)
  → Switch to Gravis (classic network view)
  → Switch to Notebook (if HTML available)
  → Pick the one you like best!
```

## Technical Implementation

### Tab Order Update

**Before**: `'code' | 'parser' | 'layout' | 'style' | 'theme'`
**After**: `'source' | 'parse' | 'layout' | 'visual' | 'theme'`

### Default Tab

**Before**: Opens on `'code'` tab
**After**: Opens on `'source'` tab (step 1 of tutorial)

### Renderer Detection

**Before**:
```typescript
// Strict type checking
if (metadata.type === 'd3') { use D3 }
else if (metadata.type === 'gravis') { use Gravis }
```

**After**:
```typescript
// Priority system with flexibility
1. User-selected renderer (from Visual tab dropdown)
2. Metadata hint (if backend specifies)
3. Auto-detection (based on format)
4. Default fallback (D3)
```

### Render Priority

1. **User Choice** (highest): What user selected in Visual tab
2. **Backend Hint**: `metadata.type` from API response
3. **Auto-detect**: Format-based detection
4. **Default**: D3.js if nothing else matches

This means user selection **always wins**, giving full control.

## UX Improvements

### Visual Progression

- **Numbered tabs**: "1. Source", "2. Parse", "3. Layout", etc.
- **Icons**: Visual cues for each step
- **Left-to-right flow**: Natural reading order
- **Active tab highlighting**: Clear current position

### Contextual Help

- **Tab help text**: Explains purpose of current step
- **Field help text**: Details about specific settings
- **Dynamic hints**: Help text changes based on selections

### Error Prevention

- **Required fields at top**: Can't miss them
- **Sensible defaults**: Works out of box
- **Progressive disclosure**: Advanced options hidden until needed

## Status Indicators

The control panel includes a status bar showing:
- **Connection status**: Dot indicator (green/yellow/red)
- **Status message**: "Ready", "Loading...", error messages
- **Current theme**: Visual confirmation

## Accessibility

- **Keyboard navigation**: Tab through controls
- **Clear labels**: All fields properly labeled
- **Logical flow**: Follows natural task order
- **Visual feedback**: Hover states, active indicators

## Future Enhancements

Potential improvements to tutorial flow:

1. **Inline tooltips**: Hover over settings for more info
2. **Guided tour**: First-time user walkthrough
3. **Presets**: "Beginner", "Advanced", "Custom" button sets
4. **Undo/Reset**: Reset tab to defaults
5. **Save/Load**: Save favorite configurations
6. **Export config**: Share visualization settings
7. **Keyboard shortcuts**: Quick tab switching

## Summary

The redesigned control panel:

✅ **Guides users** through visualization process step-by-step
✅ **Numbered tabs** show clear progression (1→2→3→4→5)
✅ **Required fields first** so users don't miss critical settings
✅ **Optional fields below** for advanced customization
✅ **Help text** at tab and field level
✅ **All renderers** work with all data types
✅ **User choice** takes priority over auto-detection
✅ **Progressive disclosure** - simple by default, powerful when needed

The result is a tutorial-in-a-UI that works for beginners (3 clicks to visualize) and experts (full customization available).
