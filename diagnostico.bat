@echo off
setlocal
REM ============================================================
REM DIAGNOSTICO - rode este arquivo no PC de CASA com 2 cliques.
REM Ele nao altera nada, so coleta informacao e gera diagnostico.txt
REM Abra o diagnostico.txt e cole o conteudo no chat.
REM ============================================================

cd /d "%~dp0"
set OUT=diagnostico.txt

echo ============================================================ > "%OUT%"
echo DIAGNOSTICO GRAHAM-LYNCH  -  %date% %time%                  >> "%OUT%"
echo Maquina: %COMPUTERNAME%   Usuario: %USERNAME%               >> "%OUT%"
echo Pasta:   %CD%                                               >> "%OUT%"
echo ============================================================ >> "%OUT%"
echo. >> "%OUT%"

echo [1] PYTHON >> "%OUT%"
where python                      >> "%OUT%" 2>&1
python --version                  >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo [2] PIP E DEPENDENCIAS >> "%OUT%"
where pip                         >> "%OUT%" 2>&1
python -c "import requests, bs4, yfinance; print('imports OK: requests, bs4, yfinance')" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo [3] GIT >> "%OUT%"
where git                         >> "%OUT%" 2>&1
git --version                     >> "%OUT%" 2>&1
git remote -v                     >> "%OUT%" 2>&1
git branch --show-current         >> "%OUT%" 2>&1
git config --get credential.helper >> "%OUT%" 2>&1
git config --get user.email       >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo [4] ESTADO DO REPOSITORIO >> "%OUT%"
git status --short                >> "%OUT%" 2>&1
echo --- ultimos commits locais --- >> "%OUT%"
git --no-pager log --oneline -5   >> "%OUT%" 2>&1
echo --- rebase/merge em andamento? --- >> "%OUT%"
if exist ".git\rebase-merge" echo ATENCAO: existe rebase EM ANDAMENTO (.git\rebase-merge) >> "%OUT%"
if exist ".git\rebase-apply" echo ATENCAO: existe rebase EM ANDAMENTO (.git\rebase-apply) >> "%OUT%"
if exist ".git\MERGE_HEAD"   echo ATENCAO: existe merge EM ANDAMENTO (.git\MERGE_HEAD)   >> "%OUT%"
if exist ".git\index.lock"   echo ATENCAO: existe .git\index.lock travando o repositorio >> "%OUT%"
echo. >> "%OUT%"

echo [5] COMPARACAO COM O REMOTO >> "%OUT%"
git fetch origin main             >> "%OUT%" 2>&1
echo --- commits locais nao enviados (ahead) --- >> "%OUT%"
git --no-pager log --oneline origin/main..HEAD >> "%OUT%" 2>&1
echo --- commits remotos nao baixados (behind) --- >> "%OUT%"
git --no-pager log --oneline HEAD..origin/main >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo [6] TESTE DE PUSH (simulado, nao envia nada) >> "%OUT%"
git push --dry-run origin main    >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo [7] CONECTIVIDADE >> "%OUT%"
powershell -NoProfile -Command ^
  "foreach($u in @('https://statusinvest.com.br/acoes/petr4','https://github.com')){ try { $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 20 -Headers @{'User-Agent'='Mozilla/5.0'}; Write-Output ('{0} -> HTTP {1}' -f $u,$r.StatusCode) } catch { Write-Output ('{0} -> FALHOU: {1}' -f $u,$_.Exception.Message) } }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo [8] ULTIMAS 40 LINHAS DE atualizacao.log >> "%OUT%"
if exist atualizacao.log (
    powershell -NoProfile -Command "Get-Content 'atualizacao.log' -Tail 40" >> "%OUT%" 2>&1
) else (
    echo atualizacao.log NAO EXISTE - a bat nunca chegou a rodar nesta maquina. >> "%OUT%"
)
echo. >> "%OUT%"
echo ==================== FIM DO DIAGNOSTICO ==================== >> "%OUT%"

echo.
echo Diagnostico gerado em: %CD%\diagnostico.txt
echo Abra o arquivo e cole o conteudo no chat.
echo.
notepad "%OUT%"
endlocal
