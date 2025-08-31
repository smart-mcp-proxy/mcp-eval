"""Command-line interface for MCP Evaluation Utility."""

import click
import yaml
import json
import os
import subprocess
import time
import traceback
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from .scenario_runner import FailureAwareScenarioRunner
from .evaluator import TrajectoryEvaluator
from .reporter import ReportGenerator
from .html_reporter import HTMLReporter
from .multi_agent_dialog import MultiAgentDialogEngine
from .multi_turn_evaluator import MultiTurnDialogEvaluator

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
def record(scenario: Path, output: Path, mcp_config: Path, verbose: bool):
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
    """Run multiple scenarios in batch mode."""
    console.print(f"🚀 [bold blue]Running batch evaluation:[/bold blue] {scenarios}")
    
    # Find all scenario files
    scenario_files = list(scenarios.glob("*.yaml")) + list(scenarios.glob("*.yml"))
    
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
                    
                    runner = FailureAwareScenarioRunner(output_dir=scenario_output, mcp_config=str(mcp_config))
                    success, execution_data = await runner.execute_scenario(scenario_file, mode="baseline")
                    
                    # Save individual results using FailureAwareScenarioRunner
                    runner.save_execution_results(execution_data, scenario_name, "baseline")
                    
                    results.append({
                        "scenario": scenario_name,
                        "status": "SUCCESS" if success else "FAILED",
                        "execution_time": execution_data.get("execution_time", 0),
                        "tool_calls": len(execution_data.get("tool_calls_summary", [])),
                        "output_dir": str(scenario_output)
                    })
                    
                except Exception as e:
                    console.print(f"❌ Failed: {scenario_name} - {e}")
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
def test(scenarios_dir: Path, tag: tuple, scenario: tuple, mcp_config: Path, verbose: bool, fail_fast: bool):
    """Run MCP evaluation scenarios in pytest-style with compact output."""
    
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
            status, score = run_scenario_with_comparison(scenario_file, baseline_dir, mcp_config, verbose)
        else:
            # Run baseline recording mode
            status, score = run_scenario_baseline(scenario_file, mcp_config, verbose)
        
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
        
        if status in ["FAIL", "ERROR"]:
            failed_count += 1
            if fail_fast:
                break
    
    # Print summary
    console.print()
    passed = len([r for r in results if r["status"] == "PASS"])
    recorded = len([r for r in results if r["status"] == "RECORDED"])
    failed = failed_count
    
    summary_text = Text()
    if failed == 0:
        summary_text.append("✅ ", style="green")
    else:
        summary_text.append("❌ ", style="red")
    
    summary_text.append(f"{passed} passed", style="green" if passed > 0 else "dim")
    if recorded > 0:
        summary_text.append(f", {recorded} recorded", style="blue")
    if failed > 0:
        summary_text.append(f", {failed} failed", style="red")
    
    console.print(summary_text)


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


def run_scenario_with_comparison(scenario_file: Path, baseline_dir: Path, mcp_config: Path, verbose: bool) -> tuple[str, Optional[float]]:
    """Run scenario and compare against baseline."""
    try:
        import asyncio
        
        # Load baseline data
        baseline_detailed = baseline_dir / "detailed_log.json"
        with open(baseline_detailed) as f:
            baseline_data = json.load(f)
        
        # Execute current scenario
        async def execute_scenario():
            runner = FailureAwareScenarioRunner(output_dir=Path("temp_comparison"), mcp_config=str(mcp_config))
            success, execution_data = await runner.execute_scenario(scenario_file, mode="evaluation")
            return success, execution_data
        
        success, execution_data = asyncio.run(execute_scenario())
        
        if not success:
            return "FAIL", 0.0
        
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
        
        return status, score
        
    except Exception as e:
        if verbose:
            console.print(f"   [red]Error: {e}[/red]")
        return "ERROR", None


def run_scenario_baseline(scenario_file: Path, mcp_config: Path, verbose: bool) -> tuple[str, Optional[float]]:
    """Run scenario in baseline recording mode."""
    try:
        import asyncio
        
        scenario_name = scenario_file.stem
        scenario_rel_path = get_scenario_relative_path(scenario_file)
        output_dir = Path("baselines") / scenario_rel_path / f"{scenario_name}_baseline"
        
        async def record_scenario():
            runner = FailureAwareScenarioRunner(output_dir=output_dir, mcp_config=str(mcp_config))
            success, execution_data = await runner.execute_scenario(scenario_file, mode="baseline")
            
            if success:
                runner.save_execution_results(execution_data, scenario_name, "baseline")
            
            return success, execution_data
        
        success, execution_data = asyncio.run(record_scenario())
        
        if success:
            # Generate HTML baseline report
            from .html_reporter import HTMLReporter
            html_reporter = HTMLReporter()
            html_report_path = html_reporter.generate_baseline_report(execution_data, scenario_name)
            
            if verbose:
                console.print(f"   [dim]📊 HTML baseline report: {html_report_path}[/dim]")
                
            return "RECORDED", None
        else:
            return "ERROR", None
            
    except Exception as e:
        if verbose:
            console.print(f"   [red]Error: {e}[/red]")
        return "ERROR", None


@cli.command()
@click.option(
    "--scenario", 
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to multi-turn scenario YAML file"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True, 
    help="Output directory for dialog results"
)
@click.option(
    "--mcp-config",
    type=click.Path(exists=True, path_type=Path),
    default="mcp_servers.json",
    help="Path to MCP servers configuration file"
)
def record_multi_turn(scenario: Path, output: Path, mcp_config: Path):
    """Record a multi-turn dialog baseline between user and agent."""
    import asyncio
    
    console.print(f"🎭 [bold blue]Recording multi-turn dialog: {scenario.name}[/bold blue]")
    
    # Load scenario
    try:
        with open(scenario, 'r') as f:
            scenario_data = yaml.safe_load(f)
    except Exception as e:
        console.print(f"❌ [red]Failed to load scenario: {e}[/red]")
        return
    
    # Check if it's a multi-turn scenario
    if scenario_data.get('type') != 'multi_turn_dialog':
        console.print(f"❌ [red]Scenario is not a multi-turn dialog type[/red]")
        return
    
    async def execute_dialog():
        async with MultiAgentDialogEngine(scenario_data, str(mcp_config), output) as engine:
            results = await engine.execute_multi_turn_dialog()
            return results
    
    try:
        results = asyncio.run(execute_dialog())
        
        if results.get('success'):
            console.print(f"✅ [green]Multi-turn dialog recorded successfully[/green]")
            console.print(f"📊 [blue]Total turns: {results['total_turns']}[/blue]")
            console.print(f"📄 [dim]Results saved to: {output}[/dim]")
        else:
            console.print(f"❌ [red]Dialog recording failed[/red]")
            
    except Exception as e:
        console.print(f"❌ [red]Error executing multi-turn dialog: {e}[/red]")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


@cli.command()
@click.option(
    "--scenario", 
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to multi-turn scenario YAML file"
)
@click.option(
    "--baseline",
    type=click.Path(exists=True, path_type=Path),
    required=True, 
    help="Path to baseline dialog results directory"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    required=True, 
    help="Output directory for comparison results"
)
@click.option(
    "--mcp-config",
    type=click.Path(exists=True, path_type=Path),
    default="mcp_servers.json",
    help="Path to MCP servers configuration file"
)
def compare_multi_turn(scenario: Path, baseline: Path, output: Path, mcp_config: Path):
    """Compare a multi-turn dialog execution with baseline."""
    import asyncio
    
    console.print(f"🔍 [bold blue]Comparing multi-turn dialog: {scenario.name}[/bold blue]")
    
    # Load scenario
    try:
        with open(scenario, 'r') as f:
            scenario_data = yaml.safe_load(f)
    except Exception as e:
        console.print(f"❌ [red]Failed to load scenario: {e}[/red]")
        return
    
    # Check if it's a multi-turn scenario
    if scenario_data.get('type') != 'multi_turn_dialog':
        console.print(f"❌ [red]Scenario is not a multi-turn dialog type[/red]")
        return
    
    # Load baseline
    try:
        baseline_log_path = baseline / "multi_agent_detailed_log.json"
        with open(baseline_log_path, 'r') as f:
            baseline_log = json.load(f)
    except Exception as e:
        console.print(f"❌ [red]Failed to load baseline: {e}[/red]")
        return
    
    async def execute_and_compare():
        # Execute current dialog
        temp_output = Path("temp_comparison_dialog")
        async with MultiAgentDialogEngine(scenario_data, str(mcp_config), temp_output) as engine:
            current_results = await engine.execute_multi_turn_dialog()
            
            # Load current results
            current_log_path = temp_output / "multi_agent_detailed_log.json"
            with open(current_log_path, 'r') as f:
                current_log = json.load(f)
        
        # Compare dialogs
        evaluator = MultiTurnDialogEvaluator()
        comparison_result = evaluator.compare_dialogs(current_log, baseline_log)
        
        # Create output directory
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save comparison results
        comparison_path = output_dir / "dialog_comparison.json"
        with open(comparison_path, 'w') as f:
            json.dump(comparison_result, f, indent=2, default=str)
        
        # Generate HTML comparison report
        from .multi_agent_reporter import MultiAgentHTMLReporter
        reporter = MultiAgentHTMLReporter()
        html_report = reporter.generate_comparison_report(current_log, baseline_log, comparison_result, scenario.stem)
        
        # Clean up temp files
        import shutil
        if temp_output.exists():
            shutil.rmtree(temp_output)
        
        return comparison_result, html_report
    
    try:
        comparison_result, html_report = asyncio.run(execute_and_compare())
        
        # Display results
        overall_score = comparison_result.get('overall_similarity', 0.0)
        console.print(f"📊 [bold]Overall Similarity: {overall_score:.3f}[/bold]")
        console.print(f"🔧 Trajectory Similarity: {comparison_result.get('trajectory_similarity', 0.0):.3f}")
        console.print(f"💬 Dialog Flow Similarity: {comparison_result.get('dialog_flow_similarity', 0.0):.3f}")
        console.print(f"🔄 Turn Similarity: {comparison_result.get('turn_similarity', 0.0):.3f}")
        console.print(f"📈 [blue]HTML Report: {html_report}[/blue]")
        
    except Exception as e:
        console.print(f"❌ [red]Error comparing multi-turn dialogs: {e}[/red]")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


if __name__ == "__main__":
    cli()