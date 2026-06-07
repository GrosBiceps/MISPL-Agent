# MISPL Agent v2 — Script de demarrage PowerShell (OpenRouter backend)
# Usage : .\start.ps1 [build|run|cli]

param([string]$Mode = "run")

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "$Root\.venv\Scripts\python.exe"
$Streamlit = "$Root\.venv\Scripts\streamlit.exe"

# Forcer UTF-8 (obligatoire Windows pour les accents dans les messages)
$env:PYTHONUTF8 = "1"

# Charger .env si présent
if (Test-Path "$Root\.env") {
    Get-Content "$Root\.env" | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.+)$") {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
    Write-Host "[OK] .env charge"
} else {
    Write-Warning ".env absent — copier .env.example vers .env et renseigner ANTHROPIC_API_KEY"
}

switch ($Mode) {
    "build" {
        Write-Host "`n[BUILD] Construction du vectorstore RAG..."
        & $Python "$Root\src\rag\build_vectorstore.py"
    }
    "cli" {
        Write-Host "`n[CLI] Mode interactif MISPL Agent..."
        & $Python "$Root\src\agent\mispl_agent.py"
    }
    "run" {
        Write-Host "`n[STREAMLIT] Lancement interface web..."
        Write-Host "Ouvrir : http://localhost:8501"
        & $Streamlit run "$Root\app.py" --server.port 8501 --server.headless false
    }
    default {
        Write-Host "Usage : .\start.ps1 [build|run|cli]"
        Write-Host "  build  : construire la base documentaire (1x)"
        Write-Host "  run    : lancer l'interface Streamlit (defaut)"
        Write-Host "  cli    : mode ligne de commande interactif"
    }
}
