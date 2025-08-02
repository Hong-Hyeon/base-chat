#!/usr/bin/env python3
"""
Performance test script for RAG system
"""

import asyncio
import aiohttp
import time
import json
from typing import List, Dict, Any
import statistics


class RAGPerformanceTest:
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.results = []

    async def test_single_embedding(self, text: str) -> Dict[str, Any]:
        """Test single embedding creation."""
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            payload = {"text": text, "metadata": {"test": True}}
            async with session.post(f"{self.base_url}/embed/", json=payload) as response:
                result = await response.json()
                duration = time.time() - start_time
                
                return {
                    "type": "single_embedding",
                    "duration": duration,
                    "status": response.status,
                    "success": response.status == 200
                }

    async def test_batch_embedding(self, texts: List[str]) -> Dict[str, Any]:
        """Test batch embedding creation."""
        start_time = time.time()
        
        documents = [
            {"document_id": f"test_{i}", "content": text, "metadata": {"test": True}}
            for i, text in enumerate(texts)
        ]
        
        async with aiohttp.ClientSession() as session:
            payload = {"documents": documents}
            async with session.post(f"{self.base_url}/embed/batch/embed", json=payload) as response:
                result = await response.json()
                duration = time.time() - start_time
                
                return {
                    "type": "batch_embedding",
                    "duration": duration,
                    "status": response.status,
                    "success": response.status == 200,
                    "job_id": result.get("job_id") if response.status == 200 else None
                }

    async def test_search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Test vector search."""
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            payload = {"query": query, "top_k": top_k, "similarity_threshold": 0.1}
            async with session.post(f"{self.base_url}/embed/search", json=payload) as response:
                result = await response.json()
                duration = time.time() - start_time
                
                return {
                    "type": "search",
                    "duration": duration,
                    "status": response.status,
                    "success": response.status == 200,
                    "results_count": len(result.get("results", [])) if response.status == 200 else 0
                }

    async def run_performance_test(self, num_tests: int = 10):
        """Run comprehensive performance test."""
        print(f"🚀 Starting RAG Performance Test ({num_tests} iterations)")
        print("=" * 60)
        
        # Test data
        test_texts = [
            "Artificial intelligence is transforming the world.",
            "Machine learning algorithms are becoming more sophisticated.",
            "Natural language processing enables better communication.",
            "Deep learning models require significant computational resources.",
            "Computer vision applications are widespread in modern technology."
        ]
        
        search_queries = [
            "AI and machine learning",
            "Natural language processing",
            "Deep learning technology",
            "Computer vision applications",
            "Artificial intelligence transformation"
        ]
        
        # Test single embeddings
        print("📝 Testing Single Embedding Creation...")
        single_results = []
        for i in range(num_tests):
            for text in test_texts:
                result = await self.test_single_embedding(text)
                single_results.append(result)
                if result["success"]:
                    print(f"  ✓ Single embedding {i+1}/{num_tests} completed in {result['duration']:.3f}s")
                else:
                    print(f"  ✗ Single embedding {i+1}/{num_tests} failed")
        
        # Test batch embeddings
        print("\n📦 Testing Batch Embedding Creation...")
        batch_results = []
        for i in range(num_tests):
            result = await self.test_batch_embedding(test_texts)
            batch_results.append(result)
            if result["success"]:
                print(f"  ✓ Batch embedding {i+1}/{num_tests} completed in {result['duration']:.3f}s")
            else:
                print(f"  ✗ Batch embedding {i+1}/{num_tests} failed")
        
        # Test searches
        print("\n🔍 Testing Vector Search...")
        search_results = []
        for i in range(num_tests):
            for query in search_queries:
                result = await self.test_search(query)
                search_results.append(result)
                if result["success"]:
                    print(f"  ✓ Search {i+1}/{num_tests} completed in {result['duration']:.3f}s ({result['results_count']} results)")
                else:
                    print(f"  ✗ Search {i+1}/{num_tests} failed")
        
        # Calculate statistics
        self.calculate_statistics(single_results, batch_results, search_results)
        
        return {
            "single_embeddings": single_results,
            "batch_embeddings": batch_results,
            "searches": search_results
        }

    def calculate_statistics(self, single_results, batch_results, search_results):
        """Calculate and display performance statistics."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE STATISTICS")
        print("=" * 60)
        
        # Single embedding statistics
        successful_single = [r for r in single_results if r["success"]]
        if successful_single:
            single_durations = [r["duration"] for r in successful_single]
            print(f"Single Embedding ({len(successful_single)} successful):")
            print(f"  Average: {statistics.mean(single_durations):.3f}s")
            print(f"  Median:  {statistics.median(single_durations):.3f}s")
            print(f"  Min:     {min(single_durations):.3f}s")
            print(f"  Max:     {max(single_durations):.3f}s")
            print(f"  Std Dev: {statistics.stdev(single_durations):.3f}s")
        
        # Batch embedding statistics
        successful_batch = [r for r in batch_results if r["success"]]
        if successful_batch:
            batch_durations = [r["duration"] for r in successful_batch]
            print(f"\nBatch Embedding ({len(successful_batch)} successful):")
            print(f"  Average: {statistics.mean(batch_durations):.3f}s")
            print(f"  Median:  {statistics.median(batch_durations):.3f}s")
            print(f"  Min:     {min(batch_durations):.3f}s")
            print(f"  Max:     {max(batch_durations):.3f}s")
            print(f"  Std Dev: {statistics.stdev(batch_durations):.3f}s")
        
        # Search statistics
        successful_search = [r for r in search_results if r["success"]]
        if successful_search:
            search_durations = [r["duration"] for r in successful_search]
            print(f"\nVector Search ({len(successful_search)} successful):")
            print(f"  Average: {statistics.mean(search_durations):.3f}s")
            print(f"  Median:  {statistics.median(search_durations):.3f}s")
            print(f"  Min:     {min(search_durations):.3f}s")
            print(f"  Max:     {max(search_durations):.3f}s")
            print(f"  Std Dev: {statistics.stdev(search_durations):.3f}s")
        
        # Success rates
        total_tests = len(single_results) + len(batch_results) + len(search_results)
        successful_tests = len(successful_single) + len(successful_batch) + len(successful_search)
        success_rate = (successful_tests / total_tests) * 100
        
        print(f"\nOverall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")


async def main():
    """Main function to run performance test."""
    tester = RAGPerformanceTest()
    await tester.run_performance_test(num_tests=5)


if __name__ == "__main__":
    asyncio.run(main())
