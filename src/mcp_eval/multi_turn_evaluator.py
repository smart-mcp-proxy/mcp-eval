"""Multi-turn dialog trajectory evaluation and comparison."""

import json
from typing import Dict, List, Any, Tuple
from pathlib import Path

from .similarity import calculate_trajectory_similarity


class MultiTurnDialogEvaluator:
    """Evaluate and compare multi-turn dialog trajectories."""
    
    def compare_dialogs(self, current_log: Dict[str, Any], baseline_log: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current dialog execution with baseline dialog."""
        
        current_conversation = current_log.get('conversation_log', [])
        baseline_conversation = baseline_log.get('conversation_log', [])
        
        # Extract tool trajectories for comparison
        current_trajectory = self._extract_tool_trajectory(current_conversation)
        baseline_trajectory = self._extract_tool_trajectory(baseline_conversation)
        
        # Calculate trajectory similarity
        trajectory_similarity = calculate_trajectory_similarity(current_trajectory, baseline_trajectory)
        
        # Calculate dialog flow similarity
        dialog_flow_similarity = self._calculate_dialog_flow_similarity(
            current_conversation, baseline_conversation
        )
        
        # Calculate turn sequence similarity
        turn_similarity = self._calculate_turn_similarity(
            current_conversation, baseline_conversation
        )
        
        # Overall score (weighted average)
        overall_score = (
            trajectory_similarity * 0.4 +  # Tool usage is important
            dialog_flow_similarity * 0.35 + # Dialog naturalness 
            turn_similarity * 0.25           # Turn sequence
        )
        
        # Detailed analysis
        comparison_result = {
            "overall_similarity": round(overall_score, 3),
            "trajectory_similarity": round(trajectory_similarity, 3),
            "dialog_flow_similarity": round(dialog_flow_similarity, 3),
            "turn_similarity": round(turn_similarity, 3),
            "current_turns": len(current_conversation),
            "baseline_turns": len(baseline_conversation),
            "current_tool_calls": len(current_trajectory),
            "baseline_tool_calls": len(baseline_trajectory),
            "turn_by_turn_analysis": self._analyze_turns(current_conversation, baseline_conversation),
            "tool_usage_comparison": self._compare_tool_usage(current_trajectory, baseline_trajectory)
        }
        
        return comparison_result
    
    def _extract_tool_trajectory(self, conversation_log: List[Dict]) -> List[Dict]:
        """Extract tool calls from conversation log."""
        trajectory = []
        
        for turn in conversation_log:
            tool_calls = turn.get('tool_calls', [])
            for tool_call in tool_calls:
                # Only include MCP tools in trajectory comparison
                tool_name = tool_call.get('tool_name', '')
                if tool_name.startswith('mcp__'):
                    trajectory.append({
                        'tool_name': tool_name,
                        'tool_input': tool_call.get('tool_input', {})
                    })
        
        return trajectory
    
    def _calculate_dialog_flow_similarity(self, current: List[Dict], baseline: List[Dict]) -> float:
        """Calculate similarity of dialog flow patterns."""
        if not current or not baseline:
            return 0.0
        
        # Compare speaker patterns
        current_speakers = [turn['speaker'] for turn in current]
        baseline_speakers = [turn['speaker'] for turn in baseline]
        
        # Use longest common subsequence for speaker pattern similarity
        speaker_similarity = self._lcs_similarity(current_speakers, baseline_speakers)
        
        # Compare message length patterns (normalized)
        current_lengths = [len(turn.get('message', '')) for turn in current]
        baseline_lengths = [len(turn.get('message', '')) for turn in baseline]
        
        length_similarity = self._compare_sequences(current_lengths, baseline_lengths)
        
        return (speaker_similarity + length_similarity) / 2
    
    def _calculate_turn_similarity(self, current: List[Dict], baseline: List[Dict]) -> float:
        """Calculate similarity of turn count and timing."""
        if not baseline:
            return 1.0 if not current else 0.0
        
        current_turns = len(current)
        baseline_turns = len(baseline)
        
        # Penalize large differences in turn count
        turn_diff = abs(current_turns - baseline_turns)
        max_turns = max(current_turns, baseline_turns)
        
        if max_turns == 0:
            return 1.0
        
        # Similarity decreases as turn difference increases
        turn_similarity = max(0.0, 1.0 - (turn_diff / max_turns))
        
        return turn_similarity
    
    def _analyze_turns(self, current: List[Dict], baseline: List[Dict]) -> List[Dict]:
        """Provide turn-by-turn analysis."""
        analysis = []
        max_turns = max(len(current), len(baseline))
        
        for i in range(max_turns):
            turn_analysis = {
                "turn_number": i,
                "current_present": i < len(current),
                "baseline_present": i < len(baseline)
            }
            
            if i < len(current):
                current_turn = current[i]
                turn_analysis["current_speaker"] = current_turn.get('speaker', 'Unknown')
                turn_analysis["current_tool_calls"] = len(current_turn.get('tool_calls', []))
                turn_analysis["current_message_length"] = len(current_turn.get('message', ''))
            
            if i < len(baseline):
                baseline_turn = baseline[i]
                turn_analysis["baseline_speaker"] = baseline_turn.get('speaker', 'Unknown')
                turn_analysis["baseline_tool_calls"] = len(baseline_turn.get('tool_calls', []))
                turn_analysis["baseline_message_length"] = len(baseline_turn.get('message', ''))
            
            # Calculate turn-level similarity
            if turn_analysis["current_present"] and turn_analysis["baseline_present"]:
                speaker_match = turn_analysis.get("current_speaker") == turn_analysis.get("baseline_speaker")
                tool_calls_match = turn_analysis.get("current_tool_calls", 0) == turn_analysis.get("baseline_tool_calls", 0)
                turn_analysis["similarity"] = 1.0 if speaker_match and tool_calls_match else 0.5 if speaker_match else 0.0
            else:
                turn_analysis["similarity"] = 0.0
            
            analysis.append(turn_analysis)
        
        return analysis
    
    def _compare_tool_usage(self, current: List[Dict], baseline: List[Dict]) -> Dict[str, Any]:
        """Compare tool usage patterns between dialogs."""
        current_tools = [call['tool_name'] for call in current]
        baseline_tools = [call['tool_name'] for call in baseline]
        
        current_unique = set(current_tools)
        baseline_unique = set(baseline_tools)
        
        common_tools = current_unique & baseline_unique
        current_only = current_unique - baseline_unique  
        baseline_only = baseline_unique - current_unique
        
        return {
            "common_tools": list(common_tools),
            "current_only_tools": list(current_only),
            "baseline_only_tools": list(baseline_only),
            "tool_overlap_ratio": len(common_tools) / len(baseline_unique) if baseline_unique else 0.0,
            "current_tool_count": len(current_tools),
            "baseline_tool_count": len(baseline_tools)
        }
    
    def _lcs_similarity(self, seq1: List, seq2: List) -> float:
        """Calculate similarity using longest common subsequence."""
        if not seq1 or not seq2:
            return 0.0
        
        # Dynamic programming LCS
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_length = dp[m][n]
        return lcs_length / max(m, n)
    
    def _compare_sequences(self, seq1: List[int], seq2: List[int]) -> float:
        """Compare two numeric sequences for similarity."""
        if not seq1 or not seq2:
            return 0.0
        
        # Normalize sequences
        max_len = max(len(seq1), len(seq2))
        seq1_padded = seq1 + [0] * (max_len - len(seq1))
        seq2_padded = seq2 + [0] * (max_len - len(seq2))
        
        # Calculate normalized differences
        differences = []
        for a, b in zip(seq1_padded, seq2_padded):
            max_val = max(a, b, 1)  # Avoid division by zero
            diff = abs(a - b) / max_val
            differences.append(1.0 - diff)  # Convert to similarity
        
        return sum(differences) / len(differences) if differences else 0.0