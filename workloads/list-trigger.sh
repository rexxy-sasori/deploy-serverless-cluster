#!/bin/bash

# Set default namespace (empty = all namespaces)
NAMESPACE="${1:-}"

# Run the query with namespace filtering
if [[ -z "$NAMESPACE" ]]; then
  kubectl get trigger -A -o json | jq -r '
    ["TRIGGER", "SERVICE", "FILTER_TYPE", "NAMESPACE"],
    (.items[] | 
      [
        .metadata.name,
        (.spec.subscriber | if .ref then .ref.name else .uri end),
        (.spec.filter.attributes.type // ""),
        .metadata.namespace
      ]
    ) | @tsv' | column -t -s $'\t'
else
  kubectl get trigger -n "$NAMESPACE" -o json | jq -r '
    ["TRIGGER", "SERVICE", "FILTER_TYPE"],
    (.items[] | 
      [
        .metadata.name,
        (.spec.subscriber | if .ref then .ref.name else .uri end),
        (.spec.filter.attributes.type // "")
      ]
    ) | @tsv' | column -t -s $'\t'
fi
