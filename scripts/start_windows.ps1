$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ImageName = "pm-mvp:dev"
$ContainerName = "pm-mvp"
$Port = 8000
$EnvFile = Join-Path $RootDir ".env"

Write-Host "Building Docker image: $ImageName"
docker build -t $ImageName $RootDir

docker rm -f $ContainerName | Out-Null

if (Test-Path $EnvFile) {
  docker run -d --name $ContainerName -p "${Port}:8000" --env-file $EnvFile $ImageName | Out-Null
} else {
  docker run -d --name $ContainerName -p "${Port}:8000" $ImageName | Out-Null
}

Write-Host "Container started: $ContainerName"
Write-Host "App URL: http://localhost:$Port"
