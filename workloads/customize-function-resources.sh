#!/bin/bash

# Knative Service Resource Patcher
# Safely updates CPU/memory requests/limits for Knative services
# Usage: ./patch-knative-resources.sh <service-name> [namespace] [options]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Flags
AUTO_YES=false

show_usage() {
  echo -e "${GREEN}Usage:${NC} $0 <service-name> [namespace] [options]"
  echo -e "${GREEN}Options:${NC}"
  echo "  -y, --yes         Skip confirmation and apply changes immediately"
  echo "  --cpu-request     CPU request (e.g., \"500m\")"
  echo "  --cpu-limit       CPU limit (e.g., \"1000m\")"
  echo "  --memory-request  Memory request (e.g., \"256Mi\")"
  echo "  --memory-limit    Memory limit (e.g., \"512Mi\")"
  echo -e "\n${YELLOW}Examples:${NC}"
  echo "  $0 my-service -y --cpu-request \"500m\""
  echo "  $0 my-service staging --memory-request \"256Mi\" --memory-limit \"1Gi\""
  exit 1
}

# Validate at least service name is provided
if [[ $# -eq 0 ]]; then
  echo -e "${RED}Error: Service name is required${NC}"
  show_usage
fi

# Parse arguments
SERVICE_NAME="$1"
NAMESPACE="default"
shift

# Check if next argument is a namespace (not starting with -)
if [[ $# -gt 0 && "$1" != -* ]]; then
  NAMESPACE="$1"
  shift
fi

# Initialize resource variables
CPU_REQUEST=""
CPU_LIMIT=""
MEMORY_REQUEST=""
MEMORY_LIMIT=""

# Parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      AUTO_YES=true
      shift
      ;;
    --cpu-request)
      [[ -z "${2:-}" ]] && { echo -e "${RED}Error: --cpu-request requires a value${NC}"; show_usage; }
      CPU_REQUEST="$2"
      shift 2
      ;;
    --cpu-limit)
      [[ -z "${2:-}" ]] && { echo -e "${RED}Error: --cpu-limit requires a value${NC}"; show_usage; }
      CPU_LIMIT="$2"
      shift 2
      ;;
    --memory-request)
      [[ -z "${2:-}" ]] && { echo -e "${RED}Error: --memory-request requires a value${NC}"; show_usage; }
      MEMORY_REQUEST="$2"
      shift 2
      ;;
    --memory-limit)
      [[ -z "${2:-}" ]] && { echo -e "${RED}Error: --memory-limit requires a value${NC}"; show_usage; }
      MEMORY_LIMIT="$2"
      shift 2
      ;;
    *)
      echo -e "${RED}Error: Unknown option $1${NC}"
      show_usage
      ;;
  esac
done

# Validate at least one resource field was specified
if [[ -z "$CPU_REQUEST" && -z "$CPU_LIMIT" && -z "$MEMORY_REQUEST" && -z "$MEMORY_LIMIT" ]]; then
  echo -e "${RED}Error: No resource values specified${NC}"
  show_usage
fi

# Get current configuration
echo -e "${GREEN}Fetching current configuration for ${YELLOW}$SERVICE_NAME${GREEN} in namespace ${YELLOW}$NAMESPACE${NC}"

if ! CURRENT_JSON=$(kubectl get ksvc "$SERVICE_NAME" -n "$NAMESPACE" -o json 2>/dev/null); then
  echo -e "${RED}Error: Service $SERVICE_NAME not found in namespace $NAMESPACE${NC}"
  exit 1
fi

IMAGE=$(jq -r '.spec.template.spec.containers[0].image' <<< "$CURRENT_JSON")
CURRENT_RESOURCES=$(jq '.spec.template.spec.containers[0].resources' <<< "$CURRENT_JSON")

# Show current resources
echo -e "\n${YELLOW}Current resources:${NC}"
if [[ "$CURRENT_RESOURCES" == "null" ]]; then
  echo "  No resource limits configured"
else
  jq <<< "$CURRENT_RESOURCES"
fi

# Build resources patch
RESOURCES_PATCH=""
if [[ -n "$CPU_REQUEST" || -n "$MEMORY_REQUEST" ]]; then
  RESOURCES_PATCH='"requests": {'
  [[ -n "$CPU_REQUEST" ]] && RESOURCES_PATCH+="\"cpu\": \"$CPU_REQUEST\""
  [[ -n "$MEMORY_REQUEST" ]] && RESOURCES_PATCH+="${CPU_REQUEST:+, }\"memory\": \"$MEMORY_REQUEST\""
  RESOURCES_PATCH+="}"
fi

if [[ -n "$CPU_LIMIT" || -n "$MEMORY_LIMIT" ]]; then
  RESOURCES_PATCH+="${RESOURCES_PATCH:+, }\"limits\": {"
  [[ -n "$CPU_LIMIT" ]] && RESOURCES_PATCH+="\"cpu\": \"$CPU_LIMIT\""
  [[ -n "$MEMORY_LIMIT" ]] && RESOURCES_PATCH+="${CPU_LIMIT:+, }\"memory\": \"$MEMORY_LIMIT\""
  RESOURCES_PATCH+="}"
fi

# Build complete patch
PATCH_JSON=$(cat <<EOF
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "image": "$IMAGE",
            "resources": {
              $RESOURCES_PATCH
            }
          }
        ]
      }
    }
  }
}
EOF
)

# Show what will be changed
echo -e "\n${YELLOW}Proposed changes:${NC}"
jq <<< "$PATCH_JSON"

# Skip confirmation if -y flag is set
if [[ "$AUTO_YES" == false ]]; then
  read -rp $'\033[1;33mApply these changes? (y/n): \033[0m' confirm
  if [[ "$confirm" != [yY] ]]; then
    echo -e "${RED}Aborting. No changes made.${NC}"
    exit 0
  fi
else
  echo -e "${GREEN}Auto-confirmed changes (using -y flag)${NC}"
fi

# Apply patch
echo -e "\n${GREEN}Applying changes...${NC}"
kubectl patch ksvc "$SERVICE_NAME" -n "$NAMESPACE" \
  --type=merge \
  --patch "$PATCH_JSON"

# Verify changes
echo -e "\n${GREEN}Verifying changes...${NC}"
UPDATED_RESOURCES=$(kubectl get ksvc "$SERVICE_NAME" -n "$NAMESPACE" -o json | \
  jq '.spec.template.spec.containers[0].resources')

echo -e "${YELLOW}Updated resources:${NC}"
jq <<< "$UPDATED_RESOURCES"

echo -e "\n${GREEN}Successfully updated resources for ${YELLOW}$SERVICE_NAME${NC}"
