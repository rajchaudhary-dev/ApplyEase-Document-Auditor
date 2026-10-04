$pythonDir = "$env:TEMP\python-embed"
$pthFile = Join-Path $pythonDir "python311._pth"

if (Test-Path $pthFile) {
    $content = Get-Content $pthFile
    $content = $content -replace '#import site', 'import site'
    Set-Content -Path $pthFile -Value $content
}

$pipFile = Join-Path $pythonDir "get-pip.py"
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $pipFile
& "$pythonDir\python.exe" $pipFile
& "$pythonDir\python.exe" -m pip install google-genai opencv-python-headless pillow pydantic fastapi uvicorn requests python-multipart
