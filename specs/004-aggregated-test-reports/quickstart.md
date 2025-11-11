# Quickstart: Implementing Aggregated Test Reports

**Feature**: 004-aggregated-test-reports
**Audience**: Developers implementing this feature
**Estimated Time**: 3-4 hours for P1/P2 implementation

## Prerequisites

- Python 3.11+ environment with uv package manager
- Familiarity with existing `mcp-eval` codebase
- Understanding of Pydantic data models
- Basic HTML/CSS knowledge

## Implementation Checklist

### Phase 1: Data Models (30 minutes)

1. **Create `src/mcp_eval/summary_models.py`**:
   ```bash
   touch src/mcp_eval/summary_models.py
   ```

2. **Implement Pydantic models**:
   - [ ] Copy `ScenarioStatus` enum from `data-model.md` example
   - [ ] Implement `ScenarioExecutionSummary` with all fields and validators
   - [ ] Implement `TestRunSummary` with aggregate counts and validators
   - [ ] Add `pass_rate` and `total_duration` properties
   - [ ] Import models in `src/mcp_eval/__init__.py`

3. **Verify models**:
   ```bash
   uv run python -c "from mcp_eval.summary_models import TestRunSummary; print('✓ Models importable')"
   ```

### Phase 2: HTML Generation (90 minutes)

1. **Extend `src/mcp_eval/html_reporter.py`**:
   - [ ] Add import: `from mcp_eval.summary_models import TestRunSummary, ScenarioExecutionSummary`
   - [ ] Create `generate_summary_report(test_run: TestRunSummary) -> str` function
   - [ ] Implement HTML document structure from `contracts/summary-report-html.md`
   - [ ] Copy CSS color variables from existing detailed report CSS
   - [ ] Add status badge rendering with correct colors
   - [ ] Implement table row generation loop over `test_run.scenario_summaries`
   - [ ] Add intent truncation logic (60 char limit)
   - [ ] Format duration to 1 decimal place, similarity to 2 decimals
   - [ ] Handle `similarity_score=None` → display "N/A"

2. **Helper function for status colors**:
   ```python
   def _get_status_color(status: ScenarioStatus) -> str:
       colors = {
           ScenarioStatus.PASSED: "#28a745",
           ScenarioStatus.FAILED: "#dc3545",
           ScenarioStatus.RECORDED: "#007bff",
           ScenarioStatus.ERROR: "#ffc107"
       }
       return colors[status]
   ```

3. **Test HTML generation**:
   ```bash
   # Create test script to generate sample report
   uv run python -c "
   from mcp_eval.summary_models import *
   from mcp_eval.html_reporter import generate_summary_report
   from datetime import datetime

   summary = ScenarioExecutionSummary(
       scenario_name='test',
       scenario_path='test.yaml',
       user_intent='Test scenario',
       status=ScenarioStatus.PASSED,
       tool_count=5,
       duration_seconds=12.3,
       detailed_report_path='test_baseline_20251111_143147.html',
       similarity_score=0.95
   )

   test_run = TestRunSummary(
       test_run_timestamp=datetime.now(),
       total_scenarios=1,
       passed_count=1,
       failed_count=0,
       recorded_count=0,
       error_count=0,
       scenario_summaries=[summary]
   )

   html = generate_summary_report(test_run)
   print('✓ HTML generated, length:', len(html))
   "
   ```

### Phase 3: CLI Integration (60 minutes)

1. **Modify `src/mcp_eval/cli.py` - test command**:

   Find the `test()` function and add:

   ```python
   from mcp_eval.summary_models import ScenarioExecutionSummary, TestRunSummary, ScenarioStatus
   from datetime import datetime

   # At start of test() function:
   run_start_time = datetime.now()
   scenario_summaries: List[ScenarioExecutionSummary] = []
   ```

   After each scenario execution, collect metadata:

   ```python
   # After scenario completes
   summary = ScenarioExecutionSummary(
       scenario_name=scenario_file.stem,
       scenario_path=str(scenario_file.relative_to(scenarios_dir)),
       user_intent=scenario_data.get("user_intent", ""),
       status=ScenarioStatus[result.status.upper()],  # Convert string to enum
       tool_count=result.tool_calls_count,
       duration_seconds=result.duration,
       detailed_report_path=Path(result.html_report_path).name,  # Relative filename only
       similarity_score=result.similarity_score if hasattr(result, 'similarity_score') else None
   )
   scenario_summaries.append(summary)
   ```

   After all scenarios complete:

   ```python
   # Generate summary report
   test_run = TestRunSummary(
       test_run_timestamp=run_start_time,
       total_scenarios=len(scenario_summaries),
       passed_count=sum(1 for s in scenario_summaries if s.status == ScenarioStatus.PASSED),
       failed_count=sum(1 for s in scenario_summaries if s.status == ScenarioStatus.FAILED),
       recorded_count=sum(1 for s in scenario_summaries if s.status == ScenarioStatus.RECORDED),
       error_count=sum(1 for s in scenario_summaries if s.status == ScenarioStatus.ERROR),
       scenario_summaries=scenario_summaries,
       mcp_config_path=str(mcp_config) if mcp_config else None,
       git_hash=get_git_hash()  # Implement or import this helper
   )

   from mcp_eval.html_reporter import generate_summary_report
   summary_html = generate_summary_report(test_run)

   timestamp_str = run_start_time.strftime("%Y%m%d_%H%M%S")
   summary_path = reports_dir / f"test_summary_{timestamp_str}.html"
   summary_path.write_text(summary_html, encoding="utf-8")

   console.print(f"\n📊 [green]Summary report:[/green] {summary_path}")
   ```

2. **Implement `get_git_hash()` helper**:
   ```python
   def get_git_hash() -> Optional[str]:
       """Get current git commit hash (8 chars) or None if not in git repo."""
       try:
           import subprocess
           result = subprocess.run(
               ["git", "rev-parse", "--short=8", "HEAD"],
               capture_output=True,
               text=True,
               check=True
           )
           return result.stdout.strip()
       except (subprocess.CalledProcessError, FileNotFoundError):
           return None
   ```

3. **Repeat for `batch()` command**:
   - [ ] Add same summary collection logic to `batch()` function
   - [ ] Ensure summary report generated at end of batch run
   - [ ] Test both commands generate summary reports

### Phase 4: Testing (45 minutes)

1. **Create unit tests** in `tests/unit/test_summary_report.py`:

   ```python
   import pytest
   from mcp_eval.summary_models import *
   from mcp_eval.html_reporter import generate_summary_report
   from datetime import datetime

   def test_scenario_summary_validation():
       """Test ScenarioExecutionSummary validates fields correctly."""
       # Valid summary
       summary = ScenarioExecutionSummary(
           scenario_name="test",
           scenario_path="tool_management/test",
           user_intent="Test intent",
           status=ScenarioStatus.PASSED,
           tool_count=5,
           duration_seconds=10.5,
           detailed_report_path="test_baseline.html",
           similarity_score=0.95
       )
       assert summary.tool_count == 5

       # Invalid tool_count (negative)
       with pytest.raises(ValidationError):
           ScenarioExecutionSummary(
               scenario_name="test",
               scenario_path="test",
               user_intent="",
               status=ScenarioStatus.PASSED,
               tool_count=-1,  # Invalid
               duration_seconds=10.0,
               detailed_report_path="test.html"
           )

   def test_summary_html_generation():
       """Test generate_summary_report produces valid HTML."""
       summary = ScenarioExecutionSummary(...)  # Create test data
       test_run = TestRunSummary(...)

       html = generate_summary_report(test_run)

       assert "<!DOCTYPE html>" in html
       assert "<title>" in html
       assert "PASSED" in html or "FAILED" in html  # Status badge present
       assert "test_baseline.html" in html  # Link present

   def test_intent_truncation():
       """Test long intents are truncated in HTML."""
       long_intent = "A" * 100  # 100 char intent
       summary = ScenarioExecutionSummary(
           ...,
           user_intent=long_intent,
           ...
       )
       test_run = TestRunSummary(scenario_summaries=[summary], ...)

       html = generate_summary_report(test_run)
       assert long_intent[:60] + "..." in html  # Truncated
       assert f'title="{long_intent}"' in html  # Full text in tooltip
   ```

2. **Run unit tests**:
   ```bash
   uv run pytest tests/unit/test_summary_report.py -v
   ```

3. **Manual integration test**:
   ```bash
   # Run test command with multiple scenarios
   source .env && uv run mcp-eval test --scenarios-dir scenarios/tool_management/

   # Check summary report generated
   ls -lh reports/test_summary_*.html

   # Open in browser
   open reports/test_summary_$(ls -t reports/test_summary_*.html | head -1 | sed 's/.*test_summary_//' | sed 's/.html//')*.html
   ```

4. **Validation checklist**:
   - [ ] Summary HTML file exists in `reports/` directory
   - [ ] File size reasonable (<500KB for 10-20 scenarios)
   - [ ] Opens in browser without errors
   - [ ] Header shows correct total counts
   - [ ] Table has one row per scenario
   - [ ] All status colors display correctly (green/red/blue/yellow)
   - [ ] Clicking scenario name opens detailed report
   - [ ] Intents >60 chars show tooltip on hover
   - [ ] Duration and similarity score formatted correctly

### Phase 5: Documentation (15 minutes)

1. **Update `CLAUDE.md`**:
   - [ ] Add summary report section to "Output Files" documentation
   - [ ] Document new file naming pattern: `test_summary_TIMESTAMP.html`
   - [ ] Explain summary report structure and contents

2. **Update CLI help text**:
   ```python
   @click.command()
   @click.option("--scenarios-dir", ...)
   def test(scenarios_dir):
       """
       Run test scenarios and generate reports.

       Generates:
       - Individual HTML reports for each scenario
       - Aggregated summary report listing all scenarios
       """
   ```

3. **Add example to README** (if exists):
   ```markdown
   ## Multi-Scenario Testing

   Run all scenarios and get a summary report:

   ```bash
   mcp-eval test --scenarios-dir scenarios/
   ```

   This generates:
   - `reports/test_summary_TIMESTAMP.html` - Summary dashboard
   - Individual detailed reports for each scenario
   ```

## Common Issues & Solutions

### Issue: Pydantic validation errors

**Symptom**: `ValidationError` when creating `TestRunSummary`

**Solution**: Verify count arithmetic:
```python
# Counts must sum to total
assert passed + failed + recorded + error == total_scenarios
assert len(scenario_summaries) == total_scenarios
```

### Issue: Relative links broken

**Symptom**: Clicking scenario names shows "File not found"

**Solution**: Use filename only, not full path:
```python
# Correct
detailed_report_path=Path(report_path).name

# Wrong
detailed_report_path=str(report_path)  # Absolute path breaks portability
```

### Issue: Status colors not showing

**Symptom**: Status badges all same color

**Solution**: Check CSS class names match exactly:
```python
# HTML must use: status-passed, status-failed (lowercase)
# CSS must define: .status-passed { background-color: #28a745; }
```

### Issue: Summary report not generated

**Symptom**: Test runs complete but no summary HTML file

**Solution**: Check console output for errors, verify `reports/` directory exists:
```bash
mkdir -p reports/
```

## Next Steps

After P1/P2 implementation:

1. **Test with large scenario sets**: Run with 50+ scenarios, verify performance
2. **Cross-browser testing**: Open in Chrome, Firefox, Safari
3. **Code review**: Submit PR for review
4. **P3 implementation (optional)**: Add JavaScript filtering/sorting

## Getting Help

- Check existing `html_reporter.py` code for patterns
- Review `data-model.md` for Pydantic model examples
- See `contracts/summary-report-html.md` for HTML structure requirements
- Run `uv run mcp-eval --help` to verify CLI changes integrated
