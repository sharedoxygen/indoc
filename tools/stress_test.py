#!/usr/bin/env python3
"""
Production Resilience Stress Test

Demonstrates the system can handle production-level loads
"""
import asyncio
import httpx
import time
import statistics
from typing import List
import random

import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TOKEN = os.getenv("API_TOKEN", "")  # Set via environment variable


async def make_request(client: httpx.AsyncClient, request_id: int) -> dict:
    """Make a single chat request"""
    start = time.time()
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/chat/chat",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "message": f"Test message {request_id}: What is {random.randint(1,100)} + {random.randint(1,100)}?",
                "model": "gemma3:27b"
            },
            timeout=30
        )
        elapsed = time.time() - start
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response_time": elapsed,
            "request_id": request_id
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "error": str(e),
            "response_time": elapsed,
            "request_id": request_id
        }


async def stress_test(concurrent_users: int, total_requests: int):
    """Run stress test with specified concurrency"""
    print(f"\n🚀 Starting stress test: {concurrent_users} concurrent users, {total_requests} total requests")
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Warm up
        print("  Warming up...")
        await make_request(client, 0)
        
        # Run test
        print("  Running stress test...")
        results = []
        start_time = time.time()
        
        # Create batches of concurrent requests
        for batch_start in range(0, total_requests, concurrent_users):
            batch_size = min(concurrent_users, total_requests - batch_start)
            tasks = [
                make_request(client, batch_start + i) 
                for i in range(batch_size)
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Small delay between batches to avoid overwhelming
            if batch_start + batch_size < total_requests:
                await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        response_times = [r["response_time"] for r in successful]
        
        print("\n📊 STRESS TEST RESULTS:")
        print("-" * 40)
        print(f"  Total Requests: {len(results)}")
        print(f"  Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
        print(f"  Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Requests/Second: {len(results)/total_time:.2f}")
        
        if response_times:
            print(f"\n  Response Time Statistics:")
            print(f"    Min: {min(response_times):.3f}s")
            print(f"    Max: {max(response_times):.3f}s")
            print(f"    Mean: {statistics.mean(response_times):.3f}s")
            print(f"    Median: {statistics.median(response_times):.3f}s")
            if len(response_times) > 1:
                print(f"    Std Dev: {statistics.stdev(response_times):.3f}s")
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.5)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 100 else sorted_times[-1]
            
            print(f"\n  Percentiles:")
            print(f"    50th (median): {p50:.3f}s")
            print(f"    95th: {p95:.3f}s")
            print(f"    99th: {p99:.3f}s")
        
        # Error analysis
        if failed:
            print(f"\n  Error Analysis:")
            error_types = {}
            for f in failed:
                error = f.get("error", "Unknown")
                error_types[error] = error_types.get(error, 0) + 1
            for error, count in error_types.items():
                print(f"    {error[:50]}: {count}")
        
        return len(successful) / len(results) * 100


async def main():
    """Run multiple stress test scenarios"""
    print("="*60)
    print("🏋️ PRODUCTION RESILIENCE STRESS TEST")
    print("="*60)
    
    scenarios = [
        (1, 5, "Single User"),
        (5, 20, "Light Load"),
        (10, 50, "Medium Load"),
        (20, 100, "Heavy Load")
    ]
    
    results = []
    for concurrent, total, name in scenarios:
        print(f"\n📌 Scenario: {name}")
        success_rate = await stress_test(concurrent, total)
        results.append((name, success_rate))
        await asyncio.sleep(2)  # Cool down between tests
    
    print("\n" + "="*60)
    print("🏆 FINAL ASSESSMENT")
    print("="*60)
    
    for name, rate in results:
        status = "✅" if rate >= 80 else "⚠️" if rate >= 60 else "❌"
        print(f"  {status} {name}: {rate:.1f}% success rate")
    
    avg_success = sum(r[1] for r in results) / len(results)
    
    print(f"\n  Average Success Rate: {avg_success:.1f}%")
    
    print("\n🎯 PRODUCTION READINESS:")
    if avg_success >= 90:
        print("  ✅ EXCELLENT: System is production-ready!")
        print("  The system handles concurrent load gracefully.")
    elif avg_success >= 70:
        print("  ⚠️ GOOD: System is mostly production-ready.")
        print("  Consider optimization for heavy loads.")
    else:
        print("  ❌ NEEDS IMPROVEMENT: System needs optimization.")
    
    print("="*60)


if __name__ == "__main__":
    print("Note: This test requires the backend to be running on port 8000")
    asyncio.run(main())
