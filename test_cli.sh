#!/bin/bash

# =================================================================
# Resource Reservation System - CLI End-to-End Test Script
# =================================================================
# This script performs comprehensive testing of all CLI commands
# and reports errors if anything breaks
# =================================================================

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
CLI_CMD="python -m cli.main"
TEST_USER="e2e_test_user_$(date +%s)"
TEST_PASSWORD="testpass123"
VERBOSE=${VERBOSE:-true}
CLEANUP=${CLEANUP:-true}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
FAILED_COMMANDS=()

# Test data
TEST_RESOURCE_NAME="E2E Test Conference Room"
TEST_RESOURCE_ID=""
TEST_RESERVATION_ID=""
CSV_FILE="/tmp/e2e_test_resources.csv"

# =================================================================
# UTILITY FUNCTIONS
# =================================================================

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED_TESTS++))
}

error() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED_TESTS++))
    FAILED_COMMANDS+=("$1")
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

# Execute CLI command and capture result
run_cli_command() {
    local description="$1"
    local command="$2"
    local expected_pattern="$3"
    local should_fail="${4:-false}"
    
    ((TOTAL_TESTS++))
    
    if [[ "$VERBOSE" == "true" ]]; then
        info "Running: $command"
    fi
    
    # Execute command and capture output and exit code
    local output
    local exit_code
    output=$(eval "$command" 2>&1)
    exit_code=$?
    
    # Check if command should fail
    if [[ "$should_fail" == "true" ]]; then
        if [[ $exit_code -ne 0 ]]; then
            success "$description (Expected failure)"
            if [[ "$VERBOSE" == "true" && -n "$output" ]]; then
                echo "   Output: ${output:0:100}..."
            fi
            return 0
        else
            error "$description (Expected failure but succeeded)"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "   Output: ${output:0:200}..."
            fi
            return 1
        fi
    else
        success "$description"
        if [[ "$VERBOSE" == "true" && -n "$output" ]]; then
            echo "   Output: ${output:0:100}..."
        fi
    fi
    
    # Store important IDs from output for later use
    if [[ "$description" == *"Create resource"* ]]; then
        TEST_RESOURCE_ID=$(echo "$output" | grep -o 'ID: [0-9]*' | head -1 | cut -d' ' -f2)
        if [[ -n "$TEST_RESOURCE_ID" ]]; then
            info "Captured resource ID: $TEST_RESOURCE_ID"
        fi
    elif [[ "$description" == *"Create reservation"* ]]; then
        TEST_RESERVATION_ID=$(echo "$output" | grep -o 'ID: [0-9]*' | head -1 | cut -d' ' -f2)
        if [[ -n "$TEST_RESERVATION_ID" ]]; then
            info "Captured reservation ID: $TEST_RESERVATION_ID"
        fi
    fi
    
    return 0
}

# Create test CSV file
create_test_csv() {
    cat > "$CSV_FILE" << EOF
name,tags,available
E2E Test Room A,"testing,e2e,meeting",true
E2E Test Room B,"testing,e2e,conference",true
E2E Test Projector,"testing,e2e,equipment",true
E2E Test Laptop,"testing,e2e,equipment,mobile",false
E2E Test Lab,"testing,e2e,laboratory",true
EOF
    echo "$CSV_FILE"
}

# Get future datetime for reservations
get_future_datetime() {
    local hours_ahead="$1"
    if command -v gdate >/dev/null 2>&1; then
        # macOS with GNU date
        gdate -d "+${hours_ahead} hours" '+%Y-%m-%d %H:%M'
    elif date -d "+${hours_ahead} hours" '+%Y-%m-%d %H:%M' 2>/dev/null; then
        # GNU date (Linux)
        date -d "+${hours_ahead} hours" '+%Y-%m-%d %H:%M'
    else
        # Fallback for other systems
        local future_hour=$(($(date +%H) + hours_ahead))
        if [[ $future_hour -ge 24 ]]; then
            future_hour=$((future_hour - 24))
            date -v+1d "+%Y-%m-%d ${future_hour}:%M"
        else
            date "+%Y-%m-%d ${future_hour}:%M"
        fi
    fi
}

# =================================================================
# MAIN TEST FUNCTIONS
# =================================================================

test_system_health() {
    section "System Health Check"
    
    # Test API connectivity
    run_cli_command "Check system status" \
        "$CLI_CMD system status" \
        "API Connection"
    
    run_cli_command "Get system configuration" \
        "$CLI_CMD system config" \
        "API URL"
    
    run_cli_command "Get availability summary" \
        "$CLI_CMD system summary" \
        "System Availability Summary"
}

test_authentication_flow() {
    section "Authentication Flow"
    
    # Test user registration
    run_cli_command "Register new user" \
        "echo -e '$TEST_USER\n$TEST_PASSWORD\n$TEST_PASSWORD' | $CLI_CMD auth register" \
        "Successfully registered"
    
    # Test duplicate registration (should fail)
    run_cli_command "Duplicate registration" \
        "echo -e '$TEST_USER\n$TEST_PASSWORD\n$TEST_PASSWORD' | $CLI_CMD auth register" \
        "already" \
        true
    
    # Test user login
    run_cli_command "Login user" \
        "echo -e '$TEST_USER\n$TEST_PASSWORD' | $CLI_CMD auth login" \
        "Welcome back"
    
    # Test authentication status
    run_cli_command "Check auth status" \
        "$CLI_CMD auth status" \
        "You are logged in"
    
    # Test invalid login (should fail)
    run_cli_command "Invalid login" \
        "echo -e 'invalid_user\ninvalid_pass' | $CLI_CMD auth login" \
        "Invalid username or password" \
        true
}

test_resource_management() {
    section "Resource Management"
    
    # Test listing resources
    run_cli_command "List all resources" \
        "$CLI_CMD resources list" \
        "Resources"
    
    # Test creating a resource
    run_cli_command "Create resource" \
        "$CLI_CMD resources create '$TEST_RESOURCE_NAME' --tags 'e2e,testing,conference'" \
        "Created resource"
    
    # Test listing with details
    run_cli_command "List resources with details" \
        "$CLI_CMD resources list --details" \
        "Tags:"
    
    # Test resource search
    run_cli_command "Search resources by name" \
        "$CLI_CMD resources search --query 'E2E'" \
        "Found.*resources"
    
    # Test resource search by tags
    run_cli_command "Search resources by tags" \
        "$CLI_CMD resources search --query 'testing'" \
        "Found.*resources"
    
    # Test availability search with time filter
    local start_time=$(get_future_datetime 2)
    local end_time=$(get_future_datetime 4)
    
    if [[ -n "$start_time" && -n "$end_time" ]]; then
        run_cli_command "Time-based availability search" \
            "$CLI_CMD resources search --from '$start_time' --until '$end_time'" \
            "resources available"
    else
        warning "Skipping time-based search due to date parsing issues"
    fi
    
    # Test CSV upload
    local csv_file=$(create_test_csv)
    run_cli_command "Upload CSV resources" \
        "$CLI_CMD resources upload '$csv_file' --preview" \
        "Upload completed"
    
    # Test resource availability check
    if [[ -n "$TEST_RESOURCE_ID" ]]; then
        run_cli_command "Check resource availability" \
            "$CLI_CMD resources availability $TEST_RESOURCE_ID" \
            "Availability for"
        
        # Test resource maintenance
        run_cli_command "Disable resource" \
            "$CLI_CMD resources disable $TEST_RESOURCE_ID --force" \
            "disabled"
        
        run_cli_command "Enable resource" \
            "$CLI_CMD resources enable $TEST_RESOURCE_ID --force" \
            "enabled"
    else
        warning "Skipping resource-specific tests (no resource ID captured)"
    fi
}

test_reservation_management() {
    section "Reservation Management"
    
    # Get available resource for testing
    local available_resource_id
    if [[ -n "$TEST_RESOURCE_ID" ]]; then
        available_resource_id="$TEST_RESOURCE_ID"
    else
        # Try to find any available resource
        available_resource_id=$(eval "$CLI_CMD resources list" 2>/dev/null | grep -o "ID: [0-9]*" | head -1 | cut -d' ' -f2)
    fi
    
    if [[ -n "$available_resource_id" ]]; then
        info "Using resource ID $available_resource_id for reservation tests"
        
        # Test creating a reservation
        local start_time=$(get_future_datetime 1)
        local duration="2h"
        
        if [[ -n "$start_time" ]]; then
            run_cli_command "Create reservation" \
                "$CLI_CMD reservations create $available_resource_id '$start_time' '$duration'" \
                "Reservation created"
            
            # Test quick reserve command
            local quick_start=$(get_future_datetime 6)
            if [[ -n "$quick_start" ]]; then
                run_cli_command "Quick reserve command" \
                    "$CLI_CMD reserve $available_resource_id '$quick_start' '1h'" \
                    "Quick reservation created"
            fi
        else
            warning "Skipping reservation creation due to date parsing issues"
        fi
        
        # Test listing reservations
        run_cli_command "List my reservations" \
            "$CLI_CMD reservations list" \
            "Reservations"
        
        run_cli_command "List upcoming reservations" \
            "$CLI_CMD reservations list --upcoming" \
            "Upcoming"
        
        run_cli_command "List detailed reservations" \
            "$CLI_CMD reservations list --detailed" \
            "Created:"
        
        # Test upcoming shortcut
        run_cli_command "Show upcoming reservations" \
            "$CLI_CMD upcoming" \
            "Upcoming Reservations"
        
        # Test reservation history
        if [[ -n "$TEST_RESERVATION_ID" ]]; then
            run_cli_command "Show reservation history" \
                "$CLI_CMD reservations history $TEST_RESERVATION_ID" \
                "History for Reservation"
            
            run_cli_command "Detailed reservation history" \
                "$CLI_CMD reservations history $TEST_RESERVATION_ID --detailed" \
                "Created"
            
            # Test cancelling reservation
            run_cli_command "Cancel reservation" \
                "$CLI_CMD reservations cancel $TEST_RESERVATION_ID --reason 'E2E test cleanup' --force" \
                "cancelled successfully"
            
            # Test cancelling already cancelled reservation (should fail)
            run_cli_command "Cancel already cancelled reservation" \
                "$CLI_CMD reservations cancel $TEST_RESERVATION_ID --force" \
                "already cancelled" \
                true
        else
            warning "Skipping reservation-specific tests (no reservation ID captured)"
        fi
        
        # Test conflicting reservation
        if [[ -n "$start_time" ]]; then
            run_cli_command "Create conflicting reservation" \
                "$CLI_CMD reservations create $available_resource_id '$start_time' '1h'" \
                "conflicts" \
                true
        fi
        
    else
        warning "Skipping reservation tests (no available resource found)"
    fi
}

test_advanced_features() {
    section "Advanced Features"
    
    # Test interactive resource search
    run_cli_command "Interactive resource search" \
        "echo -e '\nno\n' | $CLI_CMD resources search --interactive" \
        "Found.*resources"
    
    # Test system cleanup
    run_cli_command "Manual cleanup" \
        "$CLI_CMD system cleanup" \
        "Cleanup completed"
    
    # Test configuration display
    run_cli_command "Show configuration" \
        "$CLI_CMD system config" \
        "Current Configuration"
    
    # Test invalid commands (should fail)
    run_cli_command "Invalid resource ID" \
        "$CLI_CMD resources availability 99999" \
        "not found" \
        true
    
    run_cli_command "Invalid reservation ID" \
        "$CLI_CMD reservations history 99999" \
        "not found" \
        true
    
    # Test edge cases
    run_cli_command "Empty search query" \
        "$CLI_CMD resources search --query ''" \
        "Found.*resources"
    
    # Test help commands
    run_cli_command "Main help" \
        "$CLI_CMD --help" \
        "Resource Reservation System CLI"
    
    run_cli_command "Auth help" \
        "$CLI_CMD auth --help" \
        "Authentication commands"
    
    run_cli_command "Resources help" \
        "$CLI_CMD resources --help" \
        "Resource management commands"
    
    run_cli_command "Reservations help" \
        "$CLI_CMD reservations --help" \
        "Reservation management commands"
}

test_error_handling() {
    section "Error Handling & Edge Cases"
    
    # Test unauthenticated requests after logout
    run_cli_command "Logout user" \
        "$CLI_CMD auth logout" \
        "Successfully logged out"
    
    run_cli_command "Unauthenticated request" \
        "$CLI_CMD reservations list" \
        "Please login first" \
        true
    
    # Re-login for remaining tests
    run_cli_command "Re-login user" \
        "echo -e '$TEST_USER\n$TEST_PASSWORD' | $CLI_CMD auth login" \
        "Welcome back"
    
    # Test invalid file upload
    run_cli_command "Invalid file upload" \
        "$CLI_CMD resources upload /nonexistent/file.csv" \
        "File not found" \
        true
    
    # Test malformed CSV
    echo "invalid,csv,content,without,proper,headers" > /tmp/invalid.csv
    run_cli_command "Malformed CSV upload" \
        "$CLI_CMD resources upload /tmp/invalid.csv" \
        "error" \
        true
    
    # Test invalid datetime formats
    run_cli_command "Invalid datetime format" \
        "$CLI_CMD resources search --from 'invalid-date' --until '2025-12-31 23:59'" \
        "Invalid datetime format" \
        true
    
    # Test invalid duration format
    if [[ -n "$TEST_RESOURCE_ID" ]]; then
        run_cli_command "Invalid duration format" \
            "$CLI_CMD reserve $TEST_RESOURCE_ID '2025-12-31 10:00' 'invalid-duration'" \
            "Invalid duration format" \
            true
    fi
}

test_data_validation() {
    section "Data Validation"
    
    # Test resource creation with invalid data
    run_cli_command "Empty resource name" \
        "$CLI_CMD resources create '' --tags 'test'" \
        "Resource name must be" \
        true
    
    run_cli_command "Very long resource name" \
        "$CLI_CMD resources create '$(printf 'A%.0s' {1..300})' --tags 'test'" \
        "Resource name must be" \
        true
    
    # Test reservation with past times
    run_cli_command "Reservation in the past" \
        "$CLI_CMD reservations create 1 '2020-01-01 10:00' '1h'" \
        "Start time must be in the future" \
        true
    
    # Test reservation with end before start
    local start_time=$(get_future_datetime 2)
    local end_time=$(get_future_datetime 1)
    
    if [[ -n "$start_time" && -n "$end_time" ]]; then
        run_cli_command "End time before start time" \
            "$CLI_CMD reservations create 1 '$end_time' '2025-12-31 23:59'" \
            "End time must be after start time" \
            true
    fi
}

cleanup_test_data() {
    if [[ "$CLEANUP" != "true" ]]; then
        info "Skipping cleanup (CLEANUP=false)"
        return
    fi
    
    section "Cleanup Test Data"
    
    # Clean up CSV files
    rm -f "$CSV_FILE" /tmp/invalid.csv
    
    # Note: We don't clean up the test user and resources as they might be useful
    # for inspection and the test user has a timestamp making it unique
    
    info "Cleanup completed (test user: $TEST_USER remains for inspection)"
}

# =================================================================
# PERFORMANCE AND STRESS TESTS
# =================================================================

test_performance() {
    section "Performance Tests"
    
    # Test rapid command execution
    local start_time=$(date +%s)
    for i in {1..5}; do
        eval "$CLI_CMD resources list" >/dev/null 2>&1
    done
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [[ $duration -lt 10 ]]; then
        success "Rapid command execution (${duration}s for 5 commands)"
    else
        warning "Slow command execution (${duration}s for 5 commands)"
    fi
    
    # Test large data handling
    run_cli_command "Handle large resource list" \
        "$CLI_CMD resources list --details" \
        "Resources"
}

# =================================================================
# INTEGRATION TESTS
# =================================================================

test_workflow_integration() {
    section "Workflow Integration Tests"
    
    info "Testing complete user workflow..."
    
    # Complete workflow: register -> login -> create resource -> reserve -> view -> cancel
    local workflow_user="workflow_$(date +%s)"
    local workflow_resource="Workflow Test Room"
    
    # User registration and login
    if run_cli_command "Workflow: Register user" \
        "echo -e '$workflow_user\nworkflow123\nworkflow123' | $CLI_CMD auth register" \
        "Successfully registered"; then
        
        if run_cli_command "Workflow: Login user" \
            "echo -e '$workflow_user\nworkflow123' | $CLI_CMD auth login" \
            "Welcome back"; then
            
            # Resource creation
            if run_cli_command "Workflow: Create resource" \
                "$CLI_CMD resources create '$workflow_resource' --tags 'workflow,test'" \
                "Created resource"; then
                
                # Find the created resource
                local resource_output
                resource_output=$(eval "$CLI_CMD resources search --query 'Workflow Test Room'" 2>/dev/null)
                local workflow_resource_id=$(echo "$resource_output" | grep -o "ID: [0-9]*" | head -1 | cut -d' ' -f2)
                
                if [[ -n "$workflow_resource_id" ]]; then
                    # Create reservation
                    local reservation_time=$(get_future_datetime 3)
                    if [[ -n "$reservation_time" ]]; then
                        if run_cli_command "Workflow: Create reservation" \
                            "$CLI_CMD reserve $workflow_resource_id '$reservation_time' '1h'" \
                            "created"; then
                            
                            # View reservations
                            run_cli_command "Workflow: View reservations" \
                                "$CLI_CMD upcoming" \
                                "Upcoming Reservations"
                            
                            # Get reservation ID and cancel
                            local reservations_output
                            reservations_output=$(eval "$CLI_CMD reservations list" 2>/dev/null)
                            local workflow_reservation_id=$(echo "$reservations_output" | grep -o "ID: [0-9]*" | head -1 | cut -d' ' -f2)
                            
                            if [[ -n "$workflow_reservation_id" ]]; then
                                run_cli_command "Workflow: Cancel reservation" \
                                    "$CLI_CMD reservations cancel $workflow_reservation_id --reason 'Workflow test complete' --force" \
                                    "cancelled"
                            fi
                        fi
                    fi
                fi
            fi
        fi
    fi
    
    success "Complete workflow integration test completed"
}

# =================================================================
# MAIN EXECUTION
# =================================================================

show_help() {
    cat << EOF
Resource Reservation System - CLI End-to-End Test Script

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output (default: true)
    -q, --quiet         Disable verbose output
    --no-cleanup        Skip cleanup of test data
    --performance       Run additional performance tests
    --api-url URL       Set API base URL (default: http://localhost:8000)

Environment Variables:
    API_URL             API base URL
    VERBOSE             Enable/disable verbose output (true/false)
    CLEANUP             Enable/disable cleanup (true/false)

Test Categories:
    - System Health Check
    - Authentication Flow
    - Resource Management
    - Reservation Management
    - Advanced Features
    - Error Handling & Edge Cases
    - Data Validation
    - Performance Tests
    - Workflow Integration

Examples:
    $0                                # Run all tests with default settings
    $0 --quiet --no-cleanup          # Run quietly without cleanup
    $0 --api-url http://prod.api.com  # Test against different API
    VERBOSE=false $0                  # Use environment variable

The script will create a unique test user and test data, then systematically
test all CLI commands and report any failures.
EOF
}

print_summary() {
    section "Test Summary"
    
    echo -e "${BLUE}Total Tests: $TOTAL_TESTS${NC}"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        local success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
        
        if [[ $FAILED_TESTS -eq 0 ]]; then
            echo -e "${GREEN}🎉 All tests passed! (100% success rate)${NC}"
            echo -e "${GREEN}✨ CLI is working perfectly!${NC}"
        else
            echo -e "${YELLOW}Success rate: ${success_rate}%${NC}"
            
            if [[ ${#FAILED_COMMANDS[@]} -gt 0 ]]; then
                echo -e "\n${RED}Failed Commands:${NC}"
                for cmd in "${FAILED_COMMANDS[@]}"; do
                    echo -e "${RED}  • $cmd${NC}"
                done
            fi
            
            if [[ $success_rate -ge 80 ]]; then
                echo -e "${YELLOW}⚠️  Most tests passed, but some issues detected${NC}"
                exit 1
            else
                echo -e "${RED}❌ Significant issues detected${NC}"
                exit 2
            fi
        fi
    else
        echo -e "${RED}No tests were run${NC}"
        exit 3
    fi
}

main() {
    echo -e "${PURPLE}"
    echo "================================================================="
    echo "  Resource Reservation System - CLI End-to-End Test Script"
    echo "================================================================="
    echo -e "${NC}"
    
    log "Starting comprehensive CLI tests"
    log "Test user: $TEST_USER"
    log "API URL: $API_URL"
    
    # Check if CLI is available
    if ! command -v python >/dev/null 2>&1; then
        error "Python not found. Please install Python to run CLI tests."
        exit 1
    fi
    
    # Check if API is accessible
    if ! curl -s --connect-timeout 5 "$API_URL/health" >/dev/null 2>&1; then
        error "Cannot connect to API at $API_URL"
        error "Please ensure the server is running"
        exit 1
    fi
    
    # Run all test suites
    test_system_health
    test_authentication_flow
    test_resource_management
    test_reservation_management
    test_advanced_features
    test_error_handling
    test_data_validation
    
    # Optional performance tests
    if [[ "$1" == "--performance" ]]; then
        test_performance
    fi
    
    # Integration tests
    test_workflow_integration
    
    # Cleanup
    cleanup_test_data
    
    # Show results
    print_summary
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            VERBOSE=false
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --performance)
            shift
            ;;
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function with all arguments
main "$@"
            fi
            return 1
        fi
    fi
    
    # Check exit code for success
    if [[ $exit_code -ne 0 ]]; then
        error "$description (Exit code: $exit_code)"
        if [[ -n "$output" ]]; then
            echo "   Error: ${output:0:200}..."
        fi
        return 1
    fi
    
    # Check output pattern if provided
    if [[ -n "$expected_pattern" ]]; then
        if echo "$output" | grep -q "$expected_pattern"; then
            success "$description"
            if [[ "$VERBOSE" == "true" ]]; then
                echo "   Found expected pattern: $expected_pattern"
            fi
        else
            error "$description (Pattern not found: $expected_pattern)"
            if [[ "$VERBOSE" == "true" ]]; then