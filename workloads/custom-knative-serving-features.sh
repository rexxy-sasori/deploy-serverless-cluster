#!/bin/bash

# Knative Feature Configuration Script with Argument Parsing
# Adjusts Knative Serving features while preserving existing values
# Based on: https://knative.dev/docs/serving/configuration/feature-flags/

# Default values
DEFAULT_NAMESPACE="knative-serving"
DEFAULT_CONFIG_MAP="config-features"
DEFAULT_FEATURE="kubernetes.podspec-priorityclassname"
DEFAULT_VALUE="enabled"

# Usage instructions
usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -n, --namespace <namespace>  Knative Serving namespace (default: $DEFAULT_NAMESPACE)"
  echo "  -c, --configmap <name>        ConfigMap name (default: $DEFAULT_CONFIG_MAP)"
  echo "  -f, --feature <key>          Feature flag key (default: $DEFAULT_FEATURE)"
  echo "  -v, --value <value>          Feature flag value [enabled|disabled] (default: $DEFAULT_VALUE)"
  echo "  -h, --help                   Show this help message"
  exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    -c|--configmap)
      CONFIG_MAP="$2"
      shift 2
      ;;
    -f|--feature)
      FEATURE_KEY="$2"
      shift 2
      ;;
    -v|--value)
      FEATURE_VALUE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Error: Unknown option $1" >&2
      usage
      ;;
  esac
done

# Set defaults if arguments not provided
NAMESPACE="${NAMESPACE:-$DEFAULT_NAMESPACE}"
CONFIG_MAP="${CONFIG_MAP:-$DEFAULT_CONFIG_MAP}"
FEATURE_KEY="${FEATURE_KEY:-$DEFAULT_FEATURE}"
FEATURE_VALUE="${FEATURE_VALUE:-$DEFAULT_VALUE}"

# Validate feature value
if [[ "$FEATURE_VALUE" != "enabled" && "$FEATURE_VALUE" != "disabled" ]]; then
  echo "Error: Feature value must be either 'enabled' or 'disabled'" >&2
  exit 1
fi

# Check prerequisites
check_prerequisites() {
  if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH" >&2
    exit 1
  fi

  if ! command -v jq &> /dev/null; then
    echo "Error: jq is not installed. Please install jq for JSON processing." >&2
    exit 1
  fi

  if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Unable to connect to Kubernetes cluster" >&2
    exit 1
  fi
}

# Main function to update feature flag
update_feature_flag() {
  echo "Updating Knative feature configuration:"
  echo "  Namespace:    $NAMESPACE"
  echo "  ConfigMap:    $CONFIG_MAP"
  echo "  Feature:      $FEATURE_KEY"
  echo "  New value:    $FEATURE_VALUE"
  echo

  # Get current ConfigMap
  echo "Fetching current configuration..."
  CONFIGMAP_DATA=$(kubectl -n "$NAMESPACE" get configmap "$CONFIG_MAP" -o json 2>/dev/null)

  if [ -z "$CONFIGMAP_DATA" ]; then
    echo "Error: ConfigMap '$CONFIG_MAP' not found in namespace '$NAMESPACE'" >&2
    exit 1
  fi

  # Update configuration
  UPDATED_CONFIG=$(echo "$CONFIGMAP_DATA" | jq --arg key "$FEATURE_KEY" --arg value "$FEATURE_VALUE" '
      if .data == null then .data = {} else . end |
      .data[$key] = $value |
      .'
  )

  if [ $? -ne 0 ]; then
    echo "Error: Failed to process ConfigMap data" >&2
    exit 1
  fi

  # Apply changes
  echo "Applying updated configuration..."
  echo "$UPDATED_CONFIG" | kubectl -n "$NAMESPACE" apply -f -

  # Verify update
  echo -e "\nVerification:"
  kubectl -n "$NAMESPACE" get configmap "$CONFIG_MAP" -o jsonpath="{.data.$FEATURE_KEY}"
  echo -e "\n\nFeature flag updated successfully."
}

# Execute
check_prerequisites
update_feature_flag
