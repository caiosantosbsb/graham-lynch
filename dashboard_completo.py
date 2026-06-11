#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Graham & Peter Lynch - Versão Completa
Consulta StatusInvest + brapi.dev (Brasil) e yfinance (EUA)
"""

import requests
import json
import math
import sys
import os
import io
from datetime import datetime
from typing import Optional

# Força UTF-8 no stdout (Windows)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ============================================================
# CONFIGURAÇÃO
# ============================================================

TICKERS = [
    # Brasil - Blue Chips & Dividendos
    "SAPR11", "PETR4", "GOAU4", "CMIG4", "ITSA4", "AXIA3",
    "ENBR3", "FLRY3", "SUZB3", "PSSA3", "BNBR3", "BBAS3", "CPFE3",
    "GGBR4", "LEVE3", "NEOE3", "SBSP3", "VALE3", "TAEE11",
    "VIVT3", "TUPY3", "CPLE3", "AURE3", "RAPT4", "CSNA3", "WEGE3",
    
    # Brasil - Crescimento & Tech
    "ASAI3", "MULT3", "TIMS3", "RENT3", "MGLU3", "B3SA3",
    "CIEL3", "SQIA3", "PCAR3", "GRND3",
    
    # S&P 500 / Nasdaq (via yfinance)
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JNJ", "V", "WMT", "JPM", "MA", "PG", "COST", "MCD",
    "NFLX", "INTC", "AMD", "PYPL", "CRM", "ADBE", "CSCO", "IBM"
]

GRAHAM_CONSTANT = 22.5
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MIN_LIQUIDITY = 50000  # Volume mínimo em R$ para ser considerado bom (< = baixa liquidez)
BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN", "")  # Token gratuito de brapi.dev


# ============================================================
# FETCH DE DADOS
# ============================================================

def fetch_from_brapi(ticker: str) -> Optional[dict]:
    """API brapi.dev (fallback ou primária com token)"""
    try:
        url = f"https://brapi.dev/api/quote/{ticker}"
        params = {"fundamental": "true"}
        if BRAPI_TOKEN:
            params["token"] = BRAPI_TOKEN
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        
        results = resp.json().get("results", [])
        if not results:
            return None
        
        r = results[0]
        cotacao = r.get("regularMarketPrice")
        if not cotacao:
            return None
        
        return {
            "ticker": ticker,
            "cotacao": cotacao,
            "vpa": r.get("bookValue"),
            "lpa": r.get("earningsPerShare"),
            "pl": r.get("priceEarnings"),
            "pvpa": r.get("priceToBook"),
            "roe": r.get("returnOnEquity"),
            "div_ebitda": r.get("netDebtByEbitda"),
            "div_pl": r.get("netDebtByEquity"),
            "volume_dia": r.get("tradeVolume"),
            "growth_rate": r.get("revenuegrowth5year", 5),
            "dividend_yield": r.get("dividendYield"),
            "fonte": "brapi.dev"
        }
    except Exception as e:
        return None


def fetch_from_statusinvest(ticker: str) -> Optional[dict]:
    """Web scraping StatusInvest - apenas para tickers Bovespa"""
    try:
        # Skip US tickers - StatusInvest only has Bovespa data
        if not (ticker[-1].isdigit()):
            return None
        
        from bs4 import BeautifulSoup
        
        tipo = "acoes" if not ticker.endswith("11") else "acoes"
        url = f"https://statusinvest.com.br/{tipo}/{ticker.lower()}"
        
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, "html.parser")
        _found = {}
        
        def extract_value(title_text):
            title_upper = title_text.upper().strip()
            if title_upper in _found:
                return _found[title_upper]
            
            for tag in soup.find_all("h3"):
                if tag.get_text(strip=True).upper() == title_upper:
                    for parent in [tag.parent, tag.parent.parent]:
                        if parent:
                            strong = parent.find("strong")
                            if strong:
                                val = strong.get_text(strip=True).replace(".", "").replace(",", ".").replace("%", "")
                                try:
                                    result = float(val)
                                    _found[title_upper] = result
                                    return result
                                except:
                                    pass
            _found[title_upper] = None
            return None
        
        cotacao = extract_value("VALOR ATUAL")
        if cotacao is None:
            cotacao_el = soup.find("strong", class_="value")
            if cotacao_el:
                try:
                    cotacao = float(cotacao_el.get_text(strip=True).replace(".", "").replace(",", "."))
                except:
                    pass
        
        if not cotacao:
            return None
        
        roe = extract_value("ROE")
        if roe and abs(roe) > 1:
            roe = roe / 100.0
        
        # Div. liquida/PL e Div. liquida/EBITDA - tentar variações de nome
        div_pl = extract_value("DIV. LIQUIDA/PL")
        if div_pl is None:
            div_pl = extract_value("Div. liquida/PL")
        if div_pl is None:
            # Busca flexível: procurar por conteúdo parcial
            for tag in soup.find_all("h3"):
                txt = tag.get_text(strip=True).upper()
                if "QUIDA/PL" in txt and "EBITDA" not in txt:
                    for parent in [tag.parent, tag.parent.parent]:
                        if parent:
                            strong = parent.find("strong")
                            if strong:
                                val = strong.get_text(strip=True).replace(".", "").replace(",", ".").replace("%", "")
                                try:
                                    div_pl = float(val)
                                except:
                                    pass
                                break
                    if div_pl is not None:
                        break
        
        div_ebitda = extract_value("DIV. LIQUIDA/EBITDA")
        if div_ebitda is None:
            div_ebitda = extract_value("Div. liquida/EBITDA")
        if div_ebitda is None:
            for tag in soup.find_all("h3"):
                txt = tag.get_text(strip=True).upper()
                if "QUIDA/EBITDA" in txt:
                    for parent in [tag.parent, tag.parent.parent]:
                        if parent:
                            strong = parent.find("strong")
                            if strong:
                                val = strong.get_text(strip=True).replace(".", "").replace(",", ".").replace("%", "")
                                try:
                                    div_ebitda = float(val)
                                except:
                                    pass
                                break
                    if div_ebitda is not None:
                        break
        
        # Growth: CAGR Receitas 5 anos ou CAGR Lucros 5 anos
        growth = None
        for tag in soup.find_all("h3"):
            txt = tag.get_text(strip=True).upper()
            if "CAGR" in txt and "RECEITA" in txt:
                for parent in [tag.parent, tag.parent.parent]:
                    if parent:
                        strong = parent.find("strong")
                        if strong:
                            val = strong.get_text(strip=True).replace(".", "").replace(",", ".").replace("%", "").replace("-", "")
                            try:
                                growth = float(val)
                                if growth > 1:
                                    growth = growth  # já em %
                                break
                            except:
                                pass
                if growth is not None:
                    break
        
        # Fallback: CAGR Lucros
        if growth is None:
            for tag in soup.find_all("h3"):
                txt = tag.get_text(strip=True).upper()
                if "CAGR" in txt and "LUCRO" in txt:
                    for parent in [tag.parent, tag.parent.parent]:
                        if parent:
                            strong = parent.find("strong")
                            if strong:
                                val = strong.get_text(strip=True).replace(".", "").replace(",", ".").replace("%", "").replace("-", "")
                                try:
                                    growth = float(val)
                                    if growth > 1:
                                        growth = growth
                                    break
                                except:
                                    pass
                    if growth is not None:
                        break
        
        return {
            "ticker": ticker,
            "cotacao": cotacao,
            "vpa": extract_value("VPA"),
            "lpa": extract_value("LPA"),
            "pl": extract_value("P/L"),
            "pvpa": extract_value("P/VP"),
            "roe": roe,
            "div_ebitda": div_ebitda,
            "div_pl": div_pl,
            "volume_dia": extract_value("VOLUME (DIA)"),
            "growth_rate": growth if growth else 5,
            "dividend_yield": extract_value("DIVIDEND YIELD"),
            "fonte": "StatusInvest"
        }
    except:
        return None


def fetch_from_yfinance(ticker: str) -> Optional[dict]:
    """Fetch US stocks via yfinance"""
    try:
        import yfinance as yf
        
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Verifica dados essenciais
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        earnings = info.get("trailingEps")
        book_value = info.get("bookValue")
        
        if not all([price, earnings, book_value]):
            return None
        
        pe = info.get("trailingPE", 0)
        if pe and pe < 0.1:
            return None
        
        # debtToEquity vem como percentual (ex: 79.5 = 0.795)
        debt_to_equity = info.get("debtToEquity")
        div_pl = debt_to_equity / 100.0 if debt_to_equity else None
        
        # enterpriseToEbitda é EV/EBITDA, não exatamente Dív/EBITDA
        # Calcular Dív Líquida/EBITDA se possível
        total_debt = info.get("totalDebt", 0)
        cash = info.get("totalCash", 0)
        ebitda = info.get("ebitda", 0)
        div_ebitda = (total_debt - cash) / ebitda if ebitda and ebitda > 0 else None
        
        # Growth: earningsGrowth (YoY) ou revenueGrowth
        growth_raw = info.get("earningsGrowth") or info.get("revenueGrowth")
        growth_pct = growth_raw * 100 if growth_raw else 5
        
        return {
            "ticker": ticker,
            "cotacao": price,
            "lpa": earnings,
            "vpa": book_value,
            "pl": pe if pe and pe > 0 else None,
            "pvpa": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "div_ebitda": div_ebitda,
            "div_pl": div_pl,
            "volume_dia": info.get("volume", 0),
            "growth_rate": growth_pct,
            "dividend_yield": info.get("dividendYield", 0),
            "fonte": "yfinance"
        }
    except Exception as e:
        return None


def fetch_stock_data(ticker: str) -> Optional[dict]:
    """Tenta StatusInvest (Brasil) → brapi → yfinance (EUA)"""
    print(f"  {ticker}...", end=" ")
    
    # Tickers brasileiros (terminam em número)
    if ticker[-1].isdigit():
        # Tenta StatusInvest primeiro (melhor dados, mas falha em datacenter)
        data = fetch_from_statusinvest(ticker)
        if data and data.get("lpa") and data.get("vpa"):
            print("OK (StatusInvest)")
            return data
        
        # Fallback: brapi.dev (funciona em datacenter com token)
        data_brapi = fetch_from_brapi(ticker)
        if data_brapi:
            if data:
                for k, v in data_brapi.items():
                    if v and not data.get(k):
                        data[k] = v
                data["fonte"] = "StatusInvest+brapi"
            else:
                data = data_brapi
            if data.get("lpa") and data.get("vpa"):
                print("OK (brapi)")
                return data
        
        # Fallback final: yfinance com sufixo .SA (funciona em datacenter)
        data_yf = fetch_from_yfinance(f"{ticker}.SA")
        if data_yf and data_yf.get("lpa") and data_yf.get("vpa"):
            data_yf["ticker"] = ticker  # Manter ticker original sem .SA
            data_yf["fonte"] = "yfinance"
            print("OK (yfinance .SA)")
            return data_yf
    
    # Tenta yfinance (para tickers de EUA)
    else:
        data_yf = fetch_from_yfinance(ticker)
        if data_yf and data_yf.get("lpa") and data_yf.get("vpa"):
            print("OK (yfinance)")
            return data_yf
    
    print("FALHA")
    return None



# ============================================================
# ANÁLISE GRAHAM
# ============================================================

def calc_graham(data: dict) -> dict:
    """Calcula indicadores Graham"""
    lpa = data.get("lpa")
    vpa = data.get("vpa")
    cotacao = data.get("cotacao")
    
    preco_justo = math.sqrt(GRAHAM_CONSTANT * lpa * vpa) if lpa and vpa and lpa > 0 and vpa > 0 else None
    margem = ((preco_justo - cotacao) / preco_justo) if preco_justo else None
    
    score = 0
    criterios = []
    
    # 1. LPA > 0
    if lpa and lpa > 0:
        score += 1
        criterios.append("LPA>0 ✓")
    else:
        criterios.append("LPA>0 ✗")
    
    # 2. P/L < 15
    pl = data.get("pl") or (cotacao / lpa if lpa else None)
    if pl and 0 < pl < 15:
        score += 1
        criterios.append("P/L<15 ✓")
    else:
        criterios.append("P/L<15 ✗")
    
    # 3. P/VPA < 1.5
    pvpa = data.get("pvpa") or (cotacao / vpa if vpa else None)
    if pvpa and 0 < pvpa < 1.5:
        score += 1
        criterios.append("P/VPA<1.5 ✓")
    else:
        criterios.append("P/VPA<1.5 ✗")
    
    # 4. Margem > 0
    if margem and margem > 0:
        score += 1
        criterios.append("Margem>0 ✓")
    else:
        criterios.append("Margem>0 ✗")
    
    # 5. Div/PL < 1
    div_pl = data.get("div_pl")
    if div_pl is not None and div_pl < 1:
        score += 1
        criterios.append("Dív/PL<1 ✓")
    else:
        criterios.append("Dív/PL<1 ✗")
    
    # 6. Div/EBITDA < 3
    div_ebitda = data.get("div_ebitda")
    if div_ebitda and 0 < div_ebitda < 3:
        score += 1
        criterios.append("Dív/EBITDA<3 ✓")
    else:
        criterios.append("Dív/EBITDA<3 ✗")
    
    status = ["FORA", "OBSERVAR", "COMPRAR", "COMPRA FORTE"][min(3, max(0, (score - 2) // 2))] if score < 3 else (["FORA", "OBSERVAR", "COMPRAR", "COMPRA FORTE"][(score - 2) // 2] if score < 6 else "COMPRA FORTE")
    
    if score >= 6:
        status = "COMPRA FORTE"
    elif score >= 4:
        status = "COMPRAR"
    elif score >= 3:
        status = "OBSERVAR"
    else:
        status = "FORA"
    
    return {
        "ticker": data.get("ticker"),
        "cotacao": cotacao,
        "preco_justo": preco_justo,
        "margem_seguranca": margem,
        "score": score,
        "criterios": criterios,
        "status": status,
        "pl": pl,
        "pvpa": pvpa,
        "roe": data.get("roe"),
        "div_pl": div_pl,
        "div_ebitda": div_ebitda,
        "volume_dia": data.get("volume_dia"),
        "liquidez": "ALTA" if (data.get("volume_dia") or 0) >= 5e6 else "MEDIA" if (data.get("volume_dia") or 0) >= 500e3 else "BAIXA",
        "fonte": data.get("fonte")
    }


# ============================================================
# ANÁLISE PETER LYNCH
# ============================================================

def calc_lynch(data: dict) -> dict:
    """Calcula indicadores Peter Lynch"""
    pl = data.get("pl")
    growth = data.get("growth_rate", 5)  # % ao ano
    roe = data.get("roe", 0)
    div_pl = data.get("div_pl")
    dividend_yield = data.get("dividend_yield", 0)
    
    peg = pl / growth if pl and pl > 0 and growth and growth > 0 else None
    
    score = 0
    criterios = []
    
    # 1. PEG < 1.0
    if peg and peg < 1.0:
        score += 1
        criterios.append("PEG<1.0 ✓")
    else:
        criterios.append("PEG<1.0 ✗")
    
    # 2. P/L < Crescimento
    if pl and growth and 0 < pl < growth:
        score += 1
        criterios.append("P/L<Growth ✓")
    else:
        criterios.append("P/L<Growth ✗")
    
    # 3. Crescimento > 10%
    if growth and growth > 10:
        score += 1
        criterios.append("Growth>10% ✓")
    else:
        criterios.append("Growth>10% ✗")
    
    # 4. ROE > 15%
    if roe and roe > 0.15:
        score += 1
        criterios.append("ROE>15% ✓")
    else:
        criterios.append("ROE>15% ✗")
    
    # 5. Yield > 0
    if dividend_yield and dividend_yield > 0:
        score += 1
        criterios.append("Yield>0 ✓")
    else:
        criterios.append("Yield>0 ✗")
    
    # 6. Div/PL < 1.5
    if div_pl is not None and div_pl < 1.5:
        score += 1
        criterios.append("Dív/PL<1.5 ✓")
    else:
        criterios.append("Dív/PL<1.5 ✗")
    
    if score >= 6:
        status = "OTIMA OPORTUNIDADE"
    elif score >= 5:
        status = "BOA OPORTUNIDADE"
    elif score >= 3:
        status = "OBSERVAR"
    else:
        status = "NAO RECOMENDADO"
    
    return {
        "ticker": data.get("ticker"),
        "cotacao": data.get("cotacao"),
        "pl": pl,
        "growth_rate": growth,
        "peg_ratio": peg,
        "roe": roe,
        "dividend_yield": dividend_yield,
        "div_pl": div_pl,
        "score": score,
        "criterios": criterios,
        "status": status
    }


# ============================================================
# GERAÇÃO HTML
# ============================================================

def generate_html(all_data: list[dict]) -> str:
    """Gera HTML com ambas análises + CARTEIRA"""
    
    graham_json = json.dumps([d["graham"] for d in all_data if d.get("graham")])
    lynch_json = json.dumps([d["lynch"] for d in all_data if d.get("lynch")])
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Carregar carteira se existir
    carteira_data = {}
    try:
        with open("carteira.json", "r", encoding="utf-8") as f:
            carteira_data = json.load(f)
    except:
        carteira_data = {"carteira": [], "meta_alocacao": {}}
    
    carteira_json = json.dumps(carteira_data.get("carteira", []))
    
    # Lista de tickers BR para identificar moeda no JS
    br_tickers = [t for t in TICKERS if any(c.isdigit() for c in t)]
    br_tickers_json = json.dumps(br_tickers)
    
    # Cotação USD/BRL via AwesomeAPI (gratuita)
    usd_brl = 5.50  # fallback
    try:
        resp = requests.get("https://economia.awesomeapi.com.br/json/last/USD-BRL", timeout=5)
        if resp.status_code == 200:
            usd_brl = float(resp.json()["USDBRL"]["bid"])
            print(f"  [USD/BRL] Cotação: R$ {usd_brl:.2f}")
    except Exception as e:
        print(f"  [USD/BRL] Falha ao buscar câmbio, usando fallback R$ {usd_brl:.2f}")
    
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Graham & Peter Lynch</title>
<style>
  :root {{
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #e6edf3; --text2: #8b949e; --green: #3fb950;
    --blue: #58a6ff; --yellow: #d29922; --red: #f85149;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); padding: 20px; }}
  .header {{ text-align: center; padding: 30px 0; }}
  .header h1 {{ font-size: 2em; margin-bottom: 8px; }}
  .header p {{ color: var(--text2); }}
  .tabs {{ display: flex; gap: 10px; justify-content: center; margin: 20px 0; flex-wrap: wrap; }}
  .tab-btn {{ background: var(--card); border: 1px solid var(--border); color: var(--text);
              padding: 10px 24px; border-radius: 20px; cursor: pointer; font-weight: 600; }}
  .tab-btn.active {{ background: var(--blue); color: #000; }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}
  .summary {{ display: flex; gap: 16px; justify-content: center; margin: 20px 0 30px; flex-wrap: wrap; }}
  .summary-card {{ background: var(--card); border: 1px solid var(--border);
                   border-radius: 12px; padding: 16px 24px; text-align: center; min-width: 140px; }}
  .summary-card .num {{ font-size: 2em; font-weight: 700; }}
  .summary-card .label {{ color: var(--text2); font-size: 0.85em; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card);
           border-radius: 12px; overflow: hidden; margin-top: 10px; }}
  th {{ background: #1c2333; padding: 14px 12px; text-align: center; font-size: 0.85em;
        color: var(--text2); text-transform: uppercase; }}
  td {{ padding: 12px; text-align: center; border-top: 1px solid var(--border); }}
  tr:hover td {{ background: #1c2128; }}
  .ticker {{ font-weight: 700; color: var(--blue); }}
  .status {{ padding: 4px 12px; border-radius: 12px; font-size: 0.8em; font-weight: 600; display: inline-block; }}
  .status-compra-forte {{ background: rgba(63,185,80,0.2); color: var(--green); }}
  .status-comprar {{ background: rgba(88,166,255,0.2); color: var(--blue); }}
  .status-observar {{ background: rgba(210,153,34,0.2); color: var(--yellow); }}
  .status-fora {{ background: rgba(248,81,73,0.2); color: var(--red); }}
  .positive {{ color: var(--green); }}
  .negative {{ color: var(--red); }}
  .formula {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px;
              padding: 20px; margin-top: 30px; text-align: center; }}
  .buy-card {{ background: var(--card); border: 2px solid var(--border); border-radius: 12px;
               padding: 20px; position: relative; overflow: hidden; }}
  .buy-card.very-strong {{ border-color: var(--green); }}
  .buy-card.strong {{ border-color: var(--blue); }}
  .buy-strength {{ position: absolute; top: 0; right: 0; background: var(--green); 
                   color: white; padding: 8px 12px; font-weight: 700; font-size: 0.9em; }}
  .buy-card.strong .buy-strength {{ background: var(--blue); }}
  .buy-ticker {{ font-size: 1.5em; font-weight: 700; color: var(--blue); margin-bottom: 8px; }}
  .buy-info {{ font-size: 0.9em; margin: 6px 0; display: flex; justify-content: space-between; }}
  .buy-method {{ display: inline-block; font-size: 0.75em; padding: 4px 8px; border-radius: 8px;
                 margin-right: 4px; background: rgba(88,166,255,0.2); color: var(--blue); }}
  .low-liquidity {{ background: rgba(210,153,34,0.1) !important; border: 1px dashed var(--yellow) !important; }}
  .liquidity-badge {{ display: inline-block; font-size: 0.7em; padding: 2px 6px; border-radius: 6px;
                      background: rgba(210,153,34,0.3); color: var(--yellow); margin-left: 4px; font-weight: 600; }}
  .pro-table {{ width: 100%; border-collapse: collapse; background: var(--card);
                border-radius: 12px; overflow: hidden; margin-top: 20px; }}
  .pro-table th {{ background: #1c2333; padding: 14px 12px; text-align: left; font-size: 0.85em;
                    color: var(--text2); text-transform: uppercase; }}
  .pro-table td {{ padding: 12px; text-align: left; border-top: 1px solid var(--border); }}
  .pro-table tr:hover td {{ background: #1c2128; }}
  .pro-table .ticker {{ font-weight: 700; color: var(--blue); }}
  .margem-col {{ color: var(--green); font-weight: 600; }}
  .carteira-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px;
                    padding: 16px; margin-bottom: 12px; display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;
                    gap: 12px; align-items: center; }}
  .carteira-card.header {{ background: #1c2333; font-weight: 600; text-transform: uppercase; font-size: 0.8em; }}
  .carteira-valor {{ text-align: right; font-weight: 600; }}
  .carteira-gain {{ padding: 4px 8px; border-radius: 6px; text-align: center; font-weight: 600; }}
  .carteira-gain.positive {{ background: rgba(63,185,80,0.2); color: var(--green); }}
  .carteira-gain.negative {{ background: rgba(248,81,73,0.2); color: var(--red); }}
  .status-badge {{ display: inline-block; font-size: 0.75em; padding: 3px 6px; border-radius: 4px;
                   font-weight: 600; background: rgba(88,166,255,0.2); color: var(--blue); }}
  .total-investido {{ background: var(--card); border: 2px solid var(--border); border-radius: 12px;
                      padding: 20px; text-align: center; margin: 20px 0; }}
  .total-investido .valor {{ font-size: 1.8em; font-weight: 700; color: var(--green); margin: 8px 0; }}
  .total-investido .label {{ color: var(--text2); font-size: 0.9em; }}


</style>
</head>
<body>

<div class="header">
  <h1>📊 Dashboard Graham & Peter Lynch</h1>
  <p>Análise de investimentos com dados reais via StatusInvest + brapi</p>
  <p style="margin-top:8px; font-size:0.85em; color:var(--text2)">Atualizado: {timestamp}</p>
</div>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('carteira')">💼 CARTEIRA</button>
  <button class="tab-btn" onclick="switchTab('topbuy')">🏆 TOP BUY</button>
  <button class="tab-btn" onclick="switchTab('pro')">💎 GRAHAM PRO</button>
  <button class="tab-btn" onclick="switchTab('lynchpro')">🚀 LYNCH PRO</button>
  <button class="tab-btn" onclick="switchTab('graham')">📈 Graham</button>
  <button class="tab-btn" onclick="switchTab('lynch')">🎯 Lynch</button>
</div>

<div id="carteira" class="tab-content active">
  <div class="total-investido">
    <div class="label">Patrimonio Investido</div>
    <div class="valor" id="carteira-total">R$ 0,00</div>
    <div class="label" id="carteira-rentabilidade" style="font-size: 1.2em; margin-top: 12px;">+0,00% (R$ 0,00)</div>
  </div>
  <div id="carteira-body"></div>
  <div style="margin-top: 30px; padding: 20px; background: var(--card); border: 1px solid var(--border); border-radius: 12px;">
    <h3 style="margin-bottom: 12px;">Cenarios de Rentabilidade (12 meses)</h3>
    <div id="carteira-cenarios"></div>
  </div>
</div>

<div id="pro" class="tab-content">
  <div style="background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
    <h3 style="margin-bottom: 8px;">💎 Graham PRO — Valor com Segurança</h3>
    <p style="color: var(--text2); font-size: 0.9em;">Score >= 4 | Ranking por força de recomendação (Score + Margem + P/L + Dív/PL)</p>
    <div style="display: flex; gap: 16px; margin-top: 12px; flex-wrap: wrap;">
      <span style="font-size: 0.8em; padding: 4px 10px; border-radius: 8px; background: rgba(63,185,80,0.2); color: var(--green);">COMPRA FORTE = Score 6 + Margem > 0%</span>
      <span style="font-size: 0.8em; padding: 4px 10px; border-radius: 8px; background: rgba(88,166,255,0.2); color: var(--blue);">COMPRAR = Score >= 5</span>
      <span style="font-size: 0.8em; padding: 4px 10px; border-radius: 8px; background: rgba(210,153,34,0.2); color: var(--yellow);">OBSERVAR = Score 4</span>
    </div>
  </div>
  <div id="pro-body"></div>
</div>

<div id="topbuy" class="tab-content">
  <div style="background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
    <h3 style="margin-bottom: 8px;">🏆 Recomendações de Compra</h3>
    <p style="color: var(--text2); font-size: 0.9em;">Ranking baseado na validação cruzada Graham + Lynch. Ações aprovadas por ambos os métodos recebem destaque.</p>
    <div style="display: flex; gap: 16px; margin-top: 12px; flex-wrap: wrap;">
      <span style="font-size: 0.8em; color: var(--green);">🟢 Dupla Validação (Graham + Lynch)</span>
      <span style="font-size: 0.8em; color: var(--blue);">🔵 Apenas Graham</span>
      <span style="font-size: 0.8em; color: var(--yellow);">🟡 Apenas Lynch</span>
    </div>
  </div>
  <div id="topbuy-dual" style="margin-bottom: 24px;"></div>
  <div id="topbuy-single"></div>
</div>

<div id="lynchpro" class="tab-content">
  <div style="background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
    <h3 style="margin-bottom: 8px;">🚀 Lynch PRO — Oportunidades de Crescimento</h3>
    <p style="color: var(--text2); font-size: 0.9em;">Score >= 4 | Ordenadas por forca de recomendacao (PEG + Growth + ROE)</p>
    <div style="display: flex; gap: 16px; margin-top: 12px; flex-wrap: wrap;">
      <span style="font-size: 0.8em; padding: 4px 10px; border-radius: 8px; background: rgba(63,185,80,0.2); color: var(--green);">COMPRA FORTE = PEG &lt; 0.5 + Score 6</span>
      <span style="font-size: 0.8em; padding: 4px 10px; border-radius: 8px; background: rgba(88,166,255,0.2); color: var(--blue);">COMPRAR = PEG &lt; 1.0 + Score >= 5</span>
      <span style="font-size: 0.8em; padding: 4px 10px; border-radius: 8px; background: rgba(210,153,34,0.2); color: var(--yellow);">OBSERVAR = Score 4</span>
    </div>
  </div>
  <div id="lynchpro-body"></div>
</div>

<div id="graham" class="tab-content">
  <div class="summary" id="graham-summary"></div>
  <table><thead><tr><th>Ticker</th><th>Cotação</th><th>P.Justo</th><th>Margem %</th><th>P/L</th><th>ROE</th><th>Score</th><th>Status</th></tr></thead>
  <tbody id="graham-body"></tbody></table>
  <div class="formula" style="margin-top: 30px;">
    <p style="font-weight:600">Fórmula de Graham</p>
    <code>Preco Justo = √(22.5 × LPA × VPA)</code>
  </div>
</div>

<div id="lynch" class="tab-content">
  <div class="summary" id="lynch-summary"></div>
  <table><thead><tr><th>Ticker</th><th>Cotação</th><th>P/L</th><th>Growth %</th><th>PEG</th><th>ROE</th><th>Score</th><th>Status</th></tr></thead>
  <tbody id="lynch-body"></tbody></table>
  <div class="formula" style="margin-top: 30px;">
    <p style="font-weight:600">Método Peter Lynch</p>
    <code>PEG = P/L ÷ Taxa Crescimento (%)</code>
  </div>
</div>

<script>
const GRAHAM_DATA = {graham_json};
const LYNCH_DATA = {lynch_json};
const CARTEIRA_DATA = {carteira_json};
const USD_BRL = {usd_brl:.4f};

function switchTab(tab) {{
  document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
  document.getElementById(tab).classList.add('active');
  event.target.classList.add('active');
}}

function fmt(v, dec=2) {{
  if (v == null) return 'N/A';
  return parseFloat(v).toLocaleString('pt-BR', {{minimumFractionDigits: dec, maximumFractionDigits: dec}});
}}

function fmtPct(v) {{
  if (v == null) return 'N/A';
  return (v * 100).toFixed(1) + '%';
}}

const BR_TICKERS = {br_tickers_json};
const isUS = (ticker) => !BR_TICKERS.includes(ticker);
const moeda = (ticker) => isUS(ticker) ? 'US$' : 'R$';

function renderCarteira() {{
  if (!CARTEIRA_DATA || CARTEIRA_DATA.length === 0) {{
    document.getElementById('carteira-body').innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text2);">Nenhuma posicao registrada. Adicione suas compras em carteira.json</div>';
    return;
  }}
  
  let totalBRL_inv = 0, totalBRL_atual = 0;
  let totalUSD_inv = 0, totalUSD_atual = 0;
  
  // Calcular totais separados por moeda
  CARTEIRA_DATA.forEach(pos => {{
    const stock = GRAHAM_DATA.find(s => s.ticker === pos.ticker) || 
                  LYNCH_DATA.find(s => s.ticker === pos.ticker);
    
    if (stock) {{
      const valorInvestido = pos.quantidade * pos.preco_medio;
      const valorAtual = pos.quantidade * stock.cotacao;
      
      if (isUS(pos.ticker)) {{
        totalUSD_inv += valorInvestido;
        totalUSD_atual += valorAtual;
      }} else {{
        totalBRL_inv += valorInvestido;
        totalBRL_atual += valorAtual;
      }}
    }}
  }});
  
  const totalBRL_ganho = totalBRL_atual - totalBRL_inv;
  const totalBRL_pct = totalBRL_inv > 0 ? (totalBRL_ganho / totalBRL_inv) * 100 : 0;
  const totalUSD_ganho = totalUSD_atual - totalUSD_inv;
  const totalUSD_pct = totalUSD_inv > 0 ? (totalUSD_ganho / totalUSD_inv) * 100 : 0;
  
  // Patrimônio total convertido em BRL
  const totalPatrimonioBRL = totalBRL_atual + (totalUSD_atual * USD_BRL);
  const totalInvestidoBRL = totalBRL_inv + (totalUSD_inv * USD_BRL);
  const totalGanhoBRL = totalPatrimonioBRL - totalInvestidoBRL;
  const totalPctBRL = totalInvestidoBRL > 0 ? (totalGanhoBRL / totalInvestidoBRL) * 100 : 0;
  
  // Atualizar totalizador
  let totalStr = 'R$ ' + fmt(totalBRL_atual);
  if (totalUSD_atual > 0) totalStr += '  |  US$ ' + fmt(totalUSD_atual);
  document.getElementById('carteira-total').innerHTML = totalStr + 
    `<div style="font-size: 0.5em; color: var(--text2); margin-top: 6px;">Patrim\\u00f4nio Total: R$ ${{fmt(totalPatrimonioBRL)}} <span style="font-size: 0.85em;">(USD/BRL ${{fmt(USD_BRL, 2)}})</span></div>`;
  
  const brlLabel = totalBRL_ganho >= 0 ? '+' : '';
  const usdLabel = totalUSD_ganho >= 0 ? '+' : '';
  const totalLabel = totalGanhoBRL >= 0 ? '+' : '';
  let rentHtml = `<span style="color: ${{totalBRL_ganho >= 0 ? 'var(--green)' : 'var(--red)'}}">&#127463;&#127479; ${{brlLabel}}${{totalBRL_pct.toFixed(2)}}% (R$ ${{fmt(totalBRL_ganho)}})</span>`;
  if (totalUSD_inv > 0) {{
    rentHtml += `<span style="margin-left: 20px; color: ${{totalUSD_ganho >= 0 ? 'var(--green)' : 'var(--red)'}}">&#127482;&#127480; ${{usdLabel}}${{totalUSD_pct.toFixed(2)}}% (US$ ${{fmt(totalUSD_ganho)}})</span>`;
  }}
  rentHtml += `<div style="margin-top: 8px; color: ${{totalGanhoBRL >= 0 ? 'var(--green)' : 'var(--red)'}}; font-weight: 700;">Total em R$: ${{totalLabel}}${{totalPctBRL.toFixed(2)}}% (R$ ${{fmt(totalGanhoBRL)}})</div>`;
  document.getElementById('carteira-rentabilidade').innerHTML = rentHtml;
  
  // Renderizar posicoes
  const header = `
    <div class="carteira-card header" style="grid-template-columns: 1fr 1fr 1fr 1fr 1fr;">
      <div>Ticker</div>
      <div>Valor Investido</div>
      <div>Valor Atual</div>
      <div>Ganho / Perda</div>
      <div style="text-align: center;">Sinal</div>
    </div>
  `;
  
  const posicoes = CARTEIRA_DATA.map(pos => {{
    const stock = GRAHAM_DATA.find(s => s.ticker === pos.ticker) || 
                  LYNCH_DATA.find(s => s.ticker === pos.ticker);
    
    if (!stock) return '';
    
    const valorInvestido = pos.quantidade * pos.preco_medio;
    const valorAtual = pos.quantidade * stock.cotacao;
    const ganho = valorAtual - valorInvestido;
    const pct = (ganho / valorInvestido) * 100;
    
    const graham = GRAHAM_DATA.find(s => s.ticker === pos.ticker);
    const lynch = LYNCH_DATA.find(s => s.ticker === pos.ticker);
    
    // Sinal de ação inteligente
    let sinal = '';
    let sinalClass = '';
    let sinalMotivo = '';
    
    const gScore = graham ? graham.score : 0;
    const lScore = lynch ? lynch.score : 0;
    const margem = graham ? (graham.margem_seguranca || 0) : 0;
    const peg = lynch ? lynch.peg_ratio : null;
    
    // REFORÇAR: score alto + preço ainda bom
    if ((gScore >= 5 && margem > 0) || (lScore >= 5 && peg && peg < 0.8)) {{
      sinal = '🔵 REFORÇAR';
      sinalClass = 'color: var(--blue)';
      const motivos = [];
      if (gScore >= 5) motivos.push('Graham ' + gScore + '/6');
      if (lScore >= 5) motivos.push('Lynch ' + lScore + '/6');
      if (margem > 0) motivos.push('Margem +' + (margem * 100).toFixed(0) + '%');
      if (peg && peg < 1) motivos.push('PEG ' + peg.toFixed(2));
      sinalMotivo = motivos.join(' | ');
    }}
    // MANTER: score médio ou bom sem urgência
    else if (gScore >= 4 || lScore >= 4) {{
      sinal = '🟢 MANTER';
      sinalClass = 'color: var(--green)';
      const motivos = [];
      if (gScore >= 4) motivos.push('Graham ' + gScore + '/6');
      if (lScore >= 4) motivos.push('Lynch ' + lScore + '/6');
      sinalMotivo = motivos.join(' | ');
    }}
    // AVALIAR TROCA: score baixo, ação cara ou sem fundamento
    else if (gScore <= 3 && lScore <= 3) {{
      sinal = '🟡 AVALIAR TROCA';
      sinalClass = 'color: var(--yellow)';
      const motivos = [];
      if (gScore <= 3) motivos.push('Graham ' + gScore + '/6');
      if (lScore <= 3) motivos.push('Lynch ' + lScore + '/6');
      if (margem < -0.3) motivos.push('Cara: margem ' + (margem * 100).toFixed(0) + '%');
      sinalMotivo = motivos.join(' | ');
    }}
    // REALIZAR LUCRO: subiu muito + score caindo
    else {{
      sinal = '🟢 MANTER';
      sinalClass = 'color: var(--green)';
      sinalMotivo = 'Graham ' + gScore + '/6 | Lynch ' + lScore + '/6';
    }}
    
    // Override: se lucro > 30% e score ruim, sugerir realizar
    if (pct > 30 && gScore <= 3 && lScore <= 3) {{
      sinal = '🔴 REALIZAR LUCRO';
      sinalClass = 'color: var(--red)';
      sinalMotivo = 'Lucro +' + pct.toFixed(0) + '% | Scores baixos — trocar por ação melhor';
    }}
    
    return `
      <div class="carteira-card" style="grid-template-columns: 1fr 1fr 1fr 1fr 1fr;">
        <div>
          <strong style="color: var(--blue); font-size: 1.1em;">${{pos.ticker}}</strong> ${{isUS(pos.ticker) ? '🇺🇸' : '🇧🇷'}}<br>
          <span style="color: var(--text2); font-size: 0.85em;">${{pos.quantidade}} un</span>
        </div>
        <div class="carteira-valor">
          ${{moeda(pos.ticker)}} ${{fmt(valorInvestido)}}<br>
          <span style="color: var(--text2); font-size: 0.85em;">@${{moeda(pos.ticker)}} ${{fmt(pos.preco_medio)}}</span>
        </div>
        <div class="carteira-valor">
          ${{moeda(pos.ticker)}} ${{fmt(valorAtual)}}<br>
          <span style="color: var(--text2); font-size: 0.85em;">@${{moeda(pos.ticker)}} ${{fmt(stock.cotacao)}}</span>
        </div>
        <div class="carteira-gain ${{ganho >= 0 ? 'positive' : 'negative'}}">
          ${{(ganho >= 0 ? '+' : '')}}${{pct.toFixed(2)}}%<br>
          ${{moeda(pos.ticker)}} ${{fmt(ganho)}}
        </div>
        <div style="text-align: center;">
          <div style="font-weight: 700; font-size: 0.9em; ${{sinalClass}}">${{sinal}}</div>
          <div style="color: var(--text2); font-size: 0.72em; margin-top: 4px;">${{sinalMotivo}}</div>
        </div>
      </div>
    `;
  }}).join('');
  
  document.getElementById('carteira-body').innerHTML = header + posicoes;
  
  // Cenarios com patrimônio total em BRL
  const cenarios_html = `
    <div style="text-align: center; margin-bottom: 16px; padding: 12px; background: #0d1117; border-radius: 8px; border: 1px solid var(--border);">
      <div style="font-size: 0.85em; color: var(--text2);">Patrim\\u00f4nio Total (USD/BRL ${{fmt(USD_BRL, 2)}})</div>
      <div style="font-size: 1.6em; font-weight: 700; color: var(--blue); margin-top: 4px;">R$ ${{fmt(totalPatrimonioBRL)}}</div>
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;">
      <div style="background: #0d1117; padding: 12px; border-radius: 8px; border-left: 3px solid var(--red);">
        <div style="font-weight: 600; margin-bottom: 8px;">Pessimista (-10%)</div>
        <div style="color: var(--red); font-size: 1.2em; font-weight: 700;">R$ ${{fmt(totalPatrimonioBRL * 0.9)}}</div>
        <div style="color: var(--text2); font-size: 0.85em; margin-top: 4px;">-R$ ${{fmt(totalPatrimonioBRL * 0.1)}}</div>
      </div>
      <div style="background: #0d1117; padding: 12px; border-radius: 8px; border-left: 3px solid var(--yellow);">
        <div style="font-weight: 600; margin-bottom: 8px;">Base (0%)</div>
        <div style="color: var(--text2); font-size: 1.2em; font-weight: 700;">R$ ${{fmt(totalPatrimonioBRL)}}</div>
        <div style="color: var(--text2); font-size: 0.85em; margin-top: 4px;">Pre\\u00e7o atual</div>
      </div>
      <div style="background: #0d1117; padding: 12px; border-radius: 8px; border-left: 3px solid var(--green);">
        <div style="font-weight: 600; margin-bottom: 8px;">Otimista (+25%)</div>
        <div style="color: var(--green); font-size: 1.2em; font-weight: 700;">R$ ${{fmt(totalPatrimonioBRL * 1.25)}}</div>
        <div style="color: var(--text2); font-size: 0.85em; margin-top: 4px;">+R$ ${{fmt(totalPatrimonioBRL * 0.25)}}</div>
      </div>
    </div>
    ${{totalUSD_atual > 0 ? `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px;">
      <div style="background: #0d1117; padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="font-weight: 600; margin-bottom: 4px;">&#127463;&#127479; Brasil</div>
        <div style="color: var(--text); font-size: 1.1em; font-weight: 700;">R$ ${{fmt(totalBRL_atual)}}</div>
        <div style="color: var(--text2); font-size: 0.8em;">${{totalBRL_pct >= 0 ? '+' : ''}}${{totalBRL_pct.toFixed(2)}}%</div>
      </div>
      <div style="background: #0d1117; padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
        <div style="font-weight: 600; margin-bottom: 4px;">&#127482;&#127480; EUA</div>
        <div style="color: var(--text); font-size: 1.1em; font-weight: 700;">US$ ${{fmt(totalUSD_atual)}} <span style="font-size: 0.75em; color: var(--text2);">(R$ ${{fmt(totalUSD_atual * USD_BRL)}})</span></div>
        <div style="color: var(--text2); font-size: 0.8em;">${{totalUSD_pct >= 0 ? '+' : ''}}${{totalUSD_pct.toFixed(2)}}%</div>
      </div>
    </div>
    ` : ''}}
  `;
  
  document.getElementById('carteira-cenarios').innerHTML = cenarios_html;
}}

function renderGraham() {{
  const counts = {{}};
  GRAHAM_DATA.forEach(s => {{
    counts[s.status] = (counts[s.status] || 0) + 1;
  }});
  
  document.getElementById('graham-summary').innerHTML = Object.entries(counts).map(([k, v]) => `
    <div class="summary-card">
      <div class="num">${{v}}</div>
      <div class="label">${{k}}</div>
    </div>`).join('');
  
  document.getElementById('graham-body').innerHTML = GRAHAM_DATA.sort((a, b) => b.score - a.score).map(s => `
    <tr>
      <td class="ticker">${{s.ticker}}</td>
      <td>${{moeda(s.ticker)}} ${{fmt(s.cotacao)}}</td>
      <td>${{s.preco_justo ? moeda(s.ticker) + ' ' + fmt(s.preco_justo) : 'N/A'}}</td>
      <td class="${{s.margem_seguranca > 0 ? 'positive' : 'negative'}}">${{fmtPct(s.margem_seguranca)}}</td>
      <td>${{fmt(s.pl, 1)}}</td>
      <td>${{fmtPct(s.roe)}}</td>
      <td>${{'★'.repeat(s.score) + '☆'.repeat(6-s.score)}}</td>
      <td><span class="status status-${{s.status.toLowerCase().replace(/ /g, '-')}}">${{s.status}}</span></td>
    </tr>`).join('');
}}

function renderLynch() {{
  const counts = {{}};
  LYNCH_DATA.forEach(s => {{
    counts[s.status] = (counts[s.status] || 0) + 1;
  }});
  
  document.getElementById('lynch-summary').innerHTML = Object.entries(counts).map(([k, v]) => `
    <div class="summary-card">
      <div class="num">${{v}}</div>
      <div class="label">${{k}}</div>
    </div>`).join('');
  
  document.getElementById('lynch-body').innerHTML = LYNCH_DATA.sort((a, b) => b.score - a.score).map(s => `
    <tr>
      <td class="ticker">${{s.ticker}}</td>
      <td>${{moeda(s.ticker)}} ${{fmt(s.cotacao)}}</td>
      <td>${{fmt(s.pl, 1)}}</td>
      <td>${{fmt(s.growth_rate, 1)}}%</td>
      <td class="${{s.peg_ratio && s.peg_ratio < 1 ? 'positive' : 'negative'}}">${{s.peg_ratio ? fmt(s.peg_ratio, 2) : 'N/A'}}</td>
      <td>${{fmtPct(s.roe)}}</td>
      <td>${{'★'.repeat(s.score) + '☆'.repeat(6-s.score)}}</td>
      <td><span class="status status-${{s.status.toLowerCase().replace(/ /g, '-')}}">${{s.status}}</span></td>
    </tr>`).join('');
}}

function getStockBuyStrength(ticker) {{
  const graham = GRAHAM_DATA.find(s => s.ticker === ticker);
  const lynch = LYNCH_DATA.find(s => s.ticker === ticker);
  
  const gOk = graham && graham.score >= 4;
  const lOk = lynch && lynch.score >= 3;
  
  let strength = 0;
  let reasons = [];
  
  if (gOk) {{
    strength += graham.score * 1.5;
    if (graham.margem_seguranca > 0.4) {{ strength += 3; reasons.push('Margem > 40%'); }}
    else if (graham.margem_seguranca > 0.2) {{ strength += 1.5; reasons.push('Margem > 20%'); }}
    if (graham.pl && graham.pl < 8) {{ strength += 1; reasons.push('P/L baixo (' + graham.pl.toFixed(1) + ')'); }}
  }}
  
  if (lOk) {{
    strength += lynch.score * 1.2;
    if (lynch.peg_ratio && lynch.peg_ratio < 0.7) {{ strength += 3; reasons.push('PEG excelente (' + lynch.peg_ratio.toFixed(2) + ')'); }}
    else if (lynch.peg_ratio && lynch.peg_ratio < 1.0) {{ strength += 1.5; reasons.push('PEG bom (' + lynch.peg_ratio.toFixed(2) + ')'); }}
    if (lynch.growth_rate > 15) {{ strength += 1; reasons.push('Crescimento ' + lynch.growth_rate.toFixed(0) + '%'); }}
  }}
  
  // Bonus dupla validação
  if (gOk && lOk) {{
    strength += 4;
    reasons.unshift('Aprovada por Graham E Lynch');
  }}
  
  const tipo = (gOk && lOk) ? 'dual' : gOk ? 'graham' : lOk ? 'lynch' : 'none';
  
  return {{ strength, reasons, graham, lynch, tipo, gOk, lOk }};
}}

function renderTopBuy() {{
  const allTickers = [...new Set([
    ...GRAHAM_DATA.map(s => s.ticker),
    ...LYNCH_DATA.map(s => s.ticker)
  ])];
  
  const ranked = allTickers.map(ticker => {{
    const data = getStockBuyStrength(ticker);
    if (data.tipo === 'none') return null;
    const stock = GRAHAM_DATA.find(s => s.ticker === ticker) || LYNCH_DATA.find(s => s.ticker === ticker);
    return {{ ticker, cotacao: stock.cotacao, ...data }};
  }}).filter(Boolean).sort((a, b) => b.strength - a.strength);
  
  const duals = ranked.filter(s => s.tipo === 'dual');
  const singles = ranked.filter(s => s.tipo !== 'dual');
  
  // Cards para dupla validação
  const dualHtml = duals.length > 0 ? `
    <h3 style="margin-bottom: 12px; color: var(--green);">🟢 Dupla Validação — Melhor Recomendação</h3>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px;">
    ${{duals.map((s, i) => `
      <div style="background: var(--card); border: 2px solid var(--green); border-radius: 12px; padding: 20px; position: relative;">
        <div style="position: absolute; top: 0; right: 0; background: var(--green); color: #000;
                    padding: 6px 14px; border-radius: 0 10px 0 12px; font-weight: 700; font-size: 0.85em;">
          #${{i + 1}} — ${{s.strength.toFixed(1)}} pts
        </div>
        <div style="font-size: 1.4em; font-weight: 700; color: var(--blue); margin-bottom: 4px;">${{s.ticker}}</div>
        <div style="color: var(--text2); font-size: 0.85em; margin-bottom: 12px;">Cotacao: ${{moeda(s.ticker)}} ${{fmt(s.cotacao)}}</div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
          <div style="background: #0d1117; padding: 8px; border-radius: 8px; text-align: center;">
            <div style="font-size: 0.75em; color: var(--text2);">Graham</div>
            <div style="font-weight: 700;">${{'★'.repeat(s.graham.score)}}</div>
            <div style="font-size: 0.8em; color: var(--green);">Margem ${{(s.graham.margem_seguranca * 100).toFixed(0)}}%</div>
          </div>
          <div style="background: #0d1117; padding: 8px; border-radius: 8px; text-align: center;">
            <div style="font-size: 0.75em; color: var(--text2);">Lynch</div>
            <div style="font-weight: 700;">${{'★'.repeat(s.lynch.score)}}</div>
            <div style="font-size: 0.8em; color: ${{s.lynch.peg_ratio && s.lynch.peg_ratio < 1 ? 'var(--green)' : 'var(--text2)'}};">PEG ${{s.lynch.peg_ratio ? s.lynch.peg_ratio.toFixed(2) : 'N/A'}}</div>
          </div>
        </div>
        
        <div style="font-size: 0.85em;">
          ${{s.reasons.map(r => `<div style="color: var(--text2); padding: 2px 0;">✓ ${{r}}</div>`).join('')}}
        </div>
      </div>
    `).join('')}}
    </div>
  ` : '<p style="color: var(--text2); padding: 20px;">Nenhuma ação com dupla validação no momento.</p>';
  
  document.getElementById('topbuy-dual').innerHTML = dualHtml;
  
  // Tabela para validação simples
  const singleHtml = singles.length > 0 ? `
    <h3 style="margin-bottom: 12px; margin-top: 8px;">Validação Simples</h3>
    <table class="pro-table">
      <thead><tr>
        <th>Ticker</th><th>Cotacao</th><th>Metodo</th><th>Graham</th><th>Lynch</th><th>Pontuacao</th><th>Motivos</th>
      </tr></thead>
      <tbody>
      ${{singles.slice(0, 15).map(s => `
        <tr>
          <td class="ticker">${{s.ticker}}</td>
          <td>${{moeda(s.ticker)}} ${{fmt(s.cotacao)}}</td>
          <td>
            ${{s.tipo === 'graham'
              ? '<span style="background: rgba(88,166,255,0.2); color: var(--blue); padding: 3px 8px; border-radius: 6px; font-size: 0.8em;">Graham</span>'
              : '<span style="background: rgba(210,153,34,0.2); color: var(--yellow); padding: 3px 8px; border-radius: 6px; font-size: 0.8em;">Lynch</span>'
            }}
          </td>
          <td>${{s.graham ? '★'.repeat(s.graham.score) + '☆'.repeat(6 - s.graham.score) : '—'}}</td>
          <td>${{s.lynch ? '★'.repeat(s.lynch.score) + '☆'.repeat(6 - s.lynch.score) : '—'}}</td>
          <td style="font-weight: 700;">${{s.strength.toFixed(1)}}</td>
          <td style="font-size: 0.8em; color: var(--text2);">${{s.reasons.slice(0, 2).join(', ')}}</td>
        </tr>
      `).join('')}}
      </tbody>
    </table>
  ` : '';
  
  document.getElementById('topbuy-single').innerHTML = singleHtml;
}}

function renderPro() {{
  const MIN_LIQUIDITY = 50000;
  
  const filtered = GRAHAM_DATA
    .filter(s => s.score >= 4)
    .map(s => {{
      let forca = 0;
      let nivel = '';
      let nivelClass = '';
      
      // Score é o fator principal (6/6 = empresa excelente)
      forca += s.score * 1.5;
      
      // Margem de segurança (bonus, não fator principal)
      const margem = s.margem_seguranca || 0;
      if (margem > 0.5) forca += 3;
      else if (margem > 0.3) forca += 2.5;
      else if (margem > 0.1) forca += 2;
      else if (margem > 0) forca += 1;
      
      // P/L baixo = empresa barata
      if (s.pl && s.pl > 0 && s.pl < 5) forca += 2;
      else if (s.pl && s.pl > 0 && s.pl < 8) forca += 1.5;
      else if (s.pl && s.pl > 0 && s.pl < 12) forca += 1;
      
      // Dív/PL baixa = empresa saudável
      if (s.div_pl !== null && s.div_pl >= 0 && s.div_pl < 0.3) forca += 1.5;
      else if (s.div_pl !== null && s.div_pl >= 0 && s.div_pl < 0.5) forca += 1;
      else if (s.div_pl !== null && s.div_pl >= 0 && s.div_pl < 1) forca += 0.5;
      
      // ROE alto = empresa eficiente
      if (s.roe && s.roe > 0.25) forca += 1.5;
      else if (s.roe && s.roe > 0.15) forca += 1;
      
      // Liquidez (penalidade se baixa)
      const lowLiq = (s.volume_dia || 0) < MIN_LIQUIDITY;
      if (lowLiq) forca -= 1;
      
      // Nivel de recomendação
      if (s.score >= 6 && margem > 0) {{
        nivel = 'COMPRA FORTE';
        nivelClass = 'status-compra-forte';
      }} else if (s.score >= 6) {{
        nivel = 'COMPRAR';
        nivelClass = 'status-comprar';
      }} else if (s.score >= 5) {{
        nivel = 'COMPRAR';
        nivelClass = 'status-comprar';
      }} else {{
        nivel = 'OBSERVAR';
        nivelClass = 'status-observar';
      }}
      
      // Verificar Lynch
      const lynch = LYNCH_DATA.find(l => l.ticker === s.ticker);
      const dualOk = lynch && lynch.score >= 4;
      
      return {{ ...s, forca, nivel, nivelClass, lowLiq, dualOk, lynch }};
    }})
    .sort((a, b) => b.forca - a.forca);
  
  if (filtered.length === 0) {{
    document.getElementById('pro-body').innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text2);">Nenhuma acao com score >= 4 no metodo Graham</div>';
    return;
  }}
  
  document.getElementById('pro-body').innerHTML = filtered.map((s, i) => `
    <div style="background: var(--card); border: 2px solid ${{s.nivel === 'COMPRA FORTE' ? 'var(--green)' : s.nivel === 'COMPRAR' ? 'var(--blue)' : 'var(--border)'}}; border-radius: 12px; padding: 16px 20px; margin-bottom: 10px; ${{s.lowLiq ? 'opacity: 0.7; border-style: dashed;' : ''}}">
      
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <span style="font-size: 1.4em; font-weight: 700; color: var(--text2); min-width: 40px;">#${{i + 1}}</span>
        <span style="font-size: 1.2em; font-weight: 700; color: var(--blue);">
          ${{s.ticker}}
          ${{s.dualOk ? '<span style="font-size: 0.6em; background: rgba(63,185,80,0.2); color: var(--green); padding: 2px 6px; border-radius: 4px; margin-left: 4px; vertical-align: middle;">+Lynch</span>' : ''}}
          ${{s.lowLiq ? '<span class="liquidity-badge">⚠️ Liq.</span>' : ''}}
        </span>
        <span class="status ${{s.nivelClass}}">${{s.nivel}}</span>
        <span style="color: var(--text2); font-size: 0.85em;">${{moeda(s.ticker)}} ${{fmt(s.cotacao)}} ${{s.preco_justo ? '→ Justo ' + moeda(s.ticker) + ' ' + fmt(s.preco_justo) : ''}}</span>
        <span style="margin-left: auto; font-size: 0.8em; color: var(--text2);">${{s.forca.toFixed(1)}} pts</span>
      </div>
      
      <div style="display: flex; gap: 12px; margin-top: 10px; flex-wrap: wrap; align-items: center;">
        <span style="background: #0d1117; padding: 8px 16px; border-radius: 8px; font-size: 1.05em;">Margem <strong style="color: ${{(s.margem_seguranca || 0) > 0 ? 'var(--green)' : 'var(--red)'}}; font-size: 1.2em;">${{s.margem_seguranca ? (s.margem_seguranca * 100).toFixed(0) + '%' : 'N/A'}}</strong></span>
        <span style="background: #0d1117; padding: 8px 16px; border-radius: 8px; font-size: 1.05em;">P/L <strong style="color: ${{s.pl && s.pl < 10 ? 'var(--green)' : 'var(--text)'}}; font-size: 1.2em;">${{s.pl ? s.pl.toFixed(1) : 'N/A'}}</strong></span>
        <span style="background: #0d1117; padding: 6px 12px; border-radius: 8px; font-size: 0.85em;">Dív/PL <strong style="color: ${{s.div_pl !== null && s.div_pl < 0.5 ? 'var(--green)' : 'var(--text)'}}">${{s.div_pl !== null ? s.div_pl.toFixed(2) : 'N/A'}}</strong></span>
        <span style="background: #0d1117; padding: 6px 12px; border-radius: 8px; font-size: 0.85em;">ROE <strong style="color: ${{s.roe && s.roe > 0.15 ? 'var(--green)' : 'var(--text)'}}">${{s.roe ? (s.roe * 100).toFixed(0) + '%' : 'N/A'}}</strong></span>
        <span style="background: #0d1117; padding: 6px 12px; border-radius: 8px; font-size: 0.85em;">${{'★'.repeat(s.score) + '☆'.repeat(6-s.score)}}</span>
        ${{s.dualOk ? '<span style="font-size: 0.75em; color: var(--green);">Lynch ' + '★'.repeat(s.lynch.score) + '</span>' : ''}}
      </div>
    </div>
  `).join('');
}}

function renderLynchPro() {{
  const MIN_LIQUIDITY = 50000;
  
  const filtered = LYNCH_DATA
    .filter(s => s.score >= 4)
    .map(s => {{
      let forca = 0;
      let nivel = '';
      let nivelClass = '';
      
      // PEG ratio (quanto menor, melhor)
      if (s.peg_ratio && s.peg_ratio < 0.3) forca += 5;
      else if (s.peg_ratio && s.peg_ratio < 0.5) forca += 4;
      else if (s.peg_ratio && s.peg_ratio < 0.7) forca += 3;
      else if (s.peg_ratio && s.peg_ratio < 1.0) forca += 2;
      else forca += 0.5;
      
      // Growth rate
      if (s.growth_rate > 50) forca += 3;
      else if (s.growth_rate > 20) forca += 2;
      else if (s.growth_rate > 10) forca += 1;
      
      // ROE
      if (s.roe > 0.30) forca += 2;
      else if (s.roe > 0.15) forca += 1;
      
      // Score bonus
      forca += s.score * 0.5;
      
      // Determinar nivel de recomendacao
      if (s.score >= 6 && s.peg_ratio && s.peg_ratio < 0.5) {{
        nivel = 'COMPRA FORTE';
        nivelClass = 'status-compra-forte';
      }} else if (s.score >= 5 && s.peg_ratio && s.peg_ratio < 1.0) {{
        nivel = 'COMPRAR';
        nivelClass = 'status-comprar';
      }} else if (s.score >= 5) {{
        nivel = 'COMPRA MODERADA';
        nivelClass = 'status-comprar';
      }} else {{
        nivel = 'OBSERVAR';
        nivelClass = 'status-observar';
      }}
      
      // Verificar se tambem passa em Graham
      const graham = GRAHAM_DATA.find(g => g.ticker === s.ticker);
      const dualOk = graham && graham.score >= 4;
      
      // Liquidez
      const lowLiq = (s.volume_dia || 0) < MIN_LIQUIDITY;
      if (lowLiq) forca -= 1;
      
      return {{ ...s, forca, nivel, nivelClass, dualOk, graham, lowLiq }};
    }})
    .sort((a, b) => b.forca - a.forca);
  
  if (filtered.length === 0) {{
    document.getElementById('lynchpro-body').innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text2);">Nenhuma acao com score >= 4 no metodo Lynch</div>';
    return;
  }}
  
  document.getElementById('lynchpro-body').innerHTML = filtered.map((s, i) => `
    <div style="background: var(--card); border: 2px solid ${{s.nivel === 'COMPRA FORTE' ? 'var(--green)' : s.nivel === 'COMPRAR' || s.nivel === 'COMPRA MODERADA' ? 'var(--blue)' : 'var(--border)'}}; border-radius: 12px; padding: 16px 20px; margin-bottom: 10px;">
      
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <span style="font-size: 1.4em; font-weight: 700; color: var(--text2); min-width: 40px;">#${{i + 1}}</span>
        <span style="font-size: 1.2em; font-weight: 700; color: var(--blue);">
          ${{s.ticker}}
          ${{s.dualOk ? '<span style="font-size: 0.6em; background: rgba(63,185,80,0.2); color: var(--green); padding: 2px 6px; border-radius: 4px; margin-left: 4px; vertical-align: middle;">+Graham</span>' : ''}}
          ${{s.lowLiq ? '<span class="liquidity-badge">⚠️ Liq.</span>' : ''}}
        </span>
        <span class="status ${{s.nivelClass}}">${{s.nivel}}</span>
        <span style="color: var(--text2); font-size: 0.85em;">${{moeda(s.ticker)}} ${{fmt(s.cotacao)}}</span>
        <span style="margin-left: auto; font-size: 0.8em; color: var(--text2);">${{s.forca.toFixed(1)}} pts</span>
      </div>
      
      <div style="display: flex; gap: 12px; margin-top: 10px; flex-wrap: wrap; align-items: center;">
        <span style="background: #0d1117; padding: 8px 16px; border-radius: 8px; font-size: 1.05em;">PEG <strong style="color: ${{s.peg_ratio && s.peg_ratio < 1 ? 'var(--green)' : 'var(--red)'}}; font-size: 1.2em;">${{s.peg_ratio ? s.peg_ratio.toFixed(2) : 'N/A'}}</strong></span>
        <span style="background: #0d1117; padding: 8px 16px; border-radius: 8px; font-size: 1.05em;">Growth <strong style="color: ${{s.growth_rate > 10 ? 'var(--green)' : 'var(--text)'}}; font-size: 1.2em;">${{s.growth_rate ? s.growth_rate.toFixed(1) + '%' : 'N/A'}}</strong></span>
        <span style="background: #0d1117; padding: 6px 12px; border-radius: 8px; font-size: 0.85em;">ROE <strong style="color: ${{s.roe && s.roe > 0.15 ? 'var(--green)' : 'var(--text)'}}">${{s.roe ? (s.roe * 100).toFixed(0) + '%' : 'N/A'}}</strong></span>
        <span style="background: #0d1117; padding: 6px 12px; border-radius: 8px; font-size: 0.85em;">Yield <strong>${{s.dividend_yield ? (s.dividend_yield > 1 ? s.dividend_yield.toFixed(1) : (s.dividend_yield * 100).toFixed(1)) + '%' : 'N/A'}}</strong></span>
        <span style="background: #0d1117; padding: 6px 12px; border-radius: 8px; font-size: 0.85em;">${{'★'.repeat(s.score) + '☆'.repeat(6-s.score)}}</span>
        ${{s.dualOk ? '<span style="font-size: 0.75em; color: var(--green);">Graham ' + '★'.repeat(s.graham.score) + '</span>' : ''}}
      </div>
    </div>
  `).join('');
}}

renderCarteira();
renderPro();
renderLynchPro();
renderGraham();
renderLynch();
renderTopBuy();
</script>

</body>
</html>"""


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n[*] Buscando dados...")
    
    all_data = []
    for ticker in TICKERS:
        data = fetch_stock_data(ticker)
        if data:
            graham = calc_graham(data)
            lynch = calc_lynch(data)
            all_data.append({
                "graham": graham,
                "lynch": lynch
            })
    
    print(f"\n[+] {len(all_data)} ações analisadas")
    
    html = generate_html(all_data)
    
    output_file = os.path.join(os.path.dirname(__file__), "graham_dashboard.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"[+] Dashboard salvo em: {output_file}")


if __name__ == "__main__":
    main()
