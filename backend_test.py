import requests
import sys
import json
from datetime import datetime, timedelta

class SalonBookinAPITester:
    def __init__(self, base_url="https://stylist-dashboard-5.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.merchant_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.content else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

def main():
    print("🚀 Starting SalonBookin Admin Platform API Tests")
    print("=" * 60)
    
    tester = SalonBookinAPITester()
    
    # Test 1: Health Check
    success, _ = tester.run_test("Health Check", "GET", "health", 200)
    
    # Test 2: Admin Login
    success, response = tester.run_test(
        "Admin Login", "POST", "auth/login", 200,
        data={"email": "admin@salonbookin.com", "password": "admin123"}
    )
    if success and 'token' in response:
        tester.token = response['token']
        print(f"   Token obtained: {tester.token[:20]}...")
    else:
        print("❌ Login failed - cannot continue")
        return 1
    
    # Test 3: Create Merchant
    merchant_data = {
        "business_name": "Test Salon",
        "dba": "Test Salon DBA", 
        "status": "active"
    }
    success, response = tester.run_test(
        "Create Test Merchant", "POST", "merchants", 200, data=merchant_data
    )
    if success and 'id' in response:
        tester.merchant_id = response['id']
        print(f"   Merchant ID: {tester.merchant_id}")
    
    # Test 4: Virtual Terminal Process
    if tester.merchant_id:
        transaction_data = {
            "merchant_id": tester.merchant_id,
            "transaction_type": "sale",
            "amount": 25.99,
            "card_number": "4111111111111111",
            "card_expiry": "12/25",
            "card_cvv": "123",
            "cardholder_name": "John Doe"
        }
        tester.run_test(
            "Virtual Terminal Process", "POST", "virtual-terminal/process", 200, 
            data=transaction_data
        )
    
    # Test 5: Transaction Report
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    params = f"start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
    tester.run_test("Transaction Report", "GET", f"reports/transactions?{params}", 200)
    
    # Test 6: Batch Report
    tester.run_test("Batch Report", "GET", f"reports/batches?{params}", 200)
    
    # Test 7: Settlement Report
    tester.run_test("Settlement Report", "GET", f"reports/settlement?{params}", 200)
    
    # Test 8: Export CSV
    tester.run_test("Export CSV", "GET", f"reports/export?{params}", 200)
    
    # Test 9: System Logs
    tester.run_test("System Logs", "GET", "logs?limit=50", 200)
    
    # Test 10: Log Actions
    tester.run_test("Log Action Types", "GET", "logs/actions", 200)
    
    # Test 11: List Merchants
    tester.run_test("List Merchants", "GET", "merchants", 200)
    
    # Test 12: Dashboard Stats
    tester.run_test("Dashboard Stats", "GET", "dashboard/stats", 200)
    
    # Print results summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"📈 Overall: {tester.tests_passed}/{tester.tests_run} tests passed")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📊 Success Rate: {success_rate:.1f}%")
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": tester.tests_run,
        "passed_tests": tester.tests_passed,
        "success_rate": success_rate
    }
    
    with open('/app/test_reports/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())