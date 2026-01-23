# Compare View - Quick Start Guide

## What is Compare View?

Compare View lets you compare Stage 1 model responses side-by-side in a full-screen modal, making it easy to evaluate different AI models' approaches to the same question.

## How to Use

### 1. Opening Compare View

After asking a question and receiving Stage 1 responses:
1. Look for the **⚖️ Compare** button in the Stage 1 header
2. Click it to open the comparison modal
3. The button only appears when you have 2+ model responses

### 2. Selecting Models to Compare

**Default Selection:**
- Opens with first 2 models (in 2-column mode) or first 3 models (in 3-column mode)

**Custom Selection:**
- Click any model chip to toggle selection
- Selected chips are highlighted with colored borders
- Maximum selections: 2 (2-column) or 3 (3-column)
- When at max, clicking a new model replaces the last selection

### 3. Switching Layout

**2-Column Layout:**
- Best for detailed side-by-side comparison
- More horizontal space per response
- Better for long responses

**3-Column Layout:**
- Compare 3 models at once
- Better for shorter responses
- Quick overview of multiple perspectives

Click the layout buttons to switch between modes.

### 4. Reading Responses

**Synchronized Scrolling:**
- Scroll in any column, all columns scroll together
- Makes it easy to compare the same section across models

**Reasoning Blocks:**
- Models with reasoning (🧠 icon) have collapsible thinking sections
- Click to expand/collapse the reasoning process
- Helps understand how each model approached the problem

**Model Headers:**
- Color-coded for easy visual distinction
- Shows full model name
- Copy button (📋) to copy individual response

### 5. Merging Best Parts

**Select Text:**
1. Highlight any text in any response column
2. Selection is automatically captured when you release mouse
3. Can select from different models multiple times

**View Merged Selections:**
- Merged selections appear in preview panel at bottom
- Shows which model each selection came from
- Remove individual selections with X button

**Copy Merged Text:**
1. Click **📋 Copy Merged Text** button
2. Paste into any document
3. Format: `[From model_name]\ntext\n\n---\n\n[From model_name2]\ntext`

**Clear Selections:**
- Click **🗑️ Clear** to remove all merged selections

### 6. Closing Compare View

- Click the **✕** button in top-right
- Click outside the modal (on dark overlay)
- Press **ESC** key (when clicking outside)

## Example Workflow

### Scenario: Evaluating Code Explanations

1. Ask: "Explain how async/await works in JavaScript"
2. Get responses from GPT-5, Claude Sonnet 4, Gemini 2.5 Pro
3. Click **⚖️ Compare**
4. Select all 3 models in 3-column layout
5. Scroll through to see different explanation styles
6. Highlight best parts from each:
   - GPT's concise definition
   - Claude's practical examples
   - Gemini's error handling section
7. Click **Copy Merged Text**
8. Paste into your notes with attribution

### Scenario: Comparing Reasoning Processes

1. Ask: "Solve this logic puzzle: ..."
2. Get responses from reasoning models (O3, DeepSeek R1, QwQ)
3. Click **⚖️ Compare**
4. Expand reasoning blocks (🧠) in each column
5. Compare step-by-step thinking approaches
6. See which model found the solution fastest
7. Copy the clearest explanation

## Tips & Tricks

### Efficient Comparison
- Use 2-column for detailed analysis
- Use 3-column for quick overview
- Scroll to same section across columns (auto-synced)

### Text Selection
- Select small, focused sections
- Build merged response incrementally
- Remove/reselect if you change your mind

### Model Selection
- Look for 🧠 indicator for reasoning models
- Compare similar model types (GPT vs Claude vs Gemini)
- Or compare reasoning vs non-reasoning approaches

### Copy Operations
- Copy individual responses for full model output
- Copy merged selections for curated best-of-all

### Responsive Design
- On mobile: Automatically switches to single-column stack
- On tablet: 2-column works best
- On desktop: 3-column gives full comparison power

## Keyboard Shortcuts

- **ESC**: Close modal (when overlay is clicked)
- **Mouse Selection**: Automatic text capture on mouseUp

## Visual Indicators

- **⚖️**: Compare button (balance scale emoji)
- **🧠**: Reasoning model indicator (brain emoji)
- **📋**: Copy to clipboard (clipboard emoji)
- **🗑️**: Clear selections (trash emoji)
- **✕**: Close modal (multiplication X)
- **▶/▼**: Expand/collapse arrows

## Color Coding

Models rotate through 6 distinct header colors:
1. Blue (#4a90e2)
2. Green (#2d8a2d)
3. Red (#e24a4a)
4. Orange (#e2a54a)
5. Purple (#a54ae2)
6. Cyan (#4ae2e2)

This makes it easy to visually distinguish models when comparing.

## Common Use Cases

### 1. Code Review
Compare how different models explain code concepts, suggest improvements, or debug issues.

### 2. Research Questions
Evaluate depth and accuracy of research answers across models.

### 3. Creative Writing
Compare creative approaches, writing styles, and narrative structures.

### 4. Problem Solving
See different solution strategies, especially with reasoning models.

### 5. Technical Documentation
Compare clarity and completeness of technical explanations.

### 6. Translation/Paraphrasing
Evaluate different phrasings and translations side-by-side.

## Troubleshooting

### Compare button not showing
- Need at least 2 model responses in Stage 1
- Make sure you've configured multiple council models in Settings

### Scroll not syncing
- Try refreshing the page
- Works best on modern browsers (Chrome, Firefox, Safari, Edge)

### Text selection not capturing
- Make sure to fully release mouse button after highlighting
- Selection must contain text (not just whitespace)

### Copy to clipboard not working
- Requires secure context (HTTPS or localhost)
- Check browser permissions for clipboard access

### Modal not responsive on mobile
- Should auto-adjust to single column
- Try rotating device to landscape for better view

## Browser Requirements

**Recommended Browsers:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Required Features:**
- CSS Grid support
- JavaScript ES6+
- Clipboard API
- Window.getSelection()

## Privacy & Performance

- All comparison happens locally in your browser
- No data sent to external services
- Scroll sync uses minimal CPU
- Large responses (>100KB) may slow down on older devices

## Next Steps

After comparing responses:
1. Review Stage 2 to see how models ranked each other
2. Check Stage 3 for the chairman's synthesis
3. Use merged text in your projects/notes
4. Adjust council models in Settings based on performance

## Feedback

Found a bug or have a feature request?
- Check `COMPARE_VIEW_IMPLEMENTATION.md` for technical details
- Submit issue to project repository
- Contribute improvements via pull request

---

**Quick Reference Card:**

| Action | Method |
|--------|--------|
| Open Compare | Click ⚖️ Compare button |
| Close Compare | Click ✕ or outside modal |
| Select Model | Click model chip |
| Switch Layout | Click 2/3 Column buttons |
| Select Text | Highlight with mouse |
| Copy Merged | Click 📋 Copy Merged Text |
| Clear Merged | Click 🗑️ Clear |
| Copy Single | Click 📋 on model header |
| Expand Reasoning | Click reasoning block summary |

**Pro Tip:** Combine Compare View with Stage 2's anonymized rankings to identify which models consistently provide the best responses for your use case!
