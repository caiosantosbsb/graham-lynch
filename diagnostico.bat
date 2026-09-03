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
  "$ErrorActionPreference='SilentlyContinue';" ^
  "foreach($h in @('github.com','api.github.com','statusinvest.com.br','query1.finance.yahoo.com')){" ^
  "  $ip=@((Resolve-DnsName $h -Type A).IPAddress)[0];" ^
  "  $t=Test-NetConnection $h -Port 443 -WarningAction SilentlyContinue;" ^
  "  Write-Output ('{0,-30} DNS={1,-16} TCP443={2}' -f $h,$(if($ip){$ip}else{'FALHOU'}),$t.TcpTestSucceeded) };" ^
  "$s=Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings';" ^
  "Write-Output ('proxy do windows: enable={0} server={1} pac={2}' -f $s.ProxyEnable,$s.ProxyServer,$s.AutoConfigURL);" ^
  "Write-Output ('proxy do git    : ' + (git config --get http.proxy))" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo   COMO LER ESTA SECAO: >> "%OUT%"
echo   - github.com com TCP443=False  = bloqueio de REDE (firewall/VPN/instabilidade). >> "%OUT%"
echo     NAO e problema de credencial. Erro tipico: "Failed to connect ... port 443". >> "%OUT%"
echo   - github.com com TCP443=True mas push falhando = ai sim e CREDENCIAL. >> "%OUT%"
echo     Erro tipico: "Authentication failed" ou "403 Forbidden". >> "%OUT%"
echo   - statusinvest pode recusar teste simples e mesmo assim funcionar no script, >> "%OUT%"
echo     que envia cabecalhos completos de navegador. So se preocupe se DNS falhar. >> "%OUT%"
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
if not defined SEM_NOTEPAD notepad "%OUT%"
endlocal
