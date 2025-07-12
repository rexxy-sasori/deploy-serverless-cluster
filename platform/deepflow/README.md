# DeepFlow Installation Guide

This guide provides instructions for installing DeepFlow to monitor a single Kubernetes cluster.

## Table of Contents
1. #1-introduction
2. #2-preparation
3. #3-deploy-deepflow
4. #4-post-installation
5. #6-next-steps

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
