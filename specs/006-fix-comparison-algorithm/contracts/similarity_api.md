# Similarity Calculation API Contract

**Module**: `src/mcp_eval/similarity.py`
**Purpose**: Enhanced similarity calculation with parameter weighting and missing value handling

## Public Functions

### calculate_tool_call_similarity (Enhanced)

Calculate similarity between two tool calls with parameter weighting.

**Signature**:
```python
def calculate_tool_call_similarity(
    call1: Dict[str, Any],
    call2: Dict[str, Any],
    config: Optional[SimilarityConfig] = None
) -> float:
    """Calculate weighted similarity between tool calls.

    Args:
        call1: First tool call dict with tool_name and tool_input
        call2: Second tool call dict with tool_name and tool_input
        config: Optional similarity configuration (uses defaults if None)

    Returns:
        Similarity score between 0.0 and 1.0

    Examples:
        >>> call1 = {"tool_name": "mcp__mcpproxy__retrieve_tools",
        ...          "tool_input": {"query": "email", "debug": true}}
        >>> call2 = {"tool_name": "mcp__mcpproxy__retrieve_tools",
        ...          "tool_input": {"query": "email tools", "debug": true, "limit": 10}}
        >>> calculate_tool_call_similarity(call1, call2)
        0.85  # High similarity despite extra parameters
    """
```

**Behavior**:
- Tool name mismatch → return 0.0 immediately
- Calculate key similarity: Jaccard(call1.keys, call2.keys)
- Calculate weighted value similarity for shared keys
- Apply parameter-specific weights (query: 1.5, operation: 1.5, others: 1.0)
- Handle missing parameters: score 0.5 instead of 0.0
- Return: (key_sim * 0.3) + (value_sim * 0.7)

**Test Cases**:
- Identical calls → 1.0
- Same tool, different query wording → >= 0.9
- Extra optional params → >= 0.8
- Missing required params → 0.5-0.7
- Different tool name → 0.0

---

### calculate_parameter_similarity (New)

Calculate similarity for a specific parameter value pair.

**Signature**:
```python
def calculate_parameter_similarity(
    param_name: str,
    value1: Any,
    value2: Any,
    weight: float = 1.0
) -> ParameterComparison:
    """Calculate similarity for specific parameter.

    Args:
        param_name: Name of the parameter
        value1: Expected value
        value2: Actual value
        weight: Parameter importance weight (default 1.0)

    Returns:
        ParameterComparison with detailed similarity breakdown

    Examples:
        >>> calculate_parameter_similarity("query", "email", "email tools", weight=1.5)
        ParameterComparison(
            parameter_name="query",
            expected_value="email",
            actual_value="email tools",
            similarity_score=0.67,
            comparison_method="jaccard",
            weight=1.5
        )
    """
```

**Comparison Methods**:
- Strings: Word-level Jaccard similarity
- Numbers: Distance-based (1 - abs(v1-v2) / max(v1,v2))
- Booleans: Exact match only (0.0 or 1.0)
- Null/None: missing_param_score (default 0.5)
- Objects/Arrays: JSON cosine similarity

---

### normalize_parameters (New)

Normalize parameter dictionary for consistent comparison.

**Signature**:
```python
def normalize_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize parameters for comparison.

    Args:
        params: Raw parameter dictionary

    Returns:
        Normalized dictionary with:
        - Sorted keys (alphabetical)
        - Consistent value formatting
        - Stripped whitespace

    Examples:
        >>> normalize_parameters({"debug": True, "query": "  email  ", "limit": 10})
        {"debug": true, "limit": 10, "query": "email"}
    """
```

**Normalization Rules**:
1. Sort keys alphabetically
2. Strip leading/trailing whitespace from strings
3. Convert boolean values to lowercase (True → true)
4. Round floats to 6 decimal places
5. Recursively normalize nested dicts/lists

---

## Configuration

### SimilarityConfig

```python
@dataclass
class SimilarityConfig:
    """Configuration for similarity calculations."""
    key_similarity_weight: float = 0.3
    value_similarity_weight: float = 0.7

    parameter_weights: Dict[str, float] = field(default_factory=lambda: {
        "tool_name": 2.0,
        "query": 1.5,
        "operation": 1.5,
        "default": 1.0
    })

    missing_param_score: float = 0.5
    min_word_overlap_threshold: float = 0.3
```

**Usage**:
```python
config = SimilarityConfig(missing_param_score=0.3)  # Stricter missing param handling
similarity = calculate_tool_call_similarity(call1, call2, config)
```

---

## Error Handling

**Invalid Inputs**:
- `tool_name` missing → raise ValueError
- `tool_input` not a dict → raise TypeError
- Threshold out of range → raise ValueError

**Graceful Degradation**:
- Unknown parameter type → use string representation
- Circular references in objects → use hash comparison
- Encoding errors → use byte comparison

---

## Performance Guarantees

- Single tool call comparison: <1ms
- 10 tool calls: <5ms
- 100 tool calls: <50ms
- No network I/O, all computation local
- Memory usage: O(n) where n = number of parameters

---

## Backward Compatibility

✅ Existing function signatures unchanged (new params are optional)
✅ Default behavior matches current implementation
✅ Existing tests continue to pass
