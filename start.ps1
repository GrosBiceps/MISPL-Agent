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
    Write-Warning ".env absent — copier .env.example vers .env et renseigner OPENROUTER_API_KEY"
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
    "router" {
        # Routeur LLM local FreeLLMAPI (cf. MISPL_LLM_* dans .env.example).
        # Exige Node >= 20.18 (module natif better-sqlite3) : NODE22_DIR force
        # une install nvm précise sans changer la version Node globale.
        $RouterDir = if ($env:FREELLMAPI_DIR) { $env:FREELLMAPI_DIR } else { "$Root\..\..\freellmapi" }
        $NodeDir = if ($env:NODE22_DIR) { $env:NODE22_DIR } else { "$env:LOCALAPPDATA\nvm\v22.18.0" }
        if (-not (Test-Path $RouterDir)) { Write-Error "FreeLLMAPI introuvable : $RouterDir (definir FREELLMAPI_DIR)"; break }
        if (Test-Path "$NodeDir\node.exe") { $env:PATH = "$NodeDir;$env:PATH" }
        Write-Host "`n[ROUTEUR] FreeLLMAPI : API http://127.0.0.1:3001/v1 - tableau de bord http://localhost:5173"
        Set-Location $RouterDir
        npm run dev
    }
    default {
        Write-Host "Usage : .\start.ps1 [build|run|cli|router]"
        Write-Host "  build  : construire la base documentaire (1x)"
        Write-Host "  run    : lancer l'interface Streamlit (defaut)"
        Write-Host "  cli    : mode ligne de commande interactif"
        Write-Host "  router : lancer le routeur LLM local FreeLLMAPI (fenetre separee)"
    }
}
