#!/bin/bash

# Function to adjust autoscaling attributes of a Knative function
adjust_function_autoscaling() {
    local function_name=$1
    local namespace=${2:-default}
    
    # Check if function name is provided
    if [[ -z "$function_name" ]]; then
        echo "Usage: $0 <function-name> [namespace] [options]"
        echo "Options:"
        echo "  --target <value>          Set autoscaling.knative.dev/target"
        echo "  --target-util <value>    Set autoscaling.knative.dev/target-utilization-percentage"
        echo "  --concurrency <value>    Set containerConcurrency (hard limit)"
        echo "  --min-scale <value>      Set autoscaling.knative.dev/minScale"
        echo "  --max-scale <value>      Set autoscaling.knative.dev/maxScale"
        return 1
    fi

    # Initialize variables
    local target=""
    local target_util=""
    local concurrency=""
    local min_scale=""
    local max_scale=""
    
    # Parse arguments
    shift 2
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --target)
                target="$2"
                shift 2
                ;;
            --target-util)
                target_util="$2"
                shift 2
                ;;
            --concurrency)
                concurrency="$2"
                shift 2
                ;;
            --min-scale)
                min_scale="$2"
                shift 2
                ;;
            --max-scale)
                max_scale="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                return 1
                ;;
        esac
    done

    # Build annotation patch
    local annotations_patch="{"
    local needs_comma=false
    
    if [[ -n "$target" ]]; then
        annotations_patch+="\"autoscaling.knative.dev/target\":\"$target\""
        needs_comma=true
    fi
    
    if [[ -n "$target_util" ]]; then
        if $needs_comma; then
            annotations_patch+=","
        fi
        annotations_patch+="\"autoscaling.knative.dev/target-utilization-percentage\":\"$target_util\""
        needs_comma=true
    fi
    
    if [[ -n "$min_scale" ]]; then
        if $needs_comma; then
            annotations_patch+=","
        fi
        annotations_patch+="\"autoscaling.knative.dev/minScale\":\"$min_scale\""
        needs_comma=true
    fi
    
    if [[ -n "$max_scale" ]]; then
        if $needs_comma; then
            annotations_patch+=","
        fi
        annotations_patch+="\"autoscaling.knative.dev/maxScale\":\"$max_scale\""
        needs_comma=true
    fi
    
    annotations_patch+="}"
    
    # Build spec patch (for containerConcurrency)
    local spec_patch="{}"
    if [[ -n "$concurrency" ]]; then
        spec_patch="{\"spec\":{\"containerConcurrency\":$concurrency}}"
    fi
    
    # Apply patches if there are changes
    if [[ "$annotations_patch" != "{}" ]]; then
        echo "Updating annotations..."
        kubectl -n "$namespace" patch ksvc "$function_name" \
            --type=merge -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":$annotations_patch}}}}"
    fi
    
    if [[ "$spec_patch" != "{}" ]]; then
        echo "Updating containerConcurrency..."
        kubectl -n "$namespace" patch ksvc "$function_name" \
            --type=merge -p "{\"spec\":{\"template\":$spec_patch}}"
    fi
    
    echo "Autoscaling configuration updated for function $function_name in namespace $namespace"
}

# Call the function with all arguments
adjust_function_autoscaling "$@"
