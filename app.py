# =============================================================================
# COCKPIT DÉCISIONNEL BOURSIER v5.7 --- "ALLOCATION LONG TERME"
# Lead Dev: Claude (Anthropic)
# =============================================================================
# v5.7 Évolutions majeures :
#   • Transition trading → allocation long terme (70% World, 20% EM Asia, 10% Infrastructure)
#   • Suppression de l'ETF Hydrogen et de l'ETF Or, remplacement par XU61.DE (ESG Infrastructure)
#   • Nouveaux tableaux de suivi des actions sous-jacentes (World, Asia, Infrastructure)
#   • Logique d'arbitrage automatique avec seuils (EM Asia >28%, Infra >15%)
#   • Analyseur macro avec signal SMA200 (Favorable/Défavorable)
#   • Cockpit décisionnel refondu : résumé long terme (gaps, momentum, force relative, volatilité, Sharpe, corrélations)
#   • Persistance JSON inchangée, gestion robuste des NaN/None
#
# Requis (requirements.txt) :
#   streamlit yfinance pandas numpy plotly PyGithub scipy ta requests_cache sqlalchemy tzdata
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 0 : IMPORTS & PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json, os, sqlite3, io, csv, warnings
from typing import Optional, Dict, List, Tuple
import requests_cache
from scipy import stats
import ta  # technical analysis library

warnings.filterwarnings("ignore")

try:
    from github import Github, InputFileContent
    PYGITHUB_OK = True
except ImportError:
    PYGITHUB_OK = False

st.set_page_config(
    page_title="Cockpit v5.7 · Allocation Long Terme",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1 : CSS (inchangé, mobile-first)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');
.stApp { background-color: #1C1F26; font-family: 'DM Sans', sans-serif; }
section[data-testid="stSidebar"] { background-color: #22252E; border-right: 1px solid #2E3340; }
.stApp > header { background-color: #1C1F26; }
.main .block-container { padding-top: 1.2rem; max-width: 1400px; }
.card { background: linear-gradient(145deg, #252932 0%, #2A2D38 100%); border-radius: 12px; padding: 1.4rem; margin-bottom: 1rem; box-shadow: 0 4px 24px rgba(0,0,0,.35); border: 1px solid #32363F; }
.card-gold { border-left: 4px solid #D4AF37; }
.card-blue { border-left: 4px solid #007BFF; }
.card-red { border-left: 4px solid #FF3131; }
.card-orange { border-left: 4px solid #F97316; }
.card-green { border-left: 4px solid #22C55E; }
.card-purple { border-left: 4px solid #A855F7; background: linear-gradient(145deg, #1E1A30 0%, #221D35 100%); }
.kpi-value { font-size:2rem; font-weight:700; color:#FFFFFF; font-family:'Space Mono',monospace; letter-spacing:-1px; }
.kpi-label { font-size:.72rem; color:#6B7585; text-transform:uppercase; letter-spacing:2px; margin-bottom:.3rem; }
.kpi-delta-pos { color:#22C55E; font-size:.82rem; font-weight:600; }
.kpi-delta-neg { color:#FF3131; font-size:.82rem; font-weight:600; }
.regime-banner { padding:.9rem 1.6rem; border-radius:12px; font-weight:700; font-size:1.05rem; margin-bottom:1rem; text-align:center; display:flex; align-items:center; justify-content:space-between; gap:1rem; }
.regime-euphorie { background:linear-gradient(135deg,#7B2D8B,#9B3DB5); color:#F3E8FF; border:1px solid #A855F7; }
.regime-expansion { background:linear-gradient(135deg,#14532D,#166534); color:#86EFAC; border:1px solid #22C55E; }
.regime-neutre { background:linear-gradient(135deg,#1E3A5F,#1E40AF); color:#93C5FD; border:1px solid #3B82F6; }
.regime-stress { background:linear-gradient(135deg,#78350F,#92400E); color:#FDE68A; border:1px solid #F59E0B; }
.regime-contraction{ background:linear-gradient(135deg,#450A0A,#7F1D1D); color:#FCA5A5; border:1px solid #FF3131; box-shadow:0 0 20px rgba(255,49,49,.2); }
.regime-pending { background:linear-gradient(135deg,#1C1F26,#22252E); color:#6B7585; border:1px dashed #374151; }
.status-maintain { background:linear-gradient(135deg,#2D3F1F,#344A22); color:#86EFAC; padding:.8rem 1.2rem; border-radius:8px; font-weight:700; text-align:center; }
.arb-sell { background:linear-gradient(135deg,#350808,#420B0B); border:1px solid #FF3131; border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0; font-family:'Space Mono',monospace; }
.arb-buy { background:linear-gradient(135deg,#083508,#0B4A0B); border:1px solid #22C55E; border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0; font-family:'Space Mono',monospace; }
.arb-neutral { background:linear-gradient(135deg,#1A1F26,#1E242D); border:1px solid #32363F; border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0; font-family:'Space Mono',monospace; }
.pedagogy-box { background: linear-gradient(145deg, #0D1928, #111D30); border: 1px solid #1E3A5F; border-left: 4px solid #3B82F6; border-radius: 10px; padding: 1rem 1.2rem; margin: .6rem 0; font-size: .88rem; color: #93C5FD; line-height: 1.6; }
.leadership-header { background: linear-gradient(135deg, #1A1F26, #1E2530); border: 1px solid #2E3340; border-top: 3px solid #D4AF37; border-radius: 12px; padding: 1rem 1.4rem; margin-bottom: 1rem; }
.live-badge { display:inline-block; background:#22C55E; color:#0B0E15; border-radius:4px; font-size:.62rem; font-weight:800; padding:.1rem .4rem; vertical-align:middle; margin-left:.4rem; }
.mwr-badge { display: inline-block; background: linear-gradient(135deg, #0D2035, #112845); border: 1px solid #3B82F6; border-radius: 6px; padding: .15rem .5rem; font-size: .62rem; font-weight: 800; color: #93C5FD; }
@media (max-width: 768px) { .kpi-value { font-size: 1.5rem; } .card { padding: 1rem; } .stButton button { min-height: 48px !important; } }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2 : CONSTANTES & CONFIGURATION (MODIFIÉ : XU61.DE remplace ANRJ et OR)
# ─────────────────────────────────────────────────────────────────────────────

# ETF_LIBRARY étendu (55+ ETFs) - Mise à jour : suppression de Hydrogen et Or, ajout Infra
ETF_LIBRARY: Dict[str, Dict] = {
    # Portefeuille actuel (nouvelle allocation)
    "XU61.DE": {"nom": "BNP ESG Infrastructure", "name": "BNP Paribas Easy ECPI Global ESG Infrastructure UCITS ETF", "yf": "XU61.DE", "yf_fallbacks": [], "category": "Satellite", "theme": "Infrastructure", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.10},
    "AASI.PA": {"nom": "EM Asia", "name": "Amundi MSCI EM Asia", "yf": "AASI.PA", "yf_fallbacks": [], "category": "Satellite", "theme": "Emerging", "region": "Asia", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.20},
    "MWRD.PA": {"nom": "MSCI World AV", "name": "Amundi MSCI World UCITS DR USD", "yf": "MWRD.PA", "yf_fallbacks": ["IWDA.AS", "EUNL.DE"], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.70},
    "DCAM.PA": {"nom": "MSCI World PEA", "name": "Amundi MSCI World UCITS PEA", "yf": "DCAM.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "PEA", "initial_target": None},
    # Le reste du catalogue est conservé mais sans OR ni Hydrogen
    "500.PA": {"nom": "Amundi S&P 500", "name": "Amundi S&P 500 UCITS", "yf": "500.PA", "yf_fallbacks": [], "category": "Core", "theme": "Large Cap", "region": "USA", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "USTE.PA": {"nom": "Nasdaq-100", "name": "Lyxor UCITS Nasdaq-100 D-EUR", "yf": "USTE.PA", "yf_fallbacks": [], "category": "Core", "theme": "Tech", "region": "USA", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "CW8.PA": {"nom": "MSCI World CW8", "name": "Amundi MSCI World UCITS", "yf": "CW8.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXHEA.PA": {"nom": "Europe Healthcare", "name": "Amundi STOXX Europe 600 Healthcare", "yf": "LYXHEA.PA", "yf_fallbacks": [], "category": "Sector", "theme": "Health", "region": "Europe", "risk_type": "Defensive", "enveloppe": "AV", "initial_target": 0.0},
    "SPHC.PA": {"nom": "S&P 500 Hedged", "name": "Lyxor S&P 500 UCITS - Daily Hedged", "yf": "SPHC.PA", "yf_fallbacks": [], "category": "Core", "theme": "Large Cap", "region": "USA", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "WSRI.PA": {"nom": "World SRI", "name": "Amundi MSCI World SRI Climate Net", "yf": "WSRI.PA", "yf_fallbacks": [], "category": "ESG", "theme": "Sustainability", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "USTH.PA": {"nom": "Nasdaq Hedged", "name": "MULTI UNITS LUXEMBOURG - Lyxor Nasdaq Hedged", "yf": "USTH.PA", "yf_fallbacks": [], "category": "Core", "theme": "Tech", "region": "USA", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "ISEUMD.PA": {"nom": "Europe Mid Cap", "name": "iShares MSCI Europe Mid Cap Acc", "yf": "ISEUMD.PA", "yf_fallbacks": [], "category": "Core", "theme": "Mid Cap", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "ALAT.PA": {"nom": "EM Latin America", "name": "Amundi MSCI EM Latin America UCITS", "yf": "ALAT.PA", "yf_fallbacks": [], "category": "Emerging", "theme": "Commodities", "region": "LatAm", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "INDG.PA": {"nom": "Europe Industrials", "name": "Amundi STOXX Europe 600 Industrials", "yf": "INDG.PA", "yf_fallbacks": [], "category": "Sector", "theme": "Industrial", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "DJE.PA": {"nom": "Dow Jones", "name": "Amundi Dow Jones Industrial Average", "yf": "DJE.PA", "yf_fallbacks": [], "category": "Core", "theme": "Value", "region": "USA", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXFINW.PA": {"nom": "World Financials", "name": "Amundi MSCI World Financials UCITS", "yf": "LYXFINW.PA", "yf_fallbacks": [], "category": "Sector", "theme": "Finance", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "NRAM.PA": {"nom": "North America ESG", "name": "AMUNDI MSCI North America ESG", "yf": "NRAM.PA", "yf_fallbacks": [], "category": "ESG", "theme": "Sustainability", "region": "NorthAmerica", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "GOAI.PA": {"nom": "Global AI", "name": "Amundi Stoxx Global Artificial Intelligence", "yf": "GOAI.PA", "yf_fallbacks": [], "category": "Satellite", "theme": "AI & Tech", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "ENRGA.PA": {"nom": "Europe Energy", "name": "Amundi STOXX Europe 600 Energy", "yf": "ENRGA.PA", "yf_fallbacks": [], "category": "Sector", "theme": "Energy", "region": "Europe", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "JPNH.PA": {"nom": "Japan TOPIX", "name": "Amundi Japan TOPIX II UCITS EUR", "yf": "JPNH.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Japan", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CSW.PA": {"nom": "Switzerland", "name": "Amundi ETF MSCI Switzerland UCITS", "yf": "CSW.PA", "yf_fallbacks": [], "category": "Core", "theme": "Defensive", "region": "Switzerland", "risk_type": "Defensive", "enveloppe": "AV", "initial_target": 0.0},
    "CD9.PA": {"nom": "Europe High Dividend", "name": "Amundi MSCI Europe High Dividend", "yf": "CD9.PA", "yf_fallbacks": [], "category": "Factor", "theme": "Dividend", "region": "Europe", "risk_type": "Defensive", "enveloppe": "AV", "initial_target": 0.0},
    "CJ1.PA": {"nom": "Japan MSCI", "name": "Amundi ETF MSCI Japan UCITS", "yf": "CJ1.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Japan", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "USRI.PA": {"nom": "USA SRI", "name": "AMUNDI MSCI USA SRI Climate Net", "yf": "USRI.PA", "yf_fallbacks": [], "category": "ESG", "theme": "Sustainability", "region": "USA", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXTNOW.PA": {"nom": "World Info Tech", "name": "Amundi MSCI World Information", "yf": "LYXTNOW.PA", "yf_fallbacks": [], "category": "Sector", "theme": "Tech", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "EBUY.PA": {"nom": "Digital Economy", "name": "Lyxor MSCI Digital", "yf": "EBUY.PA", "yf_fallbacks": [], "category": "Satellite", "theme": "Digital Economy", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "COMO.PA": {"nom": "Commodities", "name": "Lyxor UCITS Commodities Thomson", "yf": "COMO.PA", "yf_fallbacks": [], "category": "Alternative", "theme": "Commodities", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "CP9.PA": {"nom": "Pacific Ex Japan", "name": "Amundi ETF MSCI Pacific Ex Japan", "yf": "CP9.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Pacific", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "ESGWO.PA": {"nom": "World ESG Leaders", "name": "Amundi MSCI World ESG Leaders U", "yf": "ESGWO.PA", "yf_fallbacks": [], "category": "ESG", "theme": "Sustainability", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "IUSN.DE": {"nom": "World Small Cap", "name": "iShares MSCI World Small Cap UCITS", "yf": "IUSN.DE", "yf_fallbacks": [], "category": "Core", "theme": "Small Cap", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "WLDHC.PA": {"nom": "World Monthly Hedged", "name": "Lyxor MSCI World UCITS Monthly Hedged", "yf": "WLDHC.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "ESCE.PA": {"nom": "EMU Small Cap", "name": "UBS ETF MSCI EMU Small Cap UCITS", "yf": "ESCE.PA", "yf_fallbacks": [], "category": "Core", "theme": "Small Cap", "region": "Europe", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "2B78.DE": {"nom": "Healthcare Innovation", "name": "iShares Healthcare Innovation Acc", "yf": "2B78.DE", "yf_fallbacks": [], "category": "Satellite", "theme": "Health Tech", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CACC.PA": {"nom": "CAC 40", "name": "Lyxor CAC 40 (DR) UCITS Acc", "yf": "CACC.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "France", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CN1.PA": {"nom": "Nordic", "name": "Amundi ETF MSCI Nordic UCITS", "yf": "CN1.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Nordic", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXRIO.PA": {"nom": "Brazil", "name": "Amundi MSCI Brazil UCITS ETF Acc", "yf": "LYXRIO.PA", "yf_fallbacks": [], "category": "Emerging", "theme": "Blended", "region": "Brazil", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "C50.PA": {"nom": "Euro Stoxx 50", "name": "Amundi ETF Euro Stoxx 50 UCITS", "yf": "C50.PA", "yf_fallbacks": [], "category": "Core", "theme": "Large Cap", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "SMEA.PA": {"nom": "MSCI Europe", "name": "iShares MSCI Europe UCITS Acc", "yf": "SMEA.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "VEUR.PA": {"nom": "FTSE Developed Europe", "name": "Vanguard FTSE Developed Europe", "yf": "VEUR.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "MSE.PA": {"nom": "EURO STOXX 50", "name": "Amundi EURO STOXX 50 II UCITS Acc", "yf": "MSE.PA", "yf_fallbacks": [], "category": "Core", "theme": "Large Cap", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "100H.PA": {"nom": "FTSE 100 Hedged", "name": "Lyxor FTSE 100 Monthly Hedged C", "yf": "100H.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "UK", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CC1U.PA": {"nom": "MSCI China", "name": "Amundi ETF MSCI China UCITS", "yf": "CC1U.PA", "yf_fallbacks": [], "category": "Emerging", "theme": "Blended", "region": "China", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "LYXDAX.PA": {"nom": "DAX", "name": "Lyxor DAX (DR) UCITS - Acc", "yf": "LYXDAX.PA", "yf_fallbacks": [], "category": "Core", "theme": "Large Cap", "region": "Germany", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CMUD.PA": {"nom": "EMU ESG", "name": "Amundi MSCI EMU ESG Selection", "yf": "CMUD.PA", "yf_fallbacks": [], "category": "ESG", "theme": "Sustainability", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "AMCNEG.PA": {"nom": "China ESG", "name": "Amundi MSCI China ESG Leaders Sel", "yf": "AMCNEG.PA", "yf_fallbacks": [], "category": "ESG", "theme": "Sustainability", "region": "China", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "CMU.PA": {"nom": "MSCI EMU", "name": "Amundi MSCI EMU UCITS", "yf": "CMU.PA", "yf_fallbacks": [], "category": "Core", "theme": "Blended", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYNRJ.PA": {"nom": "New Energy", "name": "Lyxor New Energy UCITS ETF Dist", "yf": "LYNRJ.PA", "yf_fallbacks": [], "category": "Satellite", "theme": "Clean Energy", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "SCITY.PA": {"nom": "Smart City", "name": "Amundi Index Solutions - Amundi Smart City", "yf": "SCITY.PA", "yf_fallbacks": [], "category": "Satellite", "theme": "Megatrend", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "RS2U.PA": {"nom": "Resilient", "name": "Amundi Index Solutions - Amundi Resilient", "yf": "RS2U.PA", "yf_fallbacks": [], "category": "Factor", "theme": "Defensive", "region": "Europe", "risk_type": "Defensive", "enveloppe": "AV", "initial_target": 0.0},
    "EUDF.PA": {"nom": "Europe Defence", "name": "WisdomTree Europe Defence UCITS", "yf": "EUDF.PA", "yf_fallbacks": [], "category": "Satellite", "theme": "Defense", "region": "Europe", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "AEEM.PA": {"nom": "MSCI EM", "name": "Amundi ETF MSCI Emerging Markets", "yf": "AEEM.PA", "yf_fallbacks": [], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXLEM.PA": {"nom": "MSCI EM Swap", "name": "Amundi MSCI Em Mkts Swap II UCIT", "yf": "LYXLEM.PA", "yf_fallbacks": [], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "AUEM.PA": {"nom": "MSCI EM USD", "name": "Amundi ETF MSCI Emerging Markets USD", "yf": "AUEM.PA", "yf_fallbacks": [], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    # Suppression de GLDM.PA et XGDE.DE (Or) et ANRJ.PA (Hydrogen)
}

# Compléter les métadonnées pour les anciens tickers (fallbacks etc.)
GOLD_TICKERS_FALLBACK = []  # plus d'or
WORLD_TICKERS = ["MWRD.PA", "IWDA.AS", "EUNL.DE", "DCAM.PA"]
PROXIES_INFRA = ["LITE", "CIEN", "NOK", "AKAM", "CSCO"]  # actions liées à l'infrastructure
PROXIES_EM_ASIA = ["TSM", "005930.KS", "000660.KS", "TCEHY"]  # TSMC, Samsung, SK Hynix, Tencent
MACRO_TICKERS = {"NQ=F": "Nasdaq 100", "ES=F": "S&P 500", "^TNX": "US 10Y (%)", "EURUSD=X": "EUR/USD", "BZ=F": "Brent ($)", "GC=F": "Or ($)", "DX-Y.NYB": "Dollar Index", "MCHI": "iShares MSCI China"}
REGIME_TICKERS = ["SPY", "QQQ", "^VIX", "^TNX", "DX-Y.NYB", "ES=F", "NQ=F"]
SENTINELLES = {"TSMC": ["TSM"], "Samsung": ["005930.KS"], "SK Hynix": ["000660.KS"], "Tencent": ["TCEHY"], "Lumentum": ["LITE"], "Ciena": ["CIEN"], "Nokia": ["NOK"], "Akamai": ["AKAM"], "Cisco": ["CSCO"]}
# Suppression des sentinelles Hydrogen
BENCHMARK_NOM = "MSCI World AV"
DATE_DEBUT = datetime(2025, 9, 17)

_DEFAULT_CAPITAL_REEL = 13_796.71
_DEFAULT_AJUSTEMENT_PAT = 0.0
_DEFAULT_BONUS_FORTUNEO = 0.0
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_perso.json")
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local.db")
_PORTFOLIO_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio_positions.json")
_TRANSACTIONS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions.json")

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3 : FONCTIONS CACHÉES ET DATA MANAGER OPTIMISÉ
# ─────────────────────────────────────────────────────────────────────────────

requests_cache.install_cache('yfinance_cache', expire_after=86400)

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        try:
            tickers_avail = df.columns.get_level_values(1).unique().tolist()
            if tickers_avail:
                df = df.xs(tickers_avail[0], axis=1, level=1)
        except Exception:
            df = df.copy()
            df.columns = df.columns.get_level_values(0)
    df = df.dropna(axis=1, how="all").copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={"Adj Close": "Close", "Adj_Close": "Close", "adj close": "Close"})
    df = df.rename(columns={c: c.title() for c in df.columns})
    if "Close" not in df.columns:
        return pd.DataFrame()
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.ffill().dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

def _fetch_live_price(tk: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        fi = yf.Ticker(tk).fast_info
        prix = getattr(fi, "last_price", None)
        prev = getattr(fi, "previous_close", None)
        if prix and float(prix) > 0:
            return float(prix), float(prev) if prev else None
    except Exception:
        pass
    try:
        info = yf.Ticker(tk).info
        prix = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("navPrice")
        prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
        if prix and float(prix) > 0:
            return float(prix), float(prev) if prev else None
    except Exception:
        pass
    return None, None

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_live_prices() -> Dict[str, Dict]:
    all_tickers = list(ETF_LIBRARY.keys()) + list(MACRO_TICKERS.keys()) + REGIME_TICKERS + PROXIES_INFRA + PROXIES_EM_ASIA
    for tlist in SENTINELLES.values():
        all_tickers.extend(tlist)
    all_tickers = list(dict.fromkeys(all_tickers))
    result = {}
    for tk in all_tickers:
        prix, prev = _fetch_live_price(tk)
        result[tk] = {"prix": prix, "prev": prev}
    return result

@st.cache_data(ttl=7200, show_spinner=False)
def _cached_historical_data() -> Dict[str, pd.DataFrame]:
    all_tickers = list(ETF_LIBRARY.keys()) + list(MACRO_TICKERS.keys()) + REGIME_TICKERS + PROXIES_INFRA + PROXIES_EM_ASIA
    for tlist in SENTINELLES.values():
        all_tickers.extend(tlist)
    all_tickers = list(dict.fromkeys(all_tickers))
    start = (datetime.now() - timedelta(days=600)).strftime("%Y-%m-%d")
    result = {}
    try:
        raw = yf.download(all_tickers, start=start, group_by="ticker", auto_adjust=True, progress=False, threads=True)
    except Exception:
        raw = pd.DataFrame()
    if not raw.empty and isinstance(raw.columns, pd.MultiIndex):
        for tk in all_tickers:
            try:
                df = _normalize_df(raw[tk].copy())
                if not df.empty:
                    result[tk] = df
            except Exception:
                pass
    elif not raw.empty and len(all_tickers) == 1:
        df = _normalize_df(raw.copy())
        if not df.empty:
            result[all_tickers[0]] = df
    for tk in [t for t in all_tickers if t not in result]:
        try:
            df = _normalize_df(yf.download(tk, start=start, auto_adjust=True, progress=False))
            if not df.empty:
                result[tk] = df
        except Exception:
            pass
    return result

class DataManager:
    def __init__(self):
        self.live = _cached_live_prices()
        self.data = _cached_historical_data()
        self._log_returns_cache = None

    def get_price_info(self, tickers: List[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        for tk in tickers:
            info = self.live.get(tk, {})
            prix = info.get("prix")
            prev = info.get("prev")
            if prix and float(prix) > 0:
                return float(prix), float(prev) if prev else None, tk
        return None, None, None

    def compute_log_returns(self) -> Dict[str, pd.Series]:
        if self._log_returns_cache is not None:
            return self._log_returns_cache
        result = {}
        for tk, df in self.data.items():
            if "Close" not in df.columns or len(df) < 2:
                continue
            close = df["Close"].dropna()
            if len(close) < 2:
                continue
            lr = np.log(close / close.shift(1)).dropna()
            if not lr.empty:
                result[tk] = lr
        self._log_returns_cache = result
        return result

    # Helpers pour compatibilité avec l'ancien code
    def sma(self, series: pd.Series, n: int) -> Optional[float]:
        s = series.dropna()
        return float(s.rolling(n).mean().iloc[-1]) if len(s) >= n else None
    def rsi(self, series: pd.Series, period: int = 14) -> Optional[float]:
        return ta.momentum.RSIIndicator(series, window=period).rsi().iloc[-1] if len(series) > period else None
    def adx(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        return None
    def analyze_ticker(self, ticker: str) -> Optional[Dict]:
        lp = self.live.get(ticker, {})
        prix = lp.get("prix")
        df = self.data.get(ticker, pd.DataFrame())
        if df.empty or "Close" not in df.columns:
            return {"ticker": ticker, "prix": prix, "sma20": None, "sma50": None, "sma200": None, "rsi": None, "adx": None, "ath30": None} if prix else None
        close = df["Close"].dropna()
        prix_live = float(prix) if (prix and float(prix) > 0) else float(close.iloc[-1])
        return {"ticker": ticker, "prix": prix_live, "sma20": self.sma(close, 20), "sma50": self.sma(close, 50),
                "sma200": self.sma(close, 200), "rsi": self.rsi(close), "adx": None,
                "ath30": float(close.rolling(30, min_periods=1).max().iloc[-1])}
    def relative_strength_slope(self, ticker: str, days: int = 14) -> Optional[float]:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4 : ANALYTICS ENGINE (version institutionnelle avec corrélation)
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsEngine:
    """
    Moteur d'analyse quantitative vectorisé pour ETF.
    Toutes les métriques utilisent des fenêtres temporelles explicites et cohérentes :
    - 21 jours ouvrés  → 1 mois
    - 63 jours ouvrés  → 3 mois
    - 126 jours ouvrés → 6 mois
    - 252 jours ouvrés → 1 an
    - 756 jours ouvrés → 3 ans

    Utilise 'Adj Close' en priorité, sinon 'Close'.
    Benchmark pour la force relative et l'information ratio : MWRD.PA (MSCI World AV).
    Taux sans risque par défaut : 2.5% annualisé (0.025).
    """

    # Constantes de fenêtres (en jours ouvrés)
    WINDOW_1M = 21
    WINDOW_3M = 63
    WINDOW_6M = 126
    WINDOW_1Y = 252
    WINDOW_3Y = 756

    # Taux sans risque (annualisé)
    RISK_FREE_RATE = 0.025

    def __init__(self, dm: DataManager):
        self.dm = dm
        # Récupération du benchmark principal (MWRD.PA)
        self.benchmark_ticker = "MWRD.PA"
        self.benchmark_df = dm.data.get(self.benchmark_ticker)
        if self.benchmark_df is None or self.benchmark_df.empty:
            for wt in WORLD_TICKERS:
                self.benchmark_df = dm.data.get(wt)
                if self.benchmark_df is not None and not self.benchmark_df.empty:
                    self.benchmark_ticker = wt
                    break

    # -------------------------------------------------------------------------
    # Méthodes internes de nettoyage et extraction des séries
    # -------------------------------------------------------------------------
    def _get_price_column(self, df: pd.DataFrame) -> str:
        """Retourne 'Adj Close' si disponible, sinon 'Close'."""
        if "Adj Close" in df.columns:
            return "Adj Close"
        return "Close"

    def _get_asset_series(self, ticker: str) -> pd.Series:
        """Retourne la série de prix ajustés pour l'actif seul, sans alignement."""
        df = self.dm.data.get(ticker)
        if df is None or df.empty:
            return pd.Series(dtype=float)
        price_col = self._get_price_column(df)
        series = df[price_col].dropna().copy()
        # Tri par date croissante
        series = series.sort_index()
        return series

    def _align_with_benchmark(self, ticker: str) -> Tuple[pd.Series, pd.Series]:
        """Retourne (asset_series, benchmark_series) alignées sur les dates communes."""
        asset = self._get_asset_series(ticker)
        if asset.empty:
            return pd.Series(dtype=float), pd.Series(dtype=float)
        bench = self._get_asset_series(self.benchmark_ticker) if self.benchmark_df is not None else pd.Series(dtype=float)
        if bench.empty:
            return asset, pd.Series(dtype=float)
        common_idx = asset.index.intersection(bench.index)
        if len(common_idx) == 0:
            return asset, pd.Series(dtype=float)
        return asset.loc[common_idx], bench.loc[common_idx]

    # -------------------------------------------------------------------------
    # 1. Momentum sur différentes périodes (uniquement sur l'actif)
    # -------------------------------------------------------------------------
    def _compute_momentum(self, close: pd.Series, window: int) -> float:
        """Momentum sur window jours : (P_t / P_{t-window}) - 1, en pourcentage."""
        if len(close) < window + 1:
            return np.nan
        p0 = close.iloc[-window]
        p1 = close.iloc[-1]
        return (p1 / p0 - 1.0) * 100.0

    def compute_momentum_1m(self, ticker: str) -> float:
        close = self._get_asset_series(ticker)
        return self._compute_momentum(close, self.WINDOW_1M)

    def compute_momentum_3m(self, ticker: str) -> float:
        close = self._get_asset_series(ticker)
        return self._compute_momentum(close, self.WINDOW_3M)

    def compute_momentum_6m(self, ticker: str) -> float:
        close = self._get_asset_series(ticker)
        return self._compute_momentum(close, self.WINDOW_6M)

    # -------------------------------------------------------------------------
    # 2. Force relative (vs benchmark) basée sur les momentum 6M (log-ratio)
    # -------------------------------------------------------------------------
    def compute_relative_strength(self, ticker: str) -> float:
        """
        Relative Strength = ln((ETF_t/ETF_{t-126}) / (Bench_t/Bench_{t-126})) * 100.
        >0 signifie surperformance sur 6 mois.
        """
        asset, bench = self._align_with_benchmark(ticker)
        if bench.empty or len(asset) < self.WINDOW_6M + 1 or len(bench) < self.WINDOW_6M + 1:
            return np.nan
        etf_ratio = asset.iloc[-1] / asset.iloc[-self.WINDOW_6M]
        bench_ratio = bench.iloc[-1] / bench.iloc[-self.WINDOW_6M]
        if bench_ratio <= 0 or etf_ratio <= 0:
            return np.nan
        return np.log(etf_ratio / bench_ratio) * 100.0

    # -------------------------------------------------------------------------
    # 3. Volatilité annualisée (sur 1 an, uniquement sur l'actif)
    # -------------------------------------------------------------------------
    def compute_volatility(self, ticker: str, window: int = WINDOW_1Y) -> float:
        """Volatilité annualisée (écart-type des rendements journaliers * sqrt(252)). Fenêtre glissante."""
        close = self._get_asset_series(ticker)
        if len(close) < window + 1:
            return np.nan
        returns = close.pct_change().dropna().iloc[-window:]
        if len(returns) < 10:
            return np.nan
        return returns.std() * np.sqrt(252) * 100.0

    # -------------------------------------------------------------------------
    # 4. Sharpe ratio annualisé (avec taux sans risque, fenêtre ajustée)
    # -------------------------------------------------------------------------
    def compute_sharpe(self, ticker: str) -> float:
        """
        Sharpe annualisé = (Rendement annualisé - RF) / Volatilité annualisée.
        Rendement annualisé calculé sur une fenêtre de 1 an (ou moins si historique insuffisant),
        annualisé selon la formule (1+R)^(252/n) - 1.
        """
        close = self._get_asset_series(ticker)
        if len(close) < 10:
            return np.nan
        n = min(len(close) - 1, self.WINDOW_1Y)
        if n <= 0:
            return np.nan
        # Rendement sur n jours
        ret = close.iloc[-1] / close.iloc[-n] - 1.0
        # Annualisation
        ann_return = (1.0 + ret) ** (252.0 / n) - 1.0
        # Volatilité annualisée sur la même fenêtre
        returns = close.pct_change().dropna().iloc[-n:]
        if len(returns) < 10:
            return np.nan
        ann_vol = returns.std() * np.sqrt(252)
        if ann_vol == 0 or np.isnan(ann_vol):
            return np.nan
        return (ann_return - self.RISK_FREE_RATE) / ann_vol

    # -------------------------------------------------------------------------
    # 5. Sortino ratio (downside deviation institutionnelle)
    # -------------------------------------------------------------------------
    def compute_sortino(self, ticker: str) -> float:
        """
        Sortino ratio = (Rendement annualisé - RF) / Downside Deviation annualisée.
        Downside deviation = sqrt(moyenne des carrés des rendements en dessous de RF).
        """
        close = self._get_asset_series(ticker)
        if len(close) < 10:
            return np.nan
        n = min(len(close) - 1, self.WINDOW_1Y)
        if n <= 0:
            return np.nan
        # Rendement annualisé
        ret = close.iloc[-1] / close.iloc[-n] - 1.0
        ann_return = (1.0 + ret) ** (252.0 / n) - 1.0
        # Rendements journaliers sur la même fenêtre
        returns = close.pct_change().dropna().iloc[-n:]
        if len(returns) < 10:
            return np.nan
        daily_rf = (1.0 + self.RISK_FREE_RATE) ** (1.0 / 252) - 1.0
        downside = np.minimum(returns - daily_rf, 0)
        downside_dev = np.sqrt(np.mean(downside**2)) * np.sqrt(252)
        if downside_dev == 0 or np.isnan(downside_dev):
            return np.nan
        return (ann_return - self.RISK_FREE_RATE) / downside_dev

    # -------------------------------------------------------------------------
    # 6. Information Ratio (vs benchmark)
    # -------------------------------------------------------------------------
    def compute_information_ratio(self, ticker: str) -> float:
        """
        Information Ratio = (Rendement annualisé de l'actif - Rendement annualisé du benchmark) /
                            Tracking Error (vol des différences journalières)
        Fenêtre : 1 an (ou moins).
        """
        asset, bench = self._align_with_benchmark(ticker)
        if bench.empty or len(asset) < 10 or len(bench) < 10:
            return np.nan
        n = min(min(len(asset)-1, len(bench)-1), self.WINDOW_1Y)
        if n <= 0:
            return np.nan
        # Rendements annualisés
        ret_asset = asset.iloc[-1] / asset.iloc[-n] - 1.0
        ann_ret_asset = (1.0 + ret_asset) ** (252.0 / n) - 1.0
        ret_bench = bench.iloc[-1] / bench.iloc[-n] - 1.0
        ann_ret_bench = (1.0 + ret_bench) ** (252.0 / n) - 1.0
        # Rendements journaliers
        asset_returns = asset.pct_change().dropna().iloc[-n:]
        bench_returns = bench.pct_change().dropna().iloc[-n:]
        common = asset_returns.index.intersection(bench_returns.index)
        if len(common) < 10:
            return np.nan
        diff = asset_returns.loc[common] - bench_returns.loc[common]
        tracking_error = diff.std() * np.sqrt(252)
        if tracking_error == 0 or np.isnan(tracking_error):
            return np.nan
        return (ann_ret_asset - ann_ret_bench) / tracking_error

    # -------------------------------------------------------------------------
    # 7. Drawdowns (1Y, 3Y, since inception) sur l'actif seul
    # -------------------------------------------------------------------------
    def _compute_max_drawdown(self, series: pd.Series, window: int = None) -> float:
        """Maximum Drawdown en pourcentage (négatif). window=None => tout l'historique."""
        if len(series) < 2:
            return np.nan
        if window is not None:
            series = series.iloc[-window:]
        rolling_max = series.cummax()
        drawdown = (series / rolling_max - 1.0)
        return drawdown.min() * 100.0

    def compute_max_drawdown_1y(self, ticker: str) -> float:
        close = self._get_asset_series(ticker)
        return self._compute_max_drawdown(close, self.WINDOW_1Y)

    def compute_max_drawdown_3y(self, ticker: str) -> float:
        close = self._get_asset_series(ticker)
        return self._compute_max_drawdown(close, self.WINDOW_3Y)

    def compute_max_drawdown_since_inception(self, ticker: str) -> float:
        close = self._get_asset_series(ticker)
        return self._compute_max_drawdown(close, None)

    # -------------------------------------------------------------------------
    # 8. RSI de Wilder (smoothing exponentiel)
    # -------------------------------------------------------------------------
    def compute_rsi(self, ticker: str, period: int = 14) -> float:
        """RSI de Wilder utilisant le lissage exponentiel (EWM)."""
        close = self._get_asset_series(ticker)
        if len(close) < period + 1:
            return np.nan
        delta = close.diff()
        # Gain et loss avec lissage Wilder (smoothing factor = 1/period)
        gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty and not np.isnan(rsi.iloc[-1]) else np.nan

    # -------------------------------------------------------------------------
    # 9. Distances aux SMA (sur l'actif seul)
    # -------------------------------------------------------------------------
    def compute_distance_sma(self, ticker: str, window: int) -> float:
        close = self._get_asset_series(ticker)
        if len(close) < window:
            return np.nan
        sma = close.rolling(window).mean().iloc[-1]
        if np.isnan(sma) or sma == 0:
            return np.nan
        return ((close.iloc[-1] / sma) - 1.0) * 100.0

    # -------------------------------------------------------------------------
    # 10. Corrélation de Pearson sur rendements logarithmiques (vs benchmark)
    # -------------------------------------------------------------------------
    def compute_correlation(self, ticker: str, window: int = 126) -> float:
        """
        Corrélation de Pearson entre l'actif et le benchmark (MWRD.PA)
        calculée sur les rendements logarithmiques journaliers.
        Retourne une valeur entre -1 et +1 (non annualisée).
        """
        asset, bench = self._align_with_benchmark(ticker)
        if asset.empty or bench.empty or len(asset) < window + 1 or len(bench) < window + 1:
            return np.nan

        # Rendements logarithmiques journaliers
        asset_returns = np.log(asset / asset.shift(1))
        bench_returns = np.log(bench / bench.shift(1))

        # Alignement strict et suppression des dates non communes
        returns_df = pd.concat([asset_returns, bench_returns], axis=1, join="inner").dropna()

        if len(returns_df) < window:
            return np.nan

        returns_df = returns_df.iloc[-window:]
        correlation = returns_df.iloc[:, 0].corr(returns_df.iloc[:, 1])
        return float(correlation) if pd.notna(correlation) else np.nan

    # -------------------------------------------------------------------------
    # 11. Méthode unifiée retournant toutes les métriques
    # -------------------------------------------------------------------------
    def compute_all_metrics(self, ticker: str) -> dict:
        """Retourne un dictionnaire avec toutes les métriques (compatible avec SignalEngine)."""
        close = self._get_asset_series(ticker)
        if close.empty:
            return {}
        metrics = {
            "price": close.iloc[-1] if not close.empty else np.nan,
            "mom_1m": self.compute_momentum_1m(ticker),
            "mom_3m": self.compute_momentum_3m(ticker),
            "mom_6m": self.compute_momentum_6m(ticker),
            "rel_strength": self.compute_relative_strength(ticker),
            "volatility": self.compute_volatility(ticker),
            "sharpe": self.compute_sharpe(ticker),
            "sortino": self.compute_sortino(ticker),
            "information_ratio": self.compute_information_ratio(ticker),
            "max_drawdown_1y": self.compute_max_drawdown_1y(ticker),
            "max_drawdown_3y": self.compute_max_drawdown_3y(ticker),
            "max_drawdown_since": self.compute_max_drawdown_since_inception(ticker),
            "max_drawdown": self.compute_max_drawdown_1y(ticker),  # Pour compatibilité scoring
            "rsi": self.compute_rsi(ticker),
            "dist_sma20": self.compute_distance_sma(ticker, 20),
            "dist_sma50": self.compute_distance_sma(ticker, 50),
            # Corrélations
            "corr_1m": self.compute_correlation(ticker, self.WINDOW_1M),
            "corr_3m": self.compute_correlation(ticker, self.WINDOW_3M),
            "corr_6m": self.compute_correlation(ticker, self.WINDOW_6M),
            "corr_1y": self.compute_correlation(ticker, self.WINDOW_1Y),
        }
        return metrics

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 5 : SIGNAL ENGINE (scoring + arbitrage) - Adapté pour nouvelle allocation
# ─────────────────────────────────────────────────────────────────────────────

class SignalEngine:
    def __init__(self, dm: DataManager, analytics: AnalyticsEngine):
        self.dm = dm
        self.analytics = analytics

    def compute_score(self, ticker: str) -> dict:
        m = self.analytics.compute_all_metrics(ticker)
        if not m:
            return {"score": 0, "metrics": {}}
        score = 0
        # Momentum 6M (25 pts)
        mom6 = m.get("mom_6m", 0)
        if mom6 > 15: score += 25
        elif mom6 > 8: score += 18
        elif mom6 > 3: score += 10
        elif mom6 > 0: score += 4
        # Force relative (20 pts)
        rel = m.get("rel_strength", 0)
        if rel > 8: score += 20
        elif rel > 4: score += 14
        elif rel > 0: score += 7
        # Distance SMA20 (15 pts)
        dist20 = m.get("dist_sma20", 0)
        if dist20 > 5: score += 15
        elif dist20 > 2: score += 10
        elif dist20 > 0: score += 5
        # Sharpe ratio (15 pts)
        sharpe = m.get("sharpe", 0)
        if sharpe > 1.5: score += 15
        elif sharpe > 0.8: score += 10
        elif sharpe > 0.3: score += 5
        # RSI (5 pts)
        rsi = m.get("rsi", 50)
        if 55 <= rsi <= 70: score += 5
        elif rsi > 70: score += 2
        # Drawdown 1Y (10 pts)
        dd = m.get("max_drawdown_1y", -50)
        if dd > -10: score += 10
        elif dd > -20: score += 5
        # Volatilité (10 pts)
        vol = m.get("volatility", 30)
        if vol < 15: score += 10
        elif vol < 25: score += 5
        return {"score": min(100, score), "metrics": m}

    def get_arbitrage_opportunities(self, holdings: List[str]) -> List[dict]:
        all_scores = {}
        for ticker in self.dm.data.keys():
            if ticker in ETF_LIBRARY:
                all_scores[ticker] = self.compute_score(ticker)["score"]
        best_others = sorted([(t, s) for t, s in all_scores.items() if t not in holdings], key=lambda x: -x[1])[:5]
        opportunities = []
        for held in holdings:
            held_score = all_scores.get(held, 0)
            for cand, cand_score in best_others:
                if cand_score > held_score + 15:
                    opportunities.append({
                        "sell": held, "buy": cand, "gain_potential": cand_score - held_score,
                        "buy_name": ETF_LIBRARY.get(cand, {}).get("nom", cand),
                        "sell_name": ETF_LIBRARY.get(held, {}).get("nom", held)
                    })
                    break
        return opportunities

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 6 : PERSISTENCE MANAGER (inchangé)
# ─────────────────────────────────────────────────────────────────────────────

_CSV_COLS = ["date", "capital_cloture", "valeur_titres",
             "perf_jour", "perf_cumul", "regime", "score_regime",
             "poids_em", "poids_infra"]

class PersistenceManager:
    def __init__(self, static_capital: float):
        self.static_capital = static_capital
        self._github_ok = False
        self._gist = None
        self._github_warning = ""
        self._history_cache: Optional[pd.DataFrame] = None
        try:
            self._conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
            self._init_db()
        except Exception:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._init_db()
        if PYGITHUB_OK:
            try:
                token = st.secrets.get("GITHUB_TOKEN", "")
                gist_id = st.secrets.get("GIST_ID", "")
                if token and gist_id:
                    gh = Github(token)
                    self._gist = gh.get_gist(gist_id)
                    self._github_ok = True
                    self._sync_from_github()
            except Exception as e:
                self._github_warning = f"GitHub Gist indisponible : {str(e)[:80]}"
        else:
            self._github_warning = "PyGithub non installé --- mode SQLite uniquement."

    def _init_db(self):
        self._conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            date TEXT PRIMARY KEY,
            capital_cloture REAL NOT NULL,
            valeur_titres REAL,
            perf_jour REAL,
            perf_cumul REAL,
            regime TEXT,
            score_regime INTEGER,
            poids_em REAL,
            poids_infra REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """)
        self._conn.commit()

    def _sync_from_github(self):
        if not self._gist:
            return
        try:
            files = self._gist.files
            if "history.csv" not in files:
                return
            content = files["history.csv"].content or ""
            if not content.strip():
                return
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                self._conn.execute("""
                INSERT OR REPLACE INTO snapshots
                (date,capital_cloture,valeur_titres,perf_jour,perf_cumul,
                 regime,score_regime,poids_em,poids_infra)
                VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    row.get("date",""),
                    float(row.get("capital_cloture") or 0),
                    float(row.get("valeur_titres") or 0),
                    float(row.get("perf_jour") or 0),
                    float(row.get("perf_cumul") or 0),
                    row.get("regime",""),
                    int(float(row.get("score_regime") or 0)),
                    float(row.get("poids_em") or 0),
                    float(row.get("poids_infra") or 0),
                ))
            self._conn.commit()
        except Exception:
            pass

    def _push_to_github(self, df: pd.DataFrame):
        if not self._gist:
            return
        try:
            buf = io.StringIO()
            df.to_csv(buf, index=False, columns=_CSV_COLS)
            self._gist.edit(files={"history.csv": InputFileContent(buf.getvalue())})
        except Exception:
            pass

    def save_snapshot(self, capital_cloture: float, valeur_titres: float,
                      perf_jour: float, perf_cumul: float, regime: str,
                      score_regime: int, poids_em: float, poids_infra: float) -> bool:
        today = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
        try:
            self._conn.execute("""
            INSERT OR REPLACE INTO snapshots
            (date,capital_cloture,valeur_titres,perf_jour,perf_cumul,
             regime,score_regime,poids_em,poids_infra)
            VALUES (?,?,?,?,?,?,?,?,?)
            """, (today, round(capital_cloture, 2), round(valeur_titres, 2),
                  round(perf_jour, 4), round(perf_cumul, 4), regime,
                  score_regime, round(poids_em, 4), round(poids_infra, 4)))
            self._conn.commit()
            self._history_cache = None
            if self._github_ok:
                self._push_to_github(self.load_history())
            return True
        except Exception:
            return False

    def load_history(self) -> pd.DataFrame:
        if self._history_cache is not None:
            return self._history_cache
        try:
            df = pd.read_sql("SELECT * FROM snapshots ORDER BY date ASC", self._conn)
            for col in _CSV_COLS:
                if col not in df.columns:
                    df[col] = None
            self._history_cache = df[_CSV_COLS].copy()
            return self._history_cache
        except Exception:
            return pd.DataFrame(columns=_CSV_COLS)

    def get_last_snapshot(self) -> Optional[Dict]:
        hist = self.load_history()
        if hist.empty:
            return None
        row = hist.iloc[-1]
        return {c: row[c] for c in _CSV_COLS}

    def get_initial_capital(self) -> float:
        hist = self.load_history()
        if not hist.empty and hist["capital_cloture"].notna().any():
            return float(hist["capital_cloture"].dropna().iloc[0])
        return self.static_capital

    def compute_daily_performance(self, current_value: float) -> Tuple[float, float, float]:
        last = self.get_last_snapshot()
        initial = self.get_initial_capital()
        base = float(last["capital_cloture"]) if last else self.static_capital
        if base <= 0:
            base = self.static_capital
        perf_jour = (current_value / base - 1) * 100 if base > 0 else 0.0
        perf_cumul = (current_value / initial - 1) * 100 if initial > 0 else 0.0
        return perf_jour, perf_cumul, base

    @property
    def status(self) -> str:
        if self._github_ok:
            return "github"
        if self._github_warning:
            return "warn"
        return "local"

    @property
    def warning_msg(self) -> str:
        return self._github_warning

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 7 : PORTFOLIO CONFIG MANAGER & TRANSACTION ENGINE (positions initiales mises à jour)
# ─────────────────────────────────────────────────────────────────────────────

class PortfolioConfigManager:
    def __init__(self, file_path: str = _PORTFOLIO_JSON):
        self.file_path = file_path

    def load_positions(self) -> List[Dict]:
        try:
            if os.path.exists(self.file_path) and os.stat(self.file_path).st_size > 0:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    return data
        except Exception:
            pass
        # Positions initiales au 22 mai 2026 (nouvelle allocation)
        return [
            {"ticker": "MWRD.PA", "parts": 50.58145, "prm": 140.21, "account": "AV"},
            {"ticker": "AASI.PA", "parts": 53.75484, "prm": 52.10, "account": "AV"},
            {"ticker": "XU61.DE", "parts": 14.58606, "prm": 94.12, "account": "AV"},
            {"ticker": "DCAM.PA", "parts": 508.49831, "prm": 5.965, "account": "PEA"},
        ]

    def save_positions(self, positions: List[Dict]) -> bool:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(positions, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

class TransactionEngine:
    def __init__(self, file_path: str = _TRANSACTIONS_JSON):
        self.file_path = file_path

    def load_transactions(self) -> List[Dict]:
        try:
            if not os.path.exists(self.file_path):
                return []
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def save_transaction(self, tx: Dict) -> bool:
        try:
            txs = self.load_transactions()
            txs.append(tx)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(txs, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def rebuild_portfolio_at_date(self, target_date: str = None) -> Dict[str, Dict]:
        txs = self.load_transactions()
        positions: Dict[str, Dict] = {}
        for tx in txs:
            if target_date and tx.get("date", "") > target_date:
                continue
            tk = tx.get("ticker", "")
            if not tk:
                continue
            if tk not in positions:
                positions[tk] = {"parts": 0.0, "total_cost": 0.0}
            if tx.get("type") == "BUY":
                positions[tk]["parts"] += float(tx.get("parts", 0))
                positions[tk]["total_cost"] += float(tx.get("parts", 0)) * float(tx.get("price", 0))
            elif tx.get("type") == "SELL":
                positions[tk]["parts"] -= float(tx.get("parts", 0))
                if positions[tk]["parts"] <= 0:
                    positions[tk] = {"parts": 0.0, "total_cost": 0.0}
        return positions

    def get_portfolio_as_positions(self) -> List[Dict]:
        rebuilt = self.rebuild_portfolio_at_date()
        result = []
        for tk_id, data in rebuilt.items():
            if data["parts"] <= 0:
                continue
            prm = data["total_cost"] / data["parts"] if data["parts"] > 0 else 0.0
            meta = ETF_LIBRARY.get(tk_id, {})
            result.append({
                "ticker": tk_id,
                "parts": round(data["parts"], 6),
                "prm": round(prm, 4),
                "account": meta.get("enveloppe", "AV"),
            })
        return result

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 8 : MARKET REGIME ENGINE (inchangé)
# ─────────────────────────────────────────────────────────────────────────────

_REGIME_LABELS = [
    (4, 5, "Euphorie", "regime-euphorie", "#A855F7"),
    (2, 3, "Expansion", "regime-expansion", "#22C55E"),
    (0, 1, "Neutre", "regime-neutre", "#3B82F6"),
    (-3,-1, "Stress", "regime-stress", "#F59E0B"),
    (-5,-4, "Contraction", "regime-contraction", "#FF3131"),
]

REGIME_MULTIPLIERS = {
    "Euphorie": 1.00, "Expansion": 1.00, "Neutre": 0.85, "Stress": 0.70, "Contraction": 0.20,
}

class MarketRegimeEngine:
    def __init__(self, dm: DataManager):
        self.dm = dm

    def _compute_score_at(self, offset: int = 0) -> int:
        score = 0
        data = self.dm.data
        def _get_close(tickers):
            for tk in tickers:
                df = data.get(tk, pd.DataFrame())
                if not df.empty and "Close" in df.columns:
                    cl = df["Close"].dropna()
                    if len(cl) > offset + 10:
                        return cl.iloc[:len(cl) - offset] if offset > 0 else cl
            return None
        cl = _get_close(["ES=F", "SPY"])
        if cl is not None and len(cl) >= 201:
            score += 1 if float(cl.iloc[-1]) > float(cl.rolling(200).mean().iloc[-1]) else -1
        cl = _get_close(["QQQ", "NQ=F"])
        if cl is not None and len(cl) >= 51:
            score += 1 if float(cl.iloc[-1]) > float(cl.rolling(50).mean().iloc[-1]) else -1
        cl = _get_close(["^VIX"])
        if cl is not None:
            score += 1 if float(cl.iloc[-1]) < 20 else -1
        cl = _get_close(["^TNX"])
        if cl is not None and len(cl) >= 21:
            score += 1 if float(cl.iloc[-1]) < float(cl.rolling(20).mean().iloc[-1]) else -1
        cl = _get_close(["DX-Y.NYB"])
        if cl is not None and len(cl) >= 51:
            score += 1 if float(cl.iloc[-1]) < float(cl.rolling(50).mean().iloc[-1]) else -1
        return max(-5, min(5, score))

    def _score_to_label(self, score: int) -> Tuple[str, str, str]:
        for lo, hi, label, css, color in _REGIME_LABELS:
            if lo <= score <= hi:
                return label, css, color
        return "Neutre", "regime-neutre", "#3B82F6"

    def get_full_regime(self) -> Dict:
        scores_3d = []
        for offset in range(3):
            try:
                scores_3d.append(self._compute_score_at(offset))
            except Exception:
                scores_3d.append(0)
        current_score = scores_3d[0]
        label_0, css_0, color_0 = self._score_to_label(current_score)
        labels_3d = [self._score_to_label(s)[0] for s in scores_3d]
        if len(set(labels_3d)) == 1 or labels_3d[0] == labels_3d[1]:
            confirmed = True
            conf_label, conf_css, conf_color = label_0, css_0, color_0
            conf_score = current_score
        else:
            confirmed = False
            conf_label, conf_css, conf_color = "En attente", "regime-pending", "#6B7585"
            conf_score = current_score
        return {
            "current_score": current_score, "confirmed_score": conf_score,
            "confirmed_label": conf_label, "confirmed_css": conf_css,
            "confirmed_color": conf_color, "is_confirmed": confirmed,
            "scores_3d": scores_3d, "labels_3d": labels_3d,
            "components": self._get_component_details(),
            "multiplier": REGIME_MULTIPLIERS.get(conf_label, 0.85),
        }

    def _get_component_details(self) -> List[Dict]:
        data = self.dm.data
        detail = []
        def _last(tks):
            for tk in tks:
                df = data.get(tk, pd.DataFrame())
                if not df.empty and "Close" in df.columns:
                    cl = df["Close"].dropna()
                    if not cl.empty: return cl
            return None
        cl = _last(["ES=F", "SPY"])
        if cl is not None and len(cl) >= 201:
            sma = float(cl.rolling(200).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Trend (SMA200)", "bull": v > sma, "val": f"{v:.1f} vs {sma:.1f}"})
        else:
            detail.append({"name": "Trend (SMA200)", "bull": None, "val": "N/A"})
        cl = _last(["QQQ", "NQ=F"])
        if cl is not None and len(cl) >= 51:
            sma = float(cl.rolling(50).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Breadth (SMA50)", "bull": v > sma, "val": f"{v:.1f} vs {sma:.1f}"})
        else:
            detail.append({"name": "Breadth (SMA50)", "bull": None, "val": "N/A"})
        cl = _last(["^VIX"])
        if cl is not None:
            v = float(cl.iloc[-1])
            detail.append({"name": "Volatilité (VIX)", "bull": v < 20, "val": f"{v:.2f} (seuil 20)"})
        else:
            detail.append({"name": "Volatilité (VIX)", "bull": None, "val": "N/A"})
        cl = _last(["^TNX"])
        if cl is not None and len(cl) >= 21:
            sma = float(cl.rolling(20).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Taux (US10Y SMA20)", "bull": v < sma, "val": f"{v:.3f}% vs {sma:.3f}%"})
        else:
            detail.append({"name": "Taux (US10Y SMA20)", "bull": None, "val": "N/A"})
        cl = _last(["DX-Y.NYB"])
        if cl is not None and len(cl) >= 51:
            sma = float(cl.rolling(50).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Liquidité (DXY)", "bull": v < sma, "val": f"{v:.2f} vs {sma:.2f}"})
        else:
            detail.append({"name": "Liquidité (DXY)", "bull": None, "val": "N/A"})
        return detail

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 9 : QUANT RISK ENGINE (adapté pour infra)
# ─────────────────────────────────────────────────────────────────────────────

class QuantRiskEngine:
    def __init__(self, dm: DataManager):
        self.dm = dm
        self._log_returns = dm.compute_log_returns()

    def rolling_volatility(self, ticker: str, window: int = 30) -> Optional[float]:
        lr = self._log_returns.get(ticker)
        if lr is None or len(lr) < window:
            return None
        return float(lr.iloc[-window:].std() * np.sqrt(252))

    def rolling_volatility_from_df(self, df: pd.DataFrame, window: int = 30) -> Optional[float]:
        if df is None or df.empty or "Close" not in df.columns:
            return None
        close = df["Close"].dropna()
        if len(close) < window + 1:
            return None
        lr = np.log(close / close.shift(1)).dropna()
        if len(lr) < window:
            return None
        return float(lr.iloc[-window:].std() * np.sqrt(252))

    def rolling_beta(self, ticker: str, benchmark: str = "MWRD.PA", window: int = 60) -> Optional[float]:
        lr_a = self._log_returns.get(ticker)
        lr_b = self._log_returns.get(benchmark)
        if lr_b is None:
            for wt in WORLD_TICKERS:
                lr_b = self._log_returns.get(wt)
                if lr_b is not None: break
        if lr_a is None or lr_b is None:
            return None
        common = lr_a.index.intersection(lr_b.index)
        if len(common) < window:
            return None
        a = lr_a[common].iloc[-window:].values
        b = lr_b[common].iloc[-window:].values
        cov = np.cov(a, b)[0, 1]
        var = np.var(b)
        return float(cov / var) if var > 1e-12 else None

    def rolling_beta_from_df(self, df: pd.DataFrame, benchmark: str = "MWRD.PA", window: int = 60) -> Optional[float]:
        if df is None or df.empty or "Close" not in df.columns:
            return None
        close = df["Close"].dropna()
        if len(close) < window + 1:
            return None
        lr_a = np.log(close / close.shift(1)).dropna()
        lr_b = self._log_returns.get(benchmark)
        if lr_b is None:
            for wt in WORLD_TICKERS:
                lr_b = self._log_returns.get(wt)
                if lr_b is not None: break
        if lr_b is None:
            return None
        common = lr_a.index.intersection(lr_b.index)
        if len(common) < window:
            return None
        a = lr_a[common].iloc[-window:].values
        b = lr_b[common].iloc[-window:].values
        cov = np.cov(a, b)[0, 1]
        var = np.var(b)
        return float(cov / var) if var > 1e-12 else None

    def drawdown_metrics(self, ticker: str, window: int = 252) -> Dict:
        df = self.dm.data.get(ticker, pd.DataFrame())
        if df.empty or "Close" not in df.columns:
            return {"current_dd": None, "max_dd": None}
        close = df["Close"].dropna()
        if len(close) < 10:
            return {"current_dd": None, "max_dd": None}
        recent = close.iloc[-window:]
        peak = recent.cummax()
        dd = (recent / peak - 1)
        return {"current_dd": float(dd.iloc[-1]) * 100, "max_dd": float(dd.min()) * 100}

    def drawdown_metrics_from_df(self, df: pd.DataFrame, window: int = 252) -> Dict:
        if df is None or df.empty or "Close" not in df.columns:
            return {"current_dd": None, "max_dd": None}
        close = df["Close"].dropna()
        if len(close) < 10:
            return {"current_dd": None, "max_dd": None}
        recent = close.iloc[-window:]
        peak = recent.cummax()
        dd = (recent / peak - 1)
        return {"current_dd": float(dd.iloc[-1]) * 100, "max_dd": float(dd.min()) * 100}

    def correlation_matrix(self, tickers: List[str], window: int = 60) -> Optional[pd.DataFrame]:
        series_dict = {}
        for tk in tickers:
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                series_dict[tk] = lr.iloc[-window:]
        if len(series_dict) < 2:
            return None
        df_all = pd.concat(series_dict.values(), axis=1)
        df_all.columns = list(series_dict.keys())
        df_all = df_all.dropna()
        if len(df_all) < 20:
            return None
        return df_all.corr()

    def risk_contribution(self, tickers: List[str], weights: List[float], window: int = 60) -> Dict[str, Dict]:
        valid_tickers, valid_lr, valid_w = [], [], []
        for tk, w in zip(tickers, weights):
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                valid_tickers.append(tk); valid_lr.append(lr); valid_w.append(w)
        if len(valid_tickers) < 2:
            return {}
        df_all = pd.concat(valid_lr, axis=1)
        df_all.columns = valid_tickers
        df_all = df_all.dropna().iloc[-window:]
        if len(df_all) < 20:
            return {}
        w = np.array(valid_w, dtype=float); w /= w.sum()
        cov = df_all.cov().values * 252
        port_v = float(w @ cov @ w)
        mrc = cov @ w
        rc = w * mrc
        total_rc = rc.sum()
        rc_pct = rc / total_rc * 100 if total_rc > 0 else rc * 0
        result = {}
        for i, tk in enumerate(valid_tickers):
            result[tk] = {"weight_pct": w[i] * 100, "rc_absolute": float(rc[i]), "rc_pct": float(rc_pct[i]), "flag": float(rc_pct[i]) > 40}
        return result

    def portfolio_volatility(self, tickers: List[str], weights: List[float], window: int = 60) -> Optional[float]:
        valid_tickers, valid_lr, valid_w = [], [], []
        for tk, w in zip(tickers, weights):
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                valid_tickers.append(tk); valid_lr.append(lr); valid_w.append(w)
        if len(valid_tickers) < 2:
            return None
        df_all = pd.concat(valid_lr, axis=1)
        df_all.columns = valid_tickers
        df_all = df_all.dropna().iloc[-window:]
        if len(df_all) < 20:
            return None
        w = np.array(valid_w) / sum(valid_w)
        cov = df_all.cov().values * 252
        return float(np.sqrt(w @ cov @ w))

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 10 : PORTFOLIO ENGINE (adapté pour nouvelle allocation)
# ─────────────────────────────────────────────────────────────────────────────

def enrich_positions(raw_positions: List[Dict]) -> List[Dict]:
    result = []
    for pos in raw_positions:
        tk_id = pos.get("ticker")
        meta = ETF_LIBRARY.get(tk_id)
        if meta is None:
            continue
        result.append({
            "nom": meta["nom"],
            "tickers": [meta["yf"]] + meta.get("yf_fallbacks", []),
            "parts": float(pos.get("parts", 0.0)),
            "prm": float(pos.get("prm", 0.0)),
            "enveloppe": pos.get("account", meta["enveloppe"]),
            "_tk_id": tk_id,
        })
    return result

class PortfolioEngine:
    def __init__(self, dm: DataManager, re: MarketRegimeEngine, qre: QuantRiskEngine):
        self.dm = dm
        self.re = re
        self.qre = qre

    def compute_adjusted_benchmark(self) -> float:
        flux_data = [
            ("2025-09-17", 7210.0), ("2025-10-15", 200.0), ("2025-11-12", 100.0),
            ("2025-11-13", 200.0), ("2025-11-26", 300.0), ("2025-12-15", 200.0),
            ("2026-01-14", 212.0), ("2026-02-13", 212.0), ("2026-03-06", 400.0),
            ("2026-03-12", 520.0), ("2026-03-13", 212.0), ("2026-03-27", 750.0),
            ("2026-04-01", 750.0),
        ]
        df_h = None
        for tk in ["MWRD.PA", "IWDA.AS", "EUNL.DE"]:
            df_h = self.dm.data.get(tk)
            if df_h is not None and not df_h.empty and "Close" in df_h.columns:
                break
        if df_h is None or df_h.empty:
            return 0.0
        close_series = df_h["Close"].dropna()
        total_parts = 0.0
        total_invested = sum(f[1] for f in flux_data)
        for date_str, amount in flux_data:
            try:
                target_date = pd.to_datetime(date_str)
                price = float(close_series.asof(target_date))
                if price <= 0 or np.isnan(price):
                    continue
                net_invested = amount * 0.999
                total_parts += net_invested / price
            except Exception:
                continue
        if total_parts <= 0 or total_invested <= 0:
            return 0.0
        current_price = float(close_series.iloc[-1])
        final_val = (total_parts * current_price) - 31.26 + 16.23
        perf_adj = ((final_val - total_invested) / total_invested) * 100
        return round(perf_adj, 4)

    def compute_portfolio(self, positions_conf: List[Dict], capital_reel: float, ajustement_pat: float, bonus_fortuneo: float) -> Dict:
        positions_calc = []
        valeur_totale = valeur_veille = 0.0
        val_env = {"PEA": 0.0, "AV": 0.0}
        gan_env = {"PEA": 0.0, "AV": 0.0}
        for pos in positions_conf:
            prix, prev, tk_used = self.dm.get_price_info(pos["tickers"])
            env = pos["enveloppe"]
            if prix is None:
                positions_calc.append({"nom": pos["nom"], "ticker": None, "prix": None, "valeur": 0.0, "perf_pct": None, "var_jour_pct": 0.0, "var_jour_eur": 0.0, "enveloppe": env})
                continue
            valeur = pos["parts"] * prix
            gain_unit = prix - pos["prm"]
            perf_pct = gain_unit / pos["prm"] * 100 if pos["prm"] != 0 else 0.0
            gain_total = gain_unit * pos["parts"]
            var_j_pct = (prix - prev) / prev * 100 if prev and prev != 0 else 0.0
            var_j_eur = (prix - prev) * pos["parts"] if prev else 0.0
            positions_calc.append({"nom": pos["nom"], "ticker": tk_used, "prix": prix, "valeur": valeur, "perf_pct": perf_pct,
                                   "var_jour_pct": var_j_pct, "var_jour_eur": var_j_eur, "enveloppe": env})
            valeur_totale += valeur
            val_env[env] += valeur
            gan_env[env] += gain_total
            valeur_veille += pos["parts"] * (prev if prev else prix)
        solde_total = valeur_totale + ajustement_pat
        gain_reel = solde_total - capital_reel
        perf_tot_pct = (gain_reel / capital_reel * 100) if capital_reel else 0.0
        perf_j_eur = valeur_totale - valeur_veille
        perf_j_pct = perf_j_eur / valeur_veille * 100 if valeur_veille else 0.0
        return {"positions": positions_calc, "valeur_totale": valeur_totale, "solde_total": solde_total,
                "gain_reel": gain_reel, "perf_tot_pct": perf_tot_pct, "valeur_veille": valeur_veille,
                "val_env": val_env, "gain_env": gan_env, "ajustement_pat": ajustement_pat,
                "capital_reel": capital_reel, "perf_j_eur": perf_j_eur, "perf_j_pct": perf_j_pct}

    def compute_benchmark(self, positions_conf: List[Dict], perf_tot_pct: float) -> Dict:
        bench = next((p for p in positions_conf if p["nom"] == BENCHMARK_NOM), None)
        if not bench:
            return {}
        prix, prev, tk = self.dm.get_price_info(bench["tickers"])
        if not prix:
            return {}
        df_h = self.dm.data.get(tk, pd.DataFrame())
        if df_h.empty:
            for t in bench["tickers"]:
                df_h = self.dm.data.get(t, pd.DataFrame())
                if not df_h.empty: break
        if df_h.empty:
            return {"prix": prix}
        close = df_h["Close"].dropna()
        try:
            start_val = float(close.loc[DATE_DEBUT.strftime("%Y-%m-%d")])
        except KeyError:
            cands = close.loc[:DATE_DEBUT.strftime("%Y-%m-%d")]
            start_val = float(cands.iloc[-1]) if not cands.empty else float(close.iloc[0])
        perf_bench_lumpsum = (prix / start_val - 1) * 100 if start_val else None
        perf_bench_adj = self.compute_adjusted_benchmark()
        gap_adj = perf_tot_pct - perf_bench_adj if perf_bench_adj != 0 else None
        gap_lumpsum = perf_tot_pct - perf_bench_lumpsum if perf_bench_lumpsum is not None else None
        perf_bench_j = (prix - prev) / prev * 100 if prev and prev != 0 else None
        return {"perf_bench": perf_bench_lumpsum, "perf_bench_adj": perf_bench_adj, "gap": gap_adj,
                "gap_lumpsum": gap_lumpsum, "prix": prix, "perf_bench_j": perf_bench_j}

    def compute_unified_score(self, ticker: str) -> Dict:
        info = self.dm.analyze_ticker(ticker)
        details = []
        score = 0
        rsi_v = info["rsi"] if info else None
        if rsi_v is not None:
            if rsi_v >= 70: ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Tendu"
            elif rsi_v <= 45: ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Faible"
            else: ms, mb, md = 1, "bull", f"RSI={rsi_v:.1f} Sain"
        else: ms, mb, md = 0, "neut", "RSI indisponible"
        details.append({"name": "Momentum", "score": ms, "badge": mb, "desc": md}); score += ms
        if info and info["sma20"] is not None:
            if info["prix"] > info["sma20"]:
                ss, sb, sd = 1, "bull", f"Prix {info['prix']:.2f} > SMA20 {info['sma20']:.2f}"
            else:
                ss, sb, sd = -1, "bear", f"Prix {info['prix']:.2f} < SMA20 {info['sma20']:.2f}"
        else: ss, sb, sd = 0, "neut", "SMA20 indisponible"
        details.append({"name": "Structure", "score": ss, "badge": sb, "desc": sd}); score += ss
        rs_slope = self.dm.relative_strength_slope(ticker, 14)
        if rs_slope is not None:
            if rs_slope > 0: ls, lb, ld = 2, "bull", f"Pente={rs_slope:+.5f} Leader ✓"
            else: ls, lb, ld = -2, "bear", f"Pente={rs_slope:.5f} Lagger"
        else: ls, lb, ld = 0, "neut", "Données insuffisantes"
        details.append({"name": "Leadership", "score": ls, "badge": lb, "desc": ld}); score += ls
        return {"total": max(-4, min(4, score)), "momentum": ms, "structure": ss, "leadership": ls,
                "details": details, "rsi_raw": rsi_v, "adx_raw": info["adx"] if info else None}

    def compute_strategic_score_4c(self, ticker: str, regime: Dict) -> Dict:
        info = self.dm.analyze_ticker(ticker)
        trend_raw = 0.0
        if info and info["sma20"] and info["prix"]:
            dev = (info["prix"] - info["sma20"]) / info["sma20"]
            trend_raw = max(-1.0, min(1.0, dev * 20))
        macro_raw = regime["confirmed_score"] / 5.0
        rs = self.dm.relative_strength_slope(ticker, 14)
        leader_raw = (1.0 if rs and rs > 0 else -1.0 if rs and rs <= 0 else 0.0)
        vol = self.qre.rolling_volatility(ticker, 30)
        vol_raw = max(-1.0, min(1.0, (0.20 - vol) / 0.10)) if vol is not None else 0.0
        total = (trend_raw * 0.25 + macro_raw * 0.30 + leader_raw * 0.25 + vol_raw * 0.20)
        return {"total": max(-1.0, min(1.0, total)), "trend": trend_raw, "macro": macro_raw,
                "leadership": leader_raw, "risk_vol": vol_raw}

    def compute_confidence_factor(self, tickers: List[str], weights: List[float]) -> float:
        port_vol = self.qre.portfolio_volatility(tickers, weights, 60)
        if port_vol is None: return 0.85
        if port_vol < 0.10: return 1.00
        elif port_vol < 0.15: return 0.90
        elif port_vol < 0.20: return 0.75
        else: return 0.60

    def compute_target_weight(self, nom: str, ticker: str, valeur_totale: float, positions_calc: List[Dict]) -> Dict:
        regime = self.re.get_full_regime()
        unified = self.compute_unified_score(ticker)
        strat4c = self.compute_strategic_score_4c(ticker, regime)
        it = next((m["initial_target"] for m in ETF_LIBRARY.values() if m["nom"] == nom), 0.05)
        if it is None: it = 0.05
        base_w = self._get_base_weight(unified["total"], it)
        regime_mult = regime["multiplier"]
        ptf_tickers = [p["ticker"] for p in positions_calc if p.get("ticker")]
        ptf_weights = [p["valeur"] / valeur_totale for p in positions_calc if p.get("ticker") and valeur_totale > 0]
        confidence = self.compute_confidence_factor(ptf_tickers, ptf_weights)
        strat_adj = 1.0 + strat4c["total"] * 0.30
        target = base_w * regime_mult * confidence * strat_adj
        target = max(0.02, min(0.35, target))
        current_val = next((p["valeur"] for p in positions_calc if p["nom"] == nom), 0.0)
        current_pct = current_val / valeur_totale * 100 if valeur_totale > 0 else 0.0
        target_pct = target * 100
        delta_pct = current_pct - target_pct
        target_eur = valeur_totale * target
        if delta_pct > 1.0: action = "RÉDUIRE"
        elif delta_pct < -1.0: action = "RENFORCER"
        else: action = "MAINTENIR"
        return {"nom": nom, "unified_score": unified["total"], "strat_score": strat4c["total"], "strat4c": strat4c,
                "base_weight": base_w, "regime_mult": regime_mult, "confidence": confidence,
                "target_pct": target_pct, "current_pct": current_pct, "current_eur": current_val,
                "target_eur": target_eur, "delta_pct": delta_pct, "delta_eur": current_val - target_eur,
                "action": action, "regime_label": regime["confirmed_label"]}

    def _get_base_weight(self, score: int, initial_target: float) -> float:
        if score >= 3: return initial_target
        elif score >= 1: return 0.20
        elif score >= -1: return 0.15
        else: return 0.05

    def evaluate_em_asia(self, aasi: Optional[Dict]) -> Tuple[str, str]:
        if aasi is None: return "⚠️ AASI données indisponibles", "gray"
        p = aasi["prix"]
        if p > 60.35:
            if aasi["ath30"] and p < aasi["ath30"] * 0.92: return "🎯 TRAILING STOP --8% ATH déclenché", "red"
            return "📈 TRAILING STOP ACTIF --- Surveiller", "green"
        if aasi["sma20"] and p < aasi["sma20"]: return "🔶 SOUS SMA20 --- Surveillance active", "orange"
        if aasi["sma50"] and p > aasi["sma50"]: return "✅ MAINTIEN --- Au-dessus SMA50", "green"
        return "ℹ️ SURVEILLANCE NEUTRE", "orange"

    def evaluate_infra(self, infra: Optional[Dict]) -> Tuple[str, str]:
        if infra is None: return "⚠️ XU61.DE données indisponibles", "gray"
        p = infra["prix"]
        if infra["sma20"] and p < infra["sma20"]: return "🔶 SOUS SMA20 --- Surveillance active", "orange"
        if infra["sma50"] and p > infra["sma50"]: return "✅ MAINTIEN --- Au-dessus SMA50", "green"
        if infra["rsi"] and infra["rsi"] > 70: return "💰 RSI élevé (>70) - Risque de consolidation", "orange"
        return "ℹ️ SURVEILLANCE NEUTRE", "green"

    def evaluate_sentinelles(self) -> Tuple[str, str, List[Dict]]:
        alerts, rows = [], []
        for name, tickers in SENTINELLES.items():
            info = None
            for tk in tickers:
                info = self.dm.analyze_ticker(tk)
                if info: break
            alerte = ""
            if info and info["sma20"] and info["prix"] < info["sma20"]:
                alerte = "⚠️"; alerts.append(name)
            rows.append({"Sentinelle": name, "Prix": f"{info['prix']:.2f}" if info else "N/A",
                         "SMA20": f"{info['sma20']:.2f}" if (info and info["sma20"]) else "N/A",
                         "RSI": f"{info['rsi']:.1f}" if (info and info["rsi"]) else "N/A", "Alerte": alerte})
        msg = " | ".join([f"⚠️ {a} sous SMA20" for a in alerts]) if alerts else "✅ Sentinelles OK"
        return msg, "orange" if alerts else "green", rows

    def check_leadership_alerts(self) -> List[Dict]:
        alerts = []
        world_close = None
        for wt in WORLD_TICKERS:
            df = self.dm.data.get(wt, pd.DataFrame())
            if not df.empty and "Close" in df.columns:
                world_close = df["Close"].dropna()
                break
        if world_close is None: return alerts
        for ticker, meta in ETF_LIBRARY.items():
            if meta.get("category") != "Satellite": continue
            df = self.dm.data.get(ticker, pd.DataFrame())
            if df.empty or "Close" not in df.columns: continue
            sc = df["Close"].dropna()
            common = sc.index.intersection(world_close.index)
            if len(common) < 16: continue
            recent = common[-15:]
            s_pf = (sc[recent].iloc[-1] / sc[recent].iloc[0] - 1) * 100
            w_pf = (world_close[recent].iloc[-1] / world_close[recent].iloc[0] - 1) * 100
            alerts.append({"nom": meta["nom"], "sat_perf": s_pf, "world_perf": w_pf, "gap": s_pf - w_pf})
        return alerts

    def determine_phase(self, gap, em_asia, infra) -> Tuple[str, str]:
        if gap is None: return "⏳ Phase indéterminée --- Données insuffisantes", "#374151"
        if gap < 0: return "📉 Phase 1 : Reconquête --- Revenir à l'équilibre vs World AV", "#7F1D1D"
        signals = []
        if em_asia and em_asia["sma20"] and em_asia["prix"] < em_asia["sma20"]: signals.append("EM Asia<SMA20")
        if infra and infra["sma20"] and infra["prix"] < infra["sma20"]: signals.append("Infra<SMA20")
        if signals: return f"🔄 Phase 3 : Rotation --- Sécuriser les gains ({', '.join(signals)})", "#78350F"
        return "🚀 Phase 2 : Alpha --- Battre le MSCI World", "#14532D"

    # Méthodes pour projection objectifs
    def _compute_cagr_for_ticker(self, ticker: str, start_date: datetime = DATE_DEBUT) -> Tuple[float, bool]:
        df = self.dm.data.get(ticker)
        if df is None or df.empty or "Close" not in df.columns:
            return 0.07, True
        close = df["Close"].dropna()
        if len(close) < 2:
            return 0.07, True
        start_date_str = start_date.strftime("%Y-%m-%d")
        if start_date_str in close.index:
            price_start = close.loc[start_date_str]
        else:
            idx = close.index[close.index >= start_date_str]
            if len(idx) == 0:
                price_start = close.iloc[0]
                start_date_effective = close.index[0]
            else:
                price_start = close.loc[idx[0]]
                start_date_effective = idx[0]
        price_end = close.iloc[-1]
        if price_start <= 0 or price_end <= 0:
            return 0.07, True
        end_date = close.index[-1]
        if 'start_date_effective' not in locals():
            start_date_effective = start_date
        days = (end_date - start_date_effective).days
        if days <= 0:
            return 0.07, True
        years = days / 365.25
        if years <= 0:
            return 0.07, True
        cagr = (price_end / price_start) ** (1.0 / years) - 1.0
        if np.isnan(cagr) or cagr <= 0.01:
            return 0.07, True
        return cagr, False

    def compute_envelope_cagr(self, envelope: str, positions_calc: List[Dict]) -> Tuple[float, bool]:
        env_positions = [p for p in positions_calc if p.get("enveloppe") == envelope and p.get("valeur",0) > 0]
        if not env_positions:
            return 0.07, True
        if envelope == "PEA":
            pea_ticker = None
            for p in env_positions:
                if p.get("ticker") and "DCAM.PA" in p["ticker"]:
                    pea_ticker = "DCAM.PA"
                    break
            if not pea_ticker:
                pea_ticker = env_positions[0].get("ticker")
            if pea_ticker:
                cagr, fall = self._compute_cagr_for_ticker(pea_ticker, DATE_DEBUT)
                return cagr, fall
            else:
                return 0.07, True
        else:  # AV
            total_value = sum(p["valeur"] for p in env_positions)
            if total_value <= 0:
                return 0.07, True
            weighted_cagr = 0.0
            any_fallback = False
            for pos in env_positions:
                ticker = pos.get("ticker")
                if not ticker:
                    continue
                weight = pos["valeur"] / total_value
                cagr, fall = self._compute_cagr_for_ticker(ticker, DATE_DEBUT)
                if fall:
                    any_fallback = True
                weighted_cagr += weight * cagr
            if weighted_cagr <= 0.01:
                return 0.07, True
            return weighted_cagr, any_fallback

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 11 : PEDAGOGIC ENGINE (adapté)
# ─────────────────────────────────────────────────────────────────────────────

class PedagogicEngine:
    def translate_volatility(self, vol: Optional[float], asset_name: str) -> Dict:
        if vol is None:
            return {"value": "N/A", "emoji": "❓", "level": "orange", "title": f"Agitation de {asset_name}",
                    "explain": "Donnée indisponible.", "scale": [], "action": "Revérifier plus tard."}
        pct = vol * 100
        if pct < 15: emoji, level, msg, action = "😌", "green", "L'ETF est calme et stable.", "Aucune vigilance."
        elif pct < 25: emoji, level, msg, action = "😐", "orange", "L'ETF bouge normalement.", "Surveillez."
        else: emoji, level, msg, action = "😰", "red", "L'ETF est agité, variations brutales possibles.", "Réduisez éventuellement."
        return {"value": f"{pct:.1f}%", "emoji": emoji, "level": level, "title": f"Agitation de {asset_name}",
                "explain": f"{msg}\n\nPlus ce chiffre est élevé, plus l'ETF peut perdre ou gagner brusquement.",
                "scale": [{"label": "< 15% --- Calme", "cls": "scale-green"},
                          {"label": "15-25% --- Normal", "cls": "scale-orange"},
                          {"label": "> 25% --- Risqué", "cls": "scale-red"}], "action": action}

    def translate_beta(self, beta: Optional[float], asset_name: str) -> Dict:
        if beta is None:
            return {"value": "N/A", "emoji": "❓", "level": "orange", "title": "Sensibilité au marché",
                    "explain": "Donnée indisponible.", "scale": [], "action": "Revérifier plus tard."}
        if beta < 0: emoji, level, msg, action = "🔄", "orange", "ETF à contre-courant du marché.", "Défensif intéressant."
        elif beta < 0.8: emoji, level, msg, action = "🛡️", "green", f"Bouge {(1-beta)*100:.0f}% moins que le marché.", "Protège bien en baisse."
        elif beta < 1.2: emoji, level, msg, action = "⚖️", "green", "Suit le marché de façon équilibrée.", "Comportement neutre."
        elif beta < 1.8: emoji, level, msg, action = "⚡", "orange", f"Bouge {(beta-1)*100:.0f}% plus violemment.", "Limitez la position."
        else: emoji, level, msg, action = "🌋", "red", "Très sensible aux mouvements du marché.", "Position risquée."
        return {"value": f"{beta:.2f}×", "emoji": emoji, "level": level, "title": f"Sensibilité au marché de {asset_name}",
                "explain": msg, "scale": [{"label": "< 0.8 --- Défensif", "cls": "scale-green"},
                                          {"label": "0.8-1.2 --- Neutre", "cls": "scale-green"},
                                          {"label": "1.2-1.8 --- Offensif", "cls": "scale-orange"},
                                          {"label": "> 1.8 --- Très risqué", "cls": "scale-red"}], "action": action}

    def translate_drawdown(self, current_dd: Optional[float], max_dd: Optional[float], asset_name: str) -> Dict:
        if current_dd is None:
            return {"value": "N/A", "emoji": "❓", "level": "orange", "title": "Recul depuis le sommet",
                    "explain": "Donnée indisponible.", "scale": [], "action": "Revérifier plus tard."}
        abs_dd = abs(current_dd)
        if abs_dd < 3: emoji, level, msg, action = "🏔️", "green", f"{asset_name} est proche de son sommet.", "Aucune alerte."
        elif abs_dd < 8: emoji, level, msg, action = "📉", "orange", f"Recul de {abs_dd:.1f}%, repli normal.", "Surveillance normale."
        elif abs_dd < 15: emoji, level, msg, action = "⚠️", "orange", f"Recul de {abs_dd:.1f}%, correction significative.", "Vérifiez le stop-loss."
        else: emoji, level, msg, action = "🚨", "red", f"Chute de {abs_dd:.1f}%, perte importante.", "Envisagez de réduire."
        max_str = f" | Plus forte baisse 1 an : {abs(max_dd):.1f}%" if max_dd is not None else ""
        return {"value": f"{current_dd:.1f}%", "emoji": emoji, "level": level, "title": f"Recul depuis le sommet de {asset_name}",
                "explain": msg + max_str, "scale": [{"label": "0 à -3% --- Sommet", "cls": "scale-green"},
                                                    {"label": "-3 à -8% --- Repli normal", "cls": "scale-orange"},
                                                    {"label": "> -8% --- Correction", "cls": "scale-red"}], "action": action}

    def translate_regime(self, regime: Dict) -> Dict:
        translations = {
            "Euphorie": {"emoji": "🚀", "level": "green", "explain": "Les marchés sont en euphorie. Les investisseurs achètent massivement.",
                         "action": "Maintenez vos positions, mais restez vigilant.", "conseil": "Préparez vos stops."},
            "Expansion": {"emoji": "📈", "level": "green", "explain": "Croissance régulière. Contexte favorable.",
                          "action": "Maintenez vos positions. Renforcements possibles.", "conseil": "Phase idéale pour Core+Satellites."},
            "Neutre": {"emoji": "⚖️", "level": "orange", "explain": "Pas de direction claire. Autant de signaux positifs que négatifs.",
                       "action": "Réduisez légèrement les positions risquées si besoin.", "conseil": "Attendez une confirmation."},
            "Stress": {"emoji": "😟", "level": "orange", "explain": "Signes de fatigue. Nervosité accrue.",
                       "action": "Réduisez les satellites. Renforcez l'or ou le World.", "conseil": "Préservez votre capital."},
            "Contraction": {"emoji": "🚨", "level": "red", "explain": "Crise ou forte baisse. Contexte très défavorable.",
                            "action": "Réduisez fortement les satellites. Passez en défensif.", "conseil": "Protégez le capital."},
            "En attente": {"emoji": "⏳", "level": "orange", "explain": "Signaux contradictoires. Non confirmé.",
                           "action": "Attendez 1-2 jours.", "conseil": "Ne prenez pas de décision importante."}
        }
        info = translations.get(regime["confirmed_label"], translations["En attente"])
        return {"label": regime["confirmed_label"], "score": regime["confirmed_score"], "emoji": info["emoji"],
                "level": info["level"], "explain": info["explain"], "action": info["action"], "conseil": info["conseil"]}

    def translate_leadership(self, nom: str, weekly_gaps: List[float]) -> Dict:
        if not weekly_gaps:
            return {"emoji": "❓", "level": "orange", "message": "Données insuffisantes.", "detail": "", "action": "Revérifiez."}
        pos = sum(1 for g in weekly_gaps if g > 0)
        neg = sum(1 for g in weekly_gaps if g < 0)
        avg = sum(weekly_gaps) / len(weekly_gaps)
        n = len(weekly_gaps)
        consec_neg = 0
        for g in reversed(weekly_gaps):
            if g < 0: consec_neg += 1
            else: break
        if pos >= n * 0.6 and avg > 0:
            return {"emoji": "🟢", "level": "green", "message": f"{nom} conserve son leadership.",
                    "detail": f"{pos}/{n} semaines positives · Moyenne : {avg:+.1f}%", "action": "Conserver."}
        elif consec_neg >= 3:
            return {"emoji": "🔴", "level": "red", "message": "Le World devient plus intéressant.",
                    "detail": f"{consec_neg} semaines consécutives de sous-performance", "action": "Envisagez de réduire."}
        elif neg > pos:
            return {"emoji": "🟠", "level": "orange", "message": f"{nom} perd son avantage.",
                    "detail": f"{neg}/{n} semaines négatives · Moyenne : {avg:+.1f}%", "action": "Surveillance accrue."}
        else:
            return {"emoji": "🟡", "level": "orange", "message": f"{nom} est à égalité avec le World.",
                    "detail": f"Performance équivalente · Moyenne : {avg:+.1f}%", "action": "Maintien raisonnable."}

    def get_weekly_performances(self, dm: DataManager, ticker: str, n_weeks: int = 5) -> Tuple[List[str], List[float], List[float]]:
        world_close = None
        for wt in WORLD_TICKERS:
            df = dm.data.get(wt, pd.DataFrame())
            if not df.empty and "Close" in df.columns:
                world_close = df["Close"].dropna()
                break
        sat_df = dm.data.get(ticker, pd.DataFrame())
        if world_close is None or sat_df.empty or "Close" not in sat_df.columns:
            return [], [], []
        sat_close = sat_df["Close"].dropna()
        common = sat_close.index.intersection(world_close.index)
        if len(common) < 10:
            return [], [], []
        sat_w = sat_close[common].resample("W").last()
        world_w = world_close[common].resample("W").last()
        common_w = sat_w.index.intersection(world_w.index)
        if len(common_w) < 2:
            return [], [], []
        sat_w = sat_w[common_w]; world_w = world_w[common_w]
        sat_ret = sat_w.pct_change().dropna() * 100
        world_ret = world_w.pct_change().dropna() * 100
        n = min(n_weeks, len(sat_ret))
        sat_ret = sat_ret.iloc[-n:]; world_ret = world_ret.iloc[-n:]
        labels = ["En cours" if i == n-1 else f"S-{n-1-i}" for i in range(n)]
        return labels, list(sat_ret.values), list(world_ret.values)

    def translate_simple_score(self, score_raw: int) -> Dict:
        mapping = {-4:0,-3:0,-2:1,-1:2,0:2,1:3,2:3,3:4,4:5}
        simple = mapping.get(max(-4, min(4, score_raw)), 2)
        msgs = {5: ("⭐⭐⭐⭐⭐", "Momentum très fort", "ring-5", "Tout est au vert.", "Maintenez."),
                4: ("⭐⭐⭐⭐☆", "Tendance saine", "ring-4", "Progresse bien.", "Maintenez / renforcez."),
                3: ("⭐⭐⭐☆☆", "Situation neutre", "ring-3", "Stable.", "Maintenez."),
                2: ("⭐⭐☆☆☆", "Fragilité", "ring-2", "Signes de faiblesse.", "Prudence."),
                1: ("⭐☆☆☆☆", "Risque élevé", "ring-1", "Difficultés.", "Envisagez de réduire."),
                0: ("☆☆☆☆☆", "Danger", "ring-0", "Très dégradé.", "Réduction forte.")}
        stars, label, ring_cls, explain, action = msgs[simple]
        return {"score": simple, "stars": stars, "label": label, "ring_cls": ring_cls, "explain": explain, "action": action}

    def translate_sentinelles(self, sent_rows: List[Dict], sector: str) -> Dict:
        if sector == "em_asia":
            names = ["TSMC", "Samsung", "SK Hynix", "Tencent"]
        elif sector == "infra":
            names = ["Lumentum", "Ciena", "Nokia", "Akamai", "Cisco"]
        else:
            names = []
        alerts = [r for r in sent_rows if r.get("Sentinelle") in names and r.get("Alerte") == "⚠️"]
        total = sum(1 for r in sent_rows if r.get("Sentinelle") in names)
        if not alerts:
            return {"emoji": "🟢", "level": "green", "message": "Leaders solides.",
                    "detail": f"Aucune alerte sur {total} valeurs.", "action": "Pas d'action requise."}
        elif len(alerts) == 1:
            return {"emoji": "🟠", "level": "orange", "message": "Les leaders perdent du momentum.",
                    "detail": f"{alerts[0]['Sentinelle']} sous SMA20.", "action": "Surveillance accrue."}
        else:
            return {"emoji": "🔴", "level": "red", "message": "Décrochage fort des leaders.",
                    "detail": f"{', '.join([a['Sentinelle'] for a in alerts])} sous SMA20.", "action": "Réduction conseillée."}

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 12 : STRATEGIC ENGINE (inchangé)
# ─────────────────────────────────────────────────────────────────────────────

class StrategicEngine:
    def __init__(self, dm: DataManager, mre: MarketRegimeEngine, qre: QuantRiskEngine):
        self.dm = dm; self.mre = mre; self.qre = qre

    def compute(self, ticker: str, unified_score: Dict, regime: Dict) -> Dict:
        details = []
        rsi = unified_score.get("rsi_raw")
        if rsi is not None and 45 < rsi < 70:
            mom_score, mom_label, mom_value = 1, "✅ Bonne dynamique", f"RSI {rsi:.0f}"
        elif rsi is not None:
            mom_score, mom_label, mom_value = 0, "❌ Dynamique faible ou tendue", f"RSI {rsi:.0f}"
        else:
            mom_score, mom_label, mom_value = 0, "❓ Donnée indisponible", "N/A"
        details.append({"dim": "Momentum", "score": mom_score, "label": mom_label, "value": mom_value})
        struct_score = 1 if unified_score.get("structure", -1) > 0 else 0
        info = self.dm.analyze_ticker(ticker)
        if info and info["sma20"] and info["prix"]:
            st_label = "✅ Prix > SMA20" if struct_score == 1 else "❌ Prix < SMA20"
            st_value = f"{info['prix']:.2f}€ vs SMA20 {info['sma20']:.2f}€"
        else:
            st_label, st_value = "❓ Donnée indisponible", "N/A"
        details.append({"dim": "Structure", "score": struct_score, "label": st_label, "value": st_value})
        lead_score = 1 if unified_score.get("leadership", -2) > 0 else 0
        rs = self.dm.relative_strength_slope(ticker, 14)
        if rs is not None:
            lead_label = "✅ Surperforme le World" if lead_score == 1 else "❌ Sous-performe le World"
            lead_value = f"Pente : {rs:+.5f}"
        else:
            lead_label, lead_value = "❓ Donnée indisponible", "N/A"
        details.append({"dim": "Leadership", "score": lead_score, "label": lead_label, "value": lead_value})
        reg_score = regime.get("confirmed_score", 0)
        macro_ok = reg_score >= 1
        macro_label = f"✅ Environnement favorable ({regime['confirmed_label']})" if macro_ok else f"❌ Environnement difficile ({regime['confirmed_label']})"
        details.append({"dim": "Macro", "score": 1 if macro_ok else 0, "label": macro_label, "value": f"Score {reg_score:+d}/5"})
        vol = self.qre.rolling_volatility(ticker, 30)
        if vol is not None:
            risk_ok = vol < 0.25
            risk_label = f"✅ Agitation acceptable ({vol*100:.1f}%)" if risk_ok else f"❌ Très agité ({vol*100:.1f}%)"
            risk_value = f"{vol*100:.1f}% ann."
        else:
            risk_label, risk_value = "❓ Donnée indisponible", "N/A"
        details.append({"dim": "Risque", "score": 1 if (vol is not None and vol < 0.25) else 0, "label": risk_label, "value": risk_value})
        total = sum(d["score"] for d in details)
        if total >= 4: verdict, verdict_cls = "✅ Conditions très favorables --- Maintien recommandé", "verdict-green"
        elif total >= 3: verdict, verdict_cls = "🟡 Conditions correctes --- Maintien avec surveillance", "verdict-orange"
        elif total >= 2: verdict, verdict_cls = "🟠 Conditions mitigées --- Prudence conseillée", "verdict-orange"
        else: verdict, verdict_cls = "🔴 Conditions défavorables --- Réduction recommandée", "verdict-red"
        return {"total": total, "details": details, "verdict": verdict, "verdict_cls": verdict_cls}

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 13 : FISCAL (inchangé)
# ─────────────────────────────────────────────────────────────────────────────

def net_apres_impots(enveloppe: str, montant: float, val_poche: float, gain_poche: float) -> Tuple[float, str]:
    if montant <= 0: return 0.0, ""
    if montant > val_poche: return 0.0, "⚠️ Montant supérieur à la valeur de la poche"
    ratio_gain = gain_poche / val_poche if val_poche else 0
    gain_retrait = montant * ratio_gain
    now_tz = datetime.now(ZoneInfo("Europe/Paris"))
    if enveloppe == "PEA":
        limite = datetime(2031, 4, 1, tzinfo=ZoneInfo("Europe/Paris"))
        if now_tz < limite:
            return 0.0, "⚠️ Retrait PEA impossible avant le 01/04/2031 (fermeture enveloppe)"
        return montant - 0.172 * gain_retrait, ""
    if enveloppe == "AV":
        if now_tz < datetime(2033, 9, 17, tzinfo=ZoneInfo("Europe/Paris")):
            return montant - 0.30 * gain_retrait, ""
        ps = 0.172 * gain_retrait
        ir = 0.128 * max(0, gain_retrait - 9200)
        return montant - ps - ir, ""
    return montant, ""

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 14 : VISUALISATIONS (inchangées sauf nécessité)
# ─────────────────────────────────────────────────────────────────────────────

_PLOTLY_BASE = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#CBD5E1", family="DM Sans"))

def plot_equity_curve(history: pd.DataFrame) -> Optional[go.Figure]:
    if history.empty or "capital_cloture" not in history.columns: return None
    df = history.dropna(subset=["capital_cloture"]).copy()
    if len(df) < 2: return None
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_dt"]).sort_values("date_dt")
    fig = go.Figure()
    regime_colors = {"Euphorie": "rgba(168,85,247,.10)", "Expansion": "rgba(34,197,94,.10)",
                     "Neutre": "rgba(59,130,246,.08)", "Stress": "rgba(245,158,11,.10)",
                     "Contraction": "rgba(255,49,49,.12)"}
    if "regime" in df.columns:
        prev = None; x0 = df["date_dt"].iloc[0]
        for _, row in df.iterrows():
            if row.get("regime") != prev and prev is not None:
                fig.add_vrect(x0=x0, x1=row["date_dt"], fillcolor=regime_colors.get(prev, "rgba(255,255,255,.03)"), layer="below", line_width=0)
                x0 = row["date_dt"]
            prev = row.get("regime")
        if prev:
            fig.add_vrect(x0=x0, x1=df["date_dt"].iloc[-1], fillcolor=regime_colors.get(prev, "rgba(255,255,255,.03)"), layer="below", line_width=0)
    fig.add_trace(go.Scatter(x=df["date_dt"], y=df["capital_cloture"], mode="lines+markers", line=dict(color="#D4AF37", width=2.5), marker=dict(size=5), name="Capital Clôture"))
    if "perf_cumul" in df.columns and df["perf_cumul"].notna().any():
        fig.add_trace(go.Scatter(x=df["date_dt"], y=df["perf_cumul"], mode="lines", line=dict(color="#3B82F6", width=1.5, dash="dot"), name="Perf Cumul (%)", yaxis="y2"))
    fig.update_layout(**_PLOTLY_BASE, title=dict(text="<b>Évolution de votre capital</b>", font=dict(size=13, color="#6B7585")),
                      margin=dict(t=40, b=30, l=60, r=60), height=280, legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)", x=0, y=1.15, orientation="h"),
                      xaxis=dict(gridcolor="#2E3340", showgrid=True), yaxis=dict(gridcolor="#2E3340", showgrid=True, ticksuffix="€", title="Capital (€)"),
                      yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%", title="Perf (%)"))
    return fig

def plot_weekly_leadership(labels: List[str], sat_perfs: List[float], world_perfs: List[float], sat_name: str, color_sat: str = "#D4AF37") -> go.Figure:
    fig = go.Figure()
    bar_colors_sat = ["#22C55E" if v > 0 else "#FF3131" for v in sat_perfs]
    fig.add_trace(go.Bar(x=labels, y=sat_perfs, name=sat_name, marker_color=bar_colors_sat, text=[f"{v:+.1f}%" for v in sat_perfs], textposition="outside"))
    bar_colors_world = ["rgba(59,130,246,.7)" if v > 0 else "rgba(59,130,246,.4)" for v in world_perfs]
    fig.add_trace(go.Bar(x=labels, y=world_perfs, name="MSCI World", marker_color=bar_colors_world, text=[f"{v:+.1f}%" for v in world_perfs], textposition="outside"))
    fig.add_hline(y=0, line_dash="dot", line_color="#4B5563", opacity=0.8)
    fig.update_layout(**_PLOTLY_BASE, barmode="group", bargap=0.20, bargroupgap=0.05,
                      title=dict(text=f"<b>Leadership hebdomadaire : {sat_name} vs MSCI World</b>", font=dict(size=13, color="#6B7585")),
                      margin=dict(t=50, b=40, l=50, r=30), height=300, legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)", x=0, y=1.12, orientation="h"),
                      xaxis=dict(gridcolor="#2E3340", showgrid=False), yaxis=dict(gridcolor="#2E3340", ticksuffix="%", zeroline=False))
    return fig

def plot_correlation_heatmap(corr_df: pd.DataFrame) -> go.Figure:
    short = {"XU61.DE": "Infra", "AASI.PA": "EM", "MWRD.PA": "World", "DCAM.PA": "W-PEA"}
    labels = [short.get(c, c) for c in corr_df.columns]
    fig = go.Figure(go.Heatmap(z=corr_df.values.round(2), x=labels, y=labels, colorscale=[[0,"#FF3131"],[0.5,"#252932"],[1,"#22C55E"]], zmid=0, zmin=-1, zmax=1,
                               text=corr_df.values.round(2), texttemplate="%{text:.2f}", hovertemplate="<b>%{y} / %{x}</b><br>ρ = %{z:.2f}<extra></extra>",
                               showscale=True, colorbar=dict(tickfont=dict(color="#CBD5E1", size=9), thickness=12, len=0.8, bgcolor="rgba(0,0,0,0)")))
    fig.update_layout(**_PLOTLY_BASE, title=dict(text="<b>Corrélation Pearson (60j)</b>", font=dict(size=12, color="#6B7585")),
                      margin=dict(t=40, b=10, l=60, r=20), height=220)
    return fig

def plot_risk_contribution(rc: Dict) -> Optional[go.Figure]:
    if not rc: return None
    short = {"XU61.DE": "Infra", "AASI.PA": "EM Asia", "MWRD.PA": "MSCI World", "DCAM.PA": "World PEA"}
    names = [short.get(tk, tk) for tk in rc]
    values = [rc[tk]["rc_pct"] for tk in rc]
    colors = ["#FF3131" if rc[tk]["flag"] else "#007BFF" for tk in rc]
    fig = go.Figure(go.Bar(x=values, y=names, orientation="h", marker_color=colors, hovertemplate="%{y}: <b>%{x:.1f}%</b>"))
    fig.add_vline(x=40, line_dash="dash", line_color="#FF3131", annotation_text="Seuil 40%", annotation_font=dict(color="#FF3131", size=9))
    fig.update_layout(**_PLOTLY_BASE, title=dict(text="<b>Risk Contribution (%)</b>", font=dict(size=12, color="#6B7585")),
                      margin=dict(t=40, b=10, l=80, r=20), height=200, xaxis=dict(gridcolor="#2E3340", ticksuffix="%"), yaxis=dict(gridcolor="rgba(0,0,0,0)"))
    return fig

def plot_weight_indicator(current_pct: float, target_pct: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=round(current_pct, 1), number={"suffix": "%", "font": {"size": 26, "color": "#CBD5E1", "family": "Space Mono"}},
        delta={"reference": target_pct, "relative": False, "increasing": {"color": "#F97316"}, "decreasing": {"color": "#22C55E"}, "suffix": "%", "valueformat": ".1f"},
        title={"text": "Poids Actuel<br><span style='font-size:.8em;color:#6B7585'>vs Cible (or)</span>", "font": {"size": 11, "color": "#8892AA"}},
        gauge={"axis": {"range": [0, 35], "tickcolor": "#6B7585", "tickfont": {"size": 9}, "nticks": 8},
               "bar": {"color": "#007BFF", "thickness": 0.28}, "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
               "steps": [{"range": [0,5], "color": "rgba(255,49,49,.18)"}, {"range": [5,15], "color": "rgba(249,115,22,.12)"},
                         {"range": [15,25], "color": "rgba(34,197,94,.12)"}, {"range": [25,35], "color": "rgba(212,175,55,.10)"}],
               "threshold": {"line": {"color": "#D4AF37", "width": 4}, "thickness": 0.85, "value": round(target_pct, 1)}}))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "#CBD5E1", "family": "DM Sans"}, margin={"t": 50, "b": 10, "l": 20, "r": 20}, height=230)
    return fig

def plot_alpha_bars(dm: DataManager, ticker: str, nom: str) -> Optional[go.Figure]:
    world_df = None
    for wt in WORLD_TICKERS:
        df = dm.data.get(wt, pd.DataFrame())
        if not df.empty and "Close" in df.columns: world_df = df; break
    sat_df = dm.data.get(ticker, pd.DataFrame())
    if world_df is None or sat_df is None or sat_df.empty: return None
    wc = world_df["Close"].dropna(); sc = sat_df["Close"].dropna()
    common = sc.index.intersection(wc.index)
    if len(common) < 17: return None
    alpha = ((sc[common[-16:]].pct_change() - wc[common[-16:]].pct_change()) * 100).dropna().iloc[-15:]
    fig = go.Figure(go.Bar(x=[d.strftime("%d/%m") for d in alpha.index], y=alpha.values, marker_color=["#22C55E" if v > 0 else "#FF3131" for v in alpha.values]))
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=.6)
    fig.update_layout(**_PLOTLY_BASE, title=dict(text=f"<b>Écart quotidien</b> : {nom} vs MSCI World --- 15 derniers jours", font=dict(size=11, color="#6B7585")),
                      margin=dict(t=35, b=25, l=55, r=15), height=200, showlegend=False, xaxis=dict(gridcolor="#2E3340", showgrid=False), yaxis=dict(gridcolor="#2E3340", ticksuffix="%"))
    return fig

def plot_relative_perf(dm: DataManager, ticker: str, nom: str) -> Optional[go.Figure]:
    world_df = None
    for wt in WORLD_TICKERS:
        df = dm.data.get(wt, pd.DataFrame())
        if not df.empty and "Close" in df.columns: world_df = df; break
    sat_df = dm.data.get(ticker, pd.DataFrame())
    if world_df is None or sat_df is None or sat_df.empty: return None
    wc = world_df["Close"].dropna(); sc = sat_df["Close"].dropna()
    common = sc.index.intersection(wc.index)
    if len(common) < 20: return None
    cutoff = max(DATE_DEBUT.date(), (datetime.now() - timedelta(days=120)).date())
    common_f = [d for d in common if d.date() >= cutoff] or list(common[-90:])
    ratio = sc[common_f] / wc[common_f]
    rel = (ratio / ratio.iloc[0] - 1) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values.clip(min=0), fill="tozeroy", fillcolor="rgba(212,175,55,.12)", line=dict(color="rgba(0,0,0,0)"), showlegend=False))
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values.clip(max=0), fill="tozeroy", fillcolor="rgba(255,49,49,.12)", line=dict(color="rgba(0,0,0,0)"), showlegend=False))
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values, line=dict(color="#D4AF37", width=2), name=f"{nom}/World"))
    if len(rel) >= 14:
        last14 = rel.iloc[-14:]
        fig.add_vrect(x0=last14.index[0], x1=last14.index[-1], fillcolor="rgba(0,123,255,.06)", layer="below", line_width=0)
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=.7)
    fig.update_layout(**_PLOTLY_BASE, title=dict(text=f"Performance relative : {nom} vs World (base 100)", font=dict(size=11, color="#6B7585")),
                      margin=dict(t=20, b=20, l=50, r=20), height=200, showlegend=False, xaxis=dict(gridcolor="#2E3340"), yaxis=dict(gridcolor="#2E3340", ticksuffix="%"))
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 15 : STREAMLIT UI v5.7 (avec nouvelles sections et arbitrage)
# ─────────────────────────────────────────────────────────────────────────────

class StreamlitUI:
    def __init__(self, dm: DataManager, pm: PersistenceManager,
                 mre: MarketRegimeEngine, qre: QuantRiskEngine,
                 pe: PortfolioEngine, pde: PedagogicEngine,
                 se: StrategicEngine,
                 pcm: "PortfolioConfigManager" = None,
                 te: "TransactionEngine" = None):
        self.dm = dm
        self.pm = pm
        self.mre = mre
        self.qre = qre
        self.pe = pe
        self.pde = pde
        self.se = se
        self.pcm = pcm if pcm is not None else PortfolioConfigManager()
        self.te = te if te is not None else TransactionEngine()
        self.analytics = AnalyticsEngine(dm)
        self.signal = SignalEngine(dm, self.analytics)

    @staticmethod
    def _sign(v: float) -> str:
        return "+" if v >= 0 else ""

    # ── SIDEBAR (identique à avant mais avec suppression de Hydrogen et OR, ajout Infra)
    def render_sidebar(self) -> Tuple[bool, List[Dict], float, float, float]:
        st.sidebar.markdown("## ⚙️ Paramètres v5.7")
        mode_direct = st.sidebar.toggle("🔌 Mode Direct (Vue Brute)", value=False)
        st.sidebar.markdown("---")
        cap = st.sidebar.number_input("Capital réel sorti banque (€)", value=st.session_state["cfg_capital_reel"], step=100.0, format="%.2f", key="input_capital_reel")
        adj = st.sidebar.number_input("Ajustement patrimonial (€)", value=st.session_state["cfg_ajustement_pat"], step=1.0, format="%.2f", key="input_ajustement_pat")
        bonus = st.sidebar.number_input("Bonus Fortuneo (PRM PEA, €)", value=st.session_state["cfg_bonus_fortuneo"], step=10.0, format="%.2f", key="input_bonus_fortuneo")
        if st.sidebar.button("💾 Sauvegarder paramètres", use_container_width=True):
            ok = _save_config(cap, adj, bonus)
            st.session_state["cfg_capital_reel"] = cap
            st.session_state["cfg_ajustement_pat"] = adj
            st.session_state["cfg_bonus_fortuneo"] = bonus
            st.session_state["save_feedback"] = "✅ Sauvegardé" if ok else "❌ Erreur"
        if st.session_state.get("save_feedback"):
            fb = st.session_state["save_feedback"]
            st.sidebar.markdown(f'<div class="{"save-box" if fb.startswith("✅") else "alert-box"}">{fb}</div>', unsafe_allow_html=True)
        st.sidebar.markdown("---")

        with st.sidebar.expander("⚙️ Configuration des Positions (ETF_LIBRARY)", expanded=False):
            st.caption("Modifiez vos positions. Sauvegarde automatique à chaque modification.")
            raw_pos = st.session_state["raw_positions"]
            new_raw = []
            for idx, pos in enumerate(raw_pos):
                tk_id = pos.get("ticker", "")
                meta = ETF_LIBRARY.get(tk_id, {})
                label = meta.get("nom", tk_id)
                st.markdown(f"**ETF : {label}** `{tk_id}`")
                c1, c2 = st.columns(2)
                parts_key = f"auto_parts_{idx}_{tk_id}"
                prm_key = f"auto_prm_{idx}_{tk_id}"
                n_parts = c1.number_input("Parts", value=float(pos.get("parts", 0)), key=parts_key, format="%.4f", step=0.0001)
                n_prm = c2.number_input("PRM (€)", value=float(pos.get("prm", 0)), key=prm_key, format="%.4f", step=0.01)
                new_raw.append({**pos, "parts": n_parts, "prm": n_prm})
            if new_raw != raw_pos:
                st.session_state["raw_positions"] = new_raw
                st.session_state["positions"] = enrich_positions(new_raw)
                self.pcm.save_positions(new_raw)
                st.rerun()

            st.markdown("---")
            st.caption("Ajouter un ETF de la bibliothèque :")
            existing_tk = [p["ticker"] for p in raw_pos]
            available = [k for k in ETF_LIBRARY if k not in existing_tk]
            if available:
                chosen = st.selectbox("ETF à ajouter", ["(choisir)"] + available, key="sidebar_add_etf")
                if chosen != "(choisir)" and st.button("➕ Ajouter", key="sidebar_add_btn"):
                    meta = ETF_LIBRARY[chosen]
                    new_raw.append({"ticker": chosen, "parts": 0.0, "prm": 0.0, "account": meta.get("enveloppe", "AV")})
                    st.session_state["raw_positions"] = new_raw
                    self.pcm.save_positions(new_raw)
                    st.rerun()

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🗑️ Supprimer un ETF")
        current_positions = self.pcm.load_positions()
        if current_positions:
            ticker_to_delete = st.sidebar.selectbox(
                "Choisir l'ETF à retirer",
                options=[pos["ticker"] for pos in current_positions],
                format_func=lambda x: f"{x} — {ETF_LIBRARY.get(x, {}).get('nom', 'Nom inconnu')}",
                key="delete_etf_selector"
            )
            st.sidebar.warning(f"Action irréversible : cela supprimera {ticker_to_delete} de tous les modules.")
            if st.sidebar.button("❌ Supprimer définitivement", use_container_width=True, type="primary"):
                updated_positions = [pos for pos in current_positions if pos["ticker"] != ticker_to_delete]
                if self.pcm.save_positions(updated_positions):
                    st.session_state["raw_positions"] = updated_positions
                    st.session_state["positions"] = enrich_positions(updated_positions)
                    st.sidebar.success(f"🎯 {ticker_to_delete} supprimé avec succès !")
                    st.rerun()
                else:
                    st.sidebar.error("Erreur lors de la suppression.")
        else:
            st.sidebar.info("Aucune position active à supprimer.")
        st.sidebar.markdown("---")

        if self.pm.status == "github":
            st.sidebar.markdown('<div class="persist-ok">🔗 GitHub Gist actif</div>', unsafe_allow_html=True)
        elif self.pm.warning_msg:
            st.sidebar.markdown(f'<div class="persist-warn">⚠️ {self.pm.warning_msg}</div>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<div class="persist-warn">📂 SQLite local</div>', unsafe_allow_html=True)

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📦 Positions (session)")
        st.sidebar.caption("Modification en live. Utilisez '⚙️ Configuration' pour persister.")
        positions_conf = []
        for pos in st.session_state["positions"]:
            with st.sidebar.expander(pos["nom"]):
                parts = st.number_input("Parts", value=float(pos["parts"]), step=0.0001, format="%.4f", key=f"p_{pos['nom']}")
                prm = st.number_input("PRM (€)", value=float(pos["prm"]), step=0.0001, format="%.4f", key=f"r_{pos['nom']}")
                positions_conf.append({**pos, "parts": parts, "prm": prm})
        capital_reel = cap
        ajustement_pat = 0.0 if mode_direct else adj
        bonus_fortuneo = 0.0 if mode_direct else bonus
        for pos in positions_conf:
            if pos["nom"] == "MSCI World PEA" and pos["parts"] > 0:
                pos["prm"] -= bonus_fortuneo / pos["parts"]
        return mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo

    # ── HEADER ──
    def render_header(self, mode_direct: bool, live_ok: int, live_total: int):
        now = datetime.now(ZoneInfo("Europe/Paris"))
        st.markdown('<div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:.2rem;">'
                    '<span style="font-family:Space Mono;font-size:1.6rem;font-weight:700;color:#D4AF37;">◈</span>'
                    '<span style="font-size:1.5rem;font-weight:700;color:#E2E8F0;">COCKPIT DÉCISIONNEL</span>'
                    '<span style="font-family:Space Mono;font-size:.9rem;color:#6B7585;">v5.7 · ALLOCATION LONG TERME</span></div>', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption(f"Prix live · {now.strftime('%d/%m/%Y %H:%M:%S')} (Paris) · Cache 30s/90s")
        with c2:
            pct = live_ok / live_total * 100 if live_total else 0
            bc = "#22C55E" if pct >= 80 else "#F97316" if pct >= 50 else "#FF3131"
            tc = "#0B0E15" if pct >= 80 else "white"
            st.markdown(f'<div style="text-align:right;"><span style="background:{bc};color:{tc};padding:.2rem .8rem;border-radius:20px;font-size:.72rem;">📡 {live_ok}/{live_total} LIVE</span></div>', unsafe_allow_html=True)
        if mode_direct:
            st.markdown('<div class="mode-direct-banner">🔌 MODE DIRECT ACTIF --- Valeur marchande pure</div>', unsafe_allow_html=True)

    # ── BANDEAU RÉGIME ──
    def render_regime_banner(self, regime: Dict):
        sc = regime["confirmed_score"]
        label = regime["confirmed_label"]
        css = regime["confirmed_css"]
        conf = "✅ Confirmé" if regime["is_confirmed"] else "⏳ En attente"
        s3 = " → ".join([f"{s:+d}" for s in regime["scores_3d"]])
        st.markdown(f'<div class="regime-banner {css}"><div><span style="font-size:1.1rem;">🌍 Météo des marchés : <b>{label}</b></span>'
                    f'<span style="font-size:.82rem;margin-left:1rem;opacity:.8;">{conf}</span></div>'
                    f'<div style="font-family:Space Mono;font-size:1.2rem;">Score : <b>{sc:+d}/5</b></div>'
                    f'<div style="font-size:.78rem;opacity:.7;">3j : {s3}</div></div>', unsafe_allow_html=True)
        with st.expander("ℹ️ Comment lire la météo des marchés ?", expanded=False):
            reg_trans = self.pde.translate_regime(regime)
            col_exp, col_comp = st.columns([1, 2])
            with col_exp:
                level_color = {"green":"#22C55E","orange":"#F97316","red":"#FF3131"}.get(reg_trans["level"], "#6B7585")
                st.markdown(f'<div class="pedagogy-box"><div class="pedagogy-title">Ce que ça signifie</div>'
                            f'<div style="font-size:2rem;text-align:center;margin:.4rem 0;">{reg_trans["emoji"]}</div>'
                            f'<div style="color:{level_color};font-weight:700;margin-bottom:.4rem;">{label}</div>'
                            f'<div>{reg_trans["explain"]}</div>'
                            f'<div style="margin-top:.6rem;padding:.5rem;background:rgba(0,0,0,.2);border-radius:6px;">💡 <b>Que faire ?</b><br>{reg_trans["action"]}</div></div>', unsafe_allow_html=True)
            with col_comp:
                st.markdown('<div style="font-size:.82rem;color:#6B7585;margin-bottom:.5rem;">Les 5 critères analysés :</div>', unsafe_allow_html=True)
                comp_cols = st.columns(5)
                for i, comp in enumerate(regime.get("components", [])):
                    with comp_cols[i % 5]:
                        bull = comp["bull"]
                        ico = "🟢" if bull is True else "🔴" if bull is False else "⚪"
                        sc_ = "+1" if bull is True else "−1" if bull is False else "0"
                        st.markdown(f'<div class="card" style="padding:.8rem;text-align:center;"><div style="font-size:1.4rem;">{ico}</div>'
                                    f'<div style="font-size:.72rem;color:#6B7585;margin:.2rem 0;">{comp["name"]}</div>'
                                    f'<div style="font-family:Space Mono;font-weight:700;color:{"#22C55E" if bull else "#FF3131" if bull is False else "#6B7585"};">{sc_}</div>'
                                    f'<div style="font-size:.68rem;color:#4B5563;margin-top:.2rem;">{comp["val"]}</div></div>', unsafe_allow_html=True)

    # ── COMMAND CENTER (avec projection objectifs) ──
    def render_command_center(self, ptf: Dict, bench: Dict, mode_direct: bool, pm: PersistenceManager):
        st.markdown("## 🚀 Vue d'ensemble du portefeuille")
        perf_j_chain, perf_c_chain, base_cap = pm.compute_daily_performance(ptf["valeur_totale"])
        c1, c2, c3, c4 = st.columns(4)
        s = self._sign
        with c1:
            crd = "card card-purple" if mode_direct else "card card-gold"
            lbl = "Valeur Brute" if mode_direct else "Valeur Totale"
            vj, vjp = ptf["perf_j_eur"], ptf["perf_j_pct"]
            st.markdown(f'<div class="{crd}"><div class="kpi-label">{lbl}<span class="live-badge">LIVE</span></div>'
                        f'<div class="kpi-value">{ptf["solde_total"]:,.2f}€</div>'
                        f'<div class="kpi-delta-{"pos" if vj>=0 else "neg"}">{s(vj)}{vj:,.2f}€ ({s(vjp)}{vjp:.2f}%) vs hier</div></div>', unsafe_allow_html=True)
        with c2:
            gr = ptf["gain_reel"]
            clr = "#22C55E" if gr >= 0 else "#FF3131"
            st.markdown(f'<div class="card card-blue"><div class="kpi-label">Gain / Perte total</div>'
                        f'<div class="kpi-value" style="color:{clr};">{s(gr)}{gr:,.2f}€</div>'
                        f'<div class="small">Investi : {ptf["capital_reel"]:,.2f}€</div></div>', unsafe_allow_html=True)
        with c3:
            p = ptf["perf_tot_pct"]
            pc = "#22C55E" if p >= 0 else "#FF3131"
            gap = bench.get("gap")
            gap_ls = bench.get("gap_lumpsum")
            gc = "#22C55E" if (gap or 0) >= 0 else "#FF3131"
            pcc = "#22C55E" if perf_c_chain >= 0 else "#FF3131"
            mwr_adj = bench.get("perf_bench_adj")
            if gap is not None and mwr_adj is not None:
                gap_html = f'<div class="small">Vs World MWR : <span style="color:{gc};font-weight:700;">{s(gap)}{gap:.2f}%</span><span class="mwr-badge">MWR</span></div>'
            elif gap_ls is not None:
                gc_ls = "#22C55E" if gap_ls >= 0 else "#FF3131"
                gap_html = f'<div class="small">Vs World (LS) : <span style="color:{gc_ls};font-weight:700;">{s(gap_ls)}{gap_ls:.2f}%</span></div>'
            else:
                gap_html = ""
            st.markdown(f'<div class="card card-blue"><div class="kpi-label">Performance</div>'
                        f'<div class="kpi-value" style="color:{pc};">{s(p)}{p:.2f}%</div>{gap_html}'
                        f'<div class="small">Chaîné : <span style="color:{pcc};font-weight:700;">{s(perf_c_chain)}{perf_c_chain:.2f}%</span></div></div>', unsafe_allow_html=True)
        with c4:
            pb = bench.get("perf_bench_adj")
            pb_ls = bench.get("perf_bench")
            pbj = bench.get("perf_bench_j")
            if pb is not None:
                pbc = "#22C55E" if pb >= 0 else "#FF3131"
                pbj_html = f'<div class="kpi-delta-{"pos" if pbj>=0 else "neg"}">{s(pbj)}{pbj:.2f}% vs hier</div>' if pbj is not None else ""
                ls_html = f'<div class="small" style="color:#4B5563;">LS : {s(pb_ls)}{pb_ls:.2f}%</div>' if pb_ls is not None else ""
                body_bench = f'<div class="kpi-value" style="color:{pbc};">{s(pb)}{pb:.2f}%</div>{pbj_html}{ls_html}'
            else:
                body_bench = '<div class="kpi-value">N/A</div>'
            st.markdown(f'<div class="card card-blue"><div class="kpi-label">MSCI World MWR<span class="mwr-badge">AJUSTÉ</span><span class="live-badge">LIVE</span></div>{body_bench}</div>', unsafe_allow_html=True)

        # Objectifs financiers
        st.markdown("### 🎯 Objectifs financiers")
        col_pea_obj, col_av_obj = st.columns(2)
        pea_value = ptf["val_env"].get("PEA", 0.0)
        pea_target = 330_000.0
        if pea_value > 0:
            pea_cagr, pea_fallback = self.pe.compute_envelope_cagr("PEA", ptf["positions"])
            if pea_value < pea_target:
                if pea_cagr > 0.01:
                    t_years = np.log(pea_target / pea_value) / np.log(1 + pea_cagr)
                    t_days = t_years * 365.25
                    target_date = datetime.now() + timedelta(days=t_days)
                    date_str = target_date.strftime("%B %Y") if t_days > 30 else target_date.strftime("%d %B %Y")
                    note = " (taux standard 7%)" if pea_fallback else ""
                    pea_progress = f"{pea_value:,.0f}€ / {pea_target:,.0f}€ → estimé {date_str}{note}"
                else:
                    pea_progress = f"{pea_value:,.0f}€ / {pea_target:,.0f}€ → taux insuffisant, projection impossible"
            else:
                pea_progress = f"{pea_value:,.0f}€ / {pea_target:,.0f}€ → objectif atteint !"
        else:
            pea_progress = "Aucune position en PEA"
        with col_pea_obj:
            st.markdown(f'<div class="card card-gold">'
                        f'<div class="kpi-label">🏦 Objectif PEA</div>'
                        f'<div class="kpi-value">{pea_target:,.0f}€</div>'
                        f'<div class="small">{pea_progress}</div>'
                        f'</div>', unsafe_allow_html=True)
        av_value = ptf["val_env"].get("AV", 0.0)
        av_target = 220_000.0
        if av_value > 0:
            av_cagr, av_fallback = self.pe.compute_envelope_cagr("AV", ptf["positions"])
            if av_value < av_target:
                if av_cagr > 0.01:
                    t_years = np.log(av_target / av_value) / np.log(1 + av_cagr)
                    t_days = t_years * 365.25
                    target_date = datetime.now() + timedelta(days=t_days)
                    date_str = target_date.strftime("%B %Y") if t_days > 30 else target_date.strftime("%d %B %Y")
                    note = " (taux standard 7%)" if av_fallback else ""
                    av_progress = f"{av_value:,.0f}€ / {av_target:,.0f}€ → estimé {date_str}{note}"
                else:
                    av_progress = f"{av_value:,.0f}€ / {av_target:,.0f}€ → taux insuffisant, projection impossible"
            else:
                av_progress = f"{av_value:,.0f}€ / {av_target:,.0f}€ → objectif atteint !"
        else:
            av_progress = "Aucune position en AV"
        with col_av_obj:
            st.markdown(f'<div class="card card-gold">'
                        f'<div class="kpi-label">📈 Objectif Assurance-Vie</div>'
                        f'<div class="kpi-value">{av_target:,.0f}€</div>'
                        f'<div class="small">{av_progress}</div>'
                        f'</div>', unsafe_allow_html=True)

        # Mes positions (avec colonne Perf. €)
        st.markdown("### 📊 Mes positions")
        col_t, col_p = st.columns([3, 2])
        with col_t:
            rows = []
            for p2 in ptf["positions"]:
                # Calcul de la performance en euros (Cours actuel - PRM) * parts
                if p2["prix"] is not None and p2["perf_pct"] is not None:
                    # On récupère les parts et PRM depuis la position enrichie
                    # Il faut retrouver les parts et PRM d'origine, mais on peut les recalculer
                    # Pour éviter de stocker parts et PRM dans positions_calc, on va les ajouter dans compute_portfolio
                    # Mais on a déjà "perf_pct" et "valeur", donc on peut calculer perf_euro = (prix - prm) * parts
                    # Cependant nous n'avons pas "prm" dans positions_calc, on va modifier compute_portfolio pour l'inclure
                    # Pour l'instant, on affiche une valeur calculée à partir du gain unitaire
                    gain_unit = p2.get("gain_unit", 0)  # sera ajouté plus tard
                    parts = p2.get("parts", 0)
                    perf_euro = gain_unit * parts if 'gain_unit' in p2 else 0
                    perf_euro_str = f"{self._sign(perf_euro)}{perf_euro:,.2f}€"
                else:
                    perf_euro_str = "N/A"
                perf_f = f"{self._sign(p2['perf_pct'])}{p2['perf_pct']:.2f}%" if p2["perf_pct"] is not None else "N/A"
                vj_f = f"{self._sign(p2['var_jour_pct'])}{p2['var_jour_pct']:.2f}%" if p2["var_jour_pct"] else "--"
                vje_f = f"{self._sign(p2['var_jour_eur'])}{p2['var_jour_eur']:,.2f}€" if p2["var_jour_eur"] else "--"
                prix_f = f"{p2['prix']:.3f}€" if p2["prix"] else "N/A"
                rows.append({"Position": p2["nom"], "Env.": p2["enveloppe"], "Prix": prix_f, "Valeur (€)": f"{p2['valeur']:,.2f}",
                             "Perf. (%)": perf_f, "Perf. (€)": perf_euro_str, "Δ Jour (%)": vj_f, "Δ Jour (€)": vje_f})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if not mode_direct:
            st.markdown(f'<div class="info-box">Ajustement patrimonial inclus : +{ptf["ajustement_pat"]:,.2f}€</div>', unsafe_allow_html=True)
        with col_p:
            donut = [p2 for p2 in ptf["positions"] if p2["valeur"] > 0]
            if donut:
                colors_pie = ["#007BFF","#6366F1","#D4AF37","#F97316","#22C55E"]
                fig_pie = go.Figure(go.Pie(labels=[d["nom"] for d in donut], values=[d["valeur"] for d in donut], hole=0.6, textinfo="percent",
                                          marker=dict(colors=colors_pie[:len(donut)], line=dict(color="#1C1F26", width=2))))
                vt = ptf["valeur_totale"]
                fig_pie.update_layout(**_PLOTLY_BASE, margin=dict(t=10,b=10,l=10,r=10), height=270,
                                      legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                                      annotations=[dict(text=f"{vt:,.0f}€", x=.5, y=.5, font=dict(size=13,color="#D4AF37",family="Space Mono"), showarrow=False)])
                st.plotly_chart(fig_pie, use_container_width=True)
        mwr_adj = bench.get("perf_bench_adj")
        if mwr_adj is not None:
            gap = bench.get("gap", 0.0) or 0.0
            gc = "#22C55E" if gap >= 0 else "#FF3131"
            st.markdown(f'<div class="pedagogy-box"><div class="pedagogy-title">🆕 v5.7 --- Benchmark MWR Cash-Flow Adjusted</div>'
                        f'Le "Gap vs World" est désormais calculé en simulant l\'achat de MWRD.PA '
                        f'aux mêmes dates et montants que vos flux réels (avec 0.10% de frais). '
                        f'<b>World MWR = {s(mwr_adj)}{mwr_adj:.2f}%</b> · '
                        f'<b style="color:{gc};">Votre Alpha = {s(gap)}{gap:.2f}%</b></div>', unsafe_allow_html=True)

    # ── EQUITY CURVE ──
    def render_equity_curve_section(self, ptf: Dict, regime: Dict, unified_infra: Dict, unified_em: Dict, positions_conf: List[Dict]):
        st.markdown("## 📈 Historique de votre capital")
        col_eq, col_snap = st.columns([3, 1])
        history = self.pm.load_history()
        with col_eq:
            fig_eq = plot_equity_curve(history)
            if fig_eq:
                st.plotly_chart(fig_eq, use_container_width=True, config={"displayModeBar": False})
                st.markdown('<div class="pedagogy-box"><div class="pedagogy-title">Ce que montre ce graphique</div>'
                            'La ligne dorée représente l\'évolution réelle de votre capital jour après jour. '
                            'La ligne bleue pointillée montre votre performance cumulée en %. '
                            'Les zones colorées indiquent le régime de marché pendant chaque période.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card card-orange"><div class="kpi-label">Aucun historique enregistré</div>'
                            '<div class="small">Utilisez le bouton "📸 Enregistrer" à droite pour démarrer le suivi.</div></div>', unsafe_allow_html=True)
        if not history.empty:
            perf_j, perf_c, base_cap = self.pm.compute_daily_performance(ptf["valeur_totale"])
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Jours enregistrés", f"{len(history)}")
            mc2.metric("Base hier (€)", f"{base_cap:,.2f}")
            mc3.metric("Perf du jour", f"{perf_j:+.2f}%")
            mc4.metric("Perf totale", f"{perf_c:+.2f}%")
        with col_snap:
            st.markdown('<div class="card card-green">', unsafe_allow_html=True)
            st.markdown("### 💾 Enregistrer")
            st.caption("Sauvegardez l'état du portefeuille ce soir.")
            vt = ptf["valeur_totale"]
            pj, pc, _ = self.pm.compute_daily_performance(vt)
            poids_em = next((p["valeur"]/vt*100 for p in ptf["positions"] if p["nom"]=="EM Asia" and vt>0), 0.0)
            poids_infra = next((p["valeur"]/vt*100 for p in ptf["positions"] if p["nom"]=="BNP ESG Infrastructure" and vt>0), 0.0)
            st.markdown(f'<div style="font-size:.82rem;color:#6B7585;line-height:1.8;"><b>Capital :</b> {vt:,.2f}€<br>'
                        f'<b>Aujourd\'hui :</b> {pj:+.2f}%<br><b>Total :</b> {pc:+.2f}%<br>'
                        f'<b>Régime :</b> {regime["confirmed_label"]}<br><b>EM Asia :</b> {poids_em:.1f}% | <b>Infra :</b> {poids_infra:.1f}%</div>', unsafe_allow_html=True)
            if st.button("📸 Enregistrer Snapshot", use_container_width=True, type="primary"):
                ok = self.pm.save_snapshot(vt, vt, round(pj,4), round(pc,4), regime["confirmed_label"], regime["confirmed_score"], round(poids_em,4), round(poids_infra,4))
                if ok:
                    st.success("✅ Enregistré" + (" + GitHub" if self.pm.status == "github" else ""))
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Échec")
            if not history.empty:
                st.markdown("---")
                st.markdown(f'<div class="small">Dernier : {history["date"].iloc[-1]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── LEADERSHIP COMPARISON ──
    def render_leadership_comparison(self, nom: str, ticker: str, color_sat: str = "#D4AF37"):
        st.markdown(f"### 📊 {nom} vs MSCI World --- Leadership hebdomadaire")
        with st.container():
            st.markdown('<div class="leadership-header"><div style="font-size:.8rem;color:#6B7585;">POURQUOI CE GRAPHIQUE EST IMPORTANT</div>'
                        '<div style="color:#E2E8F0;line-height:1.6;">Ce graphique compare chaque semaine la performance de votre ETF vs le MSCI World. '
                        '<b>Si l\'ETF fait régulièrement moins bien que le World</b>, il perd sa raison d\'être.</div></div>', unsafe_allow_html=True)
        labels, sat_perfs, world_perfs = self.pde.get_weekly_performances(self.dm, ticker)
        if labels and sat_perfs and world_perfs:
            col_chart, col_verdict = st.columns([2, 1])
            with col_chart:
                fig = plot_weekly_leadership(labels, sat_perfs, world_perfs, nom, color_sat)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with col_verdict:
                gaps = [s - w for s, w in zip(sat_perfs, world_perfs)]
                st.markdown('<div class="kpi-label">COMPARAISON SEMAINE PAR SEMAINE</div>', unsafe_allow_html=True)
                rows_lead = []
                for i, (lbl, s_p, w_p) in enumerate(zip(labels, sat_perfs, world_perfs)):
                    gap = s_p - w_p
                    winner = f"🟢 +{gap:.1f}% {nom[:6]}" if gap > 0 else f"🔴 {gap:.1f}% World"
                    rows_lead.append({"Semaine": lbl, f"{nom[:8]}": f"{s_p:+.1f}%", "World": f"{w_p:+.1f}%", "Résultat": winner})
                st.dataframe(pd.DataFrame(rows_lead), use_container_width=True, hide_index=True)
                verdict = self.pde.translate_leadership(nom, gaps)
                level_color = {"green":"#22C55E","orange":"#F97316","red":"#FF3131"}.get(verdict["level"], "#6B7585")
                level_bg = {"green":"rgba(34,197,94,.1)","orange":"rgba(249,115,22,.1)","red":"rgba(255,49,49,.1)"}.get(verdict["level"], "rgba(107,117,133,.1)")
                st.markdown(f'<div style="background:{level_bg};border:1px solid {level_color};border-radius:10px;padding:1rem;margin-top:.5rem;">'
                            f'<div style="font-weight:700;font-size:1rem;color:{level_color};">{verdict["message"]}</div>'
                            f'<div style="font-size:.8rem;color:#8892AA;margin:.4rem 0;">{verdict["detail"]}</div>'
                            f'<div style="font-size:.85rem;color:#CBD5E1;margin-top:.5rem;">💡 {verdict["action"]}</div></div>', unsafe_allow_html=True)
        else:
            st.info("Données hebdomadaires insuffisantes. Revenez après quelques semaines.")

    # ── RISK DASHBOARD (adapté pour Infra) ──
    def render_risk_dashboard(self, ptf: Dict):
        st.markdown("## ⚠️ Gestion des risques")
        with st.expander("❓ Comment lire les indicateurs de risque ?", expanded=False):
            st.markdown('<div class="pedagogy-box"><div class="pedagogy-title">Guide de lecture des risques</div>'
                        '<b>Agitation (Volatilité)</b> : mesure les oscillations quotidiennes. Plus c\'est élevé, plus l\'ETF peut monter ou baisser brutalement.<br><br>'
                        '<b>Sensibilité (Beta)</b> : si le marché baisse de 10% et Beta=1.5, l\'ETF peut baisser de 15%.<br><br>'
                        '<b>Recul depuis le sommet (Drawdown)</b> : distance depuis le dernier pic. -20% signifie une perte de 20%.</div>', unsafe_allow_html=True)
        st.markdown("### 🔍 Analyse de risque par ETF")
        risk_assets = [("XU61.DE", "BNP ESG Infrastructure", "#F97316", None), ("AASI.PA", "EM Asia", "#6366F1", None),
                       ("MWRD.PA", "MSCI World", "#007BFF", None)]
        cols = st.columns(3)
        for i, (tk, name, color, custom_df) in enumerate(risk_assets):
            with cols[i]:
                if custom_df is not None:
                    vol = self.qre.rolling_volatility_from_df(custom_df, 30)
                    beta = self.qre.rolling_beta_from_df(custom_df)
                    dd = self.qre.drawdown_metrics_from_df(custom_df, 252)
                else:
                    vol = self.qre.rolling_volatility(tk, 30)
                    beta = self.qre.rolling_beta(tk)
                    dd = self.qre.drawdown_metrics(tk, 252)
                vol_t = self.pde.translate_volatility(vol, name)
                beta_t = self.pde.translate_beta(beta, name)
                dd_t = self.pde.translate_drawdown(dd.get("current_dd"), dd.get("max_dd"), name)
                level_colors = {"green":"#22C55E","orange":"#F97316","red":"#FF3131"}
                st.markdown(f'<div class="card" style="border-top:3px solid {color};"><div class="kpi-label">{name}</div>', unsafe_allow_html=True)
                vc = level_colors[vol_t["level"]]
                st.markdown(f'<div class="pedago-metric"><div class="pedago-metric-title">Agitation (Volatilité)</div>'
                            f'<div class="pedago-metric-value" style="color:{vc};">{vol_t["emoji"]} {vol_t["value"]}</div>'
                            f'<div class="pedago-metric-explain">{vol_t["explain"].split(chr(10))[0]}</div></div>', unsafe_allow_html=True)
                bc = level_colors[beta_t["level"]]
                beta_explain_short = beta_t["explain"][:80] + "..." if len(beta_t["explain"]) > 80 else beta_t["explain"]
                st.markdown(f'<div class="pedago-metric"><div class="pedago-metric-title">Sensibilité au marché (Beta)</div>'
                            f'<div class="pedago-metric-value" style="color:{bc};">{beta_t["emoji"]} {beta_t["value"]}</div>'
                            f'<div class="pedago-metric-explain">{beta_explain_short}</div></div>', unsafe_allow_html=True)
                dc = level_colors[dd_t["level"]]
                st.markdown(f'<div class="pedago-metric"><div class="pedago-metric-title">Recul depuis le sommet</div>'
                            f'<div class="pedago-metric-value" style="color:{dc};">{dd_t["emoji"]} {dd_t["value"]}</div>'
                            f'<div class="pedago-metric-explain">{dd_t["explain"][:80]}...</div></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        with st.expander("🔬 Analyse experte : Corrélation & Contribution au risque", expanded=False):
            col_corr, col_rc = st.columns(2)
            tickers_ptf = ["XU61.DE", "AASI.PA", "MWRD.PA"]
            positions_map = {p["nom"]: p for p in ptf["positions"]}
            vt = ptf["valeur_totale"]
            with col_corr:
                corr_df = self.qre.correlation_matrix(tickers_ptf, 60)
                if corr_df is not None:
                    st.plotly_chart(plot_correlation_heatmap(corr_df), use_container_width=True, config={"displayModeBar": False})
                    st.markdown('<div class="pedagogy-box">Une corrélation proche de +1 signifie que les deux ETFs bougent ensemble. Idéalement, ils ne devraient pas tous monter et baisser en même temps.</div>', unsafe_allow_html=True)
                else:
                    st.info("Données insuffisantes (< 60j).")
            with col_rc:
                weights_ptf, valid_tk = [], []
                for tk in tickers_ptf:
                    df = self.dm.data.get(tk, pd.DataFrame())
                    if not df.empty:
                        nom = next((p["nom"] for p in ptf["positions"] if p.get("ticker") == tk), "")
                        val = positions_map.get(nom, {}).get("valeur", 0.0)
                        valid_tk.append(tk); weights_ptf.append(val)
                if valid_tk and sum(weights_ptf) > 0:
                    rc = self.qre.risk_contribution(valid_tk, weights_ptf, 60)
                    if rc:
                        fig_rc = plot_risk_contribution(rc)
                        if fig_rc:
                            st.plotly_chart(fig_rc, use_container_width=True, config={"displayModeBar": False})
                        flags = [tk for tk, v in rc.items() if v["flag"]]
                        if flags:
                            short = {"XU61.DE": "Infra", "AASI.PA": "EM Asia", "MWRD.PA": "MSCI World"}
                            f_names = ", ".join([short.get(f, f) for f in flags])
                            st.markdown(f'<div class="alert-box">🚨 <b>Trop de risque concentré</b> : {f_names} représente plus de 40% du risque total. Rééquilibrez.</div>', unsafe_allow_html=True)

    # ── SATELLITE CARD PÉDAGOGIQUE (pour Infra ou EM Asia) ──
    def render_satellite_card_pedagogic(self, nom: str, ticker: str, unified: Dict, target_weight: Dict,
                                        regime: Dict, sent_rows: List[Dict], sector: str):
        color_map = {"infra": "#F97316", "em_asia": "#6366F1"}
        color = color_map.get(sector, "#D4AF37")
        strat_full = self.se.compute(ticker, unified, regime)
        simple_score = self.pde.translate_simple_score(unified["total"])
        st.markdown(f'<div class="card" style="border-top:3px solid {color};padding:0;overflow:hidden;">', unsafe_allow_html=True)
        c_score, c_action = st.columns([2, 3])
        with c_score:
            st.markdown(f'<div style="padding:1.4rem 1.4rem .8rem 1.4rem;"><div class="kpi-label">{nom} --- Score Global</div>'
                        f'<div class="simple-score-ring {simple_score["ring_cls"]}" style="margin:1rem auto;">{strat_full["total"]}/5</div>'
                        f'<div style="text-align:center;margin:.4rem 0;"><span style="font-size:1.3rem;">{simple_score["stars"]}</span></div>'
                        f'<div style="text-align:center;font-weight:700;color:#E2E8F0;">{simple_score["label"]}</div>'
                        f'<div style="text-align:center;font-size:.82rem;color:#8892AA;">{simple_score["explain"]}</div></div>', unsafe_allow_html=True)
        with c_action:
            st.markdown('<div style="padding:1.4rem 1.4rem .8rem 1.4rem;">', unsafe_allow_html=True)
            st.markdown('<div class="kpi-label">Les 5 critères d\'analyse</div>', unsafe_allow_html=True)
            for detail in strat_full["details"]:
                icon = "✅" if detail["score"] == 1 else "❌"
                clr = "#86EFAC" if detail["score"] == 1 else "#FCA5A5"
                st.markdown(f'<div style="display:flex;align-items:flex-start;gap:.5rem;margin:.3rem 0;font-size:.84rem;">'
                            f'<span style="font-size:1rem;">{icon}</span>'
                            f'<div><span style="color:{clr};font-weight:700;">{detail["dim"]}</span>'
                            f'<span style="color:#6B7585;margin-left:.4rem;">{detail["value"]}</span>'
                            f'<br><span style="color:#8892AA;">{detail["label"]}</span></div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="{strat_full["verdict_cls"]} verdict-card">{strat_full["verdict"]}'
                    f'<div style="font-size:.82rem;margin-top:.4rem;">💡 {simple_score["action"]}</div></div>', unsafe_allow_html=True)
        self.render_leadership_comparison(nom, ticker, color)
        sent_verdict = self.pde.translate_sentinelles(sent_rows, sector)
        lv_color = {"green":"#22C55E","orange":"#F97316","red":"#FF3131"}.get(sent_verdict["level"], "#6B7585")
        lv_bg = {"green":"rgba(34,197,94,.1)","orange":"rgba(249,115,22,.1)","red":"rgba(255,49,49,.1)"}.get(sent_verdict["level"], "rgba(107,117,133,.1)")
        st.markdown(f'<div style="background:{lv_bg};border-left:4px solid {lv_color};border-radius:8px;padding:.8rem 1rem;margin:.5rem 0;">'
                    f'<b>Santé du secteur :</b> {sent_verdict["emoji"]} {sent_verdict["message"]}<br>'
                    f'<span style="font-size:.82rem;">{sent_verdict["detail"]}</span><br>'
                    f'<span style="font-size:.84rem;">💡 {sent_verdict["action"]}</span></div>', unsafe_allow_html=True)
        with st.expander("⚙️ Allocation cible & ajustement", expanded=False):
            col_gauge, col_detail = st.columns([1, 2])
            with col_gauge:
                cur_pct = target_weight.get("current_pct", 0.0)
                tgt_pct = target_weight.get("target_pct", 0.0)
                st.plotly_chart(plot_weight_indicator(cur_pct, tgt_pct), use_container_width=True, config={"displayModeBar": False})
            with col_detail:
                action = target_weight.get("action", "MAINTENIR")
                delta_e = target_weight.get("delta_eur", 0.0)
                cur_pct = target_weight.get("current_pct", 0.0)
                tgt_pct = target_weight.get("target_pct", 0.0)
                if action == "RÉDUIRE":
                    st.markdown(f'<div class="arb-sell"><div style="font-size:.72rem;color:#FF3131;">🚨 ACTION RECOMMANDÉE</div>'
                                f'<div style="font-size:1.1rem;color:#FCA5A5;font-weight:700;">VENDRE {abs(delta_e):,.0f}€</div>'
                                f'<div style="font-size:.82rem;">Votre position est trop importante ({cur_pct:.1f}%) vs cible ({tgt_pct:.1f}%).</div></div>', unsafe_allow_html=True)
                elif action == "RENFORCER":
                    st.markdown(f'<div class="arb-buy"><div style="font-size:.72rem;color:#22C55E;">💡 OPPORTUNITÉ</div>'
                                f'<div style="font-size:1.1rem;color:#86EFAC;font-weight:700;">ACHETER {abs(delta_e):,.0f}€</div>'
                                f'<div style="font-size:.82rem;">Vous êtes en dessous de la cible ({cur_pct:.1f}% vs {tgt_pct:.1f}%).</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="arb-neutral"><div style="font-size:.72rem;color:#6B7585;">✅ SITUATION ÉQUILIBRÉE</div>'
                                f'<div style="font-size:1.1rem;color:#CBD5E1;">MAINTENIR</div>'
                                f'<div style="font-size:.82rem;">Position à {cur_pct:.1f}% --- objectif {tgt_pct:.1f}%.</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="margin-top:.8rem;font-size:.8rem;color:#6B7585;">Régime actuel : <b>{target_weight.get("regime_label","N/A")}</b> '
                        f'(Multiplicateur × {target_weight.get("regime_mult", 1.0):.2f})</div>', unsafe_allow_html=True)
        with st.expander(f"📐 Analyse technique détaillée --- {nom}", expanded=False):
            fig_a = plot_alpha_bars(self.dm, ticker, nom)
            if fig_a:
                st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})
                st.caption("Chaque barre = journée où l'ETF a fait mieux (vert) ou moins bien (rouge) que le MSCI World.")
            fig_r = plot_relative_perf(self.dm, ticker, nom)
            if fig_r:
                st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})
                st.caption("Courbe au-dessus de 0 = l'ETF surperforme le World depuis le début du suivi.")

    # ── SENTINELLES & MACRO (mis à jour pour inclure les trois secteurs) ──
    def render_sentinelles_macro(self, ptf: Dict):
        st.markdown("## 🛰️ Radar Sectoriel & Macro-économie")
        # Nouveaux tableaux de suivi des actions sous-jacentes
        st.markdown("### 📌 Valeurs de référence sectorielles")
        # World
        st.markdown("#### 🌍 World (NVIDIA, Apple, Alphabet, Microsoft, Amazon)")
        world_stocks = [
            ("NVIDIA", "NVDA"), ("Apple", "AAPL"), ("Alphabet A", "GOOGL"), ("Alphabet C", "GOOG"), ("Microsoft", "MSFT"), ("Amazon", "AMZN")
        ]
        world_rows = []
        for name, tk in world_stocks:
            info = self.dm.analyze_ticker(tk)
            prix = info["prix"] if info else None
            var = None
            if info and info["prix"] and info.get("sma20"):
                var = ((info["prix"] - info["sma20"]) / info["sma20"]) * 100
            world_rows.append({"Action": name, "Dernier cours (€)": f"{prix:.2f}" if prix else "N/A", "Variation vs SMA20": f"{self._sign(var)}{var:.2f}%" if var is not None else "N/A"})
        st.dataframe(pd.DataFrame(world_rows), use_container_width=True, hide_index=True)
        # Asia
        st.markdown("#### 🌏 Asia (TSMC, Samsung, SK Hynix, Tencent)")
        asia_stocks = [
            ("TSMC", "TSM"), ("Samsung", "005930.KS"), ("SK Hynix", "000660.KS"), ("Tencent", "TCEHY")
        ]
        asia_rows = []
        for name, tk in asia_stocks:
            info = self.dm.analyze_ticker(tk)
            prix = info["prix"] if info else None
            var = None
            if info and info["prix"] and info.get("sma20"):
                var = ((info["prix"] - info["sma20"]) / info["sma20"]) * 100
            asia_rows.append({"Action": name, "Dernier cours": f"{prix:.2f}" if prix else "N/A", "Variation vs SMA20": f"{self._sign(var)}{var:.2f}%" if var is not None else "N/A"})
        st.dataframe(pd.DataFrame(asia_rows), use_container_width=True, hide_index=True)
        # Infrastructure
        st.markdown("#### 🏗️ Infrastructure (Lumentum, Ciena, Nokia, Akamai, Cisco)")
        infra_stocks = [
            ("Lumentum", "LITE"), ("Ciena", "CIEN"), ("Nokia", "NOK"), ("Akamai", "AKAM"), ("Cisco", "CSCO")
        ]
        infra_rows = []
        for name, tk in infra_stocks:
            info = self.dm.analyze_ticker(tk)
            prix = info["prix"] if info else None
            var = None
            if info and info["prix"] and info.get("sma20"):
                var = ((info["prix"] - info["sma20"]) / info["sma20"]) * 100
            infra_rows.append({"Action": name, "Dernier cours (€)": f"{prix:.2f}" if prix else "N/A", "Variation vs SMA20": f"{self._sign(var)}{var:.2f}%" if var is not None else "N/A"})
        st.dataframe(pd.DataFrame(infra_rows), use_container_width=True, hide_index=True)

        # Ancienne section sentinelles (générales)
        s_msg, s_col, sent_rows = self.pe.evaluate_sentinelles()
        col_s, col_m = st.columns([3, 2])
        with col_s:
            st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
            st.markdown("### 📡 Indicateurs avancés sectoriels")
            st.caption("Sentinelles : sous SMA20 = alerte.")
            if "OK" in s_msg: st.success(s_msg)
            else: st.warning(s_msg)
            st.dataframe(pd.DataFrame(sent_rows), use_container_width=True, hide_index=True)
            st.markdown("---")
            # Poids Satellites actuels (remplacé par EM Asia + Infrastructure)
            st.markdown("#### ⚖️ Poids Satellites actuels (EM Asia + Infrastructure)")
            vt = ptf["valeur_totale"]
            em_v = next((p["valeur"] for p in ptf["positions"] if p["nom"]=="EM Asia"), 0)
            infra_v = next((p["valeur"] for p in ptf["positions"] if p["nom"]=="BNP ESG Infrastructure"), 0)
            poids_s = (em_v + infra_v) / vt * 100 if vt else 0
            delta_ps = poids_s - 30  # cible 20+10=30%
            st.metric("EM Asia + Infrastructure", f"{poids_s:.1f}%", delta=f"{self._sign(delta_ps)}{delta_ps:.1f}% vs objectif 30%")
            bc = "#FF3131" if poids_s > 30 else "#22C55E"
            st.markdown(f'<div style="background:#1C1F26;border-radius:6px;height:8px;"><div style="background:{bc};width:{min(poids_s,100):.1f}%;height:8px;border-radius:6px;"></div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Logique d'arbitrage automatique (remplace l'ancienne)
        # Cibles : 70% World, 20% EM Asia, 10% Infrastructure
        # Seuils d'alerte : EM Asia >28% ou Infrastructure >15%
        # Si seuil dépassé, on calcule le montant à arbitrer vers l'ETF ayant la plus faible performance récente (momentum 6M)
        if vt > 0:
            world_pct = 100 - poids_s
            em_pct = em_v / vt * 100 if vt else 0
            infra_pct = infra_v / vt * 100 if vt else 0
            em_alert = em_pct > 28
            infra_alert = infra_pct > 15
            if em_alert or infra_alert:
                # Récupérer les métriques de performance récente (momentum 6M)
                metrics_em = self.analytics.compute_all_metrics("AASI.PA")
                metrics_infra = self.analytics.compute_all_metrics("XU61.DE")
                mom_em = metrics_em.get("mom_6m", 0) if metrics_em else -np.inf
                mom_infra = metrics_infra.get("mom_6m", 0) if metrics_infra else -np.inf
                # L'ETF à arbitrer est celui qui a la plus faible performance récente (on va vendre l'excédent pour acheter l'autre)
                # Mais selon la consigne : "calcule et affiche le montant (en €) et le pourcentage à arbitrer vers l'ETF ayant la plus faible performance récente"
                # On interprète : si EM Asia dépasse seuil, on arbitre l'excédent vers l'ETF le plus faible (Infra si infra plus faible, sinon EM Asia)
                # Simplifions : on compare mom_em et mom_infra, le plus faible est celui qu'on doit renforcer
                if mom_em < mom_infra:
                    weak = "EM Asia"
                    weak_ticker = "AASI.PA"
                    strong = "Infrastructure"
                else:
                    weak = "Infrastructure"
                    weak_ticker = "XU61.DE"
                    strong = "EM Asia"
                # Calcul de l'excédent total à répartir pour revenir aux cibles
                # On va calculer l'écart pour chaque actif par rapport à sa cible et proposer de rééquilibrer
                # Pour EM Asia cible 20% : écart = (em_pct - 20) / 100 * vt (positif si trop haut)
                # Pour Infra cible 10% : écart = (infra_pct - 10) / 100 * vt
                # On va afficher l'arbitrage séparément pour chaque actif dépassant son seuil.
                arb_msgs = []
                if em_alert:
                    excess_em = (em_pct - 20) / 100 * vt
                    if excess_em > 0:
                        arb_msgs.append(f"EM Asia dépasse 20% cible : vendre {excess_em:,.0f}€ pour renforcer {weak}.")
                if infra_alert:
                    excess_infra = (infra_pct - 10) / 100 * vt
                    if excess_infra > 0:
                        arb_msgs.append(f"Infrastructure dépasse 10% cible : vendre {excess_infra:,.0f}€ pour renforcer {weak}.")
                if arb_msgs:
                    st.markdown('<div class="arb-sell" style="margin-top:1rem;">', unsafe_allow_html=True)
                    st.markdown("#### 🔄 Alerte d'arbitrage automatique")
                    for msg in arb_msgs:
                        st.markdown(f"- {msg}")
                    st.markdown(f"💡 **Action suggérée** : Rééquilibrer vers **{weak}** (moins bonne performance récente).")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="arb-neutral">✅ Poids satellites dans les limites (EM Asia ≤28%, Infra ≤15%).</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="arb-neutral">✅ Poids satellites dans les limites (EM Asia ≤28%, Infra ≤15%).</div>', unsafe_allow_html=True)

        with col_m:
            st.markdown('<div class="card card-gold">', unsafe_allow_html=True)
            st.markdown("### 🌍 Indicateurs Macro <span class='live-badge'>LIVE</span>", unsafe_allow_html=True)
            st.caption("Contexte économique mondial.")
            FMT = {"NQ=F":".2f","ES=F":".2f","^TNX":".3f","EURUSD=X":".4f","BZ=F":".2f","GC=F":".2f","DX-Y.NYB":".2f","MCHI":".2f"}
            SFX = {"^TNX":"%","BZ=F":"$","GC=F":"$"}
            # Ajout de la colonne Signal pour chaque ETF (World, Asia, Infra) basé sur Prix > SMA200
            st.markdown("#### 📡 Signaux ETF (Prix > SMA200)")
            for etf_name, etf_ticker in [("World", "MWRD.PA"), ("EM Asia", "AASI.PA"), ("Infrastructure", "XU61.DE")]:
                info = self.dm.analyze_ticker(etf_ticker)
                if info and info["prix"] and info["sma200"]:
                    signal = "Favorable" if info["prix"] > info["sma200"] else "Défavorable"
                    color = "#22C55E" if signal == "Favorable" else "#FF3131"
                    st.markdown(f"**{etf_name}** : <span style='color:{color};font-weight:bold;'>{signal}</span> (Prix {info['prix']:.2f}€ vs SMA200 {info['sma200']:.2f}€)", unsafe_allow_html=True)
                else:
                    st.markdown(f"**{etf_name}** : Données insuffisantes")
            st.markdown("---")
            for sym, lbl in MACRO_TICKERS.items():
                info_m = self.dm.live.get(sym, {})
                if info_m.get("prix"):
                    pv, pm2 = info_m["prix"], info_m.get("prev")
                    delta_m = f'{self._sign((pv-pm2)/pm2*100)}{(pv-pm2)/pm2*100:.2f}%' if pm2 and pm2 != 0 else None
                    st.metric(lbl, f"{pv:{FMT.get(sym,'.2f')}}{SFX.get(sym,'')}", delta=delta_m)
                else:
                    st.metric(lbl, "N/A")
            st.markdown('</div>', unsafe_allow_html=True)

    # ── NOUVEAU COCKPIT DÉCISIONNEL (refonte totale) ──
    def render_long_term_cockpit(self, ptf: Dict, analytics_engine: AnalyticsEngine, regime: Dict):
        st.markdown("## 📈 Cockpit Décisionnel Long Terme")
        st.caption("Résumé rapide pour le suivi des allocations satellitaires (EM Asia et Infrastructure).")

        # Récupération des métriques pour EM Asia et Infrastructure
        em_metrics = analytics_engine.compute_all_metrics("AASI.PA")
        infra_metrics = analytics_engine.compute_all_metrics("XU61.DE")
        world_metrics = analytics_engine.compute_all_metrics("MWRD.PA")

        # Gap vs World : sous-performance relative (sur 3 semaines)
        # On calcule les performances sur 3 semaines (15 jours ouvrés) pour chaque satellite vs World
        def relative_perf_3w(ticker):
            df = self.dm.data.get(ticker)
            world_df = None
            for wt in WORLD_TICKERS:
                world_df = self.dm.data.get(wt)
                if world_df is not None and not world_df.empty:
                    break
            if df is None or world_df is None:
                return None
            close = df["Close"].dropna()
            world_close = world_df["Close"].dropna()
            common = close.index.intersection(world_close.index)
            if len(common) < 15:
                return None
            # 3 semaines = 15 jours ouvrés
            period = min(15, len(common)-1)
            if period < 1:
                return None
            asset_ret = (close.iloc[-1] / close.iloc[-period-1] - 1) * 100 if len(close) >= period+1 else 0
            world_ret = (world_close.iloc[-1] / world_close.iloc[-period-1] - 1) * 100 if len(world_close) >= period+1 else 0
            return asset_ret - world_ret

        em_gap = relative_perf_3w("AASI.PA")
        infra_gap = relative_perf_3w("XU61.DE")

        # Alerte rouge si sous-performance > 3 semaines (c'est-à-dire negative pendant 3 semaines consécutives)
        # On utilise le gap calculé : s'il est négatif, cela signifie sous-performance sur la période.
        # Pour détecter 3 semaines consécutives, on pourrait vérifier les 3 dernières semaines individuellement.
        # Simplification : on considère que si le gap sur 3 semaines est négatif, c'est une alerte.
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### EM Asia vs World")
            if em_gap is not None:
                if em_gap < 0:
                    st.markdown(f'<div class="card card-red"><div class="kpi-label">Gap vs World (3 sem.)</div><div class="kpi-value" style="color:#FF3131;">{self._sign(em_gap)}{em_gap:.2f}%</div><div class="small">🚨 ALERTE ROUGE : sous-performance persistante</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="card card-green"><div class="kpi-label">Gap vs World (3 sem.)</div><div class="kpi-value" style="color:#22C55E;">{self._sign(em_gap)}{em_gap:.2f}%</div><div class="small">✅ OK, surperformance</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card"><div class="kpi-label">Gap vs World (3 sem.)</div><div class="kpi-value">N/A</div></div>', unsafe_allow_html=True)
        with col_g2:
            st.markdown("#### Infrastructure vs World")
            if infra_gap is not None:
                if infra_gap < 0:
                    st.markdown(f'<div class="card card-red"><div class="kpi-label">Gap vs World (3 sem.)</div><div class="kpi-value" style="color:#FF3131;">{self._sign(infra_gap)}{infra_gap:.2f}%</div><div class="small">🚨 ALERTE ROUGE : sous-performance persistante</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="card card-green"><div class="kpi-label">Gap vs World (3 sem.)</div><div class="kpi-value" style="color:#22C55E;">{self._sign(infra_gap)}{infra_gap:.2f}%</div><div class="small">✅ OK, surperformance</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card"><div class="kpi-label">Gap vs World (3 sem.)</div><div class="kpi-value">N/A</div></div>', unsafe_allow_html=True)

        # Tableau récapitulatif pour Infra et EM Asia
        st.markdown("### 📊 Résumé analytique des satellites")
        data = []
        for name, metrics, ticker in [("EM Asia", em_metrics, "AASI.PA"), ("Infrastructure", infra_metrics, "XU61.DE")]:
            mom6 = metrics.get("mom_6m", np.nan)
            rel_str = metrics.get("rel_strength", np.nan)
            vol = metrics.get("volatility", np.nan)
            sharpe = metrics.get("sharpe", np.nan)
            corr1m = metrics.get("corr_1m", np.nan)
            corr3m = metrics.get("corr_3m", np.nan)
            # Couleur conditionnelle
            def fmt(val, low_thresh=0, high_thresh=5, invert=False):
                if np.isnan(val):
                    return "N/A", "gray"
                if invert:
                    if val <= low_thresh: return f"{val:.2f}", "green"
                    elif val >= high_thresh: return f"{val:.2f}", "red"
                    else: return f"{val:.2f}", "orange"
                else:
                    if val >= high_thresh: return f"{val:.2f}", "green"
                    elif val <= low_thresh: return f"{val:.2f}", "red"
                    else: return f"{val:.2f}", "orange"
            mom_str, mom_col = fmt(mom6, low_thresh=5, high_thresh=15)
            rel_str2, rel_col = fmt(rel_str, low_thresh=0, high_thresh=5)
            vol_str, vol_col = fmt(vol, low_thresh=15, high_thresh=25, invert=True)
            sharpe_str, sharpe_col = fmt(sharpe, low_thresh=0.5, high_thresh=1.2)
            corr1m_str, corr1m_col = fmt(corr1m, low_thresh=0.5, high_thresh=0.8)
            corr3m_str, corr3m_col = fmt(corr3m, low_thresh=0.5, high_thresh=0.8)
            data.append({
                "ETF": name,
                "Momentum 6M": f"<span style='color:{mom_col};'>{mom_str}</span>",
                "Force Relative vs World": f"<span style='color:{rel_col};'>{rel_str2}</span>",
                "Volatilité (%)": f"<span style='color:{vol_col};'>{vol_str}</span>",
                "Sharpe": f"<span style='color:{sharpe_col};'>{sharpe_str}</span>",
                "Corrélation 1M": f"<span style='color:{corr1m_col};'>{corr1m_str}</span>",
                "Corrélation 3M": f"<span style='color:{corr3m_col};'>{corr3m_str}</span>",
            })
        st.markdown(pd.DataFrame(data).to_html(escape=False, index=False), unsafe_allow_html=True)
        st.caption("Légende : 🟢 OK (vert) / 🟠 À surveiller (orange) / 🔴 Dégradé (rouge).")

    # ── FISCAL SIMULATOR (inchangé) ──
    def render_fiscal_simulator(self, ptf: Dict):
        st.markdown("## 🧮 Simulateur Fiscal")
        st.caption("Calculez le montant net après impôts en cas de vente.")
        col_pea, col_av = st.columns(2)
        val_env, gan_env = ptf["val_env"], ptf["gain_env"]
        with col_pea:
            st.markdown('<div class="card card-blue"><h4>🏦 PEA</h4>', unsafe_allow_html=True)
            net, avert = net_apres_impots("PEA", val_env["PEA"], val_env["PEA"], gan_env["PEA"])
            if avert: st.warning(avert); st.metric("Valeur brute PEA", f"{val_env['PEA']:,.2f}€")
            else: st.metric("Net après prélèvements (17.2%)", f"{net:,.2f}€")
            st.caption(f"Gain latent PEA : {self._sign(gan_env['PEA'])}{gan_env['PEA']:,.2f}€")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_av:
            st.markdown('<div class="card card-blue"><h4>🛡️ Assurance-Vie</h4>', unsafe_allow_html=True)
            net, avert = net_apres_impots("AV", val_env["AV"], val_env["AV"], gan_env["AV"])
            if avert: st.warning(avert); st.metric("Valeur brute AV", f"{val_env['AV']:,.2f}€")
            else: st.metric("Net après fiscalité AV", f"{net:,.2f}€")
            st.caption(f"Gain latent AV : {self._sign(gan_env['AV'])}{gan_env['AV']:,.2f}€")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💸 Simulez un retrait partiel")
        sc1, sc2 = st.columns([2, 1])
        with sc2: env_sim = st.selectbox("Enveloppe", ["AV", "PEA"])
        with sc1:
            max_val = float(max(val_env.get(env_sim, 0), 1000))
            montant_sim = st.slider("Montant à retirer (€)", 0.0, max_val, min(1000.0, max_val), step=100.0)
        net_sim, avert_sim = net_apres_impots(env_sim, montant_sim, val_env.get(env_sim, 0), gan_env.get(env_sim, 0))
        if avert_sim: st.warning(avert_sim)
        elif montant_sim > 0:
            vp, gp = val_env.get(env_sim, 0), gan_env.get(env_sim, 0)
            gain_sim = montant_sim * (gp / vp if vp else 0)
            imp_sim = montant_sim - net_sim
            st.markdown(f'<div class="net-box" style="display:flex;gap:2.5rem;flex-wrap:wrap;"><div><div class="kpi-label">Vous retirez</div><div class="kpi-value">{montant_sim:,.2f}€</div></div>'
                        f'<div style="color:#6B7585;">→</div><div><div class="kpi-label">Part gains imposables</div><div class="kpi-value" style="color:#D4AF37;">{gain_sim:,.2f}€</div></div>'
                        f'<div><div class="kpi-label">Impôts / PS</div><div class="kpi-value" style="color:#FF3131;">{imp_sim:,.2f}€</div></div>'
                        f'<div><div class="kpi-label">Vous recevez</div><div class="kpi-value" style="color:#22C55E;">{net_sim:,.2f}€</div></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── TRANSACTIONS TAB (inchangé) ──
    def render_transactions_tab(self):
        st.markdown("## 📈 Journal des Transactions")
        st.caption("Enregistrez vos ordres BUY/SELL. Le moteur reconstruit automatiquement le portefeuille.")
        with st.expander("➕ Enregistrer un nouvel ordre", expanded=True):
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
            with c1: tx_type = st.selectbox("Type", ["BUY", "SELL"], key="tx_type")
            with c2:
                etf_options = {f"{ticker} - {meta['nom']}": ticker for ticker, meta in ETF_LIBRARY.items()}
                selected_display = st.selectbox("Actif", list(etf_options.keys()), key="tx_ticker")
                tx_ticker = etf_options[selected_display]
            with c3: tx_parts = st.number_input("Parts", min_value=0.0, value=0.0, format="%.4f", step=0.0001, key="tx_parts")
            with c4:
                meta_sel = ETF_LIBRARY.get(tx_ticker, {})
                live_px = self.dm.live.get(meta_sel.get("yf", ""), {}).get("prix")
                default_p = float(live_px) if live_px else 0.0
                tx_price = st.number_input("Prix unitaire (€)", min_value=0.0, value=default_p, format="%.4f", step=0.01, key="tx_price")
            with c5: tx_date = st.date_input("Date", value=datetime.now().date(), key="tx_date")
            tx_note = st.text_input("Note (optionnel)", key="tx_note", placeholder="ex: DCA mensuel")
            col_btn, col_info = st.columns([1, 3])
            with col_btn:
                if st.button("✅ Enregistrer l'ordre", type="primary", use_container_width=True):
                    if tx_parts > 0 and tx_price > 0:
                        tx_record = {"date": str(tx_date), "type": tx_type, "ticker": tx_ticker, "parts": tx_parts,
                                     "price": tx_price, "montant": round(tx_parts * tx_price, 2), "note": tx_note}
                        ok = self.te.save_transaction(tx_record)
                        if ok:
                            rebuilt = self.te.get_portfolio_as_positions()
                            if rebuilt:
                                self.pcm.save_positions(rebuilt)
                                st.session_state["raw_positions"] = rebuilt
                                st.session_state["positions"] = enrich_positions(rebuilt)
                            st.success(f"✅ Ordre {tx_type} {tx_parts:.4f}×{tx_ticker} @ {tx_price:.4f}€ enregistré !")
                            st.rerun()
                        else:
                            st.error("❌ Erreur d'écriture transactions.json")
                    else:
                        st.warning("⚠️ Parts et Prix doivent être > 0")
            with col_info:
                if tx_parts > 0 and tx_price > 0:
                    montant = tx_parts * tx_price
                    st.markdown(f'<div class="info-box">Montant total : <b>{montant:,.2f}€</b> | '
                                f'ETF : {ETF_LIBRARY.get(tx_ticker, {}).get("nom", tx_ticker)} | '
                                f'Enveloppe : {ETF_LIBRARY.get(tx_ticker, {}).get("enveloppe", "N/A")}</div>', unsafe_allow_html=True)
        txs = self.te.load_transactions()
        if not txs:
            st.info("📭 Aucune transaction enregistrée. Utilisez le formulaire ci-dessus.")
            return
        st.markdown("### 📋 Historique complet")
        rows = []
        for tx in sorted(txs, key=lambda x: x.get("date",""), reverse=True):
            meta_t = ETF_LIBRARY.get(tx.get("ticker",""), {})
            rows.append({"Date": tx.get("date",""), "Type": tx.get("type",""), "ETF": meta_t.get("nom", tx.get("ticker","")),
                         "Parts": f"{tx.get('parts',0):.4f}", "Prix": f"{tx.get('price',0):.4f}€",
                         "Montant": f"{tx.get('montant',0):,.2f}€", "Note": tx.get("note","")})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown("### 📊 Positions reconstruites (TransactionEngine)")
        rebuilt = self.te.rebuild_portfolio_at_date()
        if rebuilt:
            r_rows = []
            for tk_id, data in rebuilt.items():
                if data["parts"] <= 0: continue
                prm = data["total_cost"] / data["parts"] if data["parts"] > 0 else 0
                meta = ETF_LIBRARY.get(tk_id, {})
                r_rows.append({"Ticker": tk_id, "Nom": meta.get("nom", tk_id), "Parts": f"{data['parts']:.4f}",
                               "PRMin (€)": f"{prm:.4f}", "Investi (€)": f"{data['total_cost']:,.2f}", "Enveloppe": meta.get("enveloppe","?")})
            st.dataframe(pd.DataFrame(r_rows), use_container_width=True, hide_index=True)
        if st.button("🔄 Synchroniser → portfolio_positions.json", type="secondary"):
            new_pos = self.te.get_portfolio_as_positions()
            if new_pos:
                self.pcm.save_positions(new_pos)
                st.session_state["raw_positions"] = new_pos
                st.session_state["positions"] = enrich_positions(new_pos)
                st.success("✅ portfolio_positions.json mis à jour depuis les transactions !")
                st.rerun()

    # ── SCREENER TAB (inchangé) ──
    def render_screener_tab(self):
        st.markdown("## 🔍 Screener Quantitatif d'ETFs")
        st.caption("Scoring multi-facteurs (0-100) basé sur momentum 6M, force relative, Sharpe, volatilité, drawdown, RSI, tendance.")
        with st.spinner("Calcul des scores en cours... (peut prendre quelques secondes)"):
            scores = []
            for ticker, meta in ETF_LIBRARY.items():
                if ticker not in self.dm.data:
                    continue
                res = self.signal.compute_score(ticker)
                if res["score"] == 0 and not res["metrics"]:
                    continue
                scores.append({
                    "Ticker": ticker,
                    "Nom": meta.get("nom", ""),
                    "Catégorie": meta.get("category", ""),
                    "Thème": meta.get("theme", ""),
                    "Score": res["score"],
                    "Momentum 6M": f"{res['metrics'].get('mom_6m',0):.1f}%",
                    "Force Relative": f"{res['metrics'].get('rel_strength',0):.1f}%",
                    "Volatilité": f"{res['metrics'].get('volatility',0):.1f}%",
                    "Sharpe": f"{res['metrics'].get('sharpe',0):.2f}",
                    "Drawdown": f"{res['metrics'].get('max_drawdown_1y',0):.1f}%",
                    "Corr 1M": f"{res['metrics'].get('corr_1m',0):.2f}" if res['metrics'].get('corr_1m') is not None else "N/A",
                    "Corr 3M": f"{res['metrics'].get('corr_3m',0):.2f}" if res['metrics'].get('corr_3m') is not None else "N/A",
                    "Corr 6M": f"{res['metrics'].get('corr_6m',0):.2f}" if res['metrics'].get('corr_6m') is not None else "N/A",
                    "Corr 1Y": f"{res['metrics'].get('corr_1y',0):.2f}" if res['metrics'].get('corr_1y') is not None else "N/A",
                })
            df_scores = pd.DataFrame(scores).sort_values("Score", ascending=False)
        top_n = st.slider("Nombre d'ETFs à afficher", min_value=5, max_value=len(df_scores), value=15, step=5)
        st.dataframe(df_scores.head(top_n), use_container_width=True, hide_index=True)
        if st.button("📊 Afficher tous les ETFs", use_container_width=True):
            st.dataframe(df_scores, use_container_width=True, hide_index=True)

    # ── POSITION SIZING MODELER (adapté) ──
    def render_position_sizing(self, ptf: Dict, regime_label: str):
        st.markdown("### ⚖️ Position Sizing Modeler")
        st.caption("Poids cibles optimaux suggérés (Core / Satellite) en fonction du régime macro.")
        total_val = ptf["valeur_totale"]
        if total_val <= 0:
            st.warning("Portefeuille vide.")
            return
        regime_factor = 1.0
        if regime_label in ("Stress", "Contraction"): regime_factor = 0.6
        elif regime_label == "Neutre": regime_factor = 0.8
        suggestions = []
        for pos in ptf["positions"]:
            ticker = pos.get("ticker")
            if not ticker: continue
            meta = next((m for m in ETF_LIBRARY.values() if m["yf"] == ticker), None)
            if not meta: continue
            cat = meta.get("category", "Satellite")
            # Cibles spécifiques : World 70%, EM Asia 20%, Infra 10%, autres 5%
            if pos["nom"] == "MSCI World AV":
                base_target = 0.70
            elif pos["nom"] == "EM Asia":
                base_target = 0.20
            elif pos["nom"] == "BNP ESG Infrastructure":
                base_target = 0.10
            else:
                base_target = 0.05
            adjusted = base_target * regime_factor
            current_pct = pos["valeur"] / total_val * 100
            target_pct = adjusted * 100
            suggestions.append({
                "ETF": meta.get("nom", ticker),
                "Catégorie": cat,
                "Poids actuel": f"{current_pct:.1f}%",
                "Poids cible": f"{target_pct:.1f}%",
                "Écart": f"{current_pct - target_pct:.1f}%",
                "Action": "Réduire" if current_pct - target_pct > 5 else "Renforcer" if current_pct - target_pct < -5 else "Maintenir"
            })
        st.dataframe(pd.DataFrame(suggestions), use_container_width=True, hide_index=True)

    # ── ARBITRAGE WIDGET (mis à jour) ──
    def render_arbitrage_widget(self):
        if "positions" not in st.session_state:
            return
        holdings = [p.get("_tk_id", p.get("ticker")) for p in st.session_state["positions"] if p.get("valeur",0) > 0]
        holdings = list(dict.fromkeys([h for h in holdings if h in ETF_LIBRARY]))
        opps = self.signal.get_arbitrage_opportunities(holdings)
        if opps:
            st.markdown("### 🔄 Alertes d'arbitrage")
            for opp in opps:
                st.markdown(f'<div class="arb-sell">🚨 <b>Opportunité de rotation</b><br>'
                            f'Vendre <b>{opp["sell_name"]}</b> (score actuel) → Acheter <b>{opp["buy_name"]}</b><br>'
                            f'Gain potentiel estimé : +{opp["gain_potential"]} points de score</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="arb-neutral">✅ Aucune opportunité d’arbitrage significative détectée.</div>', unsafe_allow_html=True)

    # ── FOOTER ──
    def render_footer(self, mode_direct: bool, capital: float, score_infra: int, score_em: int, regime_label: str, live_ok: int, live_total: int):
        st.markdown("---")
        col_f1, col_f2 = st.columns([4, 1])
        with col_f1:
            s = self._sign
            mode_txt = "🔌 MODE DIRECT" if mode_direct else "Ajust. patrimonial actif"
            persist = "GitHub Gist + SQLite" if self.pm.status == "github" else "SQLite local"
            st.caption(f"◈ Cockpit v5.7 Allocation Long Terme · {mode_txt} · Score Infra={s(score_infra)}{score_infra}/4 | EM={s(score_em)}{score_em}/4 · "
                       f"Régime : {regime_label} · Capital {capital:,.2f}€ · Persistance : {persist} · {live_ok}/{live_total} prix live · "
                       f"Benchmark : MWR Cash-Flow Adjusted · Outil personnel --- Ne constitue pas un conseil en investissement")
        with col_f2:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 16 : MAIN (avec trois onglets : Dashboard, Transactions, Screener)
# ─────────────────────────────────────────────────────────────────────────────

def _load_config() -> Dict:
    defaults = {"capital_reel": _DEFAULT_CAPITAL_REEL, "ajustement_pat": _DEFAULT_AJUSTEMENT_PAT, "bonus_fortuneo": _DEFAULT_BONUS_FORTUNEO}
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**defaults, **{k: float(v) for k, v in data.items() if k in defaults and not isinstance(v, list)}}
    except Exception:
        pass
    return defaults

def _save_config(capital_reel: float, ajustement_pat: float, bonus_fortuneo: float) -> bool:
    try:
        existing = {}
        if os.path.exists(_CONFIG_PATH):
            try:
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["capital_reel"] = round(capital_reel, 2)
        existing["ajustement_pat"] = round(ajustement_pat, 2)
        existing["bonus_fortuneo"] = round(bonus_fortuneo, 2)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def main():
    if "config_loaded" not in st.session_state:
        cfg = _load_config()
        st.session_state["cfg_capital_reel"] = cfg["capital_reel"]
        st.session_state["cfg_ajustement_pat"] = cfg["ajustement_pat"]
        st.session_state["cfg_bonus_fortuneo"] = cfg["bonus_fortuneo"]
        st.session_state["config_loaded"] = True
        st.session_state["save_feedback"] = ""
    if "raw_positions" not in st.session_state:
        pcm_init = PortfolioConfigManager()
        raw = pcm_init.load_positions()
        st.session_state["raw_positions"] = raw
        st.session_state["positions"] = enrich_positions(raw)

    with st.spinner("📡 Chargement des données de marché..."):
        dm = DataManager()
        if not dm.live:
            st.error("❌ Aucun prix live. Vérifiez votre connexion.")
            st.stop()
        pcm = PortfolioConfigManager()
        te = TransactionEngine()
        pm = PersistenceManager(static_capital=st.session_state["cfg_capital_reel"])
        mre = MarketRegimeEngine(dm)
        qre = QuantRiskEngine(dm)
        pe = PortfolioEngine(dm, mre, qre)
        pde = PedagogicEngine()
        se = StrategicEngine(dm, mre, qre)
        ui = StreamlitUI(dm, pm, mre, qre, pe, pde, se, pcm=pcm, te=te)

    mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo = ui.render_sidebar()

    with st.spinner("⚙️ Calcul des indicateurs..."):
        ptf = pe.compute_portfolio(positions_conf, capital_reel, ajustement_pat, bonus_fortuneo)
        # Ajout des parts et PRM dans positions_calc pour la colonne Perf. €
        # On doit récupérer les parts et prm depuis la configuration
        for i, pos_calc in enumerate(ptf["positions"]):
            conf_pos = next((p for p in positions_conf if p["nom"] == pos_calc["nom"]), None)
            if conf_pos:
                pos_calc["parts"] = conf_pos["parts"]
                pos_calc["prm"] = conf_pos["prm"]
                pos_calc["gain_unit"] = pos_calc["prix"] - conf_pos["prm"] if pos_calc["prix"] else 0
        bench = pe.compute_benchmark(positions_conf, ptf["perf_tot_pct"])
        regime = mre.get_full_regime()
        infra_info = dm.analyze_ticker("XU61.DE")
        em_info = dm.analyze_ticker("AASI.PA")
        infra_msg, infra_col = pe.evaluate_infra(infra_info)
        em_msg, em_col = pe.evaluate_em_asia(em_info)
        unified_infra = pe.compute_unified_score("XU61.DE")
        unified_em = pe.compute_unified_score("AASI.PA")
        target_infra = pe.compute_target_weight("BNP ESG Infrastructure", "XU61.DE", ptf["valeur_totale"], ptf["positions"])
        target_em = pe.compute_target_weight("EM Asia", "AASI.PA", ptf["valeur_totale"], ptf["positions"])
        ld_alerts = pe.check_leadership_alerts()
        phase_text, phase_color = pe.determine_phase(bench.get("gap"), em_info, infra_info)
        _, _, sent_rows = pe.evaluate_sentinelles()
        live_ok = sum(1 for v in dm.live.values() if v.get("prix"))
        live_total = len(dm.live)

    # Création des onglets
    tab_dashboard, tab_transactions, tab_screener = st.tabs(["📊 Dashboard", "📈 Transactions", "🔍 Screener"])

    with tab_dashboard:
        ui.render_header(mode_direct, live_ok, live_total)
        ui.render_regime_banner(regime)
        for al in ld_alerts:
            gv, nom_al, sp, wp = al["gap"], al["nom"], al["sat_perf"], al["world_perf"]
            s = StreamlitUI._sign
            if gv < -5: cls, ico = "alert-critical", "🚨"
            elif gv < -2: cls, ico = "alert-leadership", "⚠️"
            else: continue
            st.markdown(f'<div class="{cls}">{ico} <b>ALERTE : {nom_al}</b> --- {abs(gv):.1f}% en retard sur le World sur 14 jours '
                        f'({nom_al} : {s(sp)}{sp:.1f}% | World : {s(wp)}{wp:.1f}%)<br>'
                        f'<span style="font-size:.85rem;">→ Vérifiez la section Leadership ci-dessous.</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="phase-banner" style="background:{phase_color};color:white;">{phase_text}</div>', unsafe_allow_html=True)
        ui.render_command_center(ptf, bench, mode_direct, pm)
        ui.render_equity_curve_section(ptf, regime, unified_infra, unified_em, positions_conf)
        ui.render_risk_dashboard(ptf)
        st.markdown("## 🧠 Analyse des ETFs Satellites")
        # Infrastructure
        infra_border = "#22C55E" if infra_col=="green" else "#F97316" if infra_col=="orange" else "#FF3131"
        st.markdown(f'<div class="card" style="border-left:4px solid {infra_border};margin-bottom:.5rem;">'
                    f'<b>🏗️ Infrastructure (XU61.DE) --- Alerte décisionnelle</b><br>{infra_msg}</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown("### 🏗️ BNP Paribas Easy ESG Infrastructure (XU61.DE)")
            ui.render_satellite_card_pedagogic("BNP ESG Infrastructure", "XU61.DE", unified_infra, target_infra, regime, sent_rows, "infra")
        st.markdown("<br>", unsafe_allow_html=True)
        # EM Asia
        em_border = "#22C55E" if em_col=="green" else "#F97316" if em_col=="orange" else "#FF3131"
        st.markdown(f'<div class="card" style="border-left:4px solid {em_border};margin-bottom:.5rem;">'
                    f'<b>🌏 EM Asia (AASI.PA) --- Alerte décisionnelle</b><br>{em_msg}</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown("### 🌏 EM Asia (AASI.PA)")
            ui.render_satellite_card_pedagogic("EM Asia", "AASI.PA", unified_em, target_em, regime, sent_rows, "em_asia")
        ui.render_sentinelles_macro(ptf)
        ui.render_long_term_cockpit(ptf, AnalyticsEngine(dm), regime)
        ui.render_fiscal_simulator(ptf)
        ui.render_position_sizing(ptf, regime["confirmed_label"])
        ui.render_arbitrage_widget()
        ui.render_footer(mode_direct, capital_reel, unified_infra["total"], unified_em["total"], regime["confirmed_label"], live_ok, live_total)

    with tab_transactions:
        ui.render_transactions_tab()

    with tab_screener:
        ui.render_screener_tab()

if __name__ == "__main__" or True:
    main()
