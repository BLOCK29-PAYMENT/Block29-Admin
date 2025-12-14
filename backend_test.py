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

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

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

    def test_health_check(self):
        """Test basic health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_login(self):
        """Test admin login"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@salonbookin.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            print(f"   Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_create_merchant(self):
        """Create a test merchant for virtual terminal"""
        merchant_data = {
            "business_name": "Test Salon",
            "dba": "Test Salon DBA",
            "tax_id": "12-3456789",
            "contact_email": "test@testsalon.com",
            "contact_phone": "(555) 123-4567",
            "address": "123 Test St, Test City, TS 12345",
            "status": "active"
        }
        success, response = self.run_test(
            "Create Test Merchant",
            "POST",
            "merchants",
            200,  # Backend returns 200, not 201
            data=merchant_data
        )
        if success and 'id' in response:
            self.merchant_id = response['id']
            print(f"   Merchant ID: {self.merchant_id}")
            return True
        return False

    def test_virtual_terminal_process(self):
        """Test virtual terminal transaction processing"""
        if not self.merchant_id:
            print("❌ No merchant ID available for virtual terminal test")
            return False
            
        transaction_data = {
            "merchant_id": self.merchant_id,
            "transaction_type": "sale",
            "amount": 25.99,
            "card_number": "4111111111111111",
            "card_expiry": "12/25",
            "card_cvv": "123",
            "cardholder_name": "John Doe",
            "customer_email": "john@example.com",
            "customer_phone": "(555) 987-6543",
            "description": "Test transaction"
        }
        return self.run_test(
            "Virtual Terminal Process",
            "POST",
            "virtual-terminal/process",
            200,
            data=transaction_data
        )

    def test_transaction_reports(self):
        """Test transaction reports API"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = f"start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        return self.run_test(
            "Transaction Report",
            "GET",
            f"reports/transactions?{params}",
            200
        )

    def test_batch_reports(self):
        """Test batch reports API"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = f"start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        return self.run_test(
            "Batch Report",
            "GET",
            f"reports/batches?{params}",
            200
        )

    def test_settlement_reports(self):
        """Test settlement reports API"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = f"start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        return self.run_test(
            "Settlement Report",
            "GET",
            f"reports/settlement?{params}",
            200
        )

    def test_export_csv(self):
        """Test CSV export functionality"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = f"start_date={start_date.isoformat()}&end_date={end_date.isoformat()}"
        return self.run_test(
            "Export CSV",
            "GET",
            f"reports/export?{params}",
            200
        )

    def test_system_logs(self):
        """Test system logs API"""
        return self.run_test(
            "System Logs",
            "GET",
            "logs?limit=50",
            200
        )

    def test_log_actions(self):
        """Test log action types API"""
        return self.run_test(
            "Log Action Types",
            "GET",
            "logs/actions",
            200
        )

    def test_merchants_list(self):
        """Test merchants listing"""
        return self.run_test(
            "List Merchants",
            "GET",
            "merchants",
            200
        )

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        return self.run_test(
            "Dashboard Stats",
            "GET",
            "dashboard/stats",
            200
        )

def main():
    print("🚀 Starting SalonBookin Admin Platform API Tests")
    print("=" * 60)
    
    tester = SalonBookinAPITester()
    
    # Test sequence
    test_results = []
    
    # Basic connectivity
    success, _ = tester.test_health_check()
    test_results.append(("Health Check", success))
    
    # Authentication
    if not tester.test_login():
        print("\n❌ Login failed - cannot continue with authenticated tests")
        return 1
    test_results.append(("Admin Login", True))
    
    # Create test merchant for virtual terminal
    success, _ = tester.test_create_merchant()
    test_results.append(("Create Merchant", success))
    
    # Virtual Terminal Tests
    success, _ = tester.test_virtual_terminal_process()
    test_results.append(("Virtual Terminal Process", success))
    
    # Reports Tests
    success, _ = tester.test_transaction_reports()
    test_results.append(("Transaction Report", success))
    
    success, _ = tester.test_batch_reports()
    test_results.append(("Batch Report", success))
    
    success, _ = tester.test_settlement_reports()
    test_results.append(("Settlement Report", success))
    
    success, _ = tester.test_export_csv()
    test_results.append(("Export CSV", success))
    
    # System Logs Tests
    success, _ = tester.test_system_logs()
    test_results.append(("System Logs", success))
    
    success, _ = tester.test_log_actions()
    test_results.append(("Log Action Types", success))
    
    # Additional API Tests
    success, _ = tester.test_merchants_list()
    test_results.append(("List Merchants", success))
    
    success, _ = tester.test_dashboard_stats()
    test_results.append(("Dashboard Stats", success))
    
    # Print results summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📈 Overall: {tester.tests_passed}/{tester.tests_run} tests passed")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📊 Success Rate: {success_rate:.1f}%")
    
    # Save results to file
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": tester.tests_run,
        "passed_tests": tester.tests_passed,
        "success_rate": success_rate,
        "test_details": [{"name": name, "passed": passed} for name, passed in test_results]
    }
    
    with open('/app/test_reports/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())