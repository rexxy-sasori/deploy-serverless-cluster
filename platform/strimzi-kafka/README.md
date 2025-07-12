#Kafka Cluster Deployment with Strimzi

This guide provides step-by-step instructions for deploying an Apache Kafka cluster using Strimzi on Kubernetes, including customization options for storage configurations.

##Prerequisites

• Kubernetes cluster (Minikube or other)

• kubectl configured to access your cluster

• Internet access to download Strimzi resources

• StorageClass configured (if using custom storage)

##Deployment Steps

1. Create Kafka Namespace
```bash
kubectl create namespace kafka
```

2. Install Strimzi Cluster Operator
```bash
kubectl create -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka
```

Monitor the operator deployment:
```bash
kubectl get pod -n kafka --watch
```

View operator logs:
```bash
kubectl logs deployment/strimzi-cluster-operator -n kafka -f
```

3. Create Kafka Cluster with Custom Configuration

First, download the sample configuration file:
```bash
curl -L https://strimzi.io/examples/latest/kafka/kafka-single-node.yaml -o kafka-custom.yaml
```

Edit the file to customize your Kafka cluster. Key customizable parameters include:
```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
spec:
  kafka:
    version: 3.6.0
    replicas: 1
    storage:
      type: persistent-claim
      size: 100Gi
      storageClass: standard # Change this to your desired StorageClass
      deleteClaim: false
    config:
      num.partitions: 1
      default.replication.factor: 1
      min.insync.replicas: 1
      offsets.topic.replication.factor: 1
      transaction.state.log.replication.factor: 1
      transaction.state.log.min.isr: 1
    resources:
      requests:
        memory: 2Gi
        cpu: "1"
      limits:
        memory: 4Gi
        cpu: "2"
  zookeeper:
    replicas: 1
    storage:
      type: persistent-claim
      size: 100Gi
      storageClass: standard # Change this to your desired StorageClass
      deleteClaim: false
    resources:
      requests:
        memory: 1Gi
        cpu: "0.5"
      limits:
        memory: 2Gi
        cpu: "1"
  entityOperator:
    topicOperator: {}
    userOperator: {}
```

After customizing, apply your configuration:
```bash
kubectl apply -f kafka-custom.yaml -n kafka
```

Wait for cluster to be ready:
```bash
kubectl wait kafka/my-cluster --for=condition=Ready --timeout=300s -n kafka
```

4. Test the Cluster

Produce Messages
```bash
kubectl -n kafka run kafka-producer -ti --image=quay.io/strimzi/kafka:0.46.1-kafka-4.0.0 --rm=true --restart=Never -- bin/kafka-console-producer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic my-topic
```

Consume Messages (in a separate terminal)
```bash
kubectl -n kafka run kafka-consumer -ti --image=quay.io/strimzi/kafka:0.46.1-kafka-4.0.0 --rm=true --restart=Never -- bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-bootstrap:9092 --topic my-topic --from-beginning
```

##Storage Configuration Options

Key storage parameters you can customize:
• storageClass: Specify your StorageClass (e.g., "standard", "gp2", "local-storage")

• size: Volume size (e.g., "100Gi", "500Gi")

• deleteClaim: Whether to delete PVC when cluster is deleted (true/false)

• type: "persistent-claim" for persistent storage or "ephemeral" for temporary storage

Example configurations:

Using AWS EBS:
storage:
  type: persistent-claim
  size: 500Gi
  storageClass: gp2
  deleteClaim: false


Using local storage:
storage:
  type: persistent-claim
  size: 200Gi
  storageClass: local-storage
  deleteClaim: true


Ephemeral storage (for testing only):
storage:
  type: ephemeral


##Cleanup

Delete Kafka Cluster

kubectl -n kafka delete $(kubectl get strimzi -o name -n kafka)
kubectl delete pvc -l strimzi.io/name=my-cluster-kafka -n kafka


Delete Strimzi Operator

kubectl -n kafka delete -f 'https://strimzi.io/install/latest?namespace=kafka'


Delete Namespace

kubectl delete namespace kafka


##Notes

• Always verify available StorageClasses in your cluster with kubectl get storageclass

• For production environments, consider using multiple replicas and appropriate resource limits

• The deleteClaim parameter controls whether data persists after cluster deletion

• Monitor disk usage as Kafka requires significant storage for message retention

For advanced configurations, refer to the https://strimzi.io/documentation/.
