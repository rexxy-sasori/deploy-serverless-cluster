#!/bin/bash

# Configuration
BASE_DOMAIN="default.172.16.11.91.sslip.io"
FUNCTIONS=(
  "test-go"
  "test-node"
  "test-python"
  "test-quarkus"
  "test-rust"
  "test-springboot"
  "test-typescript"
)

# Test a single function
test_function() {
  local func_name="$1"
  local url="http://${func_name}.${BASE_DOMAIN}"
  echo -e "\n\033[1mTesting: ${url}\033[0m"

  # Make HTTP request and measure time
  start_time=$(date +%s%N)
  response=$(curl -s -v "${url}" 2>&1)
  end_time=$(date +%s%N)
  elapsed_ms=$(( (end_time - start_time) / 1000000 ))

  # Extract HTTP status code
  http_code=$(echo "$response" | grep -oP "(?<=< HTTP/1.[01] )\d{3}")

  # Validate response
  if [[ "$http_code" == "200" ]]; then
    echo -e "✅ \033[32mSUCCESS\033[0m | Status: ${http_code} | Time: ${elapsed_ms}ms"
    echo "Response Body:"
    echo "$response" | grep -v "^[*{]" | tail -n 5  # Skip curl verbose logs
  else
    echo -e "❌ \033[31mFAILED\033[0m | Status: ${http_code} | Time: ${elapsed_ms}ms"
    echo "Debug Info:"
    echo "$response" | grep -E "< HTTP|< X-Request-Id|ERROR"
  fi
}

# Test all functions
for func in "${FUNCTIONS[@]}"; do
  test_function "$func"
done

echo -e "\n\033[1mAll tests completed!\033[0m"
