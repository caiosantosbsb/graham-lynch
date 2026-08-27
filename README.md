# 📊 Dashboard Graham & Lynch — Guia Completo

## 🏗️ Como funciona (arquitetura atual)

Este projeto tem **duas cópias** do mesmo dashboard, com propósitos diferentes:

| | 💻 Local (seu PC) | 🌐 Público (GitHub Pages) |
|---|---|---|
| **Fonte de dados** | StatusInvest (dados reais, IP residencial) | Mesmo HTML gerado localmente — **não roda mais Python na nuvem** |
| **Uso** | ✅ Decisão de compra/venda | ✅ Só consulta de posição no celular/trabalho |
| **Como atualiza** | Tarefa agendada do Windows roda `dashboard_completo.py` + `git push` todo dia útil às 19h30 | Dispara sozinho quando recebe o push (deploy automático) |

> **Por que mudou?** Antes o GitHub Actions rodava o script na nuvem, mas o StatusInvest bloqueia IPs de datacenter — ele caía para o yfinance, que gerava recomendações diferentes das que você via localmente. Agora o HTML publicado é **exatamente o mesmo gerado no seu PC**, eliminando essa divergência.

---

## 🚀 Como usar

### Executar localmente (ver na hora)
1. Abra a pasta do projeto
2. Dê **duplo-clique** em `executar.bat`
3. Aguarde (~2 min) — o dashboard abre sozinho no navegador

### Ver online (reflete o que rodou localmente)
- Acesse: **https://caiosantosbsb.github.io/graham-lynch/**
- Atualiza sozinho todo dia útil, alguns minutos depois das 19h30 (quando a tarefa local roda e publica)

---

## 🖥️ Configurar em um PC novo (ex: PC pessoal)

### 1. Instalar dependências
- **Git**: https://git-scm.com/download/win (instalação padrão)
- **Python 3.11+**: https://python.org/downloads — marque ✅ **"Add Python to PATH"**

### 2. Clonar o repositório
```powershell
cd C:\  # ou pasta de sua preferência
git clone https://github.com/caiosantosbsb/graham-lynch.git
cd graham-lynch
```
No primeiro acesso o Git vai pedir login do GitHub. Use um **Personal Access Token** (não a senha normal):
1. Acesse https://github.com/settings/tokens → "Generate new token (classic)"
2. Marque o escopo `repo`
3. Copie o token e cole quando o Git pedir a "senha" (usuário = seu usuário do GitHub)
4. O Windows Credential Manager salva o token — não pede de novo depois

### 3. Testar geração local
```powershell
pip install -r requirements.txt
python dashboard_completo.py
```
Confirme que `graham_dashboard.html` foi criado e que o banner no topo diz **"Dados via StatusInvest (local)"** (verde) — se aparecer o aviso amarelo de yfinance, algo bloqueou o StatusInvest nesse PC/rede.

### 4. Testar o push manual (fazer ANTES de agendar)
```powershell
.\atualizar_e_publicar.bat
```
Confirme no fim que apareceu "Dashboard atualizado e publicado com sucesso" (ou veja `atualizacao.log`). Confira também no GitHub se o commit chegou.

### 5. Agendar a tarefa diária
```powershell
$action = New-ScheduledTaskAction -Execute "C:\caminho\para\graham-lynch\atualizar_e_publicar.bat" -WorkingDirectory "C:\caminho\para\graham-lynch"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 19:30
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "GrahamLynch_AtualizarDashboard" -Action $action -Trigger $trigger -Settings $settings -Description "Gera dashboard Graham/Lynch com dados StatusInvest e publica no GitHub" -RunLevel Limited
```
Ajuste o caminho (`C:\caminho\para\graham-lynch`) para onde você clonou o repositório.

> ⚠️ Se usar este projeto em **mais de um PC** (ex: trabalho + pessoal), mantenha a tarefa agendada ativa em **apenas um** deles para evitar dois pushes conflitantes no mesmo horário. Desative nos demais:
> ```powershell
> Disable-ScheduledTask -TaskName "GrahamLynch_AtualizarDashboard"
> ```

### Verificar se a tarefa rodou
```powershell
Get-ScheduledTaskInfo -TaskName "GrahamLynch_AtualizarDashboard"
```
`LastTaskResult = 0` significa sucesso. Ou abra `atualizacao.log` na pasta do projeto.

---

## 📁 Estrutura do Projeto

```
graham-lynch\
├── dashboard_completo.py       ← Script principal (gera o HTML)
├── carteira.json               ← Suas posições + dividendos recebidos
├── requirements.txt            ← Dependências Python
├── executar.bat                ← Duplo-clique para rodar e ver local (sem publicar)
├── atualizar_e_publicar.bat    ← Roda + faz commit/push (usado pela tarefa agendada)
├── atualizacao.log             ← Log da última execução automática (não versionado)
├── .gitignore                  ← Arquivos ignorados pelo Git
└── .github/
    └── workflows/
        └── update-dashboard.yml ← Só publica (deploy) o HTML recebido via push
```

---

## ✏️ Atualizar a Carteira

Quando **comprar ou vender** ações, edite `carteira.json`:

### Posição (compra/venda)
```json
{
  "id": 1,
  "ticker": "PETR4",
  "quantidade": 333,
  "preco_medio": 33.40,
  "data_compra": "2025-10-01",
  "descricao": "Valor + Dividendos",
  "corretora": "Ion"
}
```

Calcular preço médio: `preco_medio = valor_total_investido / quantidade_de_acoes`

- **Ações brasileiras**: ticker com números (`PETR4`, `BBAS3`), corretora `"Ion"`, valores em R$
- **Ações americanas**: ticker sem números (`NVDA`, `GOOGL`), corretora `"Avenue"`, valores em US$

### Dividendos recebidos (caem na conta corrente, não na corretora)
```json
"dividendos_recebidos": {
  "historico": [
    {"mes": "2026-07", "valor": 320.50, "obs": "PETR4+TAEE11"}
  ]
}
```
O dashboard mostra dois valores separados na aba CARTEIRA:
- **Estimado (12 meses)**: calculado automaticamente pelo Dividend Yield atual × valor da posição
- **Recebido**: soma do que você lançar manualmente aqui

Depois de editar, rode `python dashboard_completo.py` (ou `executar.bat`) para ver refletido, e `atualizar_e_publicar.bat` (ou aguarde a tarefa agendada) para publicar.

---

## 📤 Enviar alterações manualmente (se não usar a tarefa agendada)

```powershell
cd C:\caminho\para\graham-lynch
git add -A
git commit -m "carteira: compra CMIG4 100 acoes"
git push origin main
```

### ⚠️ Se der erro no push (rejeição)
```powershell
git pull --rebase origin main
git push origin main
```

---

## 📋 Abas do Dashboard

| Aba | O que mostra | Para quê |
|-----|-------------|----------|
| **CARTEIRA** | Suas posições, sinais de ação e dividendos | Acompanhar posição e decidir reforçar/vender |
| **TOP BUY** | Ações aprovadas por Graham E/OU Lynch, ranking único | Decisão de compra principal |
| **GRAHAM PRO** | Ranking detalhado por valor (6 critérios) | Ações baratas e seguras, com detalhamento |
| **LYNCH PRO** | Ranking detalhado por crescimento (6 critérios) | Ações com potencial de valorização, com detalhamento |

> As antigas abas "Graham" e "Lynch" (tabelas cruas com todos os tickers) foram **removidas da navegação** para simplificar — os mesmos dados alimentam TOP BUY e as abas PRO.

---

## 🚦 Sinais da Carteira

| Sinal | Significado | Ação |
|-------|-------------|------|
| 🔵 **REFORÇAR** | Score alto + preço ainda bom | Comprar mais |
| 🟢 **MANTER** | Score médio, sem urgência | Deixar quieto |
| 🟠 **GIRO PARCIAL** | Lucro ≥30% mas fundamento ainda forte (score ≥5) | Considere realizar 20-30% da posição e reaportar em ação descontada, mantendo o restante |
| 🟡 **AVALIAR TROCA** | Scores baixos nos 2 métodos | Pesquisar alternativa |
| 🔴 **REALIZAR LUCRO** | Lucro >30% + scores baixos | Vender e trocar — fundamento não sustenta mais o preço |

---

## 🌐 Fontes de dados

| Fonte | Dados | Disponibilidade |
|-------|-------|------------------|
| **StatusInvest** | Fundamentos BR completos, CAGR 5 anos | Só funciona com IP residencial (local) |
| **yfinance** | Cotações e fundamentos (BR e US) | Funciona em qualquer lugar, mas growth é CAGR ~3 anos (menos preciso) |
| **AwesomeAPI** | Câmbio USD/BRL | Sempre disponível |

O banner no topo do dashboard indica qual fonte predominou na última geração (verde = StatusInvest/confiável para compra; amarelo = yfinance/só acompanhamento).

---

## ⚙️ GitHub Actions (agora só publica)

- **Quando roda**: automaticamente a cada push que altera `graham_dashboard.html`
- **O que faz**: copia o HTML já pronto e publica no GitHub Pages (não gera dados, não usa yfinance)
- **Verificar**: https://github.com/caiosantosbsb/graham-lynch/actions

---

## 🛠️ Requisitos

- **Python 3.11+** — `python --version`
- **Git** — `git --version`
- **pip** — `pip --version`

```powershell
pip install -r requirements.txt
```

---

## 💡 Estratégia de Investimento

```
Perfil: buy and hold, aporte mensal (5º dia útil após salário)
Alocação-alvo: 60% crescimento | 30% renda | 10% segurança

Decisão de compra    → SEMPRE local (StatusInvest), nunca pelo site público
Comprar nova posição → Olhar TOP BUY primeiro
Foco em dividendos   → GRAHAM PRO (TAEE11, CPFE3, SAPR11)
Foco em crescimento  → LYNCH PRO
Sinal REFORÇAR       → Prioridade máxima
Sinal GIRO PARCIAL   → Realizar uma fatia do lucro, sem abandonar a posição
```
