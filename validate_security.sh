#!/bin/bash
# Security Phase 0 Validation Script

echo "🔍 Validating MindFlow Security Phase 0 Implementation..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}❌${NC} $2 - File not found: $1"
        ((FAILED++))
    fi
}

# Function to check directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}❌${NC} $2 - Directory not found: $1"
        ((FAILED++))
    fi
}

# Function to check command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✅${NC} $2"
        ((PASSED++))
    else
        echo -e "${RED}❌${NC} $2 - Command not found: $1"
        ((FAILED++))
    fi
}

echo "📁 Checking Directory Structure..."
check_dir "python/mindflow_backend/security" "Security root directory"
check_dir "python/mindflow_backend/security/sandbox" "Sandbox directory"
check_dir "python/mindflow_backend/security/secrets" "Secrets directory"
check_dir "python/mindflow_backend/security/validators" "Validators directory"
check_dir "python/mindflow_backend/security/policies" "Policies directory"
check_dir "python/mindflow_backend/security/auth" "Auth directory"
check_dir "python/mindflow_backend/security/audit" "Audit directory"
echo ""

echo "📄 Checking Implementation Files..."
check_file "python/mindflow_backend/security/sandbox/docker_sandbox.py" "Docker Sandbox"
check_file "python/mindflow_backend/security/secrets/scanner.py" "Secret Scanner"
check_file "python/mindflow_backend/security/validators/bash_validators.py" "Bash Validators"
check_file "python/mindflow_backend/security/policies/network_policy.py" "Network Policy"
check_file "python/mindflow_backend/security/auth/jwt_secret.py" "JWT Secret Manager"
check_file "python/mindflow_backend/security/audit/security_logger.py" "Security Logger"
check_file "python/mindflow_backend/security/tools/shell_executor_v2.py" "Enhanced Shell Executor"
echo ""

echo "🧪 Checking Test Files..."
check_file "python/tests/security/test_docker_sandbox.py" "Docker Sandbox Tests"
check_file "python/tests/security/test_secret_scanner.py" "Secret Scanner Tests"
check_file "python/tests/security/test_bash_validators.py" "Bash Validators Tests"
check_file "python/tests/security/test_network_policy.py" "Network Policy Tests"
echo ""

echo "🐳 Checking Docker..."
check_command "docker" "Docker installed"
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✅${NC} Docker daemon running"
        ((PASSED++))
    else
        echo -e "${RED}❌${NC} Docker daemon not running"
        ((FAILED++))
    fi
fi
echo ""

echo "🔑 Checking Environment Variables..."
if [ -f ".env" ]; then
    if grep -q "JWT_SECRET_KEY" .env; then
        echo -e "${GREEN}✅${NC} JWT_SECRET_KEY configured in .env"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠️${NC}  JWT_SECRET_KEY not found in .env (will use fallback)"
    fi
else
    echo -e "${YELLOW}⚠️${NC}  .env file not found (will use fallback)"
fi
echo ""

echo "📦 Checking Dependencies..."
cd python
if uv pip list | grep -q "docker"; then
    echo -e "${GREEN}✅${NC} Docker Python library installed"
    ((PASSED++))
else
    echo -e "${RED}❌${NC} Docker Python library not installed"
    ((FAILED++))
fi
cd ..
echo ""

echo "🧪 Running Security Tests..."
cd python
if pytest tests/security/ -v --tb=short 2>&1 | tee /tmp/security_tests.log; then
    echo -e "${GREEN}✅${NC} All security tests passed"
    ((PASSED++))
else
    echo -e "${RED}❌${NC} Some security tests failed"
    ((FAILED++))
fi
cd ..
echo ""

echo "================================================"
echo "📊 Validation Summary"
echo "================================================"
echo -e "Passed: ${GREEN}${PASSED}${NC}"
echo -e "Failed: ${RED}${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 Phase 0 Implementation: COMPLETE${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Set JWT_SECRET_KEY in .env (if not already set)"
    echo "2. Review security logs in production"
    echo "3. Monitor Docker sandbox performance"
    echo "4. Plan Phase 1 implementation"
    exit 0
else
    echo -e "${RED}❌ Phase 0 Implementation: INCOMPLETE${NC}"
    echo ""
    echo "Please fix the failed checks above."
    exit 1
fi
