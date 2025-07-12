# Add OpenEBS helm repo
helm repo add openebs https://openebs.github.io/charts
helm repo update

# Install OpenEBS
helm install openebs openebs/openebs \
    --namespace openebs \
    --create-namespace
