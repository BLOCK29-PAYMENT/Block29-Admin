import requests
import sys
import json
from datetime import datetime

class SalonBookinAPITester:
    def __init__(self, base_url="https://stylist-dashboard-5.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test(name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_login(self):
        """Test login with default credentials"""
        print("\n🔐 Testing Authentication...")
        success, response = self.run_test(
            "Login with admin credentials",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@salonbookin.com", "password": "admin123"}
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.log_test("Token extraction", True, f"User: {response.get('user', {}).get('name', 'Unknown')}")
            return True
        else:
            self.log_test("Token extraction", False, "No token in response")
            return False

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        print("\n📊 Testing Dashboard...")
        success, response = self.run_test(
            "GET /api/dashboard/stats",
            "GET",
            "dashboard/stats",
            200
        )
        
        if success:
            merchants = response.get('merchants', {})
            terminals = response.get('terminals', {})
            transactions = response.get('transactions', {})
            
            self.log_test("Dashboard data structure", True, 
                         f"Merchants: {merchants.get('total', 0)}, Terminals: {terminals.get('total', 0)}, Transactions: {transactions.get('total', 0)}")
        
        return success

    def test_merchants_crud(self):
        """Test merchant CRUD operations"""
        print("\n🏪 Testing Merchants...")
        
        # Test GET merchants
        success, merchants = self.run_test(
            "GET /api/merchants",
            "GET",
            "merchants",
            200
        )
        
        if not success:
            return False
        
        # Test POST merchant
        merchant_data = {
            "business_name": f"Test Business {datetime.now().strftime('%H%M%S')}",
            "dba": "Test DBA",
            "tax_id": "123456789",
            "contact_email": "test@example.com",
            "contact_phone": "555-0123",
            "address": "123 Test St",
            "status": "pending"
        }
        
        success, new_merchant = self.run_test(
            "POST /api/merchants (create merchant)",
            "POST",
            "merchants",
            200,
            data=merchant_data
        )
        
        if success and 'id' in new_merchant:
            merchant_id = new_merchant['id']
            self.log_test("Merchant creation", True, f"Created merchant ID: {merchant_id}")
            
            # Test GET specific merchant
            self.run_test(
                f"GET /api/merchants/{merchant_id}",
                "GET",
                f"merchants/{merchant_id}",
                200
            )
            
            # Test PUT merchant update
            update_data = {"status": "active"}
            self.run_test(
                f"PUT /api/merchants/{merchant_id}",
                "PUT",
                f"merchants/{merchant_id}",
                200,
                data=update_data
            )
            
            return True
        
        return False

    def test_terminals_crud(self):
        """Test terminal CRUD operations"""
        print("\n💻 Testing Terminals...")
        
        # First get merchants to use one for terminal creation
        success, merchants = self.run_test(
            "GET merchants for terminal test",
            "GET",
            "merchants",
            200
        )
        
        if not success or not merchants:
            self.log_test("Terminal test setup", False, "No merchants available")
            return False
        
        merchant_id = merchants[0]['id'] if merchants else None
        if not merchant_id:
            self.log_test("Terminal test setup", False, "No merchant ID found")
            return False
        
        # Test GET terminals
        success, terminals = self.run_test(
            "GET /api/admin/terminals",
            "GET",
            "admin/terminals",
            200
        )
        
        if not success:
            return False
        
        # Test POST terminal
        terminal_data = {
            "merchant_id": merchant_id,
            "provider": "luqra",
            "terminal_number": f"TRM{datetime.now().strftime('%H%M%S')}",
            "v_number": f"V{datetime.now().strftime('%H%M%S')}",
            "merchant_number": f"MER{datetime.now().strftime('%H%M%S')}",
            "bin": "123456",
            "provisioning_status": "draft"
        }
        
        success, new_terminal = self.run_test(
            "POST /api/admin/terminals (create terminal)",
            "POST",
            "admin/terminals",
            200,
            data=terminal_data
        )
        
        if success and 'id' in new_terminal:
            terminal_id = new_terminal['id']
            self.log_test("Terminal creation", True, f"Created terminal ID: {terminal_id}")
            return True
        
        return False

    def test_block29_provision(self):
        """Test Block29 gateway provisioning"""
        print("\n🔗 Testing Block29 Gateway...")
        
        # Get merchants first
        success, merchants = self.run_test(
            "GET merchants for Block29 test",
            "GET",
            "merchants",
            200
        )
        
        if not success or not merchants:
            self.log_test("Block29 test setup", False, "No merchants available")
            return False
        
        merchant_id = merchants[0]['id']
        
        # Test Block29 provision
        provision_data = {
            "merchant_id": merchant_id,
            "processor": "clover",
            "terminal_data": {
                "terminal_id": "TEST123",
                "location": "Test Location"
            }
        }
        
        success, response = self.run_test(
            "POST /api/block29/provision-terminal",
            "POST",
            "block29/provision-terminal",
            200,
            data=provision_data
        )
        
        if success:
            self.log_test("Block29 provisioning", True, f"Provision ID: {response.get('provision_id', 'Unknown')}")
        
        return success

    def test_varsheets(self):
        """Test VAR sheet endpoints"""
        print("\n📄 Testing VAR Sheets...")
        
        # Test GET varsheets
        success, varsheets = self.run_test(
            "GET /api/admin/varsheets",
            "GET",
            "admin/varsheets",
            200
        )
        
        return success

    def test_users_and_roles(self):
        """Test user management endpoints"""
        print("\n👥 Testing Users & Roles...")
        
        # Test GET users (requires SUPER_ADMIN role)
        success, users = self.run_test(
            "GET /api/users",
            "GET",
            "users",
            200
        )
        
        return success

    def test_transactions(self):
        """Test transaction endpoints"""
        print("\n💳 Testing Transactions...")
        
        # Test GET transactions
        success, transactions = self.run_test(
            "GET /api/transactions",
            "GET",
            "transactions",
            200
        )
        
        return success

    def test_agents(self):
        """Test agent/affiliate endpoints"""
        print("\n🤝 Testing Agents & Affiliates...")
        
        # Test GET agents
        success, agents = self.run_test(
            "GET /api/agents",
            "GET",
            "agents",
            200
        )
        
        return success

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting SalonBookin Admin API Tests")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)
        
        # Authentication is required for all other tests
        if not self.test_login():
            print("\n❌ Authentication failed - stopping tests")
            return False
        
        # Run all test suites
        test_suites = [
            self.test_dashboard_stats,
            self.test_merchants_crud,
            self.test_terminals_crud,
            self.test_block29_provision,
            self.test_varsheets,
            self.test_users_and_roles,
            self.test_transactions,
            self.test_agents
        ]
        
        for test_suite in test_suites:
            try:
                test_suite()
            except Exception as e:
                print(f"❌ Test suite failed with exception: {e}")
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = SalonBookinAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/test_reports/backend_test_results.json', 'w') as f:
        json.dump({
            "summary": {
                "total_tests": tester.tests_run,
                "passed_tests": tester.tests_passed,
                "success_rate": (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "detailed_results": tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())