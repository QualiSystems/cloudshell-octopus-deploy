param(
[string]$octopusUrl,
[string]$api-key,
[string]$env,
[string]$role,
[string]$thumbprint
)

cd "C:\Program Files\Octopus Deploy\Tentacle"
.\Tentacle.exe configure --instance "Tentacle" --trust "$thumbprint" --console
.\Tentacle.exe register-with --instance "Tentacle" --server "$octopusUrl" --apiKey="$api-key" --role "$role" --environment "$env" --comms-style TentaclePassive --console
.\Tentacle.exe service --instance "Tentacle" --install --start --console