# 📊 Dashboard Graham & Lynch — Guia Completo

## 🚀 Como usar

### Executar localmente (ver na hora)
1. Abra a pasta `C:\Copilot\graham_lynch`
2. Dê **duplo-clique** em `executar.bat`
3. Aguarde (~2 min) — o dashboard abre sozinho no navegador

### Ver online (atualiza sozinho)
- Acesse: **https://caiosantosbsb.github.io/graham-lynch/**
- Atualiza automaticamente todo dia útil às **19h (BRT)**

---

## 📁 Estrutura do Projeto

```
C:\Copilot\graham_lynch\
├── dashboard_completo.py       ← Script principal (gera o HTML)
├── carteira.json               ← Suas posições (editar quando comprar/vender)
├── requirements.txt            ← Dependências Python
├── executar.bat                ← Duplo-clique para rodar local
├── .gitignore                  ← Arquivos ignorados pelo Git
└── .github/
    └── workflows/
        └── update-dashboard.yml ← Agendamento GitHub Actions
```

---

## ✏️ Atualizar a Carteira

Quando **comprar ou vender** ações, edite o arquivo `carteira.json`:

### Abrir para edição
```
notepad C:\Copilot\graham_lynch\carteira.json
```

### Formato de cada posição
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

### Calcular preço médio
```
preco_medio = valor_total_investido / quantidade_de_acoes
```
Exemplo: investiu R$ 11.121,09 em 333 ações → PM = 33,40

### Ações brasileiras
- Ticker com números: `PETR4`, `BBAS3`, `TAEE11`
- Corretora: `"Ion"`
- Valores em **R$**

### Ações americanas
- Ticker sem números: `NVDA`, `GOOGL`
- Corretora: `"Avenue"`
- Valores em **US$**

---

## 📤 Enviar alterações para o GitHub (Push)

Após editar `carteira.json` ou qualquer arquivo, envie para o GitHub:

### Passo a passo

1. **Abra o Terminal** (PowerShell ou Prompt de Comando)

2. **Entre na pasta do projeto**
```powershell
cd C:\Copilot\graham_lynch
```

3. **Verifique o que mudou**
```powershell
git status
```

4. **Adicione as alterações**
```powershell
git add -A
```

5. **Faça o commit** (descreva o que mudou)
```powershell
git commit -m "atualizar carteira - compra CMIG4"
```

6. **Envie para o GitHub**
```powershell
git push origin main
```

7. **Aguarde ~3 minutos** — o GitHub Actions gera e publica automaticamente

### ⚠️ Se o git não for encontrado
Use o caminho completo:
```powershell
& "C:\Program Files\Git\cmd\git.exe" add -A
& "C:\Program Files\Git\cmd\git.exe" commit -m "mensagem"
& "C:\Program Files\Git\cmd\git.exe" push origin main
```

### ⚠️ Se der erro no push (rejeição)
```powershell
git pull --rebase origin main
git push origin main
```

---

## 🔄 Fluxo completo (exemplo: comprei CMIG4)

```
1. Abro carteira.json no Bloco de Notas
2. Adiciono a nova posição com id, ticker, quantidade, preco_medio
3. Salvo o arquivo
4. Abro o Terminal:
   cd C:\Copilot\graham_lynch
   git add -A
   git commit -m "carteira: compra CMIG4 100 acoes"
   git push origin main
5. Em ~3 min o dashboard online atualiza
```

---

## 📋 Abas do Dashboard

| Aba | O que mostra | Para quê |
|-----|-------------|----------|
| **CARTEIRA** | Suas posições + sinais de ação | Saber quando vender/reforçar |
| **TOP BUY** | Ações aprovadas por Graham E Lynch | Melhor compra (investimento ouro) |
| **GRAHAM** | Análise de valor (6 critérios) | Ações baratas e seguras |
| **LYNCH** | Análise de crescimento (6 critérios) | Ações com potencial de valorização |
| **GRAHAM PRO** | Ranking forçado Graham | Ranking detalhado por valor |
| **LYNCH PRO** | Ranking forçado Lynch | Ranking detalhado por crescimento |

---

## 🚦 Sinais da Carteira

| Sinal | Significado | Ação |
|-------|-------------|------|
| 🔵 **REFORÇAR** | Score alto + preço bom | Comprar mais! |
| 🟢 **MANTER** | Score médio, sem urgência | Deixar quieto |
| 🟡 **AVALIAR TROCA** | Scores baixos nos 2 métodos | Pesquisar alternativa |
| 🔴 **REALIZAR LUCRO** | Lucro >30% + scores baixos | Vender e trocar |

---

## 🌐 APIs utilizadas

| API | Dados | Custo |
|-----|-------|-------|
| **yfinance** | Cotações, fundamentos (BR e US) | Gratuita |
| **AwesomeAPI** | Câmbio USD/BRL | Gratuita |
| **StatusInvest** | Fundamentos BR (só local) | Gratuita |

> **Nota**: No GitHub Actions, somente yfinance e AwesomeAPI funcionam.
> StatusInvest bloqueia IPs de datacenter.

---

## ⚙️ GitHub Actions (automação)

- **Quando roda**: Dias úteis às 22:00 UTC (19:00 BRT)
- **Também roda**: A cada push no main (arquivos .py, .json, requirements.txt)
- **O que faz**: Roda o Python → gera HTML → publica no GitHub Pages
- **Verificar**: https://github.com/caiosantosbsb/graham-lynch/actions

### Rodar manualmente pelo GitHub
1. Acesse: https://github.com/caiosantosbsb/graham-lynch/actions
2. Clique no workflow "Atualizar Dashboard"
3. Clique em "Run workflow" → "Run workflow"

---

## 🛠️ Requisitos (já instalados)

- **Python 3.12+** — `python --version`
- **Git** — `git --version`
- **pip** — `pip --version`

### Reinstalar dependências (se necessário)
```powershell
cd C:\Copilot\graham_lynch
pip install -r requirements.txt
```

---

## 💡 Estratégia de Investimento

```
Perfil: 60% crescimento | 30% renda | 10% segurança

Compra nova?     → Olhar TOP BUY primeiro
Sobrou grana?    → Lynch PRO para turbinar
Quer dividendos? → Graham PRO (TAEE11, CPFE3)
Sinal REFORÇAR?  → Prioridade máxima
```
