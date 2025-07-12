# DeepFlow Installation Guide

## 1. Introduction
DeepFlow provides zero-intrusion observability for Kubernetes applications, collecting:
- AutoMetrics
- AutoTracing
- AutoProfiling

It automatically injects Kubernetes resource information and custom labels into all observability data.

## 2. Preparation

### 2.1 Storage Class Setup
We recommend using Persistent Volumes for MySQL and ClickHouse data:

```bash
kubectl apply -f https://openebs.github.io/charts/openebs-operator.yaml
kubectl patch storageclass openebs-hostpath -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

## 3. Deploy DeepFlow

### Using Helm (Github/DockerHub)
```bash
helm repo add deepflow https://deepflowio.github.io/deepflow
helm repo update deepflow  # use `helm repo update` when helm < 3.7.0
helm install deepflow -n deepflow deepflow/deepflow --create-namespace
```

### Using Aliyun Mirror
```bash
helm repo add deepflow https://deepflow-ce.oss-cn-beijing.aliyuncs.com/chart/stable
helm repo update deepflow  # use `helm repo update` when helm < 3.7.0

cat << EOF > values-custom.yaml
global:
  image:
    repository: registry.cn-beijing.aliyuncs.com/deepflow-ce
EOF

helm install deepflow -n deepflow deepflow/deepflow --create-namespace \
  -f values-custom.yaml
```

### Configuration Notes:
- Use `--set global.storageClass` to specify storageClass
- Use `--set global.replicas` to specify replica count
- Save helm `--set` parameters in a separate yaml file for advanced configuration
- For convenience, we have downloaded the DeepFlow manifest. Feel free to adjust any parameters such as storage requests yourself

## 4. Post-Installation

### Install deepflow-ctl
```bash
curl -o /usr/bin/deepflow-ctl https://deepflow-ce.oss-cn-beijing.aliyuncs.com/bin/ctl/stable/linux/$(arch | sed 's|x86_64|amd64|' | sed 's|aarch64|arm64|')/deepflow-ctl
chmod a+x /usr/bin/deepflow-ctl
```

### Access Grafana
Run these commands to get Grafana access details:
```bash
NODE_PORT=$(kubectl get --namespace deepflow -o jsonpath="{.spec.ports[0].nodePort}" services deepflow-grafana)
NODE_IP=$(kubectl get nodes -o jsonpath="{.items[0].status.addresses[0].address}")
echo -e "Grafana URL: http://$NODE_IP:$NODE_PORT \nGrafana auth: admin:deepflow"
```

### Expose Grafana via Load Balancer
If you have an underlying load balancer and would like to expose Grafana outside the cluster:
```bash
./loadbalancer-type-grafana.sh
```

## DeepFlow Istio Bookinfo Demo

The `deepflow-istio-demo` folder contains a demonstration of DeepFlow's AutoTracing capabilities in a multi-language, Istio service mesh environment.

### Purpose
This demo showcases:
- Zero-intrusion distributed tracing across 4 programming languages (Java, Python, Ruby, Node.js)
- Automatic tracing without manual code instrumentation
- Full-stack observability including network paths between pods

### Key Features Demonstrated
1. **AutoTracing**:
   - No manual tracing code required
   - No TraceID/SpanID injection needed
   - Automatic correlation of spans across services

2. **Multi-language Support**:
   - Java (productpage service)
   - Python (details service)
   - Ruby (reviews service)
   - NodeJS (ratings service)
   - C/C++ (curl/envoy infrastructure services)

3. **Full-stack Visibility**:
   - Network paths between pods on same node
   - Cross-node communication (including tunnel encapsulation)
   - In-pod traffic (Envoy Ingress → Service → Envoy Egress)

### Getting Started
To experience the AutoTracing capabilities:

1. Deploy Istio according to the Istio folder

2. Deploy the Bookinfo application:
```bash
kubectl apply -f https://raw.githubusercontent.com/deepflowio/deepflow-demo/main/Istio-Bookinfo/bookinfo.yaml
```

3. View the traces in Grafana:
- Open the Distributed Tracing Dashboard
- Select namespace = `deepflow-ebpf-istio-demo`
- Choose any call to inspect the automatic trace

### Expected Results
You should see:
- A complete flame graph of the call chain (typically 38 spans)
- Automatic topology mapping of service relationships
- Network-level visibility between all components

This demo highlights DeepFlow's ability to provide distributed tracing without requiring any application changes or manual instrumentation.


