# Stop Ollama if running
Write-Host "Stopping Ollama..." -ForegroundColor Yellow
Get-Process -Name ollama* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Set environment variables for Intel Arc GPU
Write-Host "Setting Intel Arc GPU environment variables..." -ForegroundColor Cyan
[System.Environment]::SetEnvironmentVariable('OLLAMA_INTEL_GPU', '1', 'User')
[System.Environment]::SetEnvironmentVariable('SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS', '1', 'User')

# Refresh environment variables for current session
$env:OLLAMA_INTEL_GPU = '1'
$env:SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS = '1'

Write-Host "✓ Environment variables set" -ForegroundColor Green
Write-Host ""
Write-Host "Starting Ollama with Intel Arc GPU support..." -ForegroundColor Cyan

# Start Ollama (it will run in background)
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden

Start-Sleep -Seconds 3

Write-Host "✓ Ollama started with GPU support!" -ForegroundColor Green
Write-Host ""
Write-Host "Testing GPU usage..." -ForegroundColor Yellow

# Run a test to verify GPU is being used
ollama ps

Write-Host ""
Write-Host "If you see 'GPU' in the PROCESSOR column, Intel Arc is being used!" -ForegroundColor Cyan
Write-Host "Note: First run might still show CPU while model loads to GPU" -ForegroundColor Gray
