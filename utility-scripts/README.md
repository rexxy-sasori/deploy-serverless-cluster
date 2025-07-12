# Knative Utility Scripts

This directory contains helper scripts for managing Knative resources. Each script provides detailed usage instructions when run with `-h`.

## Script Inventory

### `customize-function-autoscaling.sh`
- **Purpose**: Configure autoscaling parameters for Knative Services
- **Help**: `./customize-function-autoscaling.sh -h`
- **Features**: Set concurrency targets, min/max scale, utilization percentages

### `customize-function-resources.sh` 
- **Purpose**: Modify CPU/memory requests/limits for Knative Services
- **Help**: `./customize-function-resources.sh -h`
- **Features**: Update resources without recreating pods, with dry-run support

### `customize-knative-serving-features.sh`
- **Purpose**: Toggle Knative Serving feature flags
- **Help**: `./customize-knative-serving-features.sh -h`  
- **Features**: Modify config maps for serving-core and autoscaler

### `list-trigger.sh`
- **Purpose**: List and filter Knative Eventing Triggers
- **Help**: `./list-trigger.sh -h`
- **Features**: Filter by broker/subscriber, multiple output formats

### `start-curl-pod.sh`
- **Purpose**: Launch temporary debugging pod with curl
- **Help**: `./start-curl-pod.sh -h`
- **Features**: Auto-cleanup, includes network debugging tools

## Requirements
- `kubectl` configured with cluster access
- `jq` for JSON processing
- Bash 4.0+
