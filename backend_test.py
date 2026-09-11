import os
import requests
import sys
import json
from datetime import datetime, timedelta

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8001").rstrip("/") + "/api"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@salonbookin.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


class Block29AdminAPITester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.merchant_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, use_token=True):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if use_token and self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.content else {}
                except Exception:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}


def main():
    print("🚀 Starting Block29 Admin Platform API Tests")
    print("=" * 60)

    tester = Block29AdminAPITester()

    # Health check
    tester.run_test("Health Check", "GET", "health", 200)

    # Security: register must NOT be open to unauthenticated callers
    tester.run_test(
        "Register requires auth", "POST", "auth/register", 403,
        data={"email": "attacker@example.com", "password": "x", "name": "x", "role": "SUPER_ADMIN"},
        use_token=False
    )

    # Admin login
    success, response = tester.run_test(
        "Admin Login", "POST", "auth/login", 200,
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if success and 'token' in response:
        tester.token = response['token']
        print(f"   Token obtained: {tester.token[:20]}...")
    else:
        print("❌ Login failed - cannot continue")
        return 1

    # Merchants
    success, response = tester.run_test(
        "Create Test Merchant", "POST", "merchants", 200,
        data={"business_name": "Test Merchant", "dba": "Test DBA", "status": "active"}
    )
    if success and 'id' in response:
        tester.merchant_id = response['id']
        print(f"   Merchant ID: {tester.merchant_id}")

    tester.run_test("List Merchants", "GET", "merchants", 200)

    # Removed features must stay removed
    tester.run_test("Virtual terminal is gone", "POST", "virtual-terminal/process", 404, data={})
    tester.run_test("Block29 gateway stub is gone", "GET", "block29/provisions", 404)
    tester.run_test("Agents stub is gone", "GET", "agents", 404)

    # Reports
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    params = f"start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
    tester.run_test("Transaction Report", "GET", f"reports/transactions?{params}", 200)
    tester.run_test("Batch Report", "GET", f"reports/batches?{params}", 200)
    tester.run_test("Settlement report is gone", "GET", f"reports/settlement?{params}", 404)
    tester.run_test("Export CSV", "GET", f"reports/export?{params}", 200)

    # Logs + dashboard
    tester.run_test("System Logs", "GET", "logs?limit=50", 200)
    tester.run_test("Log Action Types", "GET", "logs/actions", 200)
    tester.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)

    # Cleanup test merchant (no terminals/transactions attached, so delete is allowed)
    if tester.merchant_id:
        tester.run_test("Delete Test Merchant", "DELETE", f"merchants/{tester.merchant_id}", 200)

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"📈 Overall: {tester.tests_passed}/{tester.tests_run} tests passed")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📊 Success Rate: {success_rate:.1f}%")

    results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": tester.tests_run,
        "passed_tests": tester.tests_passed,
        "success_rate": success_rate
    }

    os.makedirs("test_reports", exist_ok=True)
    with open('test_reports/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    return 0 if tester.tests_passed == tester.tests_run else 1


if __name__ == "__main__":
    sys.exit(main())
