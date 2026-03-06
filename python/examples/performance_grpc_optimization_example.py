"""Performance optimization gRPC example with connection pooling and load balancing.

This script demonstrates the new performance optimization capabilities
including connection pooling, load balancing, compression, and caching.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from omnimind_backend.grpc.performance.pooling.manager import GrpcConnectionPoolManager, PoolConfig
from omnimind_backend.grpc.performance.load_balancing.balancer import GrpcLoadBalancer
from omnimind_backend.grpc.performance.load_balancing.strategies import LoadBalancingStrategyFactory
from omnimind_backend.grpc.performance.compression.compressor import GrpcMessageCompressor
from omnimind_backend.grpc.performance.caching.cache import GrpcResponseCache
from omnimind_backend.grpc.performance.monitoring.profiler import GrpcProfiler
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def example_connection_pooling():
    """Example of connection pooling system."""
    print("🔗 Connection Pooling Example")
    print("=" * 60)
    
    try:
        # Create pool manager
        from omnimind_backend.grpc.performance.pooling.manager import PoolManagerConfig
        manager_config = PoolManagerConfig(
            default_min_pool_size=5,
            default_max_pool_size=20,
            enable_auto_optimization=True,
            enable_metrics=True
        )
        
        pool_manager = GrpcConnectionPoolManager(manager_config)
        await pool_manager.start()
        
        # Create connection pool configuration
        pool_config = PoolConfig(
            host="localhost",
            port=50051,
            secure=False,
            min_pool_size=3,
            max_pool_size=10,
            connection_timeout=5.0,
            health_check_interval=30.0,
            enable_metrics=True
        )
        
        # Create pool
        pool_id = "example-pool"
        success = await pool_manager.create_pool(pool_id, pool_config)
        print(f"   ✅ Pool created: {success}")
        
        # Get pool and test connections
        pool = await pool_manager.get_pool(pool_id)
        if pool:
            print(f"   📊 Pool statistics:")
            
            # Simulate connection usage
            connections = []
            for i in range(5):
                try:
                    connection = await pool.get_connection(timeout=2.0)
                    connections.append(connection)
                    print(f"      Connection {i+1}: Acquired successfully")
                    
                    # Simulate some work
                    await asyncio.sleep(0.1)
                    
                    # Return connection
                    await pool.return_connection(connection, success=True, response_time=0.1)
                    
                except Exception as exc:
                    print(f"      Connection {i+1}: Failed - {exc}")
            
            # Get pool statistics
            stats = await pool.get_statistics()
            print(f"      Total connections: {stats.total_connections}")
            print(f"      Active connections: {stats.active_connections}")
            print(f"      Available connections: {stats.available_connections}")
            print(f"      Total requests: {stats.total_requests}")
            print(f"      Success rate: {stats.get_success_rate():.1%}")
            print(f"      Average response time: {stats.average_response_time:.3f}s")
        
        # Test pool optimization
        print(f"\n   🔧 Testing pool optimization...")
        optimization_results = await pool_manager.optimize_pools()
        for result in optimization_results:
            print(f"      Pool {result.pool_id}:")
            print(f"         Optimizations: {len(result.optimizations_applied)}")
            print(f"         Performance improvement: {result.performance_improvement:.1%}")
            for optimization in result.optimizations_applied:
                print(f"            - {optimization}")
        
        # Get manager statistics
        manager_stats = await pool_manager.get_manager_statistics()
        print(f"\n   📊 Manager statistics:")
        print(f"      Total pools: {manager_stats['total_pools']}")
        print(f"      Total connections: {manager_stats['total_connections']}")
        print(f"      Active connections: {manager_stats['active_connections']}")
        print(f"      Overall success rate: {manager_stats['overall_success_rate']:.1%}")
        
        # Cleanup
        await pool_manager.stop()
        print(f"   ✅ Pool manager stopped")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_load_balancing():
    """Example of load balancing system."""
    print("\n⚖️  Load Balancing Example")
    print("=" * 60)
    
    try:
        # Create test endpoints
        from omnimind_backend.grpc.performance.load_balancing.strategies import Endpoint, EndpointState
        
        endpoints = [
            Endpoint("endpoint-1", "localhost", 50051, weight=1.0),
            Endpoint("endpoint-2", "localhost", 50052, weight=2.0),
            Endpoint("endpoint-3", "localhost", 50053, weight=1.5),
            Endpoint("endpoint-4", "localhost", 50054, weight=0.5),
        ]
        
        # Set all endpoints as healthy
        for endpoint in endpoints:
            endpoint.state = EndpointState.HEALTHY
        
        # Test different strategies
        strategies = ["round_robin", "least_connections", "weighted_round_robin", "random", "performance_based"]
        
        for strategy_name in strategies:
            print(f"\n   🧪 Testing {strategy_name} strategy:")
            
            try:
                strategy = LoadBalancingStrategyFactory.create_strategy(strategy_name)
                
                # Simulate endpoint selection
                selections = {}
                for i in range(20):
                    from omnimind_backend.grpc.performance.load_balancing.strategies import SelectionContext
                    context = SelectionContext(
                        available_endpoints=endpoints,
                        user_id=f"user-{i % 5}",
                        session_id=f"session-{i % 3}"
                    )
                    
                    try:
                        selected = strategy.select_endpoint(endpoints, context)
                        selections[selected.id] = selections.get(selected.id, 0) + 1
                        
                        # Simulate request performance
                        import random
                        success = random.random() > 0.1  # 90% success rate
                        response_time = random.uniform(0.1, 1.0)
                        
                        selected.metrics.record_request(success, response_time)
                        strategy.update_statistics(selected, selected.metrics)
                        
                    except Exception as exc:
                        print(f"      Selection {i+1}: Failed - {exc}")
                
                # Show distribution
                print(f"      Distribution after 20 selections:")
                for endpoint_id, count in selections.items():
                    percentage = (count / 20) * 100
                    print(f"         {endpoint_id}: {count} ({percentage:.1f}%)")
                
                # Show strategy-specific info
                if hasattr(strategy, 'get_performance_scores'):
                    scores = strategy.get_performance_scores()
                    if scores:
                        print(f"      Performance scores:")
                        for ep_id, score in scores.items():
                            print(f"         {ep_id}: {score:.2f}")
                
            except Exception as exc:
                print(f"      Strategy failed: {exc}")
        
        # Test sticky session strategy
        print(f"\n   🧪 Testing sticky session strategy:")
        
        try:
            fallback_strategy = LoadBalancingStrategyFactory.create_strategy("round_robin")
            sticky_strategy = LoadBalancingStrategyFactory.create_strategy(
                "sticky_session", 
                fallback_strategy=fallback_strategy
            )
            
            # Simulate session-based requests
            session_requests = {}
            for i in range(15):
                session_id = f"session-{i % 3}"
                context = SelectionContext(
                    available_endpoints=endpoints,
                    session_id=session_id
                )
                
                try:
                    selected = sticky_strategy.select_endpoint(endpoints, context)
                    
                    if session_id not in session_requests:
                        session_requests[session_id] = selected.id
                    
                    print(f"      Session {session_id}: {selected.id}")
                    
                except Exception as exc:
                    print(f"      Session {session_id}: Failed - {exc}")
            
            print(f"      Session affinity maintained: {len(set(session_requests.values()))} unique endpoints")
            
        except Exception as exc:
            print(f"      Sticky session failed: {exc}")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_compression():
    """Example of message compression system."""
    print("\n🗜️  Message Compression Example")
    print("=" * 60)
    
    try:
        # Create compressor configuration
        from omnimind_backend.grpc.performance.compression.compressor import CompressionConfig
        config = CompressionConfig(
            enabled_algorithms=["gzip", "deflate"],
            min_compression_size=100,
            min_compression_ratio=0.7,
            max_compression_time=0.1
        )
        
        compressor = GrpcMessageCompressor(config)
        
        # Test different message sizes
        test_messages = [
            b"Small message",  # < 100 bytes
            b"A" * 200,       # 200 bytes
            b"B" * 1000,      # 1KB
            b"C" * 10000,     # 10KB
            b"D" * 100000,    # 100KB
        ]
        
        algorithms = ["gzip", "deflate"]
        
        for i, message in enumerate(test_messages):
            original_size = len(message)
            print(f"\n   📦 Message {i+1} ({original_size} bytes):")
            
            for algorithm in algorithms:
                try:
                    # Compress message
                    start_time = time.time()
                    compressed = await compressor.compress_message(message, algorithm)
                    compression_time = time.time() - start_time
                    
                    if compressed != message:  # Compression was applied
                        compressed_size = len(compressed)
                        compression_ratio = compressed_size / original_size
                        space_saved = (1 - compression_ratio) * 100
                        
                        print(f"      {algorithm.upper()}:")
                        print(f"         Compressed size: {compressed_size} bytes")
                        print(f"         Compression ratio: {compression_ratio:.3f}")
                        print(f"         Space saved: {space_saved:.1f}%")
                        print(f"         Compression time: {compression_time:.3f}s")
                        
                        # Decompress to verify
                        start_time = time.time()
                        decompressed = await compressor.decompress_message(compressed, algorithm)
                        decompression_time = time.time() - start_time
                        
                        if decompressed == message:
                            print(f"         Decompression: ✅ ({decompression_time:.3f}s)")
                        else:
                            print(f"         Decompression: ❌")
                    else:
                        print(f"      {algorithm.upper()}: Not compressed (too small)")
                        
                except Exception as exc:
                    print(f"      {algorithm.upper()}: Failed - {exc}")
        
        # Test compression negotiation
        print(f"\n   🤝 Testing compression negotiation:")
        
        try:
            client_algorithms = ["gzip", "deflate", "zstd"]
            negotiated = await compressor.negotiate_compression(client_algorithms)
            print(f"      Client algorithms: {client_algorithms}")
            print(f"      Negotiated: {negotiated}")
            
        except Exception as exc:
            print(f"      Negotiation failed: {exc}")
        
        # Get compression statistics
        try:
            stats = compressor.get_compression_stats()
            print(f"\n   📊 Compression statistics:")
            print(f"      Total compressions: {stats['total_compressions']}")
            print(f"      Average compression ratio: {stats['average_compression_ratio']:.3f}")
            print(f"      Average compression time: {stats['average_compression_time']:.3f}s")
            
            if stats['algorithm_stats']:
                print(f"      Algorithm performance:")
                for algo, algo_stats in stats['algorithm_stats'].items():
                    print(f"         {algo}: {algo_stats['count']} compressions, "
                          f"{algo_stats['average_ratio']:.3f} ratio")
            
        except Exception as exc:
            print(f"   Statistics failed: {exc}")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_caching():
    """Example of response caching system."""
    print("\n💾 Response Caching Example")
    print("=" * 60)
    
    try:
        # Create cache configuration
        from omnimind_backend.grpc.performance.caching.cache import CacheConfig
        config = CacheConfig(
            store_type="memory",
            max_entries=1000,
            default_ttl=300,  # 5 minutes
            max_cache_size=10 * 1024 * 1024,  # 10MB
            enable_metrics=True
        )
        
        cache = GrpcResponseCache(config)
        
        # Simulate gRPC responses
        from omnimind_backend.grpc.performance.caching.cache import CachedResponse
        
        test_responses = [
            ("user:123:profile", CachedResponse(b'{"name": "Alice", "age": 30}', 300)),
            ("user:456:profile", CachedResponse(b'{"name": "Bob", "age": 25}', 300)),
            ("config:app:settings", CachedResponse(b'{"theme": "dark", "lang": "en"}', 600)),
            ("search:query:python", CachedResponse(b'["result1", "result2", "result3"]', 60)),
        ]
        
        print(f"   📥 Testing cache operations:")
        
        # Test cache set and get
        for key, response in test_responses:
            try:
                # Set cache entry
                await cache.set(key, response)
                print(f"      Set {key}: ✅")
                
                # Get cache entry
                cached = await cache.get(key)
                if cached and cached.data == response.data:
                    print(f"      Get {key}: ✅ ({len(cached.data)} bytes)")
                else:
                    print(f"      Get {key}: ❌")
                    
            except Exception as exc:
                print(f"      {key}: Failed - {exc}")
        
        # Test cache miss
        print(f"\n   🔍 Testing cache miss:")
        try:
            cached = await cache.get("nonexistent:key")
            if cached is None:
                print(f"      Cache miss: ✅")
            else:
                print(f"      Cache miss: ❌ (Unexpected hit)")
        except Exception as exc:
            print(f"      Cache miss failed: {exc}")
        
        # Test cache expiration
        print(f"\n   ⏰ Testing cache expiration:")
        try:
            # Set entry with short TTL
            short_ttl_response = CachedResponse(b'{"temp": "data"}', 1)  # 1 second
            await cache.set("temp:key", short_ttl_response)
            
            # Should be available immediately
            cached = await cache.get("temp:key")
            if cached:
                print(f"      Immediate get: ✅")
            
            # Wait for expiration
            await asyncio.sleep(2)
            
            # Should be expired
            cached = await cache.get("temp:key")
            if cached is None:
                print(f"      Expired get: ✅")
            else:
                print(f"      Expired get: ❌ (Still cached)")
                
        except Exception as exc:
            print(f"      Expiration test failed: {exc}")
        
        # Test cache invalidation
        print(f"\n   🗑️  Testing cache invalidation:")
        try:
            # Invalidate specific key
            result = await cache.invalidate("user:123:profile")
            print(f"      Invalidate specific key: {result.success}")
            
            # Invalidate pattern
            result = await cache.invalidate("user:*")
            print(f"      Invalidate pattern 'user:*': {result.success}")
            print(f"      Invalidated entries: {result.invalidated_count}")
            
        except Exception as exc:
            print(f"      Invalidation failed: {exc}")
        
        # Get cache statistics
        try:
            stats = cache.get_statistics()
            print(f"\n   📊 Cache statistics:")
            print(f"      Total entries: {stats['total_entries']}")
            print(f"      Cache hits: {stats['cache_hits']}")
            print(f"      Cache misses: {stats['cache_misses']}")
            print(f"      Hit rate: {stats['hit_rate']:.1%}")
            print(f"      Cache sets: {stats['cache_sets']}")
            print(f"      Cache invalidations: {stats['cache_invalidations']}")
            
        except Exception as exc:
            print(f"   Statistics failed: {exc}")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_performance_monitoring():
    """Example of performance monitoring system."""
    print("\n📈 Performance Monitoring Example")
    print("=" * 60)
    
    try:
        # Create profiler
        profiler = GrpcProfiler()
        await profiler.start()
        
        # Simulate gRPC operations
        operations = [
            ("StreamChat", 0.1),
            ("HealthCheck", 0.05),
            ("GetMetrics", 0.2),
            ("StreamChat", 0.15),
            ("HealthCheck", 0.03),
        ]
        
        print(f"   📊 Simulating gRPC operations:")
        
        for operation, duration in operations:
            try:
                # Simulate operation
                start_time = time.time()
                await asyncio.sleep(duration)
                actual_duration = time.time() - start_time
                
                # Record operation
                await profiler.record_operation(operation, actual_duration, success=True)
                print(f"      {operation}: {actual_duration:.3f}s ✅")
                
            except Exception as exc:
                await profiler.record_operation(operation, 0.0, success=False)
                print(f"      {operation}: ❌")
        
        # Get performance report
        try:
            report = await profiler.get_performance_report()
            print(f"\n   📈 Performance Report:")
            print(f"      Total operations: {report['total_operations']}")
            print(f"      Successful operations: {report['successful_operations']}")
            print(f"      Failed operations: {report['failed_operations']}")
            print(f"      Success rate: {report['success_rate']:.1%}")
            print(f"      Average duration: {report['average_duration']:.3f}s")
            
            if report['operation_stats']:
                print(f"\n      Operation breakdown:")
                for op, stats in report['operation_stats'].items():
                    print(f"         {op}:")
                    print(f"            Count: {stats['count']}")
                    print(f"            Success rate: {stats['success_rate']:.1%}")
                    print(f"            Avg duration: {stats['average_duration']:.3f}s")
                    print(f"            Min duration: {stats['min_duration']:.3f}s")
                    print(f"            Max duration: {stats['max_duration']:.3f}s")
            
        except Exception as exc:
            print(f"   Report generation failed: {exc}")
        
        # Test performance analysis
        try:
            analysis = await profiler.analyze_performance()
            print(f"\n   🔍 Performance Analysis:")
            print(f"      Overall health: {analysis['overall_health']}")
            print(f"      Performance score: {analysis['performance_score']:.1f}/100")
            
            if analysis['recommendations']:
                print(f"      Recommendations:")
                for rec in analysis['recommendations']:
                    print(f"         - {rec}")
            
        except Exception as exc:
            print(f"   Analysis failed: {exc}")
        
        # Stop profiler
        await profiler.stop()
        print(f"\n   ✅ Profiler stopped")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def example_integrated_performance():
    """Example of integrated performance optimization system."""
    print("\n🔗 Integrated Performance Optimization Example")
    print("=" * 60)
    
    try:
        # Initialize all components
        pool_manager = GrpcConnectionPoolManager(PoolManagerConfig())
        await pool_manager.start()
        
        load_balancer = GrpcLoadBalancer(LoadBalancingStrategyFactory.create_strategy("least_connections"))
        compressor = GrpcMessageCompressor(CompressionConfig())
        cache = GrpcResponseCache(CacheConfig())
        profiler = GrpcProfiler()
        
        await profiler.start()
        
        print(f"   🚀 All performance components initialized")
        
        # Simulate integrated workflow
        print(f"\n   🔄 Simulating integrated workflow:")
        
        for i in range(5):
            try:
                operation_start = time.time()
                
                # 1. Check cache first
                cache_key = f"operation:{i}"
                cached = await cache.get(cache_key)
                
                if cached:
                    print(f"      Operation {i+1}: Cache hit ✅")
                    await profiler.record_operation("CachedOperation", time.time() - operation_start, True)
                    continue
                
                # 2. Get connection from pool
                pool_config = PoolConfig(host="localhost", port=50051, min_pool_size=2, max_pool_size=5)
                pool_id = f"pool-{i % 2}"
                
                if not await pool_manager.get_pool(pool_id):
                    await pool_manager.create_pool(pool_id, pool_config)
                
                pool = await pool_manager.get_pool(pool_id)
                connection = await pool.get_connection()
                
                # 3. Select endpoint via load balancer
                from omnimind_backend.grpc.performance.load_balancing.strategies import Endpoint, EndpointState
                endpoints = [
                    Endpoint(f"endpoint-{j}", "localhost", 50051 + j, state=EndpointState.HEALTHY)
                    for j in range(3)
                ]
                
                from omnimind_backend.grpc.performance.load_balancing.strategies import SelectionContext
                context = SelectionContext(available_endpoints=endpoints, user_id=f"user-{i}")
                endpoint = load_balancer.select_endpoint(endpoints, context)
                
                # 4. Compress request
                request_data = f"Request data for operation {i}".encode()
                compressed_request = await compressor.compress_message(request_data, "gzip")
                
                # 5. Simulate processing
                await asyncio.sleep(0.05)
                
                # 6. Cache result
                response_data = f"Response data for operation {i}".encode()
                from omnimind_backend.grpc.performance.caching.cache import CachedResponse
                await cache.set(cache_key, CachedResponse(response_data, 60))
                
                # 7. Return connection
                await pool.return_connection(connection, success=True, response_time=0.05)
                
                operation_duration = time.time() - operation_start
                await profiler.record_operation("IntegratedOperation", operation_duration, True)
                
                print(f"      Operation {i+1}: Complete ({operation_duration:.3f}s) ✅")
                
            except Exception as exc:
                await profiler.record_operation("IntegratedOperation", time.time() - operation_start, False)
                print(f"      Operation {i+1}: Failed - {exc}")
        
        # Get integrated statistics
        print(f"\n   📊 Integrated Statistics:")
        
        # Pool manager stats
        manager_stats = await pool_manager.get_manager_statistics()
        print(f"      Connection pools: {manager_stats['total_pools']}")
        print(f"      Total connections: {manager_stats['total_connections']}")
        print(f"      Overall success rate: {manager_stats['overall_success_rate']:.1%}")
        
        # Load balancer stats
        lb_stats = load_balancer.get_statistics()
        print(f"      Load balancer selections: {lb_stats['total_selections']}")
        
        # Compression stats
        comp_stats = compressor.get_compression_stats()
        print(f"      Compressions: {comp_stats['total_compressions']}")
        print(f"      Average ratio: {comp_stats['average_compression_ratio']:.3f}")
        
        # Cache stats
        cache_stats = cache.get_statistics()
        print(f"      Cache hit rate: {cache_stats['hit_rate']:.1%}")
        
        # Profiler stats
        profile_report = await profiler.get_performance_report()
        print(f"      Operations: {profile_report['total_operations']}")
        print(f"      Average duration: {profile_report['average_duration']:.3f}s")
        
        # Cleanup
        await pool_manager.stop()
        await profiler.stop()
        
        print(f"\n   ✅ Integrated performance system working!")
        
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


async def main():
    """Run all performance optimization examples."""
    print("🎯 OmniMind Performance Optimization Examples")
    print("=" * 70)
    print("This script demonstrates the performance optimization system with")
    print("connection pooling, load balancing, compression, caching, and monitoring.")
    print()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run examples
    await example_connection_pooling()
    await example_load_balancing()
    await example_compression()
    await example_caching()
    await example_performance_monitoring()
    await example_integrated_performance()
    
    print("\n✅ Performance Optimization Examples Completed!")
    print("\n🚀 Performance Benefits Achieved:")
    print("- Connection Pooling: Efficient connection reuse and management")
    print("- Load Balancing: Intelligent request distribution across endpoints")
    print("- Compression: Reduced bandwidth usage with adaptive algorithms")
    print("- Caching: Faster response times with intelligent caching")
    print("- Monitoring: Real-time performance tracking and optimization")
    print("\n🔧 Integration Tips:")
    print("- Use connection pooling for high-concurrency scenarios")
    print("- Choose load balancing strategy based on your use case")
    print("- Enable compression for large messages (>1KB)")
    print("- Cache frequently accessed, read-heavy data")
    print("- Monitor performance metrics continuously for optimization")


if __name__ == "__main__":
    asyncio.run(main())
