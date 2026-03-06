"""Example usage of Enhanced Researcher with all new components.

Demonstrates how to use the enhanced researcher with port management,
health monitoring, query planning, source trust evaluation, and result synthesis.
"""

import asyncio
import logging

from mindflow_backend.agents.research import get_enhanced_researcher_agent
from mindflow_backend.agents.research.pitchtab_monitor import get_pitchtab_monitor
from mindflow_backend.schemas.research import ResearchRequest, ResearchConfig


async def main():
    """Example of using the enhanced researcher."""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize the enhanced researcher
    researcher = await get_enhanced_researcher_agent()
    
    # Initialize monitoring (optional but recommended)
    monitor = get_pitchtab_monitor()
    await monitor.start_monitoring()
    
    try:
        # Initialize researcher session
        session_id = "example_session_001"
        agent_id = "enhanced_researcher_001"
        
        await researcher.initialize(session_id, agent_id)
        logger.info(f"Researcher initialized with session: {session_id}")
        
        # Example 1: Definition query
        print("\n=== Example 1: Definition Query ===")
        definition_request = ResearchRequest(
            query="What is microservice architecture?",
            session_id=session_id,
            agent_id=agent_id,
            config=ResearchConfig(
                max_concurrent_browsers=3,
                enable_stealth_mode=True,
                headless_mode=True,
            ),
        )
        
        definition_response = await researcher.execute_research(definition_request)
        
        if definition_response.success and definition_response.result:
            print(f"Query: {definition_response.result.original_query}")
            print(f"Summary: {definition_response.result.synthesis_summary}")
            print(f"Confidence: {definition_response.result.confidence_level}")
            print(f"Sources used: {definition_response.result.browsers_used}")
            print(f"Findings: {len(definition_response.result.findings)}")
            
            # Show conflicts if any
            if definition_response.result.conflicts_identified:
                print("Conflicts detected:")
                for conflict in definition_response.result.conflicts_identified:
                    print(f"  - {conflict.get('description', 'Unknown conflict')}")
                    
            # Show gaps if any
            if definition_response.result.gaps_identified:
                print("Information gaps:")
                for gap in definition_response.result.gaps_identified:
                    print(f"  - {gap}")
                    
            # Show recommendations
            if definition_response.result.recommendations:
                print("Recommendations:")
                for rec in definition_response.result.recommendations:
                    print(f"  - {rec}")
        else:
            print(f"Definition query failed: {definition_response.error_message}")
            
        print("\n" + "="*60)
        
        # Example 2: Comparison query
        print("\n=== Example 2: Comparison Query ===")
        comparison_request = ResearchRequest(
            query="React vs Vue for frontend development 2026",
            session_id=session_id,
            agent_id=agent_id,
            config=ResearchConfig(
                max_concurrent_browsers=5,  # More browsers for comparison
                enable_stealth_mode=True,
                headless_mode=True,
            ),
        )
        
        comparison_response = await researcher.execute_research(comparison_request)
        
        if comparison_response.success and comparison_response.result:
            print(f"Query: {comparison_response.result.original_query}")
            print(f"Summary: {comparison_response.result.synthesis_summary}")
            print(f"Confidence: {comparison_response.result.confidence_level}")
            
            # Show execution summary
            summary = comparison_response.execution_summary
            print(f"Query analysis: {summary.get('query_analysis', {})}")
            print(f"Execution metrics: {summary.get('execution', {})}")
            print(f"Source analysis: {summary.get('sources', {})}")
            
            # Show synthesis details if available
            synthesis_details = summary.get('synthesis', {})
            if synthesis_details:
                print(f"Conflicts detected: {synthesis_details.get('conflicts_detected', 0)}")
                print(f"Gaps identified: {synthesis_details.get('gaps_identified', 0)}")
        else:
            print(f"Comparison query failed: {comparison_response.error_message}")
            
        print("\n" + "="*60)
        
        # Example 3: Debug query
        print("\n=== Example 3: Debug Query ===")
        debug_request = ResearchRequest(
            query="Why does my React application crash on startup?",
            session_id=session_id,
            agent_id=agent_id,
            config=ResearchConfig(
                max_concurrent_browsers=4,  # Medium complexity for debug
                enable_stealth_mode=True,
                headless_mode=True,
            ),
        )
        
        debug_response = await researcher.execute_research(debug_request)
        
        if debug_response.success and debug_response.result:
            print(f"Query: {debug_response.result.original_query}")
            print(f"Summary: {debug_response.result.synthesis_summary}")
            print(f"Confidence: {debug_response.result.confidence_level}")
            
            # Show high confidence sources
            high_conf_sources = [
                f for f in debug_response.result.findings 
                if f.confidence_score >= 0.8
            ]
            if high_conf_sources:
                print("High confidence sources:")
                for source in high_conf_sources[:3]:  # Top 3
                    print(f"  - {source.source_url} ({source.confidence_score:.2f})")
        else:
            print(f"Debug query failed: {debug_response.error_message}")
            
        print("\n" + "="*60)
        
        # Show monitoring status
        print("\n=== Monitoring Status ===")
        monitoring_status = monitor.get_monitoring_status()
        print(f"Monitoring active: {monitoring_status['monitoring_active']}")
        print(f"Total instances: {monitoring_status['total_instances']}")
        print(f"Port management: {monitoring_status['port_management']['utilization_percent']:.1f}% utilized")
        print(f"Health monitoring: {monitoring_status['health_monitoring']['health_percentage']:.1f}% healthy")
        
        if monitoring_status['instances']:
            print("\nActive instances:")
            for instance in monitoring_status['instances']:
                health_icon = "✅" if instance.get('is_healthy', False) else "❌"
                print(f"  {health_icon} {instance['instance_id']} - Port {instance['port']} - {instance.get('status', 'unknown')}")
                
    except Exception as exc:
        logger.error(f"Error in enhanced researcher example: {exc}")
        
    finally:
        # Cleanup
        print("\n=== Cleanup ===")
        await monitor.stop_monitoring()
        await researcher.cleanup()
        print("Enhanced researcher example completed")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
