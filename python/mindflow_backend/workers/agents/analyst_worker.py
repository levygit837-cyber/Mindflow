"""Analyst worker for handling data analysis and metrics tasks."""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueConfig

_logger = get_logger(__name__)


class AnalystWorker(BaseWorker):
    """Worker specialized for Analyst Agent tasks."""
    
    def __init__(self, queue_config: QueueConfig) -> None:
        """Initialize the Analyst worker."""
        super().__init__(queue_config, worker_name="analyst_worker")
    
    async def process_message(self, message_data: dict[str, Any]) -> WorkerResult:
        """Process analysis and metrics tasks.
        
        Supported task types:
        - metrics_calculation: Calculate complex metrics
        - data_processing: Process large datasets
        - report_generation: Generate analytical reports
        - trend_analysis: Analyze trends and patterns
        - performance_analysis: Performance metrics analysis
        """
        message_data = self._normalize_message_data(message_data)
        start_time = time.time()
        task_type = message_data.get("task_type", "unknown")
        task_id = message_data.get("task_id", "unknown")
        
        try:
            _logger.info(f"AnalystWorker processing {task_type} task {task_id}")
            
            if task_type == "metrics_calculation":
                result = await self._handle_metrics_calculation(message_data)
            elif task_type == "data_processing":
                result = await self._handle_data_processing(message_data)
            elif task_type == "report_generation":
                result = await self._handle_report_generation(message_data)
            elif task_type == "trend_analysis":
                result = await self._handle_trend_analysis(message_data)
            elif task_type == "performance_analysis":
                result = await self._handle_performance_analysis(message_data)
            else:
                result = WorkerResult(
                    success=False,
                    message=f"Unsupported task type: {task_type}",
                    processing_time=time.time() - start_time,
                )
            
            _logger.info(
                f"AnalystWorker completed {task_type} task {task_id} "
                f"({'SUCCESS' if result.success else 'FAILED'})"
            )
            
            return result
            
        except Exception as e:
            _logger.error(
                f"AnalystWorker failed to process {task_type} task {task_id}: {e}",
                exc_info=True
            )
            return WorkerResult(
                success=False,
                message=f"Task processing failed: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )
    
    async def _handle_metrics_calculation(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle complex metrics calculation using system data."""
        metrics_type = message_data.get("metrics_type", "performance")
        data_source = message_data.get("data_source")
        time_range = message_data.get("time_range", "24h")
        
        try:
            metrics_results = {}
            
            # Get real metrics based on type
            if metrics_type == "performance":
                # Use database health metrics
                from mindflow_backend.infra.database.health import get_health_checker
                
                health_checker = get_health_checker()
                health_summary = health_checker.get_health_summary()
                
                metrics_results = {
                    "db_health_status": health_summary.get("status", "unknown"),
                    "avg_latency_ms": health_summary.get("recent_summary", {}).get("avg_latency_ms", 0),
                    "total_checks": health_summary.get("total_checks", 0),
                    "healthy_ratio": health_summary.get("recent_summary", {}).get("healthy", 0) / max(1, health_summary.get("recent_summary", {}).get("healthy", 0) + health_summary.get("recent_summary", {}).get("degraded", 0)),
                }
            
            elif metrics_type == "agent_activity":
                # Get agent team metrics
                from mindflow_backend.execution.agent_team_manager import AgentTeamManager
                
                team_manager = AgentTeamManager()
                active_teams = len(team_manager._teams)
                
                metrics_results = {
                    "active_teams": active_teams,
                    "total_agents": sum(len(t.get("agent_ids", [])) for t in team_manager._teams.values()),
                }
            
            elif metrics_type == "memory_usage":
                # System memory metrics
                try:
                    import psutil
                    mem = psutil.virtual_memory()
                    metrics_results = {
                        "memory_percent": mem.percent,
                        "available_mb": mem.available / 1024 / 1024,
                        "used_mb": mem.used / 1024 / 1024,
                    }
                except ImportError:
                    metrics_results = {"note": "psutil not available"}
            
            else:
                metrics_results = {"note": f"Metrics type '{metrics_type}' not implemented"}
            
            return WorkerResult(
                success=True,
                message=f"Metrics calculated for {metrics_type}",
                data={
                    "metrics_type": metrics_type,
                    "data_source": data_source,
                    "time_range": time_range,
                    "results": metrics_results,
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Metrics calculation failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_data_processing(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle dataset processing using filesystem and database."""
        dataset_path = message_data.get("dataset_path")
        processing_type = message_data.get("processing_type", "aggregation")
        
        if not dataset_path:
            return WorkerResult(
                success=False,
                message="No dataset_path provided",
                data={"error": "dataset_path required"},
            )
        
        try:
            import os
            import json
            
            # Check if file exists
            if not os.path.exists(dataset_path):
                return WorkerResult(
                    success=False,
                    message=f"Dataset not found: {dataset_path}",
                    data={"error": "file_not_found"},
                )
            
            # Get file info
            file_stat = os.stat(dataset_path)
            file_size_kb = file_stat.st_size / 1024
            
            records_processed = 0
            processing_results = {}
            
            # Process based on file type
            if dataset_path.endswith('.json'):
                with open(dataset_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records_processed = len(data)
                        
                        if processing_type == "aggregation":
                            # Simple aggregation - count by type if available
                            type_counts = {}
                            for item in data:
                                item_type = item.get('type', 'unknown')
                                type_counts[item_type] = type_counts.get(item_type, 0) + 1
                            processing_results = {"type_counts": type_counts}
                        
                        elif processing_type == "summary":
                            # Summary statistics
                            processing_results = {
                                "total_records": records_processed,
                                "fields": list(data[0].keys()) if data else [],
                            }
            
            elif dataset_path.endswith('.csv'):
                # Simple CSV processing
                import csv
                with open(dataset_path, 'r') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    records_processed = len(rows) - 1  # Exclude header
                    processing_results = {"columns": rows[0] if rows else []}
            
            return WorkerResult(
                success=True,
                message=f"Data processing completed: {records_processed} records",
                data={
                    "dataset_path": dataset_path,
                    "processing_type": processing_type,
                    "file_size_kb": round(file_size_kb, 2),
                    "records_processed": records_processed,
                    "results": processing_results,
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Data processing failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_report_generation(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle analytical report generation using LLM."""
        report_type = message_data.get("report_type", "summary")
        data_sources = message_data.get("data_sources", [])
        format_type = message_data.get("format", "json")
        
        try:
            from mindflow_backend.services.llm import get_llm_service
            
            llm_service = get_llm_service()
            
            # Gather data from sources
            report_data = []
            for source in data_sources:
                # Try to read the data source
                try:
                    import os
                    if os.path.exists(source):
                        with open(source, 'r') as f:
                            content = f.read()[:2000]  # Limit content
                            report_data.append({"source": source, "preview": content[:500]})
                except Exception:
                    report_data.append({"source": source, "error": "Could not read"})
            
            # Generate report content using LLM
            if report_data:
                prompt = f"""Generate a {report_type} report based on this data:

Data Sources: {len(report_data)}

Generate a structured analysis with:
1. Executive Summary
2. Key Findings (3-5 points)
3. Recommendations (2-3 points)

Format as markdown."""
                
                try:
                    report_content = await llm_service.generate(
                        prompt=prompt,
                        system_message="You are an expert report writer. Be concise and professional.",
                        temperature=0.3,
                        max_tokens=1000,
                    )
                except Exception:
                    report_content = f"Report generation for {report_type} with {len(report_data)} data sources."
            else:
                report_content = "No data sources available for report generation."
            
            # Save report
            import tempfile
            output_path = tempfile.mktemp(suffix=f".{format_type}")
            with open(output_path, 'w') as f:
                if format_type == "json":
                    import json
                    json.dump({
                        "report_type": report_type,
                        "content": report_content,
                        "sources": data_sources,
                    }, f, indent=2)
                else:
                    f.write(report_content)
            
            return WorkerResult(
                success=True,
                message=f"Report generated: {report_type}",
                data={
                    "report_type": report_type,
                    "data_sources": data_sources,
                    "format": format_type,
                    "report_path": output_path,
                    "summary": {
                        "total_sources": len(data_sources),
                        "sources_processed": len(report_data),
                    },
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Report generation failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_trend_analysis(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle trend analysis using LLM and data patterns."""
        analysis_target = message_data.get("analysis_target")
        time_period = message_data.get("time_period", "7d")
        
        if not analysis_target:
            return WorkerResult(
                success=False,
                message="No analysis_target provided",
                data={"error": "analysis_target required"},
            )
        
        try:
            from mindflow_backend.services.llm import get_llm_service
            from mindflow_backend.infra.database.health import get_health_checker
            
            llm_service = get_llm_service()
            
            # Get historical data for analysis
            health_checker = get_health_checker()
            history = health_checker._health_history[-20:]  # Last 20 checks
            
            # Analyze trends
            if len(history) >= 3:
                latencies = [h.latency_ms for h in history]
                avg_latency = sum(latencies) / len(latencies)
                trend = "increasing" if latencies[-1] > latencies[0] else "decreasing" if latencies[-1] < latencies[0] else "stable"
                
                trends_detected = [
                    {"pattern": trend, "metric": "latency", "current_value": round(avg_latency, 2)},
                ]
                
                # Check for anomalies
                anomalies = 0
                for i, h in enumerate(history):
                    if h.status != "healthy":
                        anomalies += 1
            else:
                trends_detected = [{"pattern": "insufficient_data", "note": "Need more historical data"}]
                anomalies = 0
            
            # Generate forecast using LLM
            prompt = f"""Based on this trend data for '{analysis_target}':

Trends: {trends_detected}
Time Period: {time_period}
Anomalies detected: {anomalies}

Provide a brief forecast (2-3 sentences) of what to expect next."""
            
            try:
                forecast = await llm_service.generate(
                    prompt=prompt,
                    system_message="You are a data analyst. Provide brief, data-driven forecasts.",
                    temperature=0.3,
                    max_tokens=200,
                )
            except Exception:
                forecast = "Forecast unavailable - insufficient data"
            
            return WorkerResult(
                success=True,
                message=f"Trend analysis completed for {analysis_target}",
                data={
                    "analysis_target": analysis_target,
                    "time_period": time_period,
                    "trends_detected": trends_detected,
                    "anomalies": anomalies,
                    "forecast": forecast,
                },
            )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Trend analysis failed: {exc}",
                data={"error": str(exc)},
            )
    
    async def _handle_performance_analysis(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle performance analysis using health check data."""
        component = message_data.get("component")
        metrics = message_data.get("metrics", [])
        benchmark = message_data.get("benchmark", False)
        
        try:
            from mindflow_backend.infra.database.health import get_health_checker
            
            health_checker = get_health_checker()
            diagnostics = await health_checker.get_diagnostics()
            
            # Analyze component performance
            if component == "database":
                perf_data = diagnostics.get("metrics", {})
                latency = perf_data.get("avg_query_time_ms", 0)
                
                # Determine performance score
                if latency < 50:
                    score = 9.0
                elif latency < 100:
                    score = 7.5
                elif latency < 200:
                    score = 6.0
                else:
                    score = 4.0
                
                bottlenecks = []
                if latency > 100:
                    bottlenecks.append({"location": "database", "impact": "high", "latency_ms": latency})
                if perf_data.get("slow_queries_count", 0) > 5:
                    bottlenecks.append({"location": "queries", "impact": "medium", "slow_queries": perf_data.get("slow_queries_count")})
                
                recommendations = []
                if latency > 100:
                    recommendations.append("Consider query optimization or indexing")
                if perf_data.get("connection_pool_utilization", 0) > 0.8:
                    recommendations.append("Increase connection pool size")
                if not recommendations:
                    recommendations.append("Performance is optimal")
                
                return WorkerResult(
                    success=True,
                    message=f"Performance analysis completed for {component}",
                    data={
                        "component": component,
                        "metrics_analyzed": ["latency", "pool_utilization", "slow_queries"],
                        "benchmark_comparison": benchmark,
                        "performance_score": score,
                        "current_metrics": {
                            "avg_latency_ms": latency,
                            "pool_utilization": perf_data.get("connection_pool_utilization"),
                        },
                        "bottlenecks": bottlenecks,
                        "recommendations": recommendations,
                    },
                )
            
            else:
                return WorkerResult(
                    success=True,
                    message=f"Performance analysis for {component}: basic metrics only",
                    data={
                        "component": component,
                        "note": f"Detailed metrics for '{component}' not yet implemented",
                    },
                )
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Performance analysis failed: {exc}",
                data={"error": str(exc)},
            )
