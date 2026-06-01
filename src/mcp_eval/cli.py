"""Command-line interface for MCP Evaluation Utility."""

import click
import yaml
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from dotenv import load_dotenv

from .scenario_runner import FailureAwareScenarioRunner
from .evaluator import TrajectoryEvaluator
from .reporter import ReportGenerator
from .html_reporter import HTMLReporter, generate_summary_report
from .summary_models import ScenarioExecutionSummary, ScenarioStatus, TestRunSummary
from .judge import JudgeAgent, save_assessment_json, generate_markdown_report
from .judge.agent import get_api_key

# Load environment variables from .env file
load_dotenv()

console = Console()


def get_scenario_relative_path(scenario_file: Path) -> Path:
    """Get the relative path of a scenario file from the scenarios directory."""
    try:
        # Try to find the scenarios directory in the path
        parts = scenario_file.parts
        if 'scenarios' in parts:
            scenarios_idx = parts.index('scenarios')
            # Get the path from scenarios directory to the parent directory of the file
            rel_parts = parts[scenarios_idx + 1:-1]  # Exclude 'scenarios' and filename
            return Path(*rel_parts) if rel_parts else Path('.')
        else:
            # If no scenarios directory found, just return current directory
            return Path('.')
    except (ValueError, IndexError):
        return Path('.')


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """MCP Evaluation Utility - Evaluate MCP server effectiveness."""
    pass


# Spec 065 D1 (evaluation foundation): datasets tooling + retrieval scorer.
from .datasets.commands import datasets as _datasets_group  # noqa: E402
from .retrieval.commands import retrieval_cmd as _retrieval_cmd  # noqa: E402

# Spec 065 D2 (evaluation foundation): security-detector scorer.
from .security.commands import security_cmd as _security_cmd  # noqa: E402

cli.add_command(_datasets_group)
cli.add_command(_retrieval_cmd)
cli.add_command(_security_cmd)


@cli.command()
@click.option(
    "--scenario", 
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to scenario YAML file"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path), 
    required=False,
    help="Output directory for results (default: baselines/{scenario_name}_baseline)"
)
@click.option(
    "--mcp-config",
    type=click.Path(exists=True, path_type=Path),
    default="mcp_servers.json",
    help="MCP server configuration file"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.option(
    "--judge",
    is_flag=True,
    help="Analyze baseline immediately after recording"
)
def record(scenario: Path, output: Path, mcp_config: Path, verbose: bool, judge: bool):
    """Record a scenario execution with detailed logs."""
    console.print(f"🎬 [bold blue]Recording scenario:[/bold blue] {scenario.name}")
    
    # Generate default output path if not provided
    if output is None:
        scenario_name = scenario.stem
        # Calculate relative path from scenarios dir to preserve subdirectory structure
        scenario_rel_path = get_scenario_relative_path(scenario)
        output = Path("baselines") / scenario_rel_path / f"{scenario_name}_baseline"
        console.print(f"📂 Using default output: {output}")
    
    # Create output directory
    output.mkdir(parents=True, exist_ok=True)
    
    async def record_async_inner():
        """Inner async function to execute scenario."""
        # Create scenario runner with git info capture
        runner = FailureAwareScenarioRunner(output_dir=output, mcp_config=str(mcp_config))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Executing scenario...", total=None)
            
            try:
                success, execution_data = await runner.execute_scenario(scenario, mode="baseline")
                progress.update(task, description="Scenario completed ✅")
                
                # Save results
                runner.save_execution_results(execution_data, scenario.stem, "baseline")
                
                # Generate HTML report  
                html_reporter = HTMLReporter()
                html_report_path = html_reporter.generate_baseline_report(execution_data, scenario.stem)
                
                console.print(f"📊 [green]HTML report generated:[/green] {html_report_path}")
                
                return execution_data
                
            except Exception as e:
                progress.update(task, description=f"Scenario failed ❌: {e}")
                raise click.ClickException(f"Scenario execution failed: {e}")
    
    # Run async function
    import asyncio
    try:
        result = asyncio.run(record_async_inner())
        console.print("✅ [green]Recording completed successfully[/green]")

        # Run judge analysis if requested
        if judge and get_api_key():
            console.print("\n🔍 [bold blue]Running judge analysis on baseline...[/bold blue]")
            try:
                agent = JudgeAgent(verbose=verbose)
                assessment = agent.analyze_baseline(output)
                if assessment:
                    json_path = save_assessment_json(assessment)
                    md_path = generate_markdown_report(assessment)
                    console.print(f"📁 [green]JSON assessment:[/green] {json_path}")
                    console.print(f"📄 [green]Markdown report:[/green] {md_path}")
                    if assessment.improvement_suggestions:
                        console.print(f"💡 [yellow]Found {len(assessment.improvement_suggestions)} improvement suggestions[/yellow]")
                    else:
                        console.print("[green]Trajectory appears optimal - no suggestions generated[/green]")
            except Exception as e:
                console.print(f"[red]Judge analysis failed: {e}[/red]")
        elif judge and not get_api_key():
            console.print("[yellow]Warning: --judge flag specified but no API key set (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN)[/yellow]")

        return result
    except Exception as e:
        console.print(f"❌ [red]Recording failed: {e}[/red]")
        raise


@cli.command()
@click.option(
    "--scenario", 
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to scenario YAML file"
)
@click.option(
    "--baseline",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to baseline results directory"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=False,
    help="Output file for comparison report (default: comparison_results/{scenario_name}_comparison)"
)
@click.option(
    "--mcp-config",
    type=click.Path(exists=True, path_type=Path),
    default="mcp_servers.json",
    help="MCP server configuration file"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
def compare(scenario: Path, baseline: Path, output: Path, mcp_config: Path, verbose: bool):
    """Compare scenario execution against baseline."""
    
    # Generate default output path if not provided
    if output is None:
        scenario_name = scenario.stem
        # Calculate relative path from scenarios dir to preserve subdirectory structure
        scenario_rel_path = get_scenario_relative_path(scenario)
        output = Path("comparison_results") / scenario_rel_path / f"{scenario_name}_comparison.json"
        console.print(f"📂 Using default output: {output}")
    console.print(f"🔍 [bold blue]Comparing scenario:[/bold blue] {scenario.name}")
    
    # Load scenario
    with open(scenario) as f:
        scenario_data = yaml.safe_load(f)
    
    # Load baseline
    baseline_detailed = baseline / "detailed_log.json"
    baseline_trajectory = baseline / "trajectory.txt"
    
    if not baseline_detailed.exists() or not baseline_trajectory.exists():
        raise click.ClickException(f"Baseline files not found in {baseline}")
    
    with open(baseline_detailed) as f:
        baseline_data = json.load(f)
    
    # Execute current scenario using same runner as baseline
    from .scenario_runner import FailureAwareScenarioRunner
    import asyncio
    
    async def execute_current_scenario():
        runner = FailureAwareScenarioRunner(output_dir=Path("temp_comparison"), mcp_config=str(mcp_config))
        success, execution_data = await runner.execute_scenario(scenario, mode="evaluation")
        return success, execution_data
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Executing scenario...", total=None)
        
        try:
            success, execution_data = asyncio.run(execute_current_scenario())
            progress.update(task, description="Evaluating trajectory...")
            
            # Compare trajectories - convert execution_data to ScenarioResult format for compatibility
            from .reporter import ScenarioResult
            current_result = ScenarioResult(
                scenario_name=execution_data.get("scenario", "unknown"),
                success=success,
                execution_time=0.0,  # Not used in comparison
                detailed_log=execution_data,
                dialog_trajectory="",  # Not used in comparison
                tool_calls=execution_data.get("tool_calls_summary", []),  # Use raw tool calls
                error=None if success else "Execution failed"
            )
            
            evaluator = TrajectoryEvaluator()
            comparison_result = evaluator.compare_executions(
                execution_data, 
                baseline_data
            )
            
            progress.update(task, description="Comparison completed ✅")
            
        except Exception as e:
            progress.update(task, description=f"Comparison failed ❌: {e}")
            raise click.ClickException(f"Comparison failed: {e}")
    
    # Generate reports
    reporter = ReportGenerator()
    report = reporter.generate_comparison_report(
        scenario_data, current_result, baseline_data, comparison_result
    )
    
    # Save JSON report
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Generate HTML comparison report
    from dataclasses import asdict
    from .html_reporter import HTMLReporter
    html_reporter = HTMLReporter()
    
    # Current execution data is already in the right format from FailureAwareScenarioRunner
    current_data_for_html = execution_data
    
    html_report_path = html_reporter.generate_comparison_report(
        current_data_for_html, baseline_data, report, scenario.stem
    )
    console.print(f"📊 [green]HTML comparison report generated:[/green] {html_report_path}")
    
    # Display summary
    score = comparison_result.overall_score
    status = "✅ PASS" if score >= 0.8 else "❌ FAIL"
    
    table = Table(title="Evaluation Results")
    table.add_column("Metric", style="bold")
    table.add_column("Score", style="cyan")
    table.add_column("Status")
    
    table.add_row("Tool Trajectory Score", f"{score:.2f}", status)
    table.add_row("Invocations Matched", f"{len([r for r in comparison_result.per_invocation_results if r.score == 1.0])}/{len(comparison_result.per_invocation_results)}", "")
    
    console.print(table)
    console.print(f"📊 [bold green]Report saved to:[/bold green] {output}")


@cli.command()
@click.option(
    "--scenarios",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Directory containing scenario YAML files"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True,
    help="Output directory for batch results"
)
@click.option(
    "--mcp-config",
    type=click.Path(exists=True, path_type=Path),
    default="mcp_servers.json",
    help="MCP server configuration file"
)
@click.option(
    "--parallel", "-p",
    is_flag=True,
    help="Run scenarios in parallel"
)
def batch(scenarios: Path, output: Path, mcp_config: Path, parallel: bool):
    """Run multiple scenarios in batch mode.

    Generates:
    - Individual baseline reports for each scenario
    - Aggregated summary report listing all scenarios
    """
    # Initialize summary report data collection
    run_start_time = datetime.now()
    scenario_summaries: List[ScenarioExecutionSummary] = []

    console.print(f"🚀 [bold blue]Running batch evaluation:[/bold blue] {scenarios}")

    # Find all scenario files recursively
    scenario_files = list(scenarios.rglob("*.yaml")) + list(scenarios.rglob("*.yml"))

    if not scenario_files:
        raise click.ClickException(f"No scenario files found in {scenarios}")

    console.print(f"Found {len(scenario_files)} scenarios to evaluate")

    # Create output directory
    output.mkdir(parents=True, exist_ok=True)

    async def batch_async():
        results = []
        
        with Progress(console=console) as progress:
            task = progress.add_task("Processing scenarios...", total=len(scenario_files))
            
            for scenario_file in scenario_files:
                scenario_name = scenario_file.stem
                scenario_output = output / scenario_name

                try:
                    # Load and execute scenario
                    with open(scenario_file) as f:
                        scenario_data = yaml.safe_load(f)

                    start_time = time.time()
                    runner = FailureAwareScenarioRunner(output_dir=scenario_output, mcp_config=str(mcp_config))
                    success, execution_data = await runner.execute_scenario(scenario_file, mode="baseline")
                    duration = time.time() - start_time

                    # Save individual results using FailureAwareScenarioRunner
                    runner.save_execution_results(execution_data, scenario_name, "baseline")

                    # Generate HTML baseline report
                    html_reporter = HTMLReporter()
                    html_report_path = html_reporter.generate_baseline_report(execution_data, scenario_name)

                    # Count MCP tools used
                    tool_count = len([t for t in execution_data.get("tool_calls_summary", [])
                                     if t.get("tool_name", "").startswith("mcp__")])

                    # Get relative scenario path
                    scenario_rel_path = get_scenario_relative_path(scenario_file)

                    # Create scenario summary
                    scenario_summary = ScenarioExecutionSummary(
                        scenario_name=scenario_name,
                        scenario_path=str(scenario_rel_path),
                        user_intent=scenario_data.get("user_intent", ""),
                        status=ScenarioStatus.RECORDED if success else ScenarioStatus.ERROR,
                        tool_count=tool_count,
                        duration_seconds=duration,
                        detailed_report_path=Path(html_report_path).name,
                        similarity_score=None
                    )
                    scenario_summaries.append(scenario_summary)

                    results.append({
                        "scenario": scenario_name,
                        "status": "SUCCESS" if success else "FAILED",
                        "execution_time": duration,
                        "tool_calls": tool_count,
                        "output_dir": str(scenario_output)
                    })

                except Exception as e:
                    console.print(f"❌ Failed: {scenario_name} - {e}")

                    # Create error scenario summary
                    scenario_rel_path = get_scenario_relative_path(scenario_file)
                    scenario_summary = ScenarioExecutionSummary(
                        scenario_name=scenario_name,
                        scenario_path=str(scenario_rel_path),
                        user_intent="",
                        status=ScenarioStatus.ERROR,
                        tool_count=0,
                        duration_seconds=0.0,
                        detailed_report_path=f"{scenario_name}_error.html",
                        similarity_score=None
                    )
                    scenario_summaries.append(scenario_summary)

                    results.append({
                        "scenario": scenario_name,
                        "status": "FAILED",
                        "error": str(e),
                        "output_dir": None
                    })

                progress.advance(task)
        
        return results
    
    # Run async batch processing
    import asyncio
    results = asyncio.run(batch_async())
    
    # Generate summary report
    reporter = ReportGenerator()
    summary_report = reporter.generate_batch_report(results)
    
    with open(output / "batch_summary.json", 'w') as f:
        json.dump(summary_report, f, indent=2, default=str)
    
    # Display summary
    success_count = len([r for r in results if r["status"] == "SUCCESS"])

    table = Table(title="Batch Evaluation Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Total Scenarios", str(len(results)))
    table.add_row("Successful", str(success_count))
    table.add_row("Failed", str(len(results) - success_count))
    table.add_row("Success Rate", f"{success_count/len(results)*100:.1f}%")

    console.print(table)
    console.print(f"📊 [bold green]Batch results saved to:[/bold green] {output}")

    # Generate aggregated summary report
    if scenario_summaries:
        # Count status types
        recorded_count = len([s for s in scenario_summaries if s.status == ScenarioStatus.RECORDED])
        error_count = len([s for s in scenario_summaries if s.status == ScenarioStatus.ERROR])

        test_run = TestRunSummary(
            test_run_timestamp=run_start_time,
            total_scenarios=len(scenario_summaries),
            passed_count=0,  # Batch mode doesn't do comparisons
            failed_count=0,
            recorded_count=recorded_count,
            error_count=error_count,
            scenario_summaries=scenario_summaries,
            mcp_config_path=str(mcp_config) if mcp_config else None,
            git_hash=get_git_hash()
        )

        summary_html = generate_summary_report(test_run)
        timestamp_str = run_start_time.strftime("%Y%m%d_%H%M%S")
        summary_path = Path("reports") / f"batch_summary_{timestamp_str}.html"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary_html, encoding="utf-8")

        console.print(f"\n📊 [green]Summary report:[/green] {summary_path}")


def get_git_hash() -> Optional[str]:
    """Get current git commit hash (8 characters) or None if not in git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


@cli.command()
@click.option(
    "--scenarios-dir",
    type=click.Path(exists=True, path_type=Path),
    default="scenarios",
    help="Directory containing scenario YAML files (recursively searched)"
)
@click.option(
    "--tag", "-t",
    multiple=True,
    help="Filter scenarios by tag (can be used multiple times)"
)
@click.option(
    "--scenario", "-s",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Run specific scenario file(s)"
)
@click.option(
    "--mcp-config",
    type=click.Path(exists=True, path_type=Path),
    default="mcp_servers.json",
    help="MCP server configuration file"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.option(
    "--fail-fast", "-x",
    is_flag=True,
    help="Stop on first failure"
)
@click.option(
    "--compact-report", "-c",
    is_flag=True,
    help="Generate compact text summary report (FR-027, FR-028)"
)
@click.option(
    "--judge-on-fail",
    is_flag=True,
    help="Run judge analysis on failed scenarios"
)
@click.option(
    "--judge-summary",
    is_flag=True,
    help="Generate consolidated judge summary after all tests"
)
def test(scenarios_dir: Path, tag: tuple, scenario: tuple, mcp_config: Path, verbose: bool, fail_fast: bool, compact_report: bool, judge_on_fail: bool, judge_summary: bool):
    """Run MCP evaluation scenarios in pytest-style with compact output.

    Generates:
    - Individual HTML reports for each scenario
    - Aggregated summary report listing all scenarios
    """

    # Initialize summary report data collection
    run_start_time = datetime.now()
    scenario_summaries: List[ScenarioExecutionSummary] = []

    # Restart MCPProxy to ensure clean state
    console.print("🔄 [yellow]Restarting MCPProxy for clean state...[/yellow]")
    restart_mcpproxy()

    # Collect scenarios to run
    scenarios_to_run = []
    
    if scenario:
        # Run specific scenario files
        scenarios_to_run = list(scenario)
    else:
        # Find all scenarios in directory recursively and filter by tags
        all_scenarios = list(scenarios_dir.rglob("*.yaml")) + list(scenarios_dir.rglob("*.yml"))
        
        for scenario_file in all_scenarios:
            try:
                with open(scenario_file) as f:
                    scenario_data = yaml.safe_load(f)
                
                # Check if scenario is enabled
                if not scenario_data.get("enabled", True):
                    continue
                
                # Filter by tags if specified
                if tag:
                    scenario_tags = scenario_data.get("tags", [])
                    if not any(t in scenario_tags for t in tag):
                        continue
                
                scenarios_to_run.append(scenario_file)
                
            except Exception as e:
                if verbose:
                    console.print(f"❌ [red]Failed to load {scenario_file.name}: {e}[/red]")
                continue
    
    if not scenarios_to_run:
        console.print("[red]No scenarios found to run[/red]")
        return
    
    console.print(f"\n🧪 [bold]Running {len(scenarios_to_run)} scenarios[/bold]")
    if tag:
        console.print(f"   [dim]Filtered by tags: {', '.join(tag)}[/dim]")
    console.print()
    
    # Run scenarios with compact output
    results = []
    failed_count = 0
    
    for i, scenario_file in enumerate(scenarios_to_run, 1):
        scenario_name = scenario_file.stem
        
        # Load scenario to get expected trajectory for comparison
        try:
            with open(scenario_file) as f:
                scenario_data = yaml.safe_load(f)
        except Exception as e:
            console.print(f"{scenario_name:<30} [red]LOAD_ERROR[/red]  - Failed to load scenario")
            failed_count += 1
            if fail_fast:
                break
            continue
        
        # Check if baseline exists for comparison
        scenario_rel_path = get_scenario_relative_path(scenario_file)
        baseline_dir = Path("baselines") / scenario_rel_path / f"{scenario_name}_baseline"
        has_baseline = baseline_dir.exists() and (baseline_dir / "detailed_log.json").exists()
        
        if has_baseline:
            # Run comparison mode
            status, score, metadata = run_scenario_with_comparison(scenario_file, baseline_dir, mcp_config, verbose)
        else:
            # Run baseline recording mode
            status, score, metadata = run_scenario_baseline(scenario_file, mcp_config, verbose)

        # Format status with colors
        status_text = Text()
        if status == "PASS":
            status_text.append("PASS", style="green bold")
        elif status == "FAIL":
            status_text.append("FAIL", style="red bold")
        elif status == "ERROR":
            status_text.append("ERROR", style="red bold")
        elif status == "RECORDED":
            status_text.append("RECORDED", style="blue bold")
        else:
            status_text.append(status, style="yellow bold")

        # Display compact result
        score_str = f"{score:.2f}" if score is not None else "N/A"
        console.print(f"{scenario_name:<30} {status_text} {score_str:>6}")

        results.append({
            "scenario": scenario_name,
            "status": status,
            "score": score
        })

        # Collect scenario summary for aggregated report
        # Map status strings to ScenarioStatus enum
        status_map = {
            "PASS": ScenarioStatus.PASSED,
            "FAIL": ScenarioStatus.FAILED,
            "ERROR": ScenarioStatus.ERROR,
            "RECORDED": ScenarioStatus.RECORDED
        }

        # Get relative path to HTML report (just filename for portability)
        html_report_path = None
        if metadata.get("html_report_path"):
            html_report_path = Path(metadata["html_report_path"]).name

        scenario_summary = ScenarioExecutionSummary(
            scenario_name=scenario_name,
            scenario_path=str(scenario_rel_path),
            user_intent=scenario_data.get("user_intent", ""),
            status=status_map.get(status, ScenarioStatus.ERROR),
            tool_count=metadata.get("tool_count", 0),
            duration_seconds=metadata.get("duration_seconds", 0.0),
            detailed_report_path=html_report_path or f"{scenario_name}_report.html",
            similarity_score=score
        )
        scenario_summaries.append(scenario_summary)
        
        # Run judge analysis on failures if requested
        if judge_on_fail and status == "FAIL" and get_api_key():
            console.print(f"   [dim]Running judge analysis...[/dim]")
            try:
                agent = JudgeAgent(verbose=verbose)
                # Find the comparison report for this scenario
                comp_file = Path("comparison_results") / scenario_rel_path / f"{scenario_name}_comparison.json"
                if comp_file.exists():
                    assessment = agent.analyze_comparison(comp_file)
                    if assessment and assessment.improvement_suggestions:
                        console.print(f"   [yellow]Judge: {len(assessment.improvement_suggestions)} suggestions[/yellow]")
                        # Save assessment
                        save_assessment_json(assessment)
            except Exception as e:
                if verbose:
                    console.print(f"   [dim red]Judge error: {e}[/dim red]")

        if status in ["FAIL", "ERROR"]:
            failed_count += 1
            if fail_fast:
                break

    # Print summary
    console.print()

    # Calculate counts from scenario_summaries for consistency
    passed = len([s for s in scenario_summaries if s.status == ScenarioStatus.PASSED])
    failed = len([s for s in scenario_summaries if s.status == ScenarioStatus.FAILED])
    recorded = len([s for s in scenario_summaries if s.status == ScenarioStatus.RECORDED])
    error = len([s for s in scenario_summaries if s.status == ScenarioStatus.ERROR])

    summary_text = Text()
    if failed == 0 and error == 0:
        summary_text.append("✅ ", style="green")
    else:
        summary_text.append("❌ ", style="red")

    summary_text.append(f"{passed} passed", style="green" if passed > 0 else "dim")
    if recorded > 0:
        summary_text.append(f", {recorded} recorded", style="blue")
    if failed > 0:
        summary_text.append(f", {failed} failed", style="red")
    if error > 0:
        summary_text.append(f", {error} error", style="yellow")

    console.print(summary_text)

    # Generate aggregated summary report
    if scenario_summaries:
        test_run = TestRunSummary(
            test_run_timestamp=run_start_time,
            total_scenarios=len(scenario_summaries),
            passed_count=passed,
            failed_count=failed,
            recorded_count=recorded,
            error_count=error,
            scenario_summaries=scenario_summaries,
            mcp_config_path=str(mcp_config) if mcp_config else None,
            git_hash=get_git_hash()
        )

        summary_html = generate_summary_report(test_run)
        timestamp_str = run_start_time.strftime("%Y%m%d_%H%M%S")
        summary_path = Path("reports") / f"test_summary_{timestamp_str}.html"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary_html, encoding="utf-8")

        console.print(f"\n📊 [green]Summary report:[/green] {summary_path}")

        # Generate compact text summary if requested (FR-027, FR-028)
        if compact_report:
            from .summary_models import CompactSummary, ToolSummary

            compact_lines = [
                f"# Test Summary: {len(results)} scenarios",
                f"Status: {len([r for r in results if r.get('status') == 'PASS'])} PASSED | "
                f"{len([r for r in results if r.get('status') == 'FAIL'])} FAILED | "
                f"{len([r for r in results if r.get('status') == 'RECORDED'])} RECORDED",
                "",
            ]

            for result in results:
                compact_lines.append(f"- {result.get('scenario', 'unknown')}: {result.get('status', 'UNKNOWN')}")
                if result.get('score') is not None:
                    compact_lines.append(f"  Score: {result.get('score', 0):.2f}")

            compact_text = "\n".join(compact_lines)
            compact_path = Path("reports") / "summary.txt"
            compact_path.write_text(compact_text, encoding="utf-8")
            console.print(f"📄 [green]Compact summary:[/green] {compact_path}")

        # Generate judge summary if requested
        if judge_summary and failed > 0 and get_api_key():
            console.print("\n🔍 [bold blue]Generating judge summary for failed scenarios...[/bold blue]")
            judge_assessments = []
            agent = JudgeAgent(verbose=verbose)

            # Analyze all failed scenarios
            failed_scenarios = [s for s in scenario_summaries if s.status == ScenarioStatus.FAILED]
            for scenario_summary in failed_scenarios:
                comp_file = Path("comparison_results") / scenario_summary.scenario_path / f"{scenario_summary.scenario_name}_comparison.json"
                if comp_file.exists():
                    try:
                        assessment = agent.analyze_comparison(comp_file)
                        if assessment:
                            judge_assessments.append(assessment)
                            save_assessment_json(assessment)
                    except Exception as e:
                        if verbose:
                            console.print(f"   [dim red]Judge error for {scenario_summary.scenario_name}: {e}[/dim red]")

            if judge_assessments:
                from .judge.reporter import generate_batch_summary_markdown
                batch_md = generate_batch_summary_markdown(judge_assessments)
                console.print(f"📊 [green]Judge summary:[/green] {batch_md}")
                _display_judge_summary(judge_assessments)


def restart_mcpproxy():
    """Restart MCPProxy Docker container for clean state with build check."""
    try:
        # Check if mcpproxy binary needs to be rebuilt
        _check_and_rebuild_mcpproxy()
        
        # Use existing restart script
        script_path = Path(__file__).parent.parent.parent / "testing" / "restart-mcpproxy.sh"
        if script_path.exists():
            subprocess.run([str(script_path)], check=True, capture_output=True)
        else:
            # Fallback to basic docker commands
            subprocess.run(["docker", "compose", "down"], cwd="testing", capture_output=True)
            subprocess.run(["docker", "compose", "up", "-d"], cwd="testing", capture_output=True)
        
        # Wait a moment for startup
        time.sleep(2)
    except Exception:
        # Non-critical if restart fails - scenarios might still work
        pass


def _check_and_rebuild_mcpproxy():
    """Check if mcpproxy source has been updated and rebuild if necessary."""
    try:
        import os
        
        # Get mcpproxy source path
        mcpproxy_source = os.getenv("MCPPROXY_SOURCE_PATH", "../mcpproxy-go")
        mcpproxy_path = Path(mcpproxy_source).expanduser().resolve()
        
        if not mcpproxy_path.exists():
            console.print(f"[yellow]Warning: MCPProxy source not found at {mcpproxy_path}[/yellow]")
            return
            
        # Check if binary exists
        binary_path = mcpproxy_path / "mcpproxy"
        
        # Get current git hash from source (8 characters for consistency)
        try:
            current_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=mcpproxy_path,
                text=True
            ).strip()[:8]
        except subprocess.CalledProcessError:
            console.print("[yellow]Warning: Could not get git hash from MCPProxy source[/yellow]")
            return
            
        # Check if we have a cached build hash
        build_info_file = mcpproxy_path / "build-info.json"
        cached_hash = None
        
        if build_info_file.exists():
            try:
                with open(build_info_file) as f:
                    build_info = json.load(f)
                    cached_hash_raw = build_info.get("commit", "")
                    # Normalize to 8 characters for consistent comparison
                    cached_hash = cached_hash_raw[:8] if cached_hash_raw and cached_hash_raw != "unknown" else cached_hash_raw
            except (json.JSONDecodeError, IOError):
                pass
        
        # Determine if rebuild is needed
        needs_rebuild = False
        rebuild_reason = ""
        
        if not binary_path.exists():
            needs_rebuild = True
            rebuild_reason = "Binary not found"
        elif cached_hash != current_hash:
            needs_rebuild = True
            rebuild_reason = f"Source updated ({cached_hash if cached_hash else 'unknown'} → {current_hash})"
        else:
            # Check if any Go source files are newer than binary
            go_files = list(mcpproxy_path.glob("**/*.go"))
            if go_files:
                binary_mtime = binary_path.stat().st_mtime
                newer_files = [f for f in go_files if f.stat().st_mtime > binary_mtime]
                if newer_files:
                    needs_rebuild = True
                    rebuild_reason = f"Source files modified ({len(newer_files)} files newer than binary)"
        
        if needs_rebuild:
            console.print(f"[yellow]🔨 MCPProxy rebuild needed: {rebuild_reason}[/yellow]")
            
            # Run the build script
            build_script = Path(__file__).parent.parent.parent / "testing" / "build-mcpproxy.sh"
            if build_script.exists():
                console.print("[blue]🏗️  Building MCPProxy binary...[/blue]")
                result = subprocess.run(
                    ["bash", str(build_script)], 
                    cwd=mcpproxy_path,
                    env=dict(os.environ, **{
                        "MCPPROXY_SOURCE": str(mcpproxy_path),
                        "BUILD_FORCE": "false",  # Let the script decide
                        "BUILD_CACHE": "true"
                    }),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    console.print("[green]✅ MCPProxy binary built successfully[/green]")
                else:
                    console.print(f"[red]❌ MCPProxy build failed: {result.stderr}[/red]")
            else:
                console.print(f"[yellow]Warning: Build script not found at {build_script}[/yellow]")
        else:
            console.print("[green]✅ MCPProxy binary is up to date[/green]")
            
    except Exception as e:
        console.print(f"[yellow]Warning: Could not check MCPProxy build status: {e}[/yellow]")


def run_scenario_with_comparison(scenario_file: Path, baseline_dir: Path, mcp_config: Path, verbose: bool) -> tuple[str, Optional[float], dict]:
    """Run scenario and compare against baseline.

    Returns:
        tuple: (status, score, metadata_dict) where metadata_dict contains:
            - execution_data: full execution data from runner
            - html_report_path: path to generated HTML report
            - tool_count: number of MCP tools invoked
            - duration_seconds: execution time
    """
    try:
        import asyncio
        import time

        # Load baseline data
        baseline_detailed = baseline_dir / "detailed_log.json"
        with open(baseline_detailed) as f:
            baseline_data = json.load(f)

        # Execute current scenario
        async def execute_scenario():
            runner = FailureAwareScenarioRunner(output_dir=Path("temp_comparison"), mcp_config=str(mcp_config))
            start_time = time.time()
            success, execution_data = await runner.execute_scenario(scenario_file, mode="evaluation")
            duration = time.time() - start_time
            return success, execution_data, duration

        success, execution_data, duration = asyncio.run(execute_scenario())

        if not success:
            return "FAIL", 0.0, {
                "execution_data": execution_data,
                "html_report_path": None,
                "tool_count": 0,
                "duration_seconds": duration
            }
        
        # Compare trajectories
        evaluator = TrajectoryEvaluator()
        comparison_result = evaluator.compare_executions(execution_data, baseline_data)
        
        score = comparison_result.overall_score
        status = "PASS" if score >= 0.8 else "FAIL"
        
        # Generate HTML comparison report for test command
        scenario_name = scenario_file.stem
        scenario_rel_path = get_scenario_relative_path(scenario_file)
        comparison_results_dir = Path("comparison_results") / scenario_rel_path
        comparison_results_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate JSON comparison report
        from .reporter import ReportGenerator, ScenarioResult
        reporter = ReportGenerator()
        
        # Load scenario data for report
        with open(scenario_file) as f:
            scenario_data = yaml.safe_load(f)
        
        current_result = ScenarioResult(
            scenario_name=execution_data.get("scenario", "unknown"),
            success=success,
            execution_time=0.0,
            detailed_log=execution_data,
            dialog_trajectory="",
            tool_calls=execution_data.get("tool_calls_summary", []),
            error=None if success else "Execution failed"
        )
        
        report = reporter.generate_comparison_report(
            scenario_data, current_result, baseline_data, comparison_result
        )
        
        # Save JSON report with .json extension
        json_report_path = comparison_results_dir / f"{scenario_name}_comparison.json"
        with open(json_report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate HTML comparison report
        html_reporter = HTMLReporter()
        html_report_path = html_reporter.generate_comparison_report(
            execution_data, baseline_data, report, scenario_name
        )

        if verbose:
            console.print(f"   [dim]📊 HTML report: {html_report_path}[/dim]")

        # Count MCP tools used
        tool_count = len([t for t in execution_data.get("tool_calls_summary", [])
                         if t.get("tool_name", "").startswith("mcp__")])

        metadata = {
            "execution_data": execution_data,
            "html_report_path": html_report_path,
            "tool_count": tool_count,
            "duration_seconds": duration
        }

        return status, score, metadata

    except Exception as e:
        if verbose:
            console.print(f"   [red]Error: {e}[/red]")
        return "ERROR", None, {
            "execution_data": {},
            "html_report_path": None,
            "tool_count": 0,
            "duration_seconds": 0.0
        }


def run_scenario_baseline(scenario_file: Path, mcp_config: Path, verbose: bool) -> tuple[str, Optional[float], dict]:
    """Run scenario in baseline recording mode.

    Returns:
        tuple: (status, score, metadata_dict) where metadata_dict contains:
            - execution_data: full execution data from runner
            - html_report_path: path to generated HTML report
            - tool_count: number of MCP tools invoked
            - duration_seconds: execution time
    """
    try:
        import asyncio
        import time

        scenario_name = scenario_file.stem
        scenario_rel_path = get_scenario_relative_path(scenario_file)
        output_dir = Path("baselines") / scenario_rel_path / f"{scenario_name}_baseline"

        async def record_scenario():
            runner = FailureAwareScenarioRunner(output_dir=output_dir, mcp_config=str(mcp_config))
            start_time = time.time()
            success, execution_data = await runner.execute_scenario(scenario_file, mode="baseline")
            duration = time.time() - start_time

            if success:
                runner.save_execution_results(execution_data, scenario_name, "baseline")

            return success, execution_data, duration

        success, execution_data, duration = asyncio.run(record_scenario())

        if success:
            # Generate HTML baseline report
            from .html_reporter import HTMLReporter
            html_reporter = HTMLReporter()
            html_report_path = html_reporter.generate_baseline_report(execution_data, scenario_name)

            if verbose:
                console.print(f"   [dim]📊 HTML baseline report: {html_report_path}[/dim]")

            # Count MCP tools used
            tool_count = len([t for t in execution_data.get("tool_calls_summary", [])
                             if t.get("tool_name", "").startswith("mcp__")])

            metadata = {
                "execution_data": execution_data,
                "html_report_path": html_report_path,
                "tool_count": tool_count,
                "duration_seconds": duration
            }

            return "RECORDED", None, metadata
        else:
            return "ERROR", None, {
                "execution_data": execution_data,
                "html_report_path": None,
                "tool_count": 0,
                "duration_seconds": duration
            }

    except Exception as e:
        if verbose:
            console.print(f"   [red]Error: {e}[/red]")
        return "ERROR", None, {
            "execution_data": {},
            "html_report_path": None,
            "tool_count": 0,
            "duration_seconds": 0.0
        }


@cli.command()
@click.option(
    "--baseline",
    type=click.Path(exists=True, path_type=Path),
    help="Path to baseline directory to analyze"
)
@click.option(
    "--comparison-report",
    type=click.Path(exists=True, path_type=Path),
    help="Path to comparison JSON file to analyze"
)
@click.option(
    "--baselines-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Analyze all baselines in directory"
)
@click.option(
    "--scenarios-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Analyze all comparison reports in directory"
)
@click.option(
    "--threshold",
    type=float,
    default=0.8,
    help="Only analyze scenarios below this score (default: 0.8)"
)
@click.option(
    "--output-format",
    type=click.Choice(["json", "markdown", "both"]),
    default="both",
    help="Output format (default: both)"
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Directory for output files (default: .judge/assessments)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
def judge(
    baseline: Optional[Path],
    comparison_report: Optional[Path],
    baselines_dir: Optional[Path],
    scenarios_dir: Optional[Path],
    threshold: float,
    output_format: str,
    output_dir: Optional[Path],
    verbose: bool
):
    """Analyze baseline or comparison reports and generate improvement suggestions.

    Uses LLM-based analysis to identify why tool usage deviated from expectations
    and suggests specific improvements to tool descriptions.

    Examples:
        # Analyze single baseline
        mcp-eval judge --baseline baselines/search_tools_baseline/

        # Analyze single comparison
        mcp-eval judge --comparison-report comparison_results/search_tools_comparison.json

        # Analyze all baselines
        mcp-eval judge --baselines-dir baselines/

        # Analyze failed comparisons below threshold
        mcp-eval judge --scenarios-dir comparison_results/ --threshold 0.8
    """
    # Validate input - at least one of baseline/comparison/baselines-dir/scenarios-dir required
    if not any([baseline, comparison_report, baselines_dir, scenarios_dir]):
        raise click.ClickException(
            "Must specify --baseline, --comparison-report, --baselines-dir, or --scenarios-dir"
        )

    # Check for API key
    if not get_api_key():
        raise click.ClickException(
            "Error: No API key found. Set ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN in your environment or .env file."
        )

    # Create judge agent
    agent = JudgeAgent(verbose=verbose)

    assessments = []

    # Single baseline analysis
    if baseline:
        console.print(f"🔍 [bold blue]Analyzing baseline:[/bold blue] {baseline}")
        assessment = _run_judge_analysis(agent, "baseline", baseline, verbose)
        if assessment:
            assessments.append(assessment)

    # Single comparison analysis
    if comparison_report:
        console.print(f"🔍 [bold blue]Analyzing comparison:[/bold blue] {comparison_report}")
        assessment = _run_judge_analysis(agent, "comparison", comparison_report, verbose)
        if assessment:
            assessments.append(assessment)

    # Batch baseline analysis
    if baselines_dir:
        console.print(f"🔍 [bold blue]Analyzing baselines in:[/bold blue] {baselines_dir}")
        baseline_dirs = [d for d in baselines_dir.iterdir() if d.is_dir() and (d / "detailed_log.json").exists()]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Analyzing {len(baseline_dirs)} baselines...", total=len(baseline_dirs))

            for baseline_path in baseline_dirs:
                progress.update(task, description=f"Analyzing {baseline_path.name}...")
                assessment = _run_judge_analysis(agent, "baseline", baseline_path, verbose)
                if assessment:
                    assessments.append(assessment)
                progress.advance(task)

    # Batch comparison analysis with threshold filtering
    if scenarios_dir:
        console.print(f"🔍 [bold blue]Analyzing comparisons in:[/bold blue] {scenarios_dir}")
        comparison_files = list(scenarios_dir.rglob("*_comparison.json"))

        # Filter by threshold
        filtered_files = []
        for comp_file in comparison_files:
            try:
                with open(comp_file) as f:
                    comp_data = json.load(f)
                # Score can be at top level or nested in evaluation_metrics
                eval_metrics = comp_data.get("evaluation_metrics", {})
                score = eval_metrics.get("overall_score", comp_data.get("similarity_score", 1.0))
                if score < threshold:
                    filtered_files.append(comp_file)
            except (json.JSONDecodeError, IOError):
                pass

        console.print(f"   Found {len(filtered_files)} scenarios below threshold {threshold}")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Analyzing {len(filtered_files)} comparisons...", total=len(filtered_files))

            for comp_file in filtered_files:
                progress.update(task, description=f"Analyzing {comp_file.stem}...")
                assessment = _run_judge_analysis(agent, "comparison", comp_file, verbose)
                if assessment:
                    assessments.append(assessment)
                progress.advance(task)

    # Save outputs
    if assessments:
        _save_judge_outputs(assessments, output_format, output_dir, verbose)
        _display_judge_summary(assessments)
    else:
        console.print("[yellow]No assessments generated[/yellow]")


def _run_judge_analysis(agent: JudgeAgent, analysis_type: str, path: Path, verbose: bool):
    """Run judge analysis and handle errors.

    Args:
        agent: JudgeAgent instance.
        analysis_type: "baseline" or "comparison".
        path: Path to analyze.
        verbose: Enable verbose output.

    Returns:
        JudgeAssessment or None if failed.
    """
    try:
        if analysis_type == "baseline":
            return agent.analyze_baseline(path)
        else:
            return agent.analyze_comparison(path)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        return None
    except Exception as e:
        if verbose:
            console.print(f"[red]Error analyzing {path}: {e}[/red]")
        else:
            console.print(f"[red]Error: {path.name} - {str(e)[:50]}[/red]")
        return None


def _save_judge_outputs(assessments: list, output_format: str, output_dir: Optional[Path], verbose: bool):
    """Save judge assessment outputs.

    Args:
        assessments: List of JudgeAssessments.
        output_format: "json", "markdown", or "both".
        output_dir: Optional output directory.
        verbose: Enable verbose output.
    """
    from .judge.reporter import generate_batch_summary_markdown

    json_paths = []
    md_paths = []

    for assessment in assessments:
        if output_format in ["json", "both"]:
            json_path = save_assessment_json(assessment, output_dir)
            json_paths.append(json_path)
            if verbose:
                console.print(f"   [dim]JSON: {json_path}[/dim]")

        if output_format in ["markdown", "both"]:
            md_path = generate_markdown_report(assessment)
            md_paths.append(md_path)
            if verbose:
                console.print(f"   [dim]Markdown: {md_path}[/dim]")

    # Generate batch summary if multiple assessments
    if len(assessments) > 1:
        batch_md = generate_batch_summary_markdown(assessments)
        console.print(f"\n📊 [green]Batch summary:[/green] {batch_md}")

    if json_paths:
        console.print(f"📁 [green]JSON outputs:[/green] {json_paths[0].parent}/")
    if md_paths:
        console.print(f"📄 [green]Markdown reports:[/green] {md_paths[0].parent}/")


def _display_judge_summary(assessments: list):
    """Display summary of judge analysis results.

    Args:
        assessments: List of JudgeAssessments.
    """
    from .judge.models import ImprovementPriority

    console.print("\n" + "━" * 50)
    console.print("[bold]Judge Analysis Summary[/bold]")
    console.print("━" * 50)

    # Count suggestions by priority
    priority_counts = {p: 0 for p in ImprovementPriority}
    total_suggestions = 0

    for assessment in assessments:
        for sug in assessment.improvement_suggestions:
            priority_counts[sug.priority] += 1
            total_suggestions += 1

    # Display table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Scenario", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Suggestions", justify="right")
    table.add_column("Duration", justify="right")

    for assessment in assessments:
        score_str = f"{assessment.original_score:.2f}" if assessment.original_score else "N/A"
        sug_counts = {}
        for sug in assessment.improvement_suggestions:
            sug_counts[sug.priority] = sug_counts.get(sug.priority, 0) + 1

        sug_summary = ", ".join([
            f"{count} {p.value.upper()}"
            for p, count in sug_counts.items()
            if count > 0
        ]) or "0"

        table.add_row(
            assessment.scenario_name,
            assessment.analysis_type.value,
            score_str,
            sug_summary,
            f"{assessment.duration_seconds:.1f}s"
        )

    console.print(table)

    # Priority summary
    console.print(f"\n[bold]Total Suggestions:[/bold] {total_suggestions}")
    console.print(f"  🔴 Critical: {priority_counts[ImprovementPriority.CRITICAL]}")
    console.print(f"  🟠 High: {priority_counts[ImprovementPriority.HIGH]}")
    console.print(f"  🟡 Medium: {priority_counts[ImprovementPriority.MEDIUM]}")
    console.print(f"  🟢 Low: {priority_counts[ImprovementPriority.LOW]}")


if __name__ == "__main__":
    cli()