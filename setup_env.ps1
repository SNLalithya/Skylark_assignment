# setup_env.ps1
# Run this once from inside your project folder to write your .env file
# Usage:  .\setup_env.ps1

$projectDir = "C:\Users\Lalithaya\Downloads\skylark-bi-agent"
$envFile    = Join-Path $projectDir ".env"

Write-Host ""
Write-Host "=== Skylark BI Agent — .env Setup ===" -ForegroundColor Cyan
Write-Host "This script writes your .env file safely without exposing keys in chat."
Write-Host ""

# Prompt — input is hidden in terminal
$groq   = Read-Host "Paste your GROQ_API_KEY   (input hidden)" -AsSecureString
$monday = Read-Host "Paste your MONDAY_API_TOKEN (input hidden)" -AsSecureString

# Convert SecureString -> plain text  (only lives in memory, not logged)
$groqPlain   = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                   [Runtime.InteropServices.Marshal]::SecureStringToBSTR($groq))
$mondayPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                   [Runtime.InteropServices.Marshal]::SecureStringToBSTR($monday))

$content = @"
GROQ_API_KEY=$groqPlain
MONDAY_API_TOKEN=$mondayPlain
"@

Set-Content -Path $envFile -Value $content -Encoding UTF8
Write-Host ""
Write-Host ".env written to: $envFile" -ForegroundColor Green

# Verify
Write-Host ""
Write-Host "--- Verifying keys load correctly ---" -ForegroundColor Yellow
& py -3.12 -c @"
from dotenv import load_dotenv; import os
load_dotenv()
print('Groq:  ', 'OK' if os.getenv('GROQ_API_KEY')      else 'MISSING')
print('Monday:', 'OK' if os.getenv('MONDAY_API_TOKEN')   else 'MISSING')
"@

Write-Host ""
Write-Host "If both show OK, run:  py -3.12 -m chainlit run app.py" -ForegroundColor Cyan
