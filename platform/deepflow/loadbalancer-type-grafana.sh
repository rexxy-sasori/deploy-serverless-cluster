kubectl patch svc deepflow-grafana -p '{"spec":{"type":"LoadBalancer"}}' -n deepflow
