"""Tool call similarity calculation module for MCP evaluation."""

import json
from typing import Dict, Any, List, Set, Optional, Literal
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class SimilarityConfig:
    """Configuration for similarity calculations."""
    # Algorithm weights
    key_similarity_weight: float = 0.3
    value_similarity_weight: float = 0.7

    # Parameter-specific weights
    parameter_weights: Dict[str, float] = field(default_factory=lambda: {
        "tool_name": 2.0,
        "query": 1.5,
        "operation": 1.5,
        "default": 1.0
    })

    # Missing parameter handling
    missing_param_score: float = 0.5  # Partial match, not complete failure

    # String comparison
    min_word_overlap_threshold: float = 0.3

    def get_parameter_weight(self, param_name: str) -> float:
        """Get weight for specific parameter."""
        return self.parameter_weights.get(param_name, self.parameter_weights["default"])


@dataclass
class ParameterComparison:
    """Comparison of a single parameter between two tool calls."""
    parameter_name: str
    expected_value: Optional[Any]
    actual_value: Optional[Any]
    similarity_score: float  # 0.0-1.0
    comparison_method: Literal["exact", "jaccard", "cosine", "missing"]
    weight: float = 1.0  # Parameter importance weight

    @property
    def is_exact_match(self) -> bool:
        return self.similarity_score == 1.0

    @property
    def is_missing(self) -> bool:
        return self.expected_value is None or self.actual_value is None


def calculate_key_similarity(keys1: Set[str], keys2: Set[str]) -> float:
    """Calculate similarity between two sets of argument keys.
    
    Args:
        keys1: Set of keys from first tool call
        keys2: Set of keys from second tool call
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not keys1 and not keys2:
        return 1.0
    
    if not keys1 or not keys2:
        return 0.0
    
    intersection = keys1.intersection(keys2)
    union = keys1.union(keys2)
    
    return len(intersection) / len(union)


def calculate_string_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings based on word intersection.
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if str1 == str2:
        return 1.0
    
    # Convert to lowercase and split into words
    words1 = set(str1.lower().split())
    words2 = set(str2.lower().split())
    
    if not words1 and not words2:
        return 1.0
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)


def calculate_number_similarity(num1: float, num2: float, max_diff: float = 1000.0) -> float:
    """Calculate similarity between two numbers based on absolute difference.
    
    Args:
        num1: First number
        num2: Second number
        max_diff: Maximum difference to normalize against
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if num1 == num2:
        return 1.0
    
    abs_diff = abs(num1 - num2)
    # Normalize by max_diff, ensuring we don't go below 0
    similarity = max(0.0, 1.0 - (abs_diff / max_diff))
    
    return similarity


def calculate_json_similarity(json1: Any, json2: Any) -> float:
    """Calculate similarity between two JSON objects using character frequency.
    
    Args:
        json1: First JSON object
        json2: Second JSON object
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if json1 == json2:
        return 1.0
    
    # Convert to JSON strings
    str1 = json.dumps(json1, sort_keys=True)
    str2 = json.dumps(json2, sort_keys=True)
    
    # Count character frequencies
    counter1 = Counter(str1)
    counter2 = Counter(str2)
    
    # Get all unique characters
    all_chars = set(counter1.keys()).union(set(counter2.keys()))
    
    if not all_chars:
        return 1.0
    
    # Calculate cosine similarity
    dot_product = sum(counter1[char] * counter2[char] for char in all_chars)
    magnitude1 = sum(count ** 2 for count in counter1.values()) ** 0.5
    magnitude2 = sum(count ** 2 for count in counter2.values()) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def calculate_value_similarity(value1: Any, value2: Any) -> float:
    """Calculate similarity between two argument values.
    
    Args:
        value1: First value
        value2: Second value
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Handle exact matches first
    if value1 == value2:
        return 1.0
    
    # Handle None values
    if value1 is None or value2 is None:
        return 0.0 if (value1 is None) != (value2 is None) else 1.0
    
    # Get types
    type1 = type(value1)
    type2 = type(value2)
    
    # If different types, try to handle string/number conversions
    if type1 != type2:
        # Try to convert both to strings for comparison
        return calculate_string_similarity(str(value1), str(value2))
    
    # Handle strings
    if isinstance(value1, str):
        return calculate_string_similarity(value1, value2)
    
    # Handle numbers (int, float)
    if isinstance(value1, (int, float)):
        return calculate_number_similarity(float(value1), float(value2))
    
    # Handle complex objects (lists, dicts) as JSON
    if isinstance(value1, (dict, list)):
        return calculate_json_similarity(value1, value2)
    
    # Fallback to string comparison
    return calculate_string_similarity(str(value1), str(value2))


def normalize_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize parameters for consistent comparison.

    Normalization includes:
    - Alphabetical key sorting (order-independent comparison)
    - String value whitespace stripping
    - Boolean value normalization to lowercase strings
    - None/null value normalization

    Args:
        params: Parameter dictionary to normalize

    Returns:
        Normalized parameter dictionary

    Example:
        >>> normalize_parameters({"query": "  email  ", "debug": True, "limit": 10})
        {'debug': 'true', 'limit': 10, 'query': 'email'}
    """
    if not params:
        return {}

    normalized = {}

    # Sort keys alphabetically for order-independent comparison
    for key in sorted(params.keys()):
        value = params[key]

        # Normalize string values: strip whitespace
        if isinstance(value, str):
            normalized[key] = value.strip()
        # Normalize boolean values to lowercase strings
        elif isinstance(value, bool):
            normalized[key] = str(value).lower()
        # Keep other values as-is (numbers, None, dicts, lists)
        else:
            normalized[key] = value

    return normalized


def calculate_parameter_similarity(
    param_name: str,
    value1: Any,
    value2: Any,
    config: Optional[SimilarityConfig] = None
) -> ParameterComparison:
    """Calculate similarity between two parameter values with weighting.

    Args:
        param_name: Name of the parameter being compared
        value1: First parameter value
        value2: Second parameter value
        config: Optional similarity configuration

    Returns:
        ParameterComparison object with similarity score and metadata

    Example:
        >>> result = calculate_parameter_similarity("query", "email", "email tools")
        >>> result.similarity_score
        0.5
        >>> result.comparison_method
        'jaccard'
    """
    if config is None:
        config = SimilarityConfig()

    # Get weight for this parameter
    weight = config.get_parameter_weight(param_name)

    # Handle missing values
    if value1 is None and value2 is None:
        return ParameterComparison(
            parameter_name=param_name,
            expected_value=value1,
            actual_value=value2,
            similarity_score=1.0,
            comparison_method="exact",
            weight=weight
        )

    if value1 is None or value2 is None:
        return ParameterComparison(
            parameter_name=param_name,
            expected_value=value1,
            actual_value=value2,
            similarity_score=config.missing_param_score,
            comparison_method="missing",
            weight=weight
        )

    # Calculate value similarity
    similarity = calculate_value_similarity(value1, value2)

    # Determine comparison method
    if similarity == 1.0:
        method = "exact"
    elif isinstance(value1, str) and isinstance(value2, str):
        method = "jaccard"
    elif isinstance(value1, (dict, list)) and isinstance(value2, (dict, list)):
        method = "cosine"
    else:
        method = "jaccard"

    return ParameterComparison(
        parameter_name=param_name,
        expected_value=value1,
        actual_value=value2,
        similarity_score=similarity,
        comparison_method=method,
        weight=weight
    )


def calculate_args_similarity(
    args1: Dict[str, Any],
    args2: Dict[str, Any],
    config: Optional[SimilarityConfig] = None
) -> float:
    """Calculate similarity between two sets of tool arguments with parameter weighting.

    Args:
        args1: First set of arguments
        args2: Second set of arguments
        config: Optional similarity configuration for parameter weights

    Returns:
        Similarity score between 0.0 and 1.0

    Example:
        >>> args1 = {"query": "email", "debug": True}
        >>> args2 = {"query": "email tools", "debug": True}
        >>> calculate_args_similarity(args1, args2)
        0.85
    """
    if config is None:
        config = SimilarityConfig()

    # Normalize parameters for consistent comparison
    normalized1 = normalize_parameters(args1)
    normalized2 = normalize_parameters(args2)

    if normalized1 == normalized2:
        return 1.0

    if not normalized1 and not normalized2:
        return 1.0

    # Get all parameter names from both sets
    keys1 = set(normalized1.keys())
    keys2 = set(normalized2.keys())
    all_keys = keys1.union(keys2)

    if not all_keys:
        return 1.0

    # Calculate weighted parameter similarities
    total_weight = 0.0
    weighted_sum = 0.0

    for key in all_keys:
        value1 = normalized1.get(key)
        value2 = normalized2.get(key)

        # Calculate parameter similarity with weighting
        param_comparison = calculate_parameter_similarity(key, value1, value2, config)

        # Accumulate weighted score
        weighted_sum += param_comparison.similarity_score * param_comparison.weight
        total_weight += param_comparison.weight

    # Return weighted average
    if total_weight == 0:
        return 0.0

    return weighted_sum / total_weight


def calculate_tool_call_similarity(
    call1: Dict[str, Any],
    call2: Dict[str, Any],
    config: Optional[SimilarityConfig] = None
) -> float:
    """Calculate similarity between two tool calls with parameter weighting.

    Uses parameter-weighted similarity calculation with normalization.
    Tool names must match exactly; if different, returns 0.0.
    Arguments are compared using weighted parameter similarity.

    Args:
        call1: First tool call with 'tool_name' and 'tool_input' keys
        call2: Second tool call with 'tool_name' and 'tool_input' keys
        config: Optional similarity configuration for custom parameter weights

    Returns:
        Similarity score between 0.0 and 1.0

    Example:
        >>> call1 = {"tool_name": "mcp__test__search", "tool_input": {"query": "email", "debug": True}}
        >>> call2 = {"tool_name": "mcp__test__search", "tool_input": {"query": "email", "debug": True}}
        >>> calculate_tool_call_similarity(call1, call2)
        1.0

        >>> call3 = {"tool_name": "mcp__test__search", "tool_input": {"query": "email tools"}}
        >>> calculate_tool_call_similarity(call1, call3)
        0.5
    """
    # Extract tool names
    name1 = call1.get('tool_name', '')
    name2 = call2.get('tool_name', '')

    # If tool names are different, similarity is 0
    if name1 != name2:
        return 0.0

    # Extract arguments
    args1 = call1.get('tool_input', {})
    args2 = call2.get('tool_input', {})

    # Calculate argument similarity with config
    return calculate_args_similarity(args1, args2, config)


def calculate_trajectory_similarity(calls1: List[Dict[str, Any]], calls2: List[Dict[str, Any]]) -> float:
    """Calculate similarity between two trajectories of tool calls.
    
    Only considers MCP tool calls (tool names starting with 'mcp__').
    
    Args:
        calls1: First trajectory of tool calls
        calls2: Second trajectory of tool calls
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Filter to only MCP tool calls
    mcp_calls1 = [call for call in calls1 if call.get('tool_name', '').startswith('mcp__')]
    mcp_calls2 = [call for call in calls2 if call.get('tool_name', '').startswith('mcp__')]
    
    # If both trajectories have no MCP calls, similarity is 1.0
    if not mcp_calls1 and not mcp_calls2:
        return 1.0
    
    # If one has MCP calls and other doesn't, similarity is 0.0
    if not mcp_calls1 or not mcp_calls2:
        return 0.0
    
    # If different number of calls, pad with None to make them equal length
    max_len = max(len(mcp_calls1), len(mcp_calls2))
    
    similarities = []
    
    for i in range(max_len):
        call1 = mcp_calls1[i] if i < len(mcp_calls1) else None
        call2 = mcp_calls2[i] if i < len(mcp_calls2) else None
        
        if call1 is None or call2 is None:
            # Missing call gets 0 similarity
            similarities.append(0.0)
        else:
            # Calculate similarity between calls
            sim = calculate_tool_call_similarity(call1, call2)
            similarities.append(sim)
    
    # Return average similarity across all positions
    return sum(similarities) / len(similarities)