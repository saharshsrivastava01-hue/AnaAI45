# NEXUS-3000 Windows GPU preflight (read-only)
$ErrorActionPreference = "Continue"
Write-Host "=== NEXUS-3000 Dell GPU preflight ===" -ForegroundColor Cyan
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM, Status | Format-Table -AutoSize
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) { nvidia-smi } else { Write-Warning "nvidia-smi not found; install/update Dell-supported NVIDIA driver and reboot." }
if (Get-Command blender -ErrorAction SilentlyContinue) { blender --version } else { Write-Warning "Blender not found in PATH. Install Blender 4.x or use full blender.exe path." }
python --version
Write-Host "Preflight only: no settings changed and no render submitted."