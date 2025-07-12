# OpenEBS Deployment

This script deploys OpenEBS using Helm in a dedicated namespace.

## Usage

1. Make the script executable:
   ```bash
   chmod +x deploy-openebs.sh
   ```

2. Run the deployment script:
```bash
   ./deploy-openebs.sh
```

## What the Script Does

1. Adds the OpenEBS Helm repository
2. Updates Helm repositories
3. Installs OpenEBS in the `openebs` namespace (creating it if needed)

## Verification

Check the installation status:
```bash
kubectl get pods -n openebs
```

## Uninstall

To remove OpenEBS:
```bash
helm uninstall openebs -n openebs
kubectl delete namespace openebs
```

## Notes

- Requires Helm 3.x and Kubernetes 1.12+
- Requires cluster admin privileges
- By default installs the latest stable version of OpenEBS
