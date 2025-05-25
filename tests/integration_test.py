import asyncio
import aiohttp
import pytest
import time
import os
from typing import Dict, List

class IntegrationTester:
    """Comprehensive integration testing for the LLM service"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    async def test_health_endpoint(self) -> Dict:
        """Test the health endpoint"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                data = await response.json()
                return {
                    "test": "health_check",
                    "status": response.status,
                    "passed": response.status == 200 and data.get("status") == "healthy",
                    "details": data
                }
    
    async def test_query_expansion_basic(self) -> Dict:
        """Test basic query expansion functionality"""
        test_query = "ML algos"
        payload = {"query": test_query, "use_queue": False}
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.post(
                f"{self.base_url}/expand", 
                json=payload
            ) as response:
                end_time = time.time()
                data = await response.json()
                
                # Check if expansion actually improved the query
                expanded = data.get("expanded_query", "")
                improved = len(expanded) > len(test_query) and expanded != test_query
                
                return {
                    "test": "basic_expansion",
                    "status": response.status,
                    "passed": response.status == 200 and improved,
                    "response_time": end_time - start_time,
                    "original": test_query,
                    "expanded": expanded,
                    "details": data
                }
    
    async def test_query_expansion_edge_cases(self) -> List[Dict]:
        """Test edge cases for query expansion"""
        test_cases = [
            ("", "empty_query"),
            ("a", "single_char"),
            ("AI ML DL NLP CV", "all_abbreviations"),
            ("artificial intelligence machine learning", "already_expanded"),
            ("x" * 500, "very_long_query"),
            ("123 456 789", "numeric_query"),
            ("ëxãmplê quérÿ", "unicode_query")
        ]
        
        results = []
        async with aiohttp.ClientSession() as session:
            for query, test_name in test_cases:
                try:
                    payload = {"query": query, "use_queue": False}
                    async with session.post(
                        f"{self.base_url}/expand", 
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        data = await response.json()
                        results.append({
                            "test": f"edge_case_{test_name}",
                            "status": response.status,
                            "passed": response.status == 200,
                            "query": query,
                            "expanded": data.get("expanded_query", ""),
                            "details": data
                        })
                except Exception as e:
                    results.append({
                        "test": f"edge_case_{test_name}",
                        "status": 0,
                        "passed": False,
                        "query": query,
                        "error": str(e)
                    })
        
        return results
    
    async def test_concurrent_requests(self, num_requests: int = 20) -> Dict:
        """Test concurrent request handling"""
        test_queries = [
            f"test query {i}" for i in range(num_requests)
        ]
        
        async def make_request(session, query):
            payload = {"query": query, "use_queue": False}
            start_time = time.time()
            async with session.post(f"{self.base_url}/expand", json=payload) as response:
                end_time = time.time()
                return {
                    "status": response.status,
                    "response_time": end_time - start_time,
                    "success": response.status == 200
                }
        
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            results = await asyncio.gather(
                *[make_request(session, query) for query in test_queries],
                return_exceptions=True
            )
            end_time = time.time()
            
            successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            
            return {
                "test": "concurrent_requests",
                "total_requests": num_requests,
                "successful": successful,
                "failed": num_requests - successful,
                "success_rate": successful / num_requests,
                "total_time": end_time - start_time,
                "passed": successful >= num_requests * 0.95  # 95% success rate
            }
    
    async def test_queue_functionality(self) -> Dict:
        """Test SQS queue functionality"""
        test_query = "test queue query"
        payload = {"query": test_query, "use_queue": True}
        
        async with aiohttp.ClientSession() as session:
            # Test queue endpoint
            async with session.post(f"{self.base_url}/expand", json=payload) as response:
                data = await response.json()
                queued_test = {
                    "status": response.status,
                    "queued": data.get("queued", False),
                    "passed": response.status == 200
                }
            
            # Test queue status endpoint
            async with session.get(f"{self.base_url}/queue/status") as response:
                status_data = await response.json()
                status_test = {
                    "status": response.status,
                    "queue_enabled": status_data.get("queue_enabled", False),
                    "passed": response.status == 200
                }
            
            return {
                "test": "queue_functionality",
                "queue_request": queued_test,
                "status_check": status_test,
                "passed": queued_test["passed"] and status_test["passed"]
            }
    
    async def test_metrics_endpoint(self) -> Dict:
        """Test Prometheus metrics endpoint"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/metrics") as response:
                text = await response.text()
                
                # Check for key metrics
                required_metrics = [
                    "requests_total",
                    "request_duration_seconds",
                    "errors_total"
                ]
                
                metrics_present = all(metric in text for metric in required_metrics)
                
                return {
                    "test": "metrics_endpoint",
                    "status": response.status,
                    "metrics_present": metrics_present,
                    "passed": response.status == 200 and metrics_present,
                    "content_length": len(text)
                }
    
    async def run_all_tests(self) -> Dict:
        """Run all integration tests"""
        print(f"Running integration tests against {self.base_url}")
        
        all_results = {}
        
        # Run individual tests
        all_results["health"] = await self.test_health_endpoint()
        all_results["basic_expansion"] = await self.test_query_expansion_basic()
        all_results["edge_cases"] = await self.test_query_expansion_edge_cases()
        all_results["concurrent"] = await self.test_concurrent_requests()
        all_results["queue"] = await self.test_queue_functionality()
        all_results["metrics"] = await self.test_metrics_endpoint()
        
        # Calculate overall results
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in all_results.items():
            if test_name == "edge_cases":
                # Handle list of results
                for edge_result in result:
                    total_tests += 1
                    if edge_result["passed"]:
                        passed_tests += 1
            else:
                total_tests += 1
                if result["passed"]:
                    passed_tests += 1
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "overall_passed": passed_tests == total_tests
        }
        
        return all_results

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument("--url", required=True, help="Base URL of the service")
    args = parser.parse_args()
    
    tester = IntegrationTester(args.url)
    results = await tester.run_all_tests()
    
    # Print results
    print("\n" + "="*50)
    print("INTEGRATION TEST RESULTS")
    print("="*50)
    
    for test_name, result in results.items():
        if test_name == "summary":
            continue
        elif test_name == "edge_cases":
            print(f"\nEdge Cases:")
            for edge_result in result:
                status = "✓" if edge_result["passed"] else "✗"
                print(f"  {status} {edge_result['test']}")
        else:
            status = "✓" if result["passed"] else "✗"
            print(f"{status} {test_name}: {result.get('status', 'N/A')}")
    
    summary = results["summary"]
    print(f"\n{'='*50}")
    print(f"SUMMARY: {summary['passed_tests']}/{summary['total_tests']} tests passed")
    print(f"Success rate: {summary['success_rate']:.1%}")
    print(f"Overall result: {'PASS' if summary['overall_passed'] else 'FAIL'}")
    
    # Exit with error code if tests failed
    if not summary['overall_passed']:
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())