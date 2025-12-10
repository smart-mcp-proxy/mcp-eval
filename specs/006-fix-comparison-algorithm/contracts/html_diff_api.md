# HTML Diff Generation API Contract

**Module**: `src/mcp_eval/html_reporter.py`
**Purpose**: Generate HTML diff reports with proper normalization to prevent false highlights

## Public Functions

### generate_normalized_dialog_diff (Enhanced)

Generate HTML diff for dialog turns with normalization.

**Signature**:
```python
def generate_normalized_dialog_diff(
    current_turns: List[Dict[str, Any]],
    baseline_turns: List[Dict[str, Any]],
    config: Optional[HtmlDiffConfig] = None
) -> str:
    """Generate HTML diff with normalized content.

    Args:
        current_turns: Dialog turns from current execution
        baseline_turns: Dialog turns from baseline execution
        config: Optional HTML diff configuration

    Returns:
        HTML string with side-by-side diff, no false highlights

    Examples:
        >>> current = [{"type": "TOOL_CALL", "content": "{'query': 'email', 'debug': True}"}]
        >>> baseline = [{"type": "TOOL_CALL", "content": "{'query': 'email', 'debug': True}"}]
        >>> html = generate_normalized_dialog_diff(current, baseline)
        >>> "diff-highlight" in html
        False  # No highlighting for identical content
    """
```

**Normalization Steps**:
1. Extract tool call parameters from content strings
2. Parse dictionaries (handle both JSON and Python repr formats)
3. Normalize each dictionary:
   - Sort keys alphabetically
   - Format as JSON with consistent indentation
   - Strip extra whitespace
4. Generate diff using normalized strings
5. Post-process HTML to remove false highlights

---

### normalize_tool_call_content (New)

Normalize tool call content string for comparison.

**Signature**:
```python
def normalize_tool_call_content(content: str) -> str:
    """Normalize tool call content for diffing.

    Handles multiple formats:
    - Python dict repr: "{'key': 'value'}"
    - JSON: '{"key": "value"}'
    - Mixed: "Calling tool({'key': 'value'})"

    Args:
        content: Raw tool call content string

    Returns:
        Normalized JSON string with sorted keys

    Examples:
        >>> normalize_tool_call_content("{'debug': True, 'query': 'email'}")
        '{"debug": true, "query": "email"}'

        >>> normalize_tool_call_content("{'query': 'email', 'debug': True}")
        '{"debug": true, "query": "email"}'  # Same output despite different order
    """
```

**Parsing Strategy**:
1. Try JSON parsing first (most reliable)
2. Try AST literal_eval for Python dicts
3. Regex extract dict patterns if embedded in text
4. Fallback: return original string (graceful degradation)

**Normalization Rules**:
- Sort dictionary keys alphabetically
- Convert Python booleans (True/False) → JSON (true/false)
- Consistent indentation: 2 spaces
- No trailing commas
- Escape special characters consistently

---

### remove_false_highlights (New)

Post-process HTML diff to remove false positive highlights.

**Signature**:
```python
def remove_false_highlights(html: str) -> str:
    """Remove false positive highlights from difflib HTML.

    Difflib may highlight visually identical strings due to:
    - Different quote styles (' vs ")
    - Whitespace differences
    - Python vs JSON boolean formats

    Args:
        html: Raw HTML from difflib.HtmlDiff

    Returns:
        Cleaned HTML with false highlights removed

    Implementation:
        - Parse HTML with BeautifulSoup/lxml
        - For each highlighted span:
            - Extract text content from both sides
            - Normalize and compare
            - Remove highlight if content is identical
        - Return cleaned HTML
    """
```

---

## Configuration

### HtmlDiffConfig

```python
@dataclass
class HtmlDiffConfig:
    """Configuration for HTML diff generation."""
    normalize_whitespace: bool = True
    normalize_dict_keys: bool = True
    normalize_json_format: bool = True
    show_line_numbers: bool = True
    context_lines: int = 3

    # Character-level diff control
    enable_character_diff: bool = True
    highlight_whole_words: bool = False

    # Color scheme (Bootstrap-compatible)
    added_bg_color: str = "#c6f6d5"
    removed_bg_color: str = "#fed7d7"
    modified_bg_color: str = "#fef5e7"
    unchanged_bg_color: str = "#f8f9fa"
```

---

## HTML Output Structure

### Side-by-Side Comparison

```html
<div class="dialog-turn-comparison">
    <h3>Dialog Turn Comparison</h3>

    <!-- Filter controls -->
    <div class="diff-filter-controls">
        <label>
            <input type="checkbox" id="show-added" checked>
            <span class="diff-badge diff-added">0 Added</span>
        </label>
        <!-- ... other filters ... -->
    </div>

    <!-- Diff rows -->
    <div class="diff-side-by-side">
        <!-- Unchanged turn -->
        <div class="diff-row turn-unchanged">
            <div class="diff-column diff-current">
                <div class="turn-content">Search for email tools</div>
            </div>
            <div class="diff-column diff-baseline">
                <div class="turn-content">Search for email tools</div>
            </div>
        </div>

        <!-- Modified turn (with normalization, no false highlights) -->
        <div class="diff-row turn-modified">
            <div class="diff-column diff-current">
                <div class="turn-content">
                    Calling tool({
                      "debug": true,
                      "query": "email"
                    })
                </div>
            </div>
            <div class="diff-column diff-baseline">
                <div class="turn-content">
                    Calling tool({
                      "debug": true,
                      "query": "email"
                    })
                </div>
            </div>
        </div>

        <!-- Actually different turn (real highlight) -->
        <div class="diff-row turn-modified">
            <div class="diff-column diff-current">
                <div class="turn-content">
                    Calling tool({
                      "debug": true,
                      "query": "<span class="diff-highlight">email tools</span>"
                    })
                </div>
            </div>
            <div class="diff-column diff-baseline">
                <div class="turn-content">
                    Calling tool({
                      "debug": true,
                      "query": "<span class="diff-highlight">email</span>"
                    })
                </div>
            </div>
        </div>
    </div>
</div>
```

---

## Integration Points

### html_reporter.py Integration

```python
def generate_comparison_html(
    current_log: Dict[str, Any],
    baseline_log: Dict[str, Any],
    comparison_result: ComparisonResult
) -> str:
    """Generate comparison HTML report."""

    # NEW: Use normalized diff generation
    config = HtmlDiffConfig(
        normalize_dict_keys=True,
        normalize_json_format=True
    )

    dialog_diff_html = generate_normalized_dialog_diff(
        current_turns=current_log["dialog_turns"],
        baseline_turns=baseline_log["dialog_turns"],
        config=config
    )

    # Existing report template rendering
    return render_html_template(
        comparison_result=comparison_result,
        dialog_diff=dialog_diff_html,
        # ... other sections ...
    )
```

---

## Error Handling

**Parsing Failures**:
- Invalid JSON/dict syntax → use original string, log warning
- Circular references in objects → use string repr
- Encoding errors → use byte comparison fallback

**HTML Generation Failures**:
- difflib raises exception → fallback to simple text diff
- Template rendering error → return minimal HTML with error message
- Missing CSS classes → use inline styles fallback

**Graceful Degradation**:
- If normalization fails → show original strings
- If highlight removal fails → show difflib output as-is
- Never crash HTML generation, always produce some output

---

## Performance Guarantees

- Normalization time: <50ms per turn
- Diff generation: <5s for 20+ turns (current constraint maintained)
- HTML size: <500KB for typical report (no JavaScript frameworks)
- Memory usage: O(n) where n = total turn content size

---

## Testing Requirements

**Unit Tests**:
- Identical dicts with different key order → no highlights
- Identical dicts with Python vs JSON format → no highlights
- Actually different values → highlights applied correctly
- Empty/null parameter handling → no crashes
- Malformed JSON → graceful fallback

**Visual Regression Tests**:
- Compare rendered HTML pixel-by-pixel (use Playwright/Selenium)
- Verify no false yellow highlights on known-identical content
- Verify real differences are highlighted appropriately
- Test multiple browser rendering (Chrome, Firefox, Safari)

---

## Backward Compatibility

✅ Existing HTML reports remain valid (no schema changes)
✅ CSS classes unchanged (backward compatible styling)
✅ JavaScript filtering logic unchanged
✅ Report URLs/file paths unchanged
