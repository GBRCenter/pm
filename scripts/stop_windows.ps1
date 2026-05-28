$ErrorActionPreference = "Stop"

$ContainerName = "pm-mvp"

docker rm -f $ContainerName | Out-Null
Write-Host "Container stopped/removed: $ContainerName"
