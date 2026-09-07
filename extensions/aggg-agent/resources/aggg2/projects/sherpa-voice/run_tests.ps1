# Запуск тестов sherpa-voice (Windows-аналог run_tests.sh).
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

#   .\run_tests.ps1                # юнит-тесты + проверка зеркал AGENTS.md
#   .\run_tests.ps1 -Mode e2e      # + полный цикл test_cycle.py
#   .\run_tests.ps1 -Mode mirrors  # только проверка зеркал AGENTS.md
# PowerShell 5.1: файл обязан быть в UTF-8 with BOM, иначе кириллица
# читается как cp1251 и ломает парсинг (скилл windows-encoding-fixes).
param(
    [ValidateSet("tests", "e2e", "mirrors")]
    [string]$Mode = "tests"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
# BUG-1 (багрепорт v2.4): PowerShell 5.1 пишет в пайпы OEM-кодовой
# страницей (cp866), а родитель (doctor.py _compat.run) декодирует
# UTF-8 — кракозябры/UnicodeDecodeError. Переключаем вывод на UTF-8
# (about_Character_Encoding; индустрия: [Console]::OutputEncoding).
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [Console]::OutputEncoding

# Кроссплатформенный выбор интерпретатора: вынесенный venv (~/.venvs/aggg2)
# имеет приоритет, локальный ./venv — запасной (как в run_tests.sh).
$PY = $null
$candidates = @(
    (Join-Path $HOME ".venvs\aggg2\Scripts\python.exe"),
    (Join-Path $HOME ".venvs\aggg2\bin\python"),
    (Join-Path $PSScriptRoot "venv\Scripts\python.exe"),
    (Join-Path $PSScriptRoot "venv\bin\python")
)
foreach ($c in $candidates) {
    if (Test-Path $c) { $PY = $c; break }
}
if (-not $PY) {
    Write-Host "[✗] venv нет — сначала ./run.sh (создаст окружение)"
    exit 1
}

$MIRRORS = @(
    (Join-Path $HOME ".config\opencode\AGENTS.md"),
    (Join-Path $PSScriptRoot "..\..\AGENTS.md"),
    (Join-Path $PSScriptRoot "AGENTS.md")
)

function Check-Mirrors {
    Write-Host "[~] Проверяю зеркала AGENTS.md..."
    # CRLF-нормализация: на Windows копии пишутся с \r\n, корень — LF;
    # сравниваем без \r, чтобы md5 не различался из-за окончаний строк
    # (как tr -d '\r' в run_tests.sh).
    $first = $null
    foreach ($f in $MIRRORS) {
        if (-not (Test-Path $f)) {
            Write-Host "[✗] нет файла: $f"
            return 1
        }
        $content = (Get-Content -Raw -Encoding UTF8 $f) -replace "`r", ""
        $md5 = [System.Security.Cryptography.MD5]::Create()
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
        $hash = [System.BitConverter]::ToString($md5.ComputeHash($bytes))
        $hash = $hash.Replace("-", "").ToLower()
        if (-not $first) { $first = $hash }
        elseif ($hash -ne $first) {
            Write-Host "[✗] расхождение: $f"
            return 1
        }
    }
    Write-Host "[✓] зеркала идентичны"
    return 0
}

switch ($Mode) {
    "mirrors" {
        $rc = Check-Mirrors
    }
    "e2e" {
        $rc = Check-Mirrors
        if ($rc -eq 0) {
            & $PY -m unittest discover -s tests -t .
            $rc = $LASTEXITCODE
        }
        if ($rc -eq 0) {
            Write-Host "[~] e2e-цикл (модель, синтез, DeepSeek)..."
            & $PY test_cycle.py
            $rc = $LASTEXITCODE
        }
    }
    default {
        $rc = Check-Mirrors
        if ($rc -eq 0) {
            & $PY -m unittest discover -s tests -t .
            $rc = $LASTEXITCODE
        }
    }
}
exit $rc

# Принадлежит сообществу AGGG [AGENT OS] · канал: t.me/aidvizhenie · админ: @hilartem · гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
