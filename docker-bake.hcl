# Docker Bake configuration for inDoc
# Build all services with: docker buildx bake

variable "REGISTRY" {
  default = "ghcr.io/your-org"
}

variable "TAG" {
  default = "latest"
}

group "default" {
  targets = ["api", "ui", "processor"]
}

target "api" {
  context = "./backend"
  dockerfile = "Dockerfile"
  tags = [
    "${REGISTRY}/indoc-api:${TAG}",
    "${REGISTRY}/indoc-api:latest"
  ]
  platforms = ["linux/amd64", "linux/arm64"]
  cache-from = ["type=registry,ref=${REGISTRY}/indoc-api:buildcache"]
  cache-to = ["type=registry,ref=${REGISTRY}/indoc-api:buildcache,mode=max"]
}

target "ui" {
  context = "./frontend"
  dockerfile = "Dockerfile"
  tags = [
    "${REGISTRY}/indoc-ui:${TAG}",
    "${REGISTRY}/indoc-ui:latest"
  ]
  platforms = ["linux/amd64", "linux/arm64"]
  cache-from = ["type=registry,ref=${REGISTRY}/indoc-ui:buildcache"]
  cache-to = ["type=registry,ref=${REGISTRY}/indoc-ui:buildcache,mode=max"]
  args = {
    VITE_API_URL = "/api/v1"
  }
}

target "processor" {
  context = "./backend"
  dockerfile = "Dockerfile.processor"
  tags = [
    "${REGISTRY}/indoc-processor:${TAG}",
    "${REGISTRY}/indoc-processor:latest"
  ]
  platforms = ["linux/amd64", "linux/arm64"]
  cache-from = ["type=registry,ref=${REGISTRY}/indoc-processor:buildcache"]
  cache-to = ["type=registry,ref=${REGISTRY}/indoc-processor:buildcache,mode=max"]
}