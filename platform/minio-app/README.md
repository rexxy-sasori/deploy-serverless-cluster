# MinIO Deployment Tools

This directory contains Kubernetes manifests for deploying and testing MinIO clusters.

## Files

### `minio-helm-local.yaml`
- MinIO Helm deployment manifest for local clusters
- Customizable storage configuration:
  - Edit `storageClass` to match your environment
  - Or download a fresh manifest:  
    ```bash
    helm show values minio/minio > minio-helm-local.yaml
    ```

### `minio-client.yaml`
- Deploys a pod with `mc` (MinIO Client) for cluster interaction
- Usage:
  ```bash
  kubectl apply -f minio-client.yaml
  kubectl exec -it minio-client -- sh
  ```

### `minio-benchmark.yaml`
- Creates a pod with MinIO's `warp` benchmarking tool installed
- **Manual benchmark execution required** (see below)

## Benchmarking with Warp

1. Start the benchmark pod:
   ```bash
   kubectl apply -f minio-benchmark.yaml
   ```

2. Connect to the pod:
   ```bash
   kubectl exec -it minio-benchmark -- sh
   ```

3. Run benchmark commands inside the pod (no `mc` needed):
   ```bash
   # Basic PUT benchmark (uploads)
   warp put --host=<minio-service>:9000 \
            --access-key=admin \
            --secret-key=password \
            --bucket=test-bucket \
            --duration=1m

   # GET benchmark (downloads)
   warp get --host=<minio-service>:9000 \
            --access-key=admin \
            --secret-key=password \
            --bucket=test-bucket

   # Mixed workload benchmark
   warp mixed --host=<minio-service>:9000 \
              --access-key=admin \
              --secret-key=password \
              --bucket=test-benchmark \
              --duration=2m
   ```

4. View real-time results in console or analyze later:
   ```bash
   warp analyze <benchmark-id>
   ```

## Quick Start

1. Deploy MinIO:
   ```bash
   kubectl apply -f minio-helm-local.yaml
   ```

2. Create a bucket for testing (using client pod):
   ```bash
   kubectl apply -f minio-client.yaml
   kubectl exec -it minio-client -- mc mb myminio/test-bucket
   ```

## Important Parameters
- `--host`: MinIO service name (usually `minio:9000`)
- `--bucket`: Existing bucket name for testing
- `--duration`: Test duration (e.g., 1m, 5m)
- `--objects`: Number of objects (default: 1000)
- `--obj.size`: Object size (e.g., "1MiB", "512KiB")

## Notes
- The benchmark pod automatically includes the `warp` binary
- For production benchmarks, use longer durations (e.g., 5-10 minutes)
- Adjust object size and count to match your workload patterns
- Set `--autoterm` for automatic benchmark completion
