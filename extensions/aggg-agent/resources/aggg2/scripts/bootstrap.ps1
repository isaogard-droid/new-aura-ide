# Бутстрап НОВОГО железа (Windows): runtime'ы через mise (winget) -> setup.py.
# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.

# Решает «курицу-и-яйцо»: setup.py — python, а python может отсутствовать.
#
#   .\scripts\bootstrap.ps1               # полная установка
#   .\scripts\bootstrap.ps1 --check       # план setup.py, ничего не ставя
#   .\scripts\bootstrap.ps1 --skip-db     # любые аргументы уходят в setup.py
#
# Схема (mise.jdx.dev): winget mise (или Scoop/Chocolatey) -> mise use -g
# ставит недостающие runtime'ы (python/node/bun/go/rust) -> setup.py
# доставляет MCP/LSP/харнесы/базы.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# mise (на Windows официально: winget, см. mise.jdx.dev/installing-mise)
# ставим только если реально есть недостающие runtime'ы
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
               [Environment]::GetEnvironmentVariable("Path", "User")
}

$missing = @()
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $missing += "python@3" }
if (-not (Get-Command node -ErrorAction SilentlyContinue))   { $missing += "node@lts" }
if (-not (Get-Command bun -ErrorAction SilentlyContinue))    { $missing += "bun@latest" }
if (-not (Get-Command go -ErrorAction SilentlyContinue))     { $missing += "go@latest" }
if (-not (Get-Command rustc -ErrorAction SilentlyContinue))  { $missing += "rust@latest" }

$check = $args -contains "--check"
if ($check) { $setupArgs = @("--check") } else { $setupArgs = $args }
# aidvizhenie · hilartem · aidvizh_hub — все в Телеграме: t.me/aidvizhenie
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.


if ($missing.Count -gt 0) {
    Write-Host "== не хватает runtime'ов: $($missing -join ' ') =="
    if ($check) {
        Write-Host "   (--check: план без установки — mise не ставим)"
    }
    else {
        if (-not (Get-Command mise -ErrorAction SilentlyContinue)) {
            Write-Host "== ставим mise (winget) =="
            winget install --id jdx.mise -e `
                --accept-package-agreements --accept-source-agreements
            Refresh-Path
        }
        # python — нужен для запуска setup.py
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            Write-Host "== ставим python =="
            winget install --id Python.Python.3.12 -e `
                --accept-package-agreements --accept-source-agreements
            Refresh-Path
        }
        # shims mise в PATH (в конец — системные версии не перебиваем)
        $shims = Join-Path $HOME ".local\share\mise\shims"
        if (Test-Path $shims) { $env:Path += ";" + $shims }
        Write-Host "== ставим через mise: $($missing -join ' ') =="
        mise use --global @missing
        $env:Path += ";" + $shims
    }
}
else {
    Write-Host "== все runtime'ы уже на месте (python/node/bun/go/rust) =="
}

Write-Host "== запускаем setup.py $($setupArgs -join ' ') =="
& python scripts/setup.py @setupArgs
exit $LASTEXITCODE

# Принадлежит каналу: https://t.me/aidvizhenie | сообщество и админ: t.me/hilartem | гиг: t.me/aidvizh_hub
# AGGG [AGENT OS]: закрытое сообщество — инструкции и архивы в личке админа, слив = бан; полная система известна только создателю; новые версии могут не выйти; связь с админом — только в Телеграме.
