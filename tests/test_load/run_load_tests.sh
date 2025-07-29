#!/bin/bash

# Load testing script for the Telegram Notion Calendar Bot

echo "=== Telegram Notion Calendar Bot Load Testing ==="
echo ""

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo "Locust is not installed. Installing..."
    pip install locust
fi

# Default values
HOST="${HOST:-http://localhost:8000}"
USERS="${USERS:-100}"
SPAWN_RATE="${SPAWN_RATE:-10}"
RUN_TIME="${RUN_TIME:-5m}"
TEST_TYPE="${TEST_TYPE:-web}"

# Display test configuration
echo "Test Configuration:"
echo "- Host: $HOST"
echo "- Total Users: $USERS"
echo "- Spawn Rate: $SPAWN_RATE users/second"
echo "- Run Time: $RUN_TIME"
echo "- Test Type: $TEST_TYPE"
echo ""

# Create results directory
mkdir -p results
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="results/load_test_$TIMESTAMP"
mkdir -p "$RESULTS_DIR"

case $TEST_TYPE in
    "web")
        echo "Starting Web UI mode..."
        echo "Access the web interface at http://localhost:8089"
        locust -f locustfile.py \
            --host "$HOST" \
            --web-host 0.0.0.0
        ;;
    
    "headless")
        echo "Starting headless mode..."
        locust -f locustfile.py \
            --headless \
            --host "$HOST" \
            --users "$USERS" \
            --spawn-rate "$SPAWN_RATE" \
            --run-time "$RUN_TIME" \
            --html "$RESULTS_DIR/report.html" \
            --csv "$RESULTS_DIR/stats"
        
        echo ""
        echo "Test completed! Results saved to: $RESULTS_DIR"
        echo "- HTML Report: $RESULTS_DIR/report.html"
        echo "- CSV Stats: $RESULTS_DIR/stats_*.csv"
        ;;
    
    "stress")
        echo "Starting stress test mode..."
        echo "This will gradually increase load until failure"
        
        # Step load pattern
        for step in 50 100 200 500 1000; do
            echo ""
            echo "Testing with $step users..."
            
            locust -f locustfile.py \
                --headless \
                --host "$HOST" \
                --users "$step" \
                --spawn-rate 20 \
                --run-time 2m \
                --csv "$RESULTS_DIR/stress_${step}users" \
                --only-summary
            
            # Check if the system is still responsive
            if ! curl -s -o /dev/null -w "%{http_code}" "$HOST/health" | grep -q "200"; then
                echo "System became unresponsive at $step users"
                break
            fi
            
            # Wait between steps
            sleep 10
        done
        ;;
    
    "spike")
        echo "Starting spike test mode..."
        echo "This will simulate sudden traffic spikes"
        
        # Normal load
        echo "Phase 1: Normal load (50 users)..."
        locust -f locustfile.py \
            --headless \
            --host "$HOST" \
            --users 50 \
            --spawn-rate 5 \
            --run-time 1m \
            --csv "$RESULTS_DIR/spike_normal" &
        
        NORMAL_PID=$!
        sleep 60
        
        # Spike
        echo "Phase 2: Traffic spike (500 users)..."
        kill $NORMAL_PID 2>/dev/null
        
        locust -f locustfile.py \
            --headless \
            --host "$HOST" \
            --users 500 \
            --spawn-rate 100 \
            --run-time 2m \
            --csv "$RESULTS_DIR/spike_high" &
        
        SPIKE_PID=$!
        sleep 120
        
        # Return to normal
        echo "Phase 3: Return to normal (50 users)..."
        kill $SPIKE_PID 2>/dev/null
        
        locust -f locustfile.py \
            --headless \
            --host "$HOST" \
            --users 50 \
            --spawn-rate 5 \
            --run-time 1m \
            --csv "$RESULTS_DIR/spike_recovery"
        ;;
    
    "endurance")
        echo "Starting endurance test mode..."
        echo "This will run for an extended period"
        
        locust -f locustfile.py \
            --headless \
            --host "$HOST" \
            --users 100 \
            --spawn-rate 5 \
            --run-time 1h \
            --html "$RESULTS_DIR/endurance_report.html" \
            --csv "$RESULTS_DIR/endurance"
        ;;
    
    *)
        echo "Unknown test type: $TEST_TYPE"
        echo "Available types: web, headless, stress, spike, endurance"
        exit 1
        ;;
esac

# Generate summary report
if [ "$TEST_TYPE" != "web" ]; then
    echo ""
    echo "=== Test Summary ==="
    
    # Parse CSV results
    if [ -f "$RESULTS_DIR/stats_stats.csv" ]; then
        echo "Request Statistics:"
        tail -n +2 "$RESULTS_DIR/stats_stats.csv" | column -t -s,
    fi
    
    # Check for failures
    if [ -f "$RESULTS_DIR/stats_failures.csv" ]; then
        FAILURES=$(wc -l < "$RESULTS_DIR/stats_failures.csv")
        if [ "$FAILURES" -gt 1 ]; then
            echo ""
            echo "⚠️  Failures detected: $((FAILURES-1))"
            echo "See $RESULTS_DIR/stats_failures.csv for details"
        fi
    fi
    
    # Performance recommendations
    echo ""
    echo "=== Performance Recommendations ==="
    
    # Analyze response times
    if [ -f "$RESULTS_DIR/stats_stats.csv" ]; then
        AVG_RESPONSE=$(awk -F, 'NR==2 {print $6}' "$RESULTS_DIR/stats_stats.csv" 2>/dev/null)
        if [ ! -z "$AVG_RESPONSE" ] && [ "$AVG_RESPONSE" -gt 1000 ]; then
            echo "⚠️  High average response time detected (${AVG_RESPONSE}ms)"
            echo "   - Consider optimizing database queries"
            echo "   - Implement caching for frequent requests"
            echo "   - Review API rate limiting settings"
        fi
    fi
fi

echo ""
echo "Load testing completed!"