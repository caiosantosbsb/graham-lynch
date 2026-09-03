@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM Atualiza dashboard com dados locais (StatusInvest) e publica
REM automaticamente no GitHub (dispara o deploy do GitHub Pages).
REM Executado diariamente pelo Agendador de Tarefas do Windows.
REM
REM Erros agora aparecem NA TELA (antes iam so para atualizacao.log
REM e a janela fechava sem mostrar nada).
REM ============================================================

cd /d "%~dp0"
set LOG=atualizacao.log
set STEPLOG=%TEMP%\graham_lynch_passo.tmp

call :log "============================================================"
call :log "[%date% %time%] Iniciando atualizacao do dashboard..."

REM ------------------------------------------------------------
REM 1) Deixa a arvore limpa. O 'git pull --rebase' recusa rodar com
REM    qualquer alteracao nao commitada ("cannot pull with rebase:
REM    You have unstaged changes"), que era a causa das falhas.
REM
REM    O HTML e artefato gerado: a versao local e descartada porque
REM    seria regenerada no passo 4 de qualquer forma, e mante-la so
REM    cria conflito quando o repositorio e usado em dois PCs.
REM
REM    Qualquer outra alteracao (carteira.json, dashboard_completo.py)
REM    e commitada automaticamente para nunca ser perdida.
REM ------------------------------------------------------------
echo [1/5] Preparando arvore de trabalho...
git checkout -- graham_dashboard.html >nul 2>&1
git add -u > "%STEPLOG%" 2>&1
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Alteracoes locais salvas antes da sincronizacao - %date% %time%" > "%STEPLOG%" 2>&1
    if errorlevel 1 (
        call :erro "Falha ao commitar as alteracoes locais antes do pull."
        goto :fim_erro
    )
    call :log "Alteracoes locais commitadas antes da sincronizacao."
)
call :append

REM Se ainda restar algo nao commitado, o pull vai falhar. Avisa antes.
git diff --quiet
if errorlevel 1 (
    call :erro "Ainda existem alteracoes nao commitadas. Rode 'git status' e resolva manualmente."
    goto :fim_erro
)

REM ------------------------------------------------------------
REM 2) Sincroniza com o repositorio remoto
REM ------------------------------------------------------------
echo [2/5] Sincronizando com o GitHub...
git pull --rebase origin main > "%STEPLOG%" 2>&1
if errorlevel 1 (
    REM Conflito. Se for so no HTML gerado, resolve sozinho pegando a
    REM versao do remoto - o arquivo e regenerado no passo seguinte.
    set RESOLVIDO=0
    for /L %%i in (1,1,5) do (
        if exist ".git\rebase-merge" (
            git checkout --ours graham_dashboard.html >nul 2>&1
            git add graham_dashboard.html >nul 2>&1
            git -c core.editor=true rebase --continue >> "%STEPLOG%" 2>&1
            if not exist ".git\rebase-merge" set RESOLVIDO=1
        )
    )
    if "!RESOLVIDO!"=="0" (
        git rebase --abort >nul 2>&1
        call :erro "Falha no 'git pull --rebase' e o conflito NAO era so no HTML gerado. Rode diagnostico.bat e verifique."
        goto :fim_erro
    )
    call :log "Conflito no HTML gerado resolvido automaticamente."
)
call :append

REM ------------------------------------------------------------
REM 3) Dependencias
REM ------------------------------------------------------------
echo [3/5] Verificando dependencias...
pip install -r requirements.txt --quiet > "%STEPLOG%" 2>&1
if errorlevel 1 (
    call :erro "Falha no 'pip install -r requirements.txt'. Python/pip instalado e no PATH?"
    goto :fim_erro
)
call :append

REM ------------------------------------------------------------
REM 4) Gera o dashboard (dados StatusInvest = IP residencial)
REM ------------------------------------------------------------
echo [4/5] Gerando dashboard (86 acoes, leva alguns minutos)...
set PYTHONIOENCODING=utf-8
python dashboard_completo.py > "%STEPLOG%" 2>&1
if errorlevel 1 (
    call :erro "Falha ao executar dashboard_completo.py."
    goto :fim_erro
)
call :append

REM ------------------------------------------------------------
REM 5) Publica somente se houve mudanca real
REM ------------------------------------------------------------
echo [5/5] Publicando no GitHub...
git add graham_dashboard.html carteira.json dashboard_completo.py > "%STEPLOG%" 2>&1
call :append
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Atualizacao automatica do dashboard - %date% %time%" > "%STEPLOG%" 2>&1
    call :append
    git push origin main > "%STEPLOG%" 2>&1
    if errorlevel 1 (
        call :erro "Falha no 'git push'. Dashboard foi GERADO mas NAO publicado. Provavel problema de credencial do GitHub nesta maquina."
        goto :fim_erro
    )
    call :append
    call :log "[%date% %time%] Dashboard atualizado e publicado com sucesso."
    echo.
    echo  OK - Dashboard atualizado e publicado.
) else (
    call :log "[%date% %time%] Nenhuma mudanca detectada, nada a publicar."
    echo.
    echo  OK - Nenhuma mudanca detectada, nada a publicar.
)

call :log "[%date% %time%] Concluido."
call :log ""
if exist "%STEPLOG%" del "%STEPLOG%" >nul 2>&1
echo.
timeout /t 15 >nul
endlocal
exit /b 0

REM ============================================================
REM Sub-rotinas
REM ============================================================
:log
echo %~1 >> "%LOG%"
exit /b 0

:append
if exist "%STEPLOG%" type "%STEPLOG%" >> "%LOG%" 2>&1
exit /b 0

:erro
echo.
echo ############################################################
echo  ERRO: %~1
echo ############################################################
echo.
echo  --- saida do comando que falhou ---
if exist "%STEPLOG%" type "%STEPLOG%"
echo  -----------------------------------
call :log "[%date% %time%] ERRO: %~1"
call :append
exit /b 0

:fim_erro
echo.
echo  Log completo em: %CD%\%LOG%
echo  Para investigar, rode: diagnostico.bat
echo.
echo  (esta janela fecha sozinha em 2 minutos)
timeout /t 120 >nul
if exist "%STEPLOG%" del /q "%STEPLOG%"
endlocal
exit /b 1
