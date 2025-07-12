kubectl run curl-tool \
  --image=curlimages/curl \
  --restart=Never \
  --rm -it \
  --command -- sh
