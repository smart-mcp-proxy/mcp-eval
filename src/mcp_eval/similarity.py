"""Tool call similarity calculation module for MCP evaluation."""

import json
from typing import Dict, Any, List, Set
from collections import Counter


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


def calculate_args_similarity(args1: Dict[str, Any], args2: Dict[str, Any]) -> float:
    """Calculate similarity between two sets of tool arguments.
    
    Args:
        args1: First set of arguments
        args2: Second set of arguments
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    if args1 == args2:
        return 1.0
    
    if not args1 and not args2:
        return 1.0
    
    # Calculate key similarity
    keys1 = set(args1.keys())
    keys2 = set(args2.keys())
    key_similarity = calculate_key_similarity(keys1, keys2)
    
    # If no common keys, return key similarity only
    common_keys = keys1.intersection(keys2)
    if not common_keys:
        return key_similarity * 0.5  # Penalize for no common keys
    
    # Calculate value similarities for common keys
    value_similarities = []
    for key in common_keys:
        value_sim = calculate_value_similarity(args1[key], args2[key])
        value_similarities.append(value_sim)
    
    # Average value similarity
    avg_value_similarity = sum(value_similarities) / len(value_similarities)
    
    # Combine key and value similarities (weighted average)
    # Key structure is 30% important, values are 70% important
    combined_similarity = (key_similarity * 0.3) + (avg_value_similarity * 0.7)
    
    return combined_similarity


def calculate_tool_call_similarity(call1: Dict[str, Any], call2: Dict[str, Any]) -> float:
    """Calculate similarity between two tool calls.
    
    Args:
        call1: First tool call with 'tool_name' and 'tool_input' keys
        call2: Second tool call with 'tool_name' and 'tool_input' keys
        
    Returns:
        Similarity score between 0.0 and 1.0
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
    
    # Calculate argument similarity
    return calculate_args_similarity(args1, args2)


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