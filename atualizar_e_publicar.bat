@echo off
REM ============================================================
REM Atualiza dashboard com dados locais (StatusInvest) e publica
REM automaticamente no GitHub (dispara o deploy do GitHub Pages).
REM Executado diariamente pelo Agendador de Tarefas do Windows.
REM ============================================================

cd /d "%~dp0"

echo [%date% %time%] Iniciando atualizacao do dashboard... >> atualizacao.log

REM Instala/atualiza dependencias silenciosamente
pip install -r requirements.txt --quiet >> atualizacao.log 2>&1

REM Gera o dashboard com dados StatusInvest (roda localmente = IP residencial)
python dashboard_completo.py >> atualizacao.log 2>&1
if errorlevel 1 (
    echo [%date% %time%] ERRO ao gerar dashboard. Abortando publicacao. >> atualizacao.log
    exit /b 1
)

REM Publica apenas se houver mudanca real no HTML gerado
git add graham_dashboard.html carteira.json >> atualizacao.log 2>&1
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Atualizacao automatica do dashboard - %date% %time%" >> atualizacao.log 2>&1
    git push origin main >> atualizacao.log 2>&1
    echo [%date% %time%] Dashboard atualizado e publicado com sucesso. >> atualizacao.log
) else (
    echo [%date% %time%] Nenhuma mudanca detectada, nada a publicar. >> atualizacao.log
)

echo [%date% %time%] Concluido. >> atualizacao.log
echo. >> atualizacao.log
