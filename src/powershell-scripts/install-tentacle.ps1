[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri http://octopusdeploy.com/downloads/latest/OctopusTentacle64 -OutFile c:\OctopusTentacle_x64.msi
msiexec /i OctopusTentacle_x64.msi /quiet
cd "C:\Program Files\Octopus Deploy\Tentacle"

.\Tentacle.exe create-instance --instance "Tentacle" --config "C:\Octopus\Tentacle\Tentacle.config" --console
.\Tentacle.exe new-certificate --instance "Tentacle" --console
.\Tentacle.exe configure --instance "Tentacle" --home "C:\Octopus" --console
.\Tentacle.exe configure --instance "Tentacle" --app "C:\Octopus\Applications" --console
.\Tentacle.exe configure --instance "Tentacle" --port "10933" --console

