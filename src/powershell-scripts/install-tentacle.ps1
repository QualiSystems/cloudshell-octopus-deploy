Param(
[string]$OCTOPUS_SERVER,
[string]$API_KEY,
[string]$ENVIRONMENT_NAME
)

Start-Transcript -Path "c:\tentacle-transcript.txt"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri http://octopusdeploy.com/downloads/latest/OctopusTentacle64 -OutFile c:\OctopusTentacle_x64.msi
cd c:\
msiexec /i OctopusTentacle_x64.msi /quiet

& 'C:\Program Files\Octopus Deploy\Tentacle\Tentacle.exe' create-instance --instance "Tentacle" --config "C:\Octopus\Tentacle\Tentacle.config" --console
& 'C:\Program Files\Octopus Deploy\Tentacle\Tentacle.exe' new-certificate --instance "Tentacle" --console
& 'C:\Program Files\Octopus Deploy\Tentacle\Tentacle.exe' configure --instance "Tentacle" --home "C:\Octopus" --console
& 'C:\Program Files\Octopus Deploy\Tentacle\Tentacle.exe' configure --instance "Tentacle" --app "C:\Octopus\Applications" --console
& 'C:\Program Files\Octopus Deploy\Tentacle\Tentacle.exe' configure --instance "Tentacle" --port "10933" --console

netsh advfirewall firewall add rule "name=Octopus Deploy Tentacle" dir=in action=allow protocol=TCP localport=10933
& 'C:\Program Files\Octopus Deploy\Tentacle\Tentacle.exe' register-with --instance "Tentacle" --server "$OCTOPUS_SERVER" --apiKey="$API_KEY" --role "web-server" --environment "$ENVIRONMENT_NAME" --comms-style TentaclePassive --console
& 'C:\Program Files\Octopus Deploy\Tentacle\Tentacle.exe' service --instance "Tentacle" --install --start --console

Stop-Transcript