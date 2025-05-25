import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import argparse
import json

class LoadTester:
    def __init__(self, base_url: str, concurrent_users: int = 10, total_requests: int = 100):
        self.base_url = base_url.rstrip('/')
        self.concurrent_users = concurrent_users
        self.total_requests = total_requests
        self.results = []
        
        self.test_queries = [
            "ML algos",
            "AI/ML enginer jobs",
            "deep lerning models",
            "computer vison applications",
            "NLP techniques",
            "reinforcment learning",
            "neural netwrks training",
            "data science projects",
            "machine learning piplines",
            "artificial inteligence research"
        ]
    
    async def make_request(self, session: aiohttp.ClientSession, query: str):
        """Make a single request and measure response time"""
        start_time = time.time()
        try:
            payload = {"query": query, "use_queue": False}
            async with session.post(
                f"{self.base_url}/expand",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_time = time.time()
                response_data = await response.json()
                
                result = {
                    "status_code": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200,
                    "original_query": query,
                    "expanded_query": response_data.get("expanded_query", ""),
                    "processing_time": response_data.get("processing_time", 0)
                }
                return result
                
        except Exception as e:
            end_time = time.time()
            return {
                "status_code": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e),
                "original_query": query
            }
    
    async def run_load_test(self):
        """Run the load test"""
        print(f"Starting load test: {self.concurrent_users} concurrent users, {self.total_requests} total requests")
        
        connector = aiohttp.TCPConnector(limit=self.concurrent_users * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(self.concurrent_users)
            
            async def bounded_request(query):
                async with semaphore:
                    return await self.make_request(session, query)
            
            # Generate requests
            tasks = []
            for i in range(self.total_requests):
                query = self.test_queries[i % len(self.test_queries)]
                tasks.append(bounded_request(query))
            
            # Execute requests
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Process results
            valid_results = [r for r in results if isinstance(r, dict)]
            self.results = valid_results
            
            # Print summary
            self.print_summary(end_time - start_time)
    
    def print_summary(self, total_time: float):
        """Print test summary"""
        if not self.results:
            print("No valid results to analyze")
            return
        
        successful_requests = [r for r in self.results if r["success"]]
        failed_requests = [r for r in self.results if not r["success"]]
        
        response_times = [r["response_time"] for r in successful_requests]
        processing_times = [r["processing_time"] for r in successful_requests if "processing_time" in r]
        
        print("\n" + "="*50)
        print("LOAD TEST SUMMARY")
        print("="*50)
        print(f"Total requests: {len(self.results)}")
        print(f"Successful requests: {len(successful_requests)}")
        print(f"Failed requests: {len(failed_requests)}")
        print(f"Success rate: {len(successful_requests)/len(self.results)*100:.2f}%")
        print(f"Total test time: {total_time:.2f} seconds")
        print(f"Requests per second: {len(self.results)/total_time:.2f}")
        
        if response_times:
            print(f"\nResponse Time Statistics:")
            print(f"  Mean: {statistics.mean(response_times):.3f}s")
            print(f"  Median: {statistics.median(response_times):.3f}s")
            print(f"  Min: {min(response_times):.3f}s")
            print(f"  Max: {max(response_times):.3f}s")
            print(f"  95th percentile: {sorted(response_times)[int(len(response_times)*0.95)]:.3f}s")
        
        if processing_times:
            print(f"\nModel Processing Time Statistics:")
            print(f"  Mean: {statistics.mean(processing_times):.3f}s")
            print(f"  Median: {statistics.median(processing_times):.3f}s")
            print(f"  Min: {min(processing_times):.3f}s")
            print(f"  Max: {max(processing_times):.3f}s")
        
        if failed_requests:
            print(f"\nFailure Analysis:")
            error_types = {}
            for req in failed_requests:
                error = req.get("error", f"HTTP {req['status_code']}")
                error_types[error] = error_types.get(error, 0) + 1
            
            for error, count in error_types.items():
                print(f"  {error}: {count} occurrences")

async def main():
    parser = argparse.ArgumentParser(description="Load test the LLM API")
    parser.add_argument("--url", required=True, help="Base URL of the API")
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--requests", type=int, default=100, help="Total number of requests")
    
    args = parser.parse_args()
    
    tester = LoadTester(args.url, args.users, args.requests)
    await tester.run_load_test()

if __name__ == "__main__":
    asyncio.run(main())