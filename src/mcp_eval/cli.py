"""Command-line interface for MCP Evaluation Utility."""

import click
import yaml
import json
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .scenario_runner import FailureAwareScenarioRunner
from .evaluator import TrajectoryEvaluator
from .reporter import ReportGenerator
from .html_reporter import HTMLReporter

console = Console()


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
        output = Path("baselines") / f"{scenario_name}_baseline"
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
        output = Path("comparison_results") / f"{scenario_name}_comparison"
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


if __name__ == "__main__":
    cli()