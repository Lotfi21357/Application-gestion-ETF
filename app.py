# =============================================================================
# COCKPIT DÉCISIONNEL BOURSIER v6.9 — "DATA ENGINE FIABLE" + ALERTE QUANT V2 + BACKTEST
# =============================================================================
# v6.9 : Corrections majeures
#   • Benchmark World unique : MWRD.PA (WMMS exclu de WORLD_TICKERS)
#   • get_world_series() pour obtenir le benchmark en excluant l'ETF analysé
#   • wmms_gap calculé comme écart de performance sur 15 jours (pas prix unitaire)
#   • plot_alpha_bars() et plot_relative_perf() utilisent get_world_series()
#   • DataManager : historique 1200 jours, téléchargement par lots (20 tickers)
#   • Fallbacks étendus pour tous les ETF (vrais tickers alternatifs)
#   • Screener : distinction Score=0 vs Données indisponibles (N/A)
#   • Toutes les fonctionnalités v6.8 conservées
#   • AJOUT : Comparaison hebdomadaire portefeuille vs World (section dédiée)
#   • FIX : get_portfolio_weekly_performances utilise les fallbacks et aligne les dates
#   • MWR par ancrage (au lieu de figé)
#   • Corrections tickers du screener (suppressions, corrections, sécurisation)
#   • NOUVEAU : Alerte Quantitative v2 (Decision Engine)
#   • NOUVEAU : Backtest & Calibration (Priorité 3)
# =============================================================================

# -----------------------------------------------------------------------------
# MODULE 0 : IMPORTS & PAGE CONFIG
# -----------------------------------------------------------------------------
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
import ta
import time

warnings.filterwarnings("ignore")

try:
    from github import Github, InputFileContent
    PYGITHUB_OK = True
except ImportError:
    PYGITHUB_OK = False

try:
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

st.set_page_config(
    page_title="Cockpit v6.9 · Data Engine Fiable",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# MODULE 1 : CSS (inchangé)
# -----------------------------------------------------------------------------
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
.alert-box { background: linear-gradient(135deg, #3B0A0A, #5C1111); border: 1px solid #FF3131; border-radius: 10px; padding: 1rem; margin: .5rem 0; color: #FCA5A5; }
.signal-buy { background: linear-gradient(135deg, #0A2E0A, #0F4A0F); border: 1px solid #22C55E; border-radius: 10px; padding: 1rem; margin: .5rem 0; color: #86EFAC; }
.signal-sell { background: linear-gradient(135deg, #3B0A0A, #5C1111); border: 1px solid #FF3131; border-radius: 10px; padding: 1rem; margin: .5rem 0; color: #FCA5A5; }
.signal-neutral { background: linear-gradient(135deg, #1A1F26, #222A33); border: 1px solid #4B5563; border-radius: 10px; padding: 1rem; margin: .5rem 0; color: #CBD5E1; }
@media (max-width: 768px) { .kpi-value { font-size: 1.5rem; } .card { padding: 1rem; } .stButton button { min-height: 48px !important; } }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MODULE 2 : CONSTANTES & CONFIGURATION
# -----------------------------------------------------------------------------

# ---- Ancrage MWR ----
_ANCHOR_DATE = "2026-09-08"   # date de référence connue
_ANCHOR_PERF = 17.15          # performance MWR constatée à cette date (%)

HISTORICAL_DAYS = 1500  # augmenté pour backtest et calibration
BENCHMARK_WORLD_TICKER = "MWRD.PA"  # benchmark unique

# --- Nouvelles constantes Alerte Quantitative v2 ---
LINXEA_CUTOFF_HOUR = 16
LINXEA_CUTOFF_MINUTE = 30

# Seuils initiaux (À CALIBRER — voir section 11)
CRASH_THRESHOLDS = {"vol_ratio": 1.3, "dd_5d": -0.05}
CRASH_LEVELS = [(0, 1, "LOW"), (2, 3, "MODERATE"), (4, 5, "HIGH"), (6, 7, "CRITICAL")]
UNDERPERF_THRESHOLDS = {"alpha20": -0.03, "alpha60": -0.02}

# Hystérésis : seuils différents pour sortir vs réentrer
DECISION_EXIT_SCORE = 5
DECISION_REENTER_SCORE = 2

# ---- ETF_UNIVERSE : tous les fonds disponibles sur Linxea Spirit 2 ----
ETF_UNIVERSE = {
    "CG1G.DE": {"isin": "FR0010655712", "name": "Amundi ETF DAX UCITS ETF DR", "category": "Germany"},
    "AMEE.DE": {"isin": "FR0010930644", "name": "Amundi Global ETF Hydrogen UCITS ETF Acc", "category": "Hydrogen"},
    "CAC.PA": {"isin": "FR0007052782", "name": "Amundi CAC 40 UCITS ETF Dist", "category": "France"},
    "DJE.DE": {"isin": "FR0007056841", "name": "Amundi Dow Jones Industrial Average UCITS ETF Dist", "category": "USA"},
    "WLD.PA": {"isin": "FR0010315770", "name": "Amundi MSCI World II UCITS ETF Dist", "category": "World"},
    "LQQ.PA": {"isin": "FR0010342592", "name": "Amundi Nasdaq-100 Daily (2x) Leveraged UCITS ETF Acc", "category": "USA - Leveraged"},
    "LVE.PA": {"isin": "FR0010468983", "name": "Amundi EURO STOXX 50 Daily (2x) Leveraged UCITS ETF Acc", "category": "Europe - Leveraged"},
    "NRJ.PA": {"isin": "FR0010524777", "name": "Amundi MSCI New Energy UCITS ETF Dist", "category": "New Energy"},
    "WAT.PA": {"isin": "FR0010527275", "name": "Amundi MSCI Water UCITS ETF Dist", "category": "Water"},
    "LVC.PA": {"isin": "FR0010592014", "name": "Amundi CAC 40 Daily (2x) Leveraged UCITS ETF Acc", "category": "France - Leveraged"},
    "CACC.PA": {"isin": "FR0013380607", "name": "Amundi CAC 40 UCITS ETF Acc", "category": "France"},
    "WLDHC.PA": {"isin": "FR0014003N93", "name": "Amundi MSCI World Swap II UCITS ETF EUR Hedged Acc", "category": "World - Hedged"},
    "LYPS.DE": {"isin": "LU0496786574", "name": "Amundi S&P 500 II UCITS ETF EUR Dist", "category": "USA"},
    "LYPD.DE": {"isin": "LU0533032859", "name": "Amundi MSCI World Financials UCITS ETF EUR Acc", "category": "World - Financials"},
    "LYPE.DE": {"isin": "LU0533033238", "name": "Amundi MSCI World Health Care UCITS ETF EUR Acc", "category": "World - Healthcare"},
    "LYPG.DE": {"isin": "LU0533033667", "name": "Amundi MSCI World Information Technology UCITS ETF EUR Acc", "category": "World - Technology"},
    "LGQI.DE": {"isin": "LU0832436512", "name": "Amundi Global Equity Quality Income UCITS ETF Dist", "category": "World - Quality Income"},
    "AM5H.DE": {"isin": "LU0959211326", "name": "Amundi Core S&P 500 Swap UCITS ETF EUR Hedged Acc", "category": "USA - Hedged"},
    "LGWS.DE": {"isin": "LU1598690169", "name": "Lyxor MSCI EMU Value (DR) UCITS ETF", "category": "Europe - Value"},
    "100H.DE": {"isin": "LU1650492330", "name": "Amundi FTSE 100 UCITS ETF EUR Hedged Acc", "category": "UK"},
    "LCUA.DE": {"isin": "LU1781541849", "name": "Amundi MSCI EM Asia ESG Broad Transition UCITS ETF Acc", "category": "Emerging Asia"},
    "LYBK.DE": {"isin": "LU1829219390", "name": "Amundi Euro Stoxx Banks UCITS ETF Acc", "category": "Europe - Banks"},
    "LYMS.DE": {"isin": "LU1829221024", "name": "Amundi Nasdaq-100 II UCITS ETF Acc", "category": "USA - Technology"},
    "LHTC.DE": {"isin": "LU1834986900", "name": "Amundi STOXX Europe 600 Healthcare UCITS ETF Acc", "category": "Europe - Healthcare"},
    "LIGS.DE": {"isin": "LU1834987890", "name": "Amundi STOXX Europe 600 Industrials UCITS ETF Acc", "category": "Europe - Industrials"},
    "LOGS.DE": {"isin": "LU1834988278", "name": "Amundi STOXX Europe 600 Energy Screened UCITS ETF Acc", "category": "Europe - Energy"},
    "LTUG.DE": {"isin": "LU1834988518", "name": "Amundi STOXX Europe 600 Technology UCITS ETF Acc", "category": "Europe - Technology"},
    "CHIP.PA": {"isin": "LU1900066033", "name": "Amundi MSCI Semiconductors UCITS ETF Acc", "category": "Semiconductors"},
    "LBRAG.DE": {"isin": "LU1900066207", "name": "Amundi MSCI Brazil UCITS ETF Acc", "category": "Brazil"},
    "KRW.PA": {"isin": "LU1900066975", "name": "Amundi MSCI Korea UCITS ETF Acc", "category": "South Korea"},
    "LCHI.DE": {"isin": "LU1900068914", "name": "Amundi MSCI China ESG Selection Extra UCITS ETF Acc", "category": "China"},
    # "GEN1.DE" supprimé (Cause C)
    "EBUY.DE": {"isin": "LU2023678878", "name": "Amundi MSCI Digital Economy UCITS ETF Acc", "category": "Digital Economy"},
    "LYP6.DE": {"isin": "LU0908500753", "name": "Amundi Core Stoxx Europe 600 UCITS ETF Acc", "category": "Europe"},
    # "EPRA.DE" supprimé (Cause C)
    # "UKSR.DE" supprimé (Cause C)
    "J1GR.DE": {"isin": "LU1602144732", "name": "Amundi MSCI Japan ESG Broad Transition UCITS ETF EUR Acc", "category": "Japan"},
    "18MM.DE": {"isin": "LU1602144906", "name": "Amundi MSCI Pacific Ex Japan SRI Climate Paris Aligned UCITS ETF DR-EUR (C)", "category": "Pacific"},
    "RS2K.DE": {"isin": "LU1681038672", "name": "Amundi Russell 2000 UCITS ETF EUR (C)", "category": "USA - Small Cap"},
    "REAL.DE": {"isin": "LU1681039480", "name": "Amundi FTSE EPRA Europe Real Estate UCITS ETF EUR (C)", "category": "Europe - Real Estate"},
    "CI2.DE": {"isin": "LU1681043086", "name": "Amundi MSCI India UCITS ETF EUR (C)", "category": "India"},
    "AMEW.DE": {"isin": "LU1681043599", "name": "Amundi MSCI World Swap UCITS ETF EUR Acc", "category": "World"},
    "18MG.DE": {"isin": "LU1681043912", "name": "Amundi MSCI China Tech UCITS ETF EUR", "category": "China - Technology"},
    "AMEA.DE": {"isin": "LU1681044480", "name": "Amundi MSCI EM Asia UCITS ETF EUR (C)", "category": "Emerging Asia"},
    "CN1G.DE": {"isin": "LU1681044647", "name": "Amundi MSCI Nordic UCITS ETF EUR (C)", "category": "Nordic"},
    "CSW.DE": {"isin": "LU1681044720", "name": "Amundi MSCI Switzerland UCITS ETF EUR (C)", "category": "Switzerland"},
    "AMEL.DE": {"isin": "LU1681045024", "name": "Amundi MSCI EM Latin America UCITS ETF EUR (C)", "category": "Latin America"},
    "AMEM.DE": {"isin": "LU1681045370", "name": "Amundi MSCI Emerging Markets UCITS ETF EUR (C)", "category": "Emerging Markets"},
    "GC40.DE": {"isin": "LU1681046931", "name": "Amundi CAC 40 ESG UCITS ETF DR - EUR (C)", "category": "France - ESG"},
    "C50.DE": {"isin": "LU1681047236", "name": "Amundi Core EURO STOXX 50 UCITS ETF Acc", "category": "Eurozone"},
    "GLUX.DE": {"isin": "LU1681048630", "name": "Amundi Global Luxury UCITS ETF EUR (C)", "category": "Luxury"},
    "AUM5.DE": {"isin": "LU1681048804", "name": "Amundi S&P 500 UCITS ETF EUR (C)", "category": "USA"},
    "LBNK.DE": {"isin": "LU1834983477", "name": "Amundi STOXX Europe 600 Banks UCITS ETF Acc", "category": "Europe - Banks"},
    "ROAI.DE": {"isin": "LU1861132840", "name": "Amundi MSCI Robotics & AI UCITS ETF Acc", "category": "Robotics & AI"},
    # "MUEU.DE" supprimé (Cause C)
    "MSED.DE": {"isin": "LU1861138961", "name": "Amundi MSCI Emerging Markets SRI Climate Paris Aligned UCITS ETF DR (C)", "category": "Emerging Markets - ESG"},
    "SCITY.DE": {"isin": "LU2037748345", "name": "Amundi MSCI Smart Cities UCITS ETF Acc", "category": "Smart Cities"},
    "ECR3.DE": {"isin": "LU2037748774", "name": "Amundi EUR Corporate Bond 0-3Y ESG UCITS ETF DR (C)", "category": "Euro Bonds"},
    "CD91.DE": {"isin": "LU2611731824", "name": "Amundi NYSE ARCA GOLD BUGS UCITS ETF Dist", "category": "Gold Miners"},
    "LCEU.DE": {"isin": "LU1377382368", "name": "BNP Paribas Easy Low Carbon 100 Europe PAB UCITS ETF", "category": "Europe - ESG"},
    "ASRR.DE": {"isin": "LU1753045332", "name": "BNP Paribas Easy MSCI Europe SRI PAB UCITS ETF Capitalisation", "category": "Europe - ESG"},
    "EMEC.DE": {"isin": "LU1953136527", "name": "BNP Paribas Easy ECPI Circular Economy Leaders UCITS ETF Cap", "category": "Circular Economy"},
    "BJLE.DE": {"isin": "LU2194447293", "name": "BNP Paribas Easy ECPI Global ESG Blue Economy UCITS ETF Cap", "category": "Blue Economy"},
    "IQQI.DE": {"isin": "IE00B1FZS467", "name": "iShares Global Infrastructure UCITS ETF USD Dist", "category": "Infrastructure"},
    "IUSC.DE": {"isin": "IE00B27YCK28", "name": "iShares MSCI EM Latin America UCITS ETF USD Dist", "category": "Latin America"},
    "IUSD.DE": {"isin": "IE00B27YCN58", "name": "iShares MSCI World Islamic UCITS ETF USD Dist", "category": "World - Islamic"},
    "EUNK.DE": {"isin": "IE00B4K48X80", "name": "iShares Core MSCI Europe UCITS ETF EUR Acc", "category": "Europe"},
    "IBC6.DE": {"isin": "IE00B5377D42", "name": "iShares MSCI Australia UCITS ETF USD Acc", "category": "Australia"},
    "2B72.DE": {"isin": "IE00BF20LF40", "name": "iShares MSCI Europe Mid Cap UCITS ETF EUR Acc", "category": "Europe - Mid Cap"},
    "L0CK.DE": {"isin": "IE00BG0J4C88", "name": "iShares Digital Security UCITS ETF USD Acc", "category": "Cybersecurity"},
    "IEVD.DE": {"isin": "IE00BGL86Z12", "name": "iShares Electric Vehicles and Driving Technology UCITS ETF USD Acc", "category": "Electric Vehicles"},
    "IWLE.DE": {"isin": "IE00BKBF6H24", "name": "iShares Core MSCI World ETF EUR H Dist", "category": "World - Hedged"},
    "2B7K.DE": {"isin": "IE00BYX2JD69", "name": "iShares MSCI World SRI UCITS ETF EUR Acc", "category": "World - ESG"},
    "2B76.DE": {"isin": "IE00BYZK4552", "name": "iShares Automation & Robotics UCITS ETF", "category": "Automation & Robotics"},
    "2B77.DE": {"isin": "IE00BYZK4669", "name": "iShares Ageing Population UCITS ETF USD Acc", "category": "Demographics"},
    "2B78.DE": {"isin": "IE00BYZK4776", "name": "iShares Healthcare Innovation UCITS ETF USD Acc", "category": "Healthcare"},
    "2B79.DE": {"isin": "IE00BYZK4883", "name": "iShares Digitalisation UCITS ETF USD Acc", "category": "Digitalisation"},
    "XAIX.DE": {"isin": "IE00BGV5VN51", "name": "Xtrackers Artificial Intelligence & Big Data UCITS ETF 1C", "category": "Artificial Intelligence"},
    "WMMS.DE": {"isin": "IE000AZV0AS3", "name": "Amundi MSCI World IMI Value Advanced UCITS ETF Acc", "category": "World - Value"},
    "BUNH.DE": {"isin": "LU1954152853", "name": "Amundi Nasdaq-100 II UCITS ETF EUR Hedged Acc", "category": "USA - Technology - Hedged"},
}

# ---- EXISTING_ETFS : fonds détenus ou suivis (avec initial_target, etc.) ----
EXISTING_ETFS = {
    "DCAM.PA": {
        "isin": "",
        "nom": "MSCI World PEA",
        "name": "Amundi MSCI World UCITS PEA",
        "yf": "DCAM.PA",
        "yf_fallbacks": ["DCAM.PA", "CW8.PA"],
        "category": "Core",
        "theme": "Blended",
        "region": "Global",
        "risk_type": "Standard",
        "enveloppe": "PEA",
        "initial_target": 0.183
    },
    "MWRD.PA": {
        "isin": "",
        "nom": "MSCI World AV",
        "name": "Amundi MSCI World UCITS DR USD",
        "yf": "MWRD.PA",
        "yf_fallbacks": ["MWRD.PA", "IWDA.AS", "EUNL.DE", "CW8.PA"],
        "category": "Core",
        "theme": "Blended",
        "region": "Global",
        "risk_type": "Standard",
        "enveloppe": "AV",
        "initial_target": 0.154
    },
    "KRW.PA": {
        "isin": "LU1900066975",
        "nom": "MSCI Korea",
        "name": "Amundi MSCI Korea UCITS",
        "yf": "KRW.PA",
        "yf_fallbacks": ["KRW.PA", "EWY"],
        "category": "Satellite",
        "theme": "Korea",
        "region": "Asia",
        "risk_type": "HighVol",
        "enveloppe": "AV",
        "initial_target": 0.155
    },
    "CHIP.PA": {
        "isin": "LU1900066033",
        "nom": "MSCI Semiconductors",
        "name": "Amundi MSCI Semiconductors UCITS",
        "yf": "CHIP.PA",
        "yf_fallbacks": ["CHIP.PA", "SOXX"],
        "category": "Satellite",
        "theme": "Tech",
        "region": "Global",
        "risk_type": "HighVol",
        "enveloppe": "AV",
        "initial_target": 0.138
    },
    "WMMS.DE": {
        "isin": "IE000AZV0AS3",
        "nom": "Amundi MSCI World IMI Value Advanced",
        "name": "Amundi MSCI World IMI Value Advanced UCITS ETF Acc",
        "yf": "WMMS.DE",
        "yf_fallbacks": ["WMMS.DE", "WMMS.XETRA"],
        "category": "Core",
        "theme": "Value",
        "region": "Global",
        "risk_type": "Standard",
        "enveloppe": "AV",
        "initial_target": 0.37
    },
    "500.PA": {"isin": "LU1681048804", "nom": "Amundi S&P 500", "name": "Amundi S&P 500 UCITS", "yf": "500.PA", "yf_fallbacks": ["500.PA", "SPY"], "category": "Core", "theme": "Large Cap", "region": "USA", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "USTE.PA": {"isin": "LU1829221024", "nom": "Nasdaq-100", "name": "Lyxor UCITS Nasdaq-100 D-EUR", "yf": "LYMS.DE", "yf_fallbacks": ["LYMS.DE", "USTE.PA", "QQQ"], "category": "Core", "theme": "Tech", "region": "USA", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "CW8.PA": {"isin": "LU1681043599", "nom": "MSCI World CW8", "name": "Amundi MSCI World UCITS", "yf": "CW8.PA", "yf_fallbacks": ["CW8.PA", "IWDA.AS"], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXHEA.PA": {"isin": "LU1834986900", "nom": "Europe Healthcare", "name": "Amundi STOXX Europe 600 Healthcare", "yf": "LHTC.DE", "yf_fallbacks": ["LHTC.DE", "LYXHEA.PA"], "category": "Sector", "theme": "Health", "region": "Europe", "risk_type": "Defensive", "enveloppe": "AV", "initial_target": 0.0},
    "SPHC.PA": {"isin": "LU0959211326", "nom": "S&P 500 Hedged", "name": "Lyxor S&P 500 UCITS - Daily Hedged", "yf": "SPHC.PA", "yf_fallbacks": ["SPHC.PA", "SPY"], "category": "Core", "theme": "Large Cap", "region": "USA", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "WSRI.PA": {"isin": "IE00BYX2JD69", "nom": "World SRI", "name": "Amundi MSCI World SRI Climate Net", "yf": "WSRI.PA", "yf_fallbacks": ["WSRI.PA", "SAWD.DE"], "category": "ESG", "theme": "Sustainability", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "USTH.PA": {"isin": "LU1954152853", "nom": "Nasdaq Hedged", "name": "Amundi Nasdaq-100 II UCITS ETF EUR Hedged Acc", "yf": "BUNH.DE", "yf_fallbacks": ["BUNH.DE", "USTH.PA", "QQQH.DE"], "category": "Core", "theme": "Tech", "region": "USA", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "ISEUMD.PA": {"isin": "IE00BF20LF40", "nom": "Europe Mid Cap", "name": "iShares MSCI Europe Mid Cap Acc", "yf": "2B72.DE", "yf_fallbacks": ["2B72.DE", "ISEUMD.PA"], "category": "Core", "theme": "Mid Cap", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "ALAT.PA": {"isin": "LU1681045024", "nom": "EM Latin America", "name": "Amundi MSCI EM Latin America UCITS", "yf": "ALAT.PA", "yf_fallbacks": ["ALAT.PA", "ILA.DE"], "category": "Emerging", "theme": "Commodities", "region": "LatAm", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "INDG.PA": {"isin": "LU1834987890", "nom": "Europe Industrials", "name": "Amundi STOXX Europe 600 Industrials", "yf": "LIGS.DE", "yf_fallbacks": ["LIGS.DE", "INDG.PA"], "category": "Sector", "theme": "Industrial", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "DJE.PA": {"isin": "FR0007056841", "nom": "Dow Jones", "name": "Amundi Dow Jones Industrial Average", "yf": "DJE.PA", "yf_fallbacks": ["DJE.PA", "DIA"], "category": "Core", "theme": "Value", "region": "USA", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "NRAM.PA": {"isin": "", "nom": "North America ESG", "name": "AMUNDI MSCI North America ESG", "yf": "NRAM.PA", "yf_fallbacks": ["NRAM.PA", "NAR.DE"], "category": "ESG", "theme": "Sustainability", "region": "NorthAmerica", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "GOAI.PA": {"isin": "", "nom": "Global AI", "name": "Amundi Stoxx Global Artificial Intelligence", "yf": "GOAI.PA", "yf_fallbacks": ["GOAI.PA", "AIXX.DE"], "category": "Satellite", "theme": "AI & Tech", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "ENRGA.PA": {"isin": "LU1834988278", "nom": "Europe Energy", "name": "Amundi STOXX Europe 600 Energy", "yf": "LOGS.DE", "yf_fallbacks": ["LOGS.DE", "ENRGA.PA"], "category": "Sector", "theme": "Energy", "region": "Europe", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "JPNH.PA": {"isin": "LU1602144732", "nom": "Japan TOPIX", "name": "Amundi Japan TOPIX II UCITS EUR", "yf": "JPNH.PA", "yf_fallbacks": ["JPNH.PA", "EWJ"], "category": "Core", "theme": "Blended", "region": "Japan", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CSW.PA": {"isin": "LU1681044720", "nom": "Switzerland", "name": "Amundi ETF MSCI Switzerland UCITS", "yf": "CSW.PA", "yf_fallbacks": ["CSW.PA", "EWL"], "category": "Core", "theme": "Defensive", "region": "Switzerland", "risk_type": "Defensive", "enveloppe": "AV", "initial_target": 0.0},
    "CD9.PA": {"isin": "", "nom": "Europe High Dividend", "name": "Amundi MSCI Europe High Dividend", "yf": "CD9.PA", "yf_fallbacks": ["CD9.PA", "EUDV.DE"], "category": "Factor", "theme": "Dividend", "region": "Europe", "risk_type": "Defensive", "enveloppe": "AV", "initial_target": 0.0},
    "CJ1.PA": {"isin": "", "nom": "Japan MSCI", "name": "Amundi ETF MSCI Japan UCITS", "yf": "CJ1.PA", "yf_fallbacks": ["CJ1.PA", "EWJ"], "category": "Core", "theme": "Blended", "region": "Japan", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "USRI.PA": {"isin": "", "nom": "USA SRI", "name": "AMUNDI MSCI USA SRI Climate Net", "yf": "USRI.PA", "yf_fallbacks": ["USRI.PA", "USS.DE"], "category": "ESG", "theme": "Sustainability", "region": "USA", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "EBUY.PA": {"isin": "LU2023678878", "nom": "Digital Economy", "name": "Lyxor MSCI Digital", "yf": "EBUY.PA", "yf_fallbacks": ["EBUY.PA", "EBUY.DE"], "category": "Satellite", "theme": "Digital Economy", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "COMO.PA": {"isin": "", "nom": "Commodities", "name": "Lyxor UCITS Commodities Thomson", "yf": "COMO.PA", "yf_fallbacks": ["COMO.PA", "COMO.DE"], "category": "Alternative", "theme": "Commodities", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "CP9.PA": {"isin": "LU1602144906", "nom": "Pacific Ex Japan", "name": "Amundi ETF MSCI Pacific Ex Japan", "yf": "CP9.PA", "yf_fallbacks": ["CP9.PA", "EPP"], "category": "Core", "theme": "Blended", "region": "Pacific", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    # "ESGWO.PA" supprimé (Cause C)
    "IUSN.DE": {"isin": "IE00B3F81R35", "nom": "World Small Cap", "name": "iShares MSCI World Small Cap UCITS", "yf": "IUSN.DE", "yf_fallbacks": ["IUSN.DE", "WSML.DE"], "category": "Core", "theme": "Small Cap", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "WLDHC.PA": {"isin": "FR0014003N93", "nom": "World Monthly Hedged", "name": "Lyxor MSCI World UCITS Monthly Hedged", "yf": "WLDHC.PA", "yf_fallbacks": ["WLDHC.PA", "WLDH.DE"], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    # "ESCE.PA" supprimé (Cause C)
    "2B78.DE": {"isin": "IE00BYZK4776", "nom": "Healthcare Innovation", "name": "iShares Healthcare Innovation Acc", "yf": "2B78.DE", "yf_fallbacks": ["2B78.DE", "HEAL.DE"], "category": "Satellite", "theme": "Health Tech", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CACC.PA": {"isin": "FR0013380607", "nom": "CAC 40", "name": "Lyxor CAC 40 (DR) UCITS Acc", "yf": "CACC.PA", "yf_fallbacks": ["CACC.PA", "CAC.PA"], "category": "Core", "theme": "Blended", "region": "France", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CN1.PA": {"isin": "LU1681044647", "nom": "Nordic", "name": "Amundi ETF MSCI Nordic UCITS", "yf": "CN1.PA", "yf_fallbacks": ["CN1.PA", "NORD.DE"], "category": "Core", "theme": "Blended", "region": "Nordic", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXRIO.PA": {"isin": "LU1900066207", "nom": "Brazil", "name": "Amundi MSCI Brazil UCITS ETF Acc", "yf": "LBRAG.DE", "yf_fallbacks": ["LBRAG.DE", "LYXRIO.PA"], "category": "Emerging", "theme": "Blended", "region": "Brazil", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "C50.PA": {"isin": "LU1681047236", "nom": "Euro Stoxx 50", "name": "Amundi ETF Euro Stoxx 50 UCITS", "yf": "C50.PA", "yf_fallbacks": ["C50.PA", "SX5E.DE"], "category": "Core", "theme": "Large Cap", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "SMEA.PA": {"isin": "IE00B4K48X80", "nom": "MSCI Europe", "name": "iShares MSCI Europe UCITS Acc", "yf": "EUNK.DE", "yf_fallbacks": ["EUNK.DE", "SMEA.PA"], "category": "Core", "theme": "Blended", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "VEUR.PA": {"isin": "IE00B945VV12", "nom": "FTSE Developed Europe", "name": "Vanguard FTSE Developed Europe", "yf": "VEUR.AS", "yf_fallbacks": ["VEUR.AS", "VEUR.L", "VDEV.DE"], "category": "Core", "theme": "Blended", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "MSE.PA": {"isin": "", "nom": "EURO STOXX 50", "name": "Amundi EURO STOXX 50 II UCITS Acc", "yf": "MSE.PA", "yf_fallbacks": ["MSE.PA", "SX5E.DE"], "category": "Core", "theme": "Large Cap", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "100H.PA": {"isin": "LU1650492330", "nom": "FTSE 100 Hedged", "name": "Lyxor FTSE 100 Monthly Hedged C", "yf": "100H.PA", "yf_fallbacks": ["100H.PA", "100H.DE"], "category": "Core", "theme": "Blended", "region": "UK", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CC1U.PA": {"isin": "LU1900068914", "nom": "MSCI China", "name": "Amundi ETF MSCI China UCITS", "yf": "CC1U.PA", "yf_fallbacks": ["CC1U.PA", "MCHI"], "category": "Emerging", "theme": "Blended", "region": "China", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "LYXDAX.PA": {"isin": "FR0010655712", "nom": "DAX", "name": "Lyxor DAX (DR) UCITS - Acc", "yf": "CG1G.DE", "yf_fallbacks": ["CG1G.DE", "LYXDAX.PA"], "category": "Core", "theme": "Large Cap", "region": "Germany", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "CMUD.PA": {"isin": "", "nom": "EMU ESG", "name": "Amundi MSCI EMU ESG Selection", "yf": "CMUD.PA", "yf_fallbacks": ["CMUD.PA", "EMU.DE"], "category": "ESG", "theme": "Sustainability", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "AMCNEG.PA": {"isin": "LU1900068914", "nom": "China ESG", "name": "Amundi MSCI China ESG Leaders Sel", "yf": "AMCNEG.PA", "yf_fallbacks": ["AMCNEG.PA", "MCHI"], "category": "ESG", "theme": "Sustainability", "region": "China", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "CMU.PA": {"isin": "", "nom": "MSCI EMU", "name": "Amundi MSCI EMU UCITS", "yf": "CMU.PA", "yf_fallbacks": ["CMU.PA", "EMU.DE"], "category": "Core", "theme": "Blended", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYNRJ.PA": {"isin": "FR0010524777", "nom": "New Energy", "name": "Lyxor New Energy UCITS ETF Dist", "yf": "LYNRJ.PA", "yf_fallbacks": ["LYNRJ.PA", "INRG.DE"], "category": "Satellite", "theme": "Clean Energy", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "SCITY.PA": {"isin": "LU2037748345", "nom": "Smart City", "name": "Amundi Index Solutions - Amundi Smart City", "yf": "SCITY.PA", "yf_fallbacks": ["SCITY.PA", "SCITY.DE"], "category": "Satellite", "theme": "Megatrend", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "RS2U.PA": {"isin": "", "nom": "Resilient", "name": "Amundi Index Solutions - Amundi Resilient", "yf": "RS2U.PA", "yf_fallbacks": ["RS2U.PA", "RS2.DE"], "category": "Factor", "theme": "Defensive", "region": "Europe", "risk_type": "Defensive", "enveloppe": "AV", "initial_target": 0.0},
    # "EUDF.PA" supprimé (Cause C)
    "AEEM.PA": {"isin": "LU1681045370", "nom": "MSCI EM", "name": "Amundi ETF MSCI Emerging Markets", "yf": "AEEM.PA", "yf_fallbacks": ["AEEM.PA", "EEM"], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXLEM.PA": {"isin": "LU1681045370", "nom": "MSCI EM Swap", "name": "Amundi MSCI Em Mkts Swap II UCIT", "yf": "LYXLEM.PA", "yf_fallbacks": ["LYXLEM.PA", "EEM"], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "AUEM.PA": {"isin": "LU1681045370", "nom": "MSCI EM USD", "name": "Amundi ETF MSCI Emerging Markets USD", "yf": "AUEM.PA", "yf_fallbacks": ["AUEM.PA", "EEM"], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXTNOW.PA": {"isin": "LU0533033667", "nom": "World Info Tech", "name": "Amundi MSCI World Information Technology", "yf": "LYPG.DE", "yf_fallbacks": ["LYPG.DE", "LYXTNOW.PA"], "category": "Sector", "theme": "Tech", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "IJPE.PA": {"isin": "IE00B4K48X80", "nom": "Japan Small Cap", "name": "iShares MSCI Japan Small Cap Acc", "yf": "IJPE.PA", "yf_fallbacks": ["IJPE.PA", "JSC.DE"], "category": "Core", "theme": "Small Cap", "region": "Japan", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "CV9.PA": {"isin": "", "nom": "Europe Value", "name": "Amundi MSCI Europe Value Factor", "yf": "CV9.PA", "yf_fallbacks": ["CV9.PA", "VEUR.DE"], "category": "Factor", "theme": "Value", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXFINW.PA": {"isin": "LU0533032859", "nom": "World Financials", "name": "Amundi MSCI World Financials UCITS", "yf": "LYPD.DE", "yf_fallbacks": ["LYPD.DE", "LYXFINW.PA"], "category": "Sector", "theme": "Finance", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
}

# ---- Fonctions d'inférence améliorées ----
def infer_region(category: str) -> str:
    cat_lower = category.lower()
    if any(x in cat_lower for x in ["world", "global", "international", "developed"]):
        return "Global"
    if any(x in cat_lower for x in ["usa", "nasdaq", "sp500", "s&p 500", "america"]):
        return "USA"
    if "europe" in cat_lower or "euro" in cat_lower or "stoxx" in cat_lower or "emu" in cat_lower:
        return "Europe"
    if "france" in cat_lower or "cac" in cat_lower:
        return "France"
    if "germany" in cat_lower or "dax" in cat_lower:
        return "Germany"
    if "uk" in cat_lower or "ftse 100" in cat_lower:
        return "UK"
    if "japan" in cat_lower:
        return "Japan"
    if "china" in cat_lower:
        return "China"
    if "korea" in cat_lower:
        return "South Korea"
    if "india" in cat_lower:
        return "India"
    if "brazil" in cat_lower:
        return "Brazil"
    if "latin america" in cat_lower:
        return "LatAm"
    if "pacific" in cat_lower:
        return "Pacific"
    if "emerging" in cat_lower:
        return "Emerging"
    if "switzerland" in cat_lower:
        return "Switzerland"
    if "nordic" in cat_lower:
        return "Nordic"
    if "australia" in cat_lower:
        return "Australia"
    return "Global"

def infer_theme(category: str) -> str:
    cat_lower = category.lower()
    if "semiconductor" in cat_lower:
        return "Semiconductors"
    if "robotics" in cat_lower or "ai" in cat_lower or "artificial intelligence" in cat_lower:
        return "Robotics & AI"
    if "cybersecurity" in cat_lower or "security" in cat_lower:
        return "Cybersecurity"
    if "automation" in cat_lower:
        return "Automation"
    if "digital economy" in cat_lower:
        return "Digital Economy"
    if "digitalisation" in cat_lower:
        return "Digitalisation"
    if "electric vehicle" in cat_lower or "ev" in cat_lower:
        return "Electric Vehicles"
    if "hydrogen" in cat_lower:
        return "Hydrogen"
    if "water" in cat_lower:
        return "Water"
    if "smart city" in cat_lower or "smart cities" in cat_lower:
        return "Smart Cities"
    if "luxury" in cat_lower:
        return "Luxury"
    if "circular economy" in cat_lower:
        return "Circular Economy"
    if "blue economy" in cat_lower:
        return "Blue Economy"
    if "clean energy" in cat_lower or "new energy" in cat_lower:
        return "Clean Energy"
    if "gold" in cat_lower or "gold miners" in cat_lower:
        return "Gold"
    if "real estate" in cat_lower or "epra" in cat_lower:
        return "Real Estate"
    if "infrastructure" in cat_lower:
        return "Infrastructure"
    if "banks" in cat_lower:
        return "Banks"
    if "healthcare" in cat_lower:
        return "Healthcare"
    if "financial" in cat_lower:
        return "Finance"
    if "technology" in cat_lower:
        return "Technology"
    if "energy" in cat_lower:
        return "Energy"
    if "industrial" in cat_lower:
        return "Industrials"
    if "consumer" in cat_lower or "millennials" in cat_lower:
        return "Consumer"
    if "quality income" in cat_lower:
        return "Quality Income"
    if "dividend" in cat_lower:
        return "Dividend"
    if "value" in cat_lower:
        return "Value"
    if "growth" in cat_lower:
        return "Growth"
    if "small cap" in cat_lower:
        return "Small Cap"
    if "mid cap" in cat_lower:
        return "Mid Cap"
    if "large cap" in cat_lower:
        return "Large Cap"
    if "esg" in cat_lower or "sri" in cat_lower or "climate" in cat_lower:
        return "Sustainability"
    if "hedged" in cat_lower:
        return "Hedged"
    if "leveraged" in cat_lower:
        return "Leveraged"
    if "islamic" in cat_lower:
        return "Islamic"
    return "Blended"

# ---- Normalisation par ISIN (sécurisée) ----
def normalize_etf_library(library: Dict) -> Dict:
    by_isin = {}
    for ticker, meta in library.items():
        isin = meta.get("isin")
        if not isin:
            by_isin[ticker] = {"ticker": ticker, "meta": meta}
            continue
        if isin not in by_isin:
            by_isin[isin] = {"ticker": ticker, "meta": meta}
        else:
            current = by_isin[isin]
            # Priorité systématique au ticker .DE (Xetra), plus fiable sur Yahoo
            if ticker.endswith(".DE") and not current["ticker"].endswith(".DE"):
                by_isin[isin] = {"ticker": ticker, "meta": meta}
    result = {}
    for isin_or_ticker, entry in by_isin.items():
        ticker = entry["ticker"]
        meta = entry["meta"].copy()
        if "isin" not in meta and (isin_or_ticker.startswith("IE") or isin_or_ticker.startswith("FR") or isin_or_ticker.startswith("LU")):
            meta["isin"] = isin_or_ticker
        result[ticker] = meta
    return result

# ---- Construction de ETF_LIBRARY ----
temp_library = dict(EXISTING_ETFS)
existing_tickers = set(temp_library.keys())
existing_isins = {meta.get("isin") for meta in temp_library.values() if meta.get("isin")}

for ticker, info in ETF_UNIVERSE.items():
    if ticker in existing_tickers:
        continue
    isin = info.get("isin")
    if isin and isin in existing_isins:
        continue
    category = info.get("category", "Unknown")
    region = infer_region(category)
    theme = infer_theme(category)
    risk_type = "HighVol" if any(x in category.lower() for x in ["leveraged", "high vol", "volatile"]) else \
                "Defensive" if any(x in category.lower() for x in ["defensive", "low carbon", "esg", "sri"]) else \
                "Standard"
    enveloppe = "PEA" if "pea" in info.get("name", "").lower() else "AV"
    temp_library[ticker] = {
        "nom": info["name"],
        "name": info["name"],
        "yf": ticker,
        "yf_fallbacks": [],
        "category": category,
        "theme": theme,
        "region": region,
        "risk_type": risk_type,
        "enveloppe": enveloppe,
        "initial_target": 0.0,
        "isin": isin
    }

ETF_LIBRARY = normalize_etf_library(temp_library)

# ---- Fonction centrale pour obtenir le benchmark World (exclut l'ETF analysé) ----
def get_world_series(dm: "DataManager", exclude_ticker: str = None) -> pd.Series:
    """
    Retourne la série de prix du benchmark World (MWRD.PA ou fallback).
    N'utilise JAMAIS WMMS.DE et exclut exclude_ticker si fourni.
    """
    candidates = [
        BENCHMARK_WORLD_TICKER,  # MWRD.PA en premier
        "CW8.PA",
        "IWDA.AS",
        "EUNL.DE",
        "DCAM.PA",
    ]
    # Éliminer les doublons et le ticker exclu
    seen = set()
    unique_candidates = []
    for t in candidates:
        if t not in seen and t != exclude_ticker and t != "WMMS.DE":
            seen.add(t)
            unique_candidates.append(t)
    # Si on a exclu MWRD.PA, on s'assure qu'un autre est disponible
    if exclude_ticker == BENCHMARK_WORLD_TICKER:
        if "CW8.PA" not in unique_candidates:
            unique_candidates.insert(0, "CW8.PA")
    for ticker in unique_candidates:
        df = dm.data.get(ticker, pd.DataFrame())
        if df is not None and not df.empty and "Close" in df.columns:
            series = df["Close"].dropna()
            if len(series) >= 20:
                return series
    # Fallback : chercher n'importe quel World non exclu
    for ticker, df in dm.data.items():
        if ticker == exclude_ticker or ticker == "WMMS.DE":
            continue
        if ticker in ["MWRD.PA", "CW8.PA", "IWDA.AS", "EUNL.DE", "DCAM.PA"]:
            if "Close" in df.columns:
                series = df["Close"].dropna()
                if len(series) >= 20:
                    return series
    return pd.Series(dtype=float)

# ---- Fonction de calcul de l'écart de performance ----
def compute_relative_gap(dm: "DataManager", ticker: str, days: int = 15) -> Optional[float]:
    """Calcule l'écart de performance entre ticker et le World sur 'days' séances."""
    asset = dm.data.get(ticker, pd.DataFrame())
    if asset.empty or "Close" not in asset.columns:
        return None
    world = get_world_series(dm, exclude_ticker=ticker)
    if world.empty:
        return None
    asset_close = asset["Close"].dropna()
    common = asset_close.index.intersection(world.index)
    if len(common) < days + 1:
        return None
    common = common.sort_values()
    asset_ret = (asset_close.loc[common[-1]] / asset_close.loc[common[-days-1]] - 1) * 100
    world_ret = (world.loc[common[-1]] / world.loc[common[-days-1]] - 1) * 100
    return asset_ret - world_ret

# ---- Variables globales ----
# WORLD_TICKERS ne doit JAMAIS contenir WMMS.DE
WORLD_TICKERS = ["MWRD.PA", "CW8.PA", "IWDA.AS", "EUNL.DE", "DCAM.PA"]
GOLD_TICKERS_FALLBACK = []
PROXIES_KR = ["005930.KS", "000660.KS"]
PROXIES_CHIP = ["TSM", "NVDA", "AMD", "INTC"]
MACRO_TICKERS = {"NQ=F": "Nasdaq 100", "ES=F": "S&P 500", "^TNX": "US 10Y (%)", "EURUSD=X": "EUR/USD", "BZ=F": "Brent ($)", "GC=F": "Or ($)", "DX-Y.NYB": "Dollar Index", "MCHI": "iShares MSCI China"}
REGIME_TICKERS = ["SPY", "QQQ", "^VIX", "^TNX", "DX-Y.NYB", "ES=F", "NQ=F"]
SENTINELLES = {"Samsung": ["005930.KS"], "SK Hynix": ["000660.KS"], "TSMC": ["TSM"], "NVIDIA": ["NVDA"], "AMD": ["AMD"], "Intel": ["INTC"]}
BENCHMARK_NOM = "MSCI World AV"
DATE_DEBUT = datetime(2025, 9, 17)

_DEFAULT_CAPITAL_REEL = 15023.05
_DEFAULT_AJUSTEMENT_PAT = 0.0
_DEFAULT_BONUS_FORTUNEO = 0.0
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_perso.json")
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local.db")
_PORTFOLIO_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portfolio_positions.json")
_TRANSACTIONS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions.json")

# -----------------------------------------------------------------------------
# MODULE 3 : DATA MANAGER (version robuste avec lots et fallbacks)
# -----------------------------------------------------------------------------
requests_cache.install_cache('yfinance_cache', expire_after=86400)

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        try:
            tickers = df.columns.get_level_values(1).unique().tolist()
            if tickers:
                df = df.xs(tickers[0], axis=1, level=1)
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

def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_live_prices() -> Dict[str, Dict]:
    all_tickers = _collect_all_yf_tickers()
    result = {}
    for tk in all_tickers:
        prix, prev = _fetch_live_price(tk)
        result[tk] = {"prix": prix, "prev": prev}
    return result

@st.cache_data(ttl=7200, show_spinner=False)
def _cached_historical_data() -> Dict[str, pd.DataFrame]:
    all_tickers = _collect_all_yf_tickers()
    start = (datetime.now() - timedelta(days=HISTORICAL_DAYS)).strftime("%Y-%m-%d")
    result = {}
    # Téléchargement par lots de 20 tickers
    batch_size = 20
    for batch in chunks(all_tickers, batch_size):
        try:
            raw = yf.download(
                batch,
                start=start,
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True
            )
            if not raw.empty and isinstance(raw.columns, pd.MultiIndex):
                for tk in batch:
                    try:
                        df = _normalize_df(raw[tk].copy())
                        if not df.empty:
                            result[tk] = df
                    except Exception:
                        pass
            elif not raw.empty and len(batch) == 1:
                df = _normalize_df(raw.copy())
                if not df.empty:
                    result[batch[0]] = df
        except Exception:
            pass
        time.sleep(0.2)
    # Deuxième passe : retry individuel pour les tickers manquants avec fallbacks
    missing = [tk for tk in all_tickers if tk not in result]
    for tk in missing:
        meta = next((m for m in ETF_LIBRARY.values() if m.get("yf") == tk), None)
        if meta:
            candidates = [meta.get("yf")] + meta.get("yf_fallbacks", [])
            candidates = list(dict.fromkeys([c for c in candidates if c]))
            for c in candidates:
                if c in result:
                    break
                try:
                    df = yf.download(c, start=start, auto_adjust=True, progress=False)
                    df = _normalize_df(df)
                    if not df.empty:
                        result[c] = df
                        if c != tk:
                            result[tk] = df
                        break
                except Exception:
                    continue
        else:
            try:
                df = yf.download(tk, start=start, auto_adjust=True, progress=False)
                df = _normalize_df(df)
                if not df.empty:
                    result[tk] = df
            except Exception:
                pass
    # NOUVEAU : tracking des échecs pour diagnostic
    final_failures = [tk for tk in all_tickers if tk not in result]
    st.session_state["_data_failures"] = final_failures
    return result

def get_working_ticker(meta: Dict) -> Optional[str]:
    candidates = []
    if meta.get("yf"):
        candidates.append(meta["yf"])
    for fb in meta.get("yf_fallbacks", []):
        if fb not in candidates:
            candidates.append(fb)
    for ticker in candidates:
        try:
            data = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
            if data is not None and not data.empty and "Close" in data.columns:
                return ticker
        except Exception:
            continue
    return None

def _collect_all_yf_tickers() -> List[str]:
    tickers = []
    for meta in ETF_LIBRARY.values():
        yf_ticker = meta.get("yf")
        if yf_ticker:
            tickers.append(yf_ticker)
        for fb in meta.get("yf_fallbacks", []):
            if fb and fb not in tickers:
                tickers.append(fb)
    tickers.extend(MACRO_TICKERS.keys())
    tickers.extend(REGIME_TICKERS)
    tickers.extend(PROXIES_KR)
    tickers.extend(PROXIES_CHIP)
    tickers.extend(["NVDA", "AAPL", "GOOGL", "GOOG", "MSFT", "AMZN"])
    for tlist in SENTINELLES.values():
        tickers.extend(tlist)
    return list(dict.fromkeys(tickers))

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
            meta = {"yf": ticker, "yf_fallbacks": []}
            working = get_working_ticker(meta)
            if working:
                df = self.data.get(working, pd.DataFrame())
                lp = self.live.get(working, {})
                prix = lp.get("prix")
        if df.empty or "Close" not in df.columns:
            return {"ticker": ticker, "prix": prix, "sma20": None, "sma50": None, "sma200": None, "rsi": None, "adx": None, "ath30": None} if prix else None
        close = df["Close"].dropna()
        prix_live = float(prix) if (prix and float(prix) > 0) else float(close.iloc[-1])
        return {"ticker": ticker, "prix": prix_live, "sma20": self.sma(close, 20), "sma50": self.sma(close, 50),
                "sma200": self.sma(close, 200), "rsi": self.rsi(close), "adx": None,
                "ath30": float(close.rolling(30, min_periods=1).max().iloc[-1])}

    def relative_strength_slope(self, ticker: str, days: int = 14) -> Optional[float]:
        return None

# -----------------------------------------------------------------------------
# MODULE 4 : ANALYTICS ENGINE (benchmark fixe MWRD.PA)
# -----------------------------------------------------------------------------
class AnalyticsEngine:
    WINDOW_1M = 21
    WINDOW_3M = 63
    WINDOW_6M = 126
    WINDOW_1Y = 252
    WINDOW_3Y = 756
    RISK_FREE_RATE = 0.025

    def __init__(self, dm: DataManager):
        self.dm = dm
        self.benchmark_ticker = BENCHMARK_WORLD_TICKER
        self.benchmark_df = dm.data.get(self.benchmark_ticker)
        if self.benchmark_df is None or self.benchmark_df.empty:
            for wt in WORLD_TICKERS:
                self.benchmark_df = dm.data.get(wt)
                if self.benchmark_df is not None and not self.benchmark_df.empty:
                    self.benchmark_ticker = wt
                    break

    def _get_price_column(self, df: pd.DataFrame) -> str:
        if "Adj Close" in df.columns:
            return "Adj Close"
        return "Close"

    def _get_asset_series(self, ticker: str) -> pd.Series:
        df = self.dm.data.get(ticker)
        if df is None or df.empty:
            return pd.Series(dtype=float)
        price_col = self._get_price_column(df)
        series = df[price_col].dropna().copy()
        series = series.sort_index()
        return series

    def _align_with_benchmark(self, ticker: str) -> Tuple[pd.Series, pd.Series]:
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

    def _compute_momentum(self, close: pd.Series, window: int) -> float:
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

    def compute_relative_strength(self, ticker: str) -> float:
        asset, bench = self._align_with_benchmark(ticker)
        if bench.empty or len(asset) < self.WINDOW_6M + 1 or len(bench) < self.WINDOW_6M + 1:
            return np.nan
        etf_ratio = asset.iloc[-1] / asset.iloc[-self.WINDOW_6M]
        bench_ratio = bench.iloc[-1] / bench.iloc[-self.WINDOW_6M]
        if bench_ratio <= 0 or etf_ratio <= 0:
            return np.nan
        return np.log(etf_ratio / bench_ratio) * 100.0

    def compute_volatility(self, ticker: str, window: int = WINDOW_1Y) -> float:
        close = self._get_asset_series(ticker)
        if len(close) < window + 1:
            return np.nan
        returns = close.pct_change().dropna().iloc[-window:]
        if len(returns) < 10:
            return np.nan
        return returns.std() * np.sqrt(252) * 100.0

    def compute_sharpe(self, ticker: str) -> float:
        close = self._get_asset_series(ticker)
        if len(close) < 10:
            return np.nan
        n = min(len(close) - 1, self.WINDOW_1Y)
        if n <= 0:
            return np.nan
        ret = close.iloc[-1] / close.iloc[-n] - 1.0
        ann_return = (1.0 + ret) ** (252.0 / n) - 1.0
        returns = close.pct_change().dropna().iloc[-n:]
        if len(returns) < 10:
            return np.nan
        ann_vol = returns.std() * np.sqrt(252)
        if ann_vol == 0 or np.isnan(ann_vol):
            return np.nan
        return (ann_return - self.RISK_FREE_RATE) / ann_vol

    def compute_sortino(self, ticker: str) -> float:
        close = self._get_asset_series(ticker)
        if len(close) < 10:
            return np.nan
        n = min(len(close) - 1, self.WINDOW_1Y)
        if n <= 0:
            return np.nan
        ret = close.iloc[-1] / close.iloc[-n] - 1.0
        ann_return = (1.0 + ret) ** (252.0 / n) - 1.0
        returns = close.pct_change().dropna().iloc[-n:]
        if len(returns) < 10:
            return np.nan
        daily_rf = (1.0 + self.RISK_FREE_RATE) ** (1.0 / 252) - 1.0
        downside = np.minimum(returns - daily_rf, 0)
        downside_dev = np.sqrt(np.mean(downside**2)) * np.sqrt(252)
        if downside_dev == 0 or np.isnan(downside_dev):
            return np.nan
        return (ann_return - self.RISK_FREE_RATE) / downside_dev

    def compute_information_ratio(self, ticker: str) -> float:
        asset, bench = self._align_with_benchmark(ticker)
        if bench.empty or len(asset) < 10 or len(bench) < 10:
            return np.nan
        n = min(min(len(asset)-1, len(bench)-1), self.WINDOW_1Y)
        if n <= 0:
            return np.nan
        ret_asset = asset.iloc[-1] / asset.iloc[-n] - 1.0
        ann_ret_asset = (1.0 + ret_asset) ** (252.0 / n) - 1.0
        ret_bench = bench.iloc[-1] / bench.iloc[-n] - 1.0
        ann_ret_bench = (1.0 + ret_bench) ** (252.0 / n) - 1.0
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

    def _compute_max_drawdown(self, series: pd.Series, window: int = None) -> float:
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

    def compute_rsi(self, ticker: str, period: int = 14) -> float:
        close = self._get_asset_series(ticker)
        if len(close) < period + 1:
            return np.nan
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty and not np.isnan(rsi.iloc[-1]) else np.nan

    def compute_distance_sma(self, ticker: str, window: int) -> float:
        close = self._get_asset_series(ticker)
        if len(close) < window:
            return np.nan
        sma = close.rolling(window).mean().iloc[-1]
        if np.isnan(sma) or sma == 0:
            return np.nan
        return ((close.iloc[-1] / sma) - 1.0) * 100.0

    def compute_correlation(self, ticker: str, window: int = 126) -> float:
        asset, bench = self._align_with_benchmark(ticker)
        if asset.empty or bench.empty or len(asset) < window + 1 or len(bench) < window + 1:
            return np.nan
        asset_returns = np.log(asset / asset.shift(1))
        bench_returns = np.log(bench / bench.shift(1))
        returns_df = pd.concat([asset_returns, bench_returns], axis=1, join="inner").dropna()
        if len(returns_df) < window:
            return np.nan
        returns_df = returns_df.iloc[-window:]
        correlation = returns_df.iloc[:, 0].corr(returns_df.iloc[:, 1])
        return float(correlation) if pd.notna(correlation) else np.nan

    def compute_all_metrics(self, ticker: str) -> dict:
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
            "max_drawdown": self.compute_max_drawdown_1y(ticker),
            "rsi": self.compute_rsi(ticker),
            "dist_sma20": self.compute_distance_sma(ticker, 20),
            "dist_sma50": self.compute_distance_sma(ticker, 50),
            "corr_1m": self.compute_correlation(ticker, self.WINDOW_1M),
            "corr_3m": self.compute_correlation(ticker, self.WINDOW_3M),
            "corr_6m": self.compute_correlation(ticker, self.WINDOW_6M),
            "corr_1y": self.compute_correlation(ticker, self.WINDOW_1Y),
        }
        return metrics

# -----------------------------------------------------------------------------
# MODULE 5 : SIGNAL ENGINE (inchangé)
# -----------------------------------------------------------------------------
class SignalEngine:
    def __init__(self, dm: DataManager, analytics: AnalyticsEngine):
        self.dm = dm
        self.analytics = analytics

    def compute_score(self, ticker: str) -> dict:
        m = self.analytics.compute_all_metrics(ticker)
        if not m:
            return {"score": 0, "metrics": {}, "status": "NO_DATA"}
        score = 0
        mom6 = m.get("mom_6m", 0)
        if mom6 > 15: score += 25
        elif mom6 > 8: score += 18
        elif mom6 > 3: score += 10
        elif mom6 > 0: score += 4
        rel = m.get("rel_strength", 0)
        if rel > 8: score += 20
        elif rel > 4: score += 14
        elif rel > 0: score += 7
        dist20 = m.get("dist_sma20", 0)
        if dist20 > 5: score += 15
        elif dist20 > 2: score += 10
        elif dist20 > 0: score += 5
        sharpe = m.get("sharpe", 0)
        if sharpe > 1.5: score += 15
        elif sharpe > 0.8: score += 10
        elif sharpe > 0.3: score += 5
        rsi = m.get("rsi", 50)
        if 55 <= rsi <= 70: score += 5
        elif rsi > 70: score += 2
        dd = m.get("max_drawdown_1y", -50)
        if dd > -10: score += 10
        elif dd > -20: score += 5
        vol = m.get("volatility", 30)
        if vol < 15: score += 10
        elif vol < 25: score += 5
        return {"score": min(100, score), "metrics": m, "status": "OK"}

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

# -----------------------------------------------------------------------------
# MODULE 6 : PERSISTENCE MANAGER (inchangé)
# -----------------------------------------------------------------------------
_CSV_COLS = ["date", "capital_cloture", "valeur_titres",
             "perf_jour", "perf_cumul", "regime", "score_regime",
             "poids_sat"]

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
            poids_sat REAL,
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
                 regime,score_regime,poids_sat)
                VALUES (?,?,?,?,?,?,?,?)
                """, (
                    row.get("date",""),
                    float(row.get("capital_cloture") or 0),
                    float(row.get("valeur_titres") or 0),
                    float(row.get("perf_jour") or 0),
                    float(row.get("perf_cumul") or 0),
                    row.get("regime",""),
                    int(float(row.get("score_regime") or 0)),
                    float(row.get("poids_sat") or 0),
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
                  score_regime: int, poids_sat: float) -> bool:
    today = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
    try:
        self._conn.execute("""
        INSERT OR REPLACE INTO snapshots
        (date,capital_cloture,valeur_titres,perf_jour,perf_cumul,
         regime,score_regime,poids_sat)
        VALUES (?,?,?,?,?,?,?,?)
        """, (today, round(capital_cloture, 2), round(valeur_titres, 2),
              round(perf_jour, 4), round(perf_cumul, 4), regime,
              score_regime, round(poids_sat, 4)))
        self._conn.commit()
        self._history_cache = None

        # Tentative de push GitHub, mais on ne bloque pas en cas d'échec
        if self._github_ok:
            try:
                self._push_to_github(self.load_history())
            except Exception as e:
                # On affiche un avertissement dans la console (ou on pourrait le remonter)
                print(f"⚠️ Échec de la synchronisation GitHub : {e}")
                # Mais on ne fait pas échouer la sauvegarde locale
        return True
    except Exception as e:
        # Affiche l'erreur dans l'interface Streamlit (utile pour le débogage)
        st.error(f"Erreur lors de l'enregistrement : {e}")
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

# -----------------------------------------------------------------------------
# MODULE 7 : PORTFOLIO CONFIG MANAGER & TRANSACTION ENGINE
# -----------------------------------------------------------------------------
class PortfolioConfigManager:
    def __init__(self, file_path: str = _PORTFOLIO_JSON):
        self.file_path = file_path

    def load_positions(self) -> List[Dict]:
        default_positions = [
            {"ticker": "WMMS.DE", "parts": 461.9561, "prm": 13.582, "account": "AV"},
            {"ticker": "DCAM.PA", "parts": 508.0000, "prm": 4.983, "account": "PEA"},
            {"ticker": "MWRD.PA", "parts": 16.6229, "prm": 149.718, "account": "AV"},
            {"ticker": "KRW.PA", "parts": 14.8501, "prm": 142.370, "account": "AV"},
            {"ticker": "CHIP.PA", "parts": 21.4922, "prm": 99.159, "account": "AV"},
        ]
        try:
            if os.path.exists(self.file_path) and os.stat(self.file_path).st_size > 0:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    existing_tickers = {pos["ticker"] for pos in data}
                    for default_pos in default_positions:
                        if default_pos["ticker"] not in existing_tickers:
                            data.append(default_pos)
                    return data
        except Exception:
            pass
        return default_positions

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

# -----------------------------------------------------------------------------
# MODULE 8 : MARKET REGIME ENGINE (inchangé)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# MODULE 9 : QUANT RISK ENGINE (inchangé)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# MODULE 10 : PORTFOLIO ENGINE (avec MWR par ancrage)
# -----------------------------------------------------------------------------
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
            "ticker": tk_id,
        })
    return result

class PortfolioEngine:
    def __init__(self, dm: DataManager, re: MarketRegimeEngine, qre: QuantRiskEngine):
        self.dm = dm
        self.re = re
        self.qre = qre

    def compute_adjusted_benchmark(self) -> Optional[float]:
        """
        Chaîne la performance ancrée (_ANCHOR_PERF à _ANCHOR_DATE) avec l'évolution
        du prix du benchmark World depuis cette date jusqu'à aujourd'hui.
        Formule : perf_adj = ((1 + ancre%) * (prix_actuel / prix_ancre) - 1) * 100
        """
        df = self.dm.data.get(BENCHMARK_WORLD_TICKER)
        if df is None or df.empty:
            for wt in WORLD_TICKERS:
                df = self.dm.data.get(wt)
                if df is not None and not df.empty:
                    break
        if df is None or df.empty or "Close" not in df.columns:
            return None

        close = df["Close"].dropna()
        anchor_dt = pd.to_datetime(_ANCHOR_DATE)
        idx_anchor = close.index[close.index <= anchor_dt]
        if len(idx_anchor) == 0:
            return None
        prix_anchor = float(close.loc[idx_anchor[-1]])

        prix_actuel, _, _ = self.dm.get_price_info([BENCHMARK_WORLD_TICKER] + WORLD_TICKERS)
        prix_actuel = float(prix_actuel) if prix_actuel else float(close.iloc[-1])

        if prix_anchor <= 0:
            return None
        ratio = prix_actuel / prix_anchor
        return ((1 + _ANCHOR_PERF / 100) * ratio - 1) * 100

    def compute_portfolio(self, positions_conf: List[Dict], capital_reel: float, ajustement_pat: float, bonus_fortuneo: float) -> Dict:
        positions_calc = []
        valeur_totale = valeur_veille = 0.0
        val_env = {"PEA": 0.0, "AV": 0.0}
        gan_env = {"PEA": 0.0, "AV": 0.0}
        for pos in positions_conf:
            prix, prev, tk_used = self.dm.get_price_info(pos["tickers"])
            env = pos["enveloppe"]
            if prix is None:
                positions_calc.append({
                    "nom": pos["nom"], "ticker": None, "prix": None, "valeur": 0.0,
                    "perf_pct": None, "var_jour_pct": 0.0, "var_jour_eur": 0.0,
                    "enveloppe": env, "parts": pos["parts"], "prm": pos["prm"], "gain_unit": 0
                })
                continue
            valeur = pos["parts"] * prix
            gain_unit = prix - pos["prm"]
            perf_pct = gain_unit / pos["prm"] * 100 if pos["prm"] != 0 else 0.0
            gain_total = gain_unit * pos["parts"]
            var_j_pct = (prix - prev) / prev * 100 if prev and prev != 0 else 0.0
            var_j_eur = (prix - prev) * pos["parts"] if prev else 0.0
            positions_calc.append({
                "nom": pos["nom"], "ticker": tk_used, "prix": prix, "valeur": valeur,
                "perf_pct": perf_pct, "var_jour_pct": var_j_pct, "var_jour_eur": var_j_eur,
                "enveloppe": env, "parts": pos["parts"], "prm": pos["prm"], "gain_unit": gain_unit
            })
            valeur_totale += valeur
            val_env[env] += valeur
            gan_env[env] += gain_total
            valeur_veille += pos["parts"] * (prev if prev else prix)
        solde_total = valeur_totale + ajustement_pat
        gain_reel = solde_total - capital_reel
        perf_tot_pct = (gain_reel / capital_reel * 100) if capital_reel else 0.0
        perf_j_eur = valeur_totale - valeur_veille
        perf_j_pct = perf_j_eur / valeur_veille * 100 if valeur_veille else 0.0
        return {
            "positions": positions_calc, "valeur_totale": valeur_totale, "solde_total": solde_total,
            "gain_reel": gain_reel, "perf_tot_pct": perf_tot_pct, "valeur_veille": valeur_veille,
            "val_env": val_env, "gain_env": gan_env, "ajustement_pat": ajustement_pat,
            "capital_reel": capital_reel, "perf_j_eur": perf_j_eur, "perf_j_pct": perf_j_pct
        }

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
        gap_adj = perf_tot_pct - perf_bench_adj if perf_bench_adj is not None else None
        gap_lumpsum = perf_tot_pct - perf_bench_lumpsum if perf_bench_lumpsum is not None else None
        perf_bench_j = (prix - prev) / prev * 100 if prev and prev != 0 else None
        return {
            "perf_bench": perf_bench_lumpsum, "perf_bench_adj": perf_bench_adj,
            "gap": gap_adj, "gap_lumpsum": gap_lumpsum, "prix": prix, "perf_bench_j": perf_bench_j
        }

    def compute_unified_score(self, ticker: str) -> Dict:
        info = self.dm.analyze_ticker(ticker)
        details = []
        score = 0
        rsi_v = info["rsi"] if info else None
        if rsi_v is not None:
            if rsi_v >= 70:
                ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Tendu"
            elif rsi_v <= 45:
                ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Faible"
            else:
                ms, mb, md = 1, "bull", f"RSI={rsi_v:.1f} Sain"
        else:
            ms, mb, md = 0, "neut", "RSI indisponible"
        details.append({"name": "Momentum", "score": ms, "badge": mb, "desc": md})
        score += ms
        if info and info["sma20"] is not None:
            if info["prix"] > info["sma20"]:
                ss, sb, sd = 1, "bull", f"Prix {info['prix']:.2f} > SMA20 {info['sma20']:.2f}"
            else:
                ss, sb, sd = -1, "bear", f"Prix {info['prix']:.2f} < SMA20 {info['sma20']:.2f}"
        else:
            ss, sb, sd = 0, "neut", "SMA20 indisponible"
        details.append({"name": "Structure", "score": ss, "badge": sb, "desc": sd})
        score += ss
        rs_slope = self.dm.relative_strength_slope(ticker, 14)
        if rs_slope is not None:
            if rs_slope > 0:
                ls, lb, ld = 2, "bull", f"Pente={rs_slope:+.5f} Leader ✓"
            else:
                ls, lb, ld = -2, "bear", f"Pente={rs_slope:.5f} Lagger"
        else:
            ls, lb, ld = 0, "neut", "Données insuffisantes"
        details.append({"name": "Leadership", "score": ls, "badge": lb, "desc": ld})
        score += ls
        return {
            "total": max(-4, min(4, score)), "momentum": ms, "structure": ss, "leadership": ls,
            "details": details, "rsi_raw": rsi_v, "adx_raw": info["adx"] if info else None
        }

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
        return {
            "total": max(-1.0, min(1.0, total)), "trend": trend_raw, "macro": macro_raw,
            "leadership": leader_raw, "risk_vol": vol_raw
        }

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
        return {
            "nom": nom, "unified_score": unified["total"], "strat_score": strat4c["total"],
            "strat4c": strat4c, "base_weight": base_w, "regime_mult": regime_mult,
            "confidence": confidence, "target_pct": target_pct, "current_pct": current_pct,
            "current_eur": current_val, "target_eur": target_eur, "delta_pct": delta_pct,
            "delta_eur": current_val - target_eur, "action": action,
            "regime_label": regime["confirmed_label"]
        }

    def _get_base_weight(self, score: int, initial_target: float) -> float:
        if score >= 3: return initial_target
        elif score >= 1: return 0.20
        elif score >= -1: return 0.15
        else: return 0.05

    def evaluate_sentinelles(self) -> Tuple[str, str, List[Dict]]:
        alerts, rows = [], []
        for name, tickers in SENTINELLES.items():
            info = None
            for tk in tickers:
                info = self.dm.analyze_ticker(tk)
                if info: break
            alerte = ""
            if info and info["sma20"] and info["prix"] and info["prix"] < info["sma20"]:
                alerte = "⚠"; alerts.append(name)
            rows.append({
                "Sentinelle": name,
                "Prix": f"{info['prix']:.2f}" if info and info['prix'] else "N/A",
                "SMA20": f"{info['sma20']:.2f}" if (info and info["sma20"]) else "N/A",
                "RSI": f"{info['rsi']:.1f}" if (info and info["rsi"]) else "N/A",
                "Alerte": alerte
            })
        msg = " | ".join([f"⚠ {a} sous SMA20" for a in alerts]) if alerts else "✅ Sentinelles OK"
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

    def determine_phase(self, gap, etf_infos) -> Tuple[str, str]:
        if gap is None:
            return "⏳ Phase indéterminée --- Données insuffisantes", "#374151"
        if gap < 0:
            return "📉 Phase 1 : Reconquête --- Revenir à l'équilibre vs World AV", "#7F1D1D"
        signals = []
        safe_infos = etf_infos or {}
        for ticker, info in safe_infos.items():
            if info and info.get("sma20") and info.get("prix") and info["prix"] < info["sma20"]:
                short_name = ETF_LIBRARY.get(ticker, {}).get("nom", ticker)[:8]
                signals.append(f"{short_name}<SMA20")
        if signals:
            return f"🔄 Phase 3 : Rotation --- Sécuriser les gains ({', '.join(signals)})", "#78350F"
        return "🚀 Phase 2 : Alpha --- Battre le MSCI World", "#14532D"

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
            start_date_effective = start_date
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
        env_positions = [p for p in positions_calc if p.get("enveloppe") == envelope and p.get("valeur", 0) > 0]
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
        else:
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

# -----------------------------------------------------------------------------
# MODULE 11 : QUANT ALERT ENGINE (ancien — conservé pour compatibilité mais plus utilisé)
# -----------------------------------------------------------------------------
class QuantAlertEngine:
    def __init__(self, dm: DataManager):
        self.dm = dm
        self.COST_BPS = 0.0010
        self.EXPOSURE_PALIERS = [0.0, 0.25, 0.50, 0.75, 1.0]

    def _compute_indicators(self, ticker: str) -> Dict:
        df = self.dm.data.get(ticker)
        if df is None or df.empty:
            return {}
        close = df["Close"].dropna()
        if len(close) < 50:
            return {}
        rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
        macd = ta.trend.MACD(close).macd_diff().iloc[-1]
        vol_ratio = close.pct_change().iloc[-20:].std() / close.pct_change().iloc[-60:].std() if len(close) >= 60 else 1.0
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma20
        dist_sma20 = (close.iloc[-1] / sma20 - 1) * 100
        dist_sma50 = (close.iloc[-1] / sma50 - 1) * 100 if len(close) >= 50 else dist_sma20
        mom5 = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0
        mom10 = (close.iloc[-1] / close.iloc[-11] - 1) * 100 if len(close) >= 11 else 0
        vix = self.dm.live.get("^VIX", {}).get("prix", 20)
        vix_ratio = vix / 20.0
        return {
            "rsi": rsi,
            "macd": macd,
            "vol_ratio": vol_ratio,
            "dist_sma20": dist_sma20,
            "dist_sma50": dist_sma50,
            "mom5": mom5,
            "mom10": mom10,
            "vix_ratio": vix_ratio,
            "price": close.iloc[-1]
        }

    def _prob_baisse(self, indicators: Dict, horizon: int) -> float:
        if not indicators:
            return 0.0
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", 0)
        dist20 = indicators.get("dist_sma20", 0)
        dist50 = indicators.get("dist_sma50", 0)
        mom5 = indicators.get("mom5", 0)
        vol_ratio = indicators.get("vol_ratio", 1.0)
        vix_ratio = indicators.get("vix_ratio", 1.0)

        score = 0.0
        if rsi > 70:
            score += (rsi - 70) / 30 * 0.6
        elif rsi < 30:
            score += (30 - rsi) / 30 * 0.4
        if macd < 0:
            score += min(-macd / 5, 0.6)
        if dist20 < -2:
            score += min(abs(dist20) / 10, 0.5)
        if dist50 < -3:
            score += min(abs(dist50) / 15, 0.5)
        if mom5 < -1:
            score += min(abs(mom5) / 10, 0.4)
        if vol_ratio > 1.2:
            score += min((vol_ratio - 1.2) * 0.4, 0.3)
        if vix_ratio > 1.1:
            score += min((vix_ratio - 1.1) * 0.3, 0.2)

        factor = 1.0 / horizon
        prob = min(score * factor, 0.65)
        if prob > 0.3:
            prob += 0.1
        return max(0.0, min(1.0, prob))

    def compute_alert(self, ticker: str, current_price: float, position_value: float) -> Optional[Dict]:
        indicators = self._compute_indicators(ticker)
        if not indicators or current_price is None:
            return None

        p1 = self._prob_baisse(indicators, 1)
        p2 = self._prob_baisse(indicators, 2)
        p3 = self._prob_baisse(indicators, 3)

        vol = self.dm.analyze_ticker(ticker).get("volatility", 20) if self.dm.analyze_ticker(ticker) else 20
        expected_drop = (abs(indicators.get("dist_sma20", 0)) + 0.5 * abs(indicators.get("dist_sma50", 0))) / 100.0
        expected_drop = max(0.005, min(0.05, expected_drop))

        cost = self.COST_BPS
        ev = p1 * expected_drop - (1 - p1) * cost

        ev_thresholds = [0.001, 0.003, 0.006]
        sell_pct = 0.0
        if ev > ev_thresholds[0]:
            sell_pct = 0.25
        if ev > ev_thresholds[1]:
            sell_pct = 0.50
        if ev > ev_thresholds[2]:
            sell_pct = 0.75
        sell_amount = sell_pct * position_value

        if p2 < 0.3 * p1 and p3 < 0.2 * p1:
            sell_pct = min(sell_pct, 0.25)

        return {
            "ticker": ticker,
            "price": current_price,
            "prob_j1": p1,
            "prob_j2": p2,
            "prob_j3": p3,
            "expected_drop": expected_drop,
            "ev": ev,
            "sell_pct": sell_pct,
            "sell_amount": sell_amount,
            "position_value": position_value,
            "cost_bps": self.COST_BPS * 100,
            "indicators": indicators
        }

# -----------------------------------------------------------------------------
# MODULE 12 : PEDAGOGIC ENGINE (avec correction de la série initiale)
# -----------------------------------------------------------------------------
class PedagogicEngine:
    def translate_volatility(self, vol: Optional[float], asset_name: str) -> Dict:
        if vol is None:
            return {"value": "N/A", "emoji": "❓", "level": "orange", "title": f"Agitation de {asset_name}",
                    "explain": "Donnée indisponible.", "scale": [], "action": "Revérifier plus tard."}
        pct = vol * 100
        if pct < 15:
            emoji, level, msg, action = "😌", "green", "L'ETF est calme et stable.", "Aucune vigilance."
        elif pct < 25:
            emoji, level, msg, action = "😐", "orange", "L'ETF bouge normalement.", "Surveillez."
        else:
            emoji, level, msg, action = "😰", "red", "L'ETF est agité, variations brutales possibles.", "Réduisez éventuellement."
        return {"value": f"{pct:.1f}%", "emoji": emoji, "level": level, "title": f"Agitation de {asset_name}",
                "explain": f"{msg}\n\nPlus ce chiffre est élevé, plus l'ETF peut perdre ou gagner brusquement.",
                "scale": [{"label": "< 15% --- Calme", "cls": "scale-green"},
                          {"label": "15-25% --- Normal", "cls": "scale-orange"},
                          {"label": "> 25% --- Risqué", "cls": "scale-red"}], "action": action}

    def translate_beta(self, beta: Optional[float], asset_name: str) -> Dict:
        if beta is None:
            return {"value": "N/A", "emoji": "❓", "level": "orange", "title": "Sensibilité au marché",
                    "explain": "Donnée indisponible.", "scale": [], "action": "Revérifier plus tard."}
        if beta < 0:
            emoji, level, msg, action = "🔄", "orange", "ETF à contre-courant du marché.", "Défensif intéressant."
        elif beta < 0.8:
            emoji, level, msg, action = "🛡", "green", f"Bouge {(1-beta)*100:.0f}% moins que le marché.", "Protège bien en baisse."
        elif beta < 1.2:
            emoji, level, msg, action = "⚖", "green", "Suit le marché de façon équilibrée.", "Comportement neutre."
        elif beta < 1.8:
            emoji, level, msg, action = "⚡", "orange", f"Bouge {(beta-1)*100:.0f}% plus violemment.", "Limitez la position."
        else:
            emoji, level, msg, action = "🌋", "red", "Très sensible aux mouvements du marché.", "Position risquée."
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
        if abs_dd < 3:
            emoji, level, msg, action = "🏔", "green", f"{asset_name} est proche de son sommet.", "Aucune alerte."
        elif abs_dd < 8:
            emoji, level, msg, action = "📉", "orange", f"Recul de {abs_dd:.1f}%, repli normal.", "Surveillance normale."
        elif abs_dd < 15:
            emoji, level, msg, action = "⚠", "orange", f"Recul de {abs_dd:.1f}%, correction significative.", "Vérifiez le stop-loss."
        else:
            emoji, level, msg, action = "🚨", "red", f"Chute de {abs_dd:.1f}%, perte importante.", "Envisagez de réduire."
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
            "Neutre": {"emoji": "⚖", "level": "orange", "explain": "Pas de direction claire. Autant de signaux positifs que négatifs.",
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

    def get_weekly_performances(self, dm: DataManager, ticker_key: str, n_weeks: int = 5) -> Tuple[List[str], List[float], List[float]]:
        meta = ETF_LIBRARY.get(ticker_key, {})
        possible_tickers = [meta.get("yf")] + meta.get("yf_fallbacks", [])
        possible_tickers = [t for t in possible_tickers if t]
        sat_df = None
        for t in possible_tickers:
            df = dm.data.get(t)
            if df is not None and not df.empty and "Close" in df.columns:
                sat_df = df
                break
        if sat_df is None:
            return [], [], []

        # Utiliser get_world_series pour le benchmark
        world = get_world_series(dm, exclude_ticker=ticker_key)
        if world.empty:
            return [], [], []
        sat_close = sat_df["Close"].dropna()
        common = sat_close.index.intersection(world.index)
        if len(common) < 10:
            return [], [], []
        sat_w = sat_close[common].resample("W").last()
        world_w = world[common].resample("W").last()
        common_w = sat_w.index.intersection(world_w.index)
        if len(common_w) < 2:
            return [], [], []
        sat_w = sat_w[common_w]; world_w = world_w[common_w]
        sat_ret = sat_w.pct_change().dropna() * 100
        world_ret = world_w.pct_change().dropna() * 100
        n = min(n_weeks, len(sat_ret))
        if n == 0:
            return [], [], []
        sat_ret = sat_ret.iloc[-n:]; world_ret = world_ret.iloc[-n:]
        labels = ["En cours" if i == n-1 else f"S-{n-1-i}" for i in range(n)]
        return labels, list(sat_ret.values), list(world_ret.values)

    def get_portfolio_weekly_performances(self, dm: DataManager, positions: List[Dict], n_weeks: int = 5) -> Tuple[List[str], List[float], List[float]]:
        """
        Calcule les performances hebdomadaires du portefeuille global (pondéré par les parts)
        vs le MSCI World.
        positions : liste de dict avec 'ticker' et 'parts'
        Retourne : labels, perf_portefeuille (%), perf_world (%)
        """
        # Récupérer les séries de prix pour chaque ticker en utilisant les fallbacks
        price_series = {}
        for pos in positions:
            ticker = pos.get('ticker')
            if not ticker:
                continue
            meta = ETF_LIBRARY.get(ticker, {})
            candidates = [meta.get('yf')] + meta.get('yf_fallbacks', [])
            candidates = [t for t in candidates if t]
            found = False
            for t in candidates:
                df = dm.data.get(t)
                if df is not None and not df.empty and 'Close' in df.columns:
                    price_series[ticker] = df['Close'].dropna()
                    found = True
                    break
            if not found:
                continue

        if not price_series:
            return [], [], []

        # Aligner les dates communes
        common_dates = None
        for s in price_series.values():
            if common_dates is None:
                common_dates = s.index
            else:
                common_dates = common_dates.intersection(s.index)
        if common_dates is None or len(common_dates) < 10:
            return [], [], []

        # CORRECTION : initialiser avec 0.0 au lieu de dtype=float (NaN)
        total_value = pd.Series(0.0, index=common_dates)

        for ticker, s in price_series.items():
            parts = next((pos['parts'] for pos in positions if pos.get('ticker') == ticker), 0)
            if parts == 0:
                continue
            s_aligned = s.loc[common_dates]
            total_value += s_aligned * parts
        if total_value.empty:
            return [], [], []

        # Resampler par semaine (dernier jour de la semaine)
        port_weekly = total_value.resample('W').last()

        # World (on n'exclut rien)
        world = get_world_series(dm, exclude_ticker=None)
        if world.empty:
            return [], [], []
        world_weekly = world.resample('W').last()

        # Aligner les semaines communes
        common_weeks = port_weekly.index.intersection(world_weekly.index)
        if len(common_weeks) < 2:
            return [], [], []
        port_weekly = port_weekly.loc[common_weeks]
        world_weekly = world_weekly.loc[common_weeks]

        # Calculer les rendements hebdomadaires
        port_ret = port_weekly.pct_change().dropna() * 100
        world_ret = world_weekly.pct_change().dropna() * 100
        n = min(n_weeks, len(port_ret))
        if n == 0:
            return [], [], []
        port_ret = port_ret.iloc[-n:]
        world_ret = world_ret.iloc[-n:]

        labels = ["En cours" if i == n-1 else f"S-{n-1-i}" for i in range(n)]
        return labels, list(port_ret.values), list(world_ret.values)

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

    def translate_simple_score(self, score_raw: int) -> Dict:
        mapping = {-4:0, -3:0, -2:1, -1:2, 0:2, 1:3, 2:3, 3:4, 4:5}
        simple = mapping.get(max(-4, min(4, score_raw)), 2)
        msgs = {
            5: ("⭐⭐⭐⭐⭐", "Momentum très fort", "ring-5", "Tout est au vert.", "Maintenez."),
            4: ("⭐⭐⭐⭐☆", "Tendance saine", "ring-4", "Progresse bien.", "Maintenez / renforcez."),
            3: ("⭐⭐⭐☆☆", "Situation neutre", "ring-3", "Stable.", "Maintenez."),
            2: ("⭐⭐☆☆☆", "Fragilité", "ring-2", "Signes de faiblesse.", "Prudence."),
            1: ("⭐☆☆☆☆", "Risque élevé", "ring-1", "Difficultés.", "Envisagez de réduire."),
            0: ("☆☆☆☆☆", "Danger", "ring-0", "Très dégradé.", "Réduction forte.")
        }
        stars, label, ring_cls, explain, action = msgs[simple]
        return {"score": simple, "stars": stars, "label": label, "ring_cls": ring_cls, "explain": explain, "action": action}

    def translate_sentinelles(self, sent_rows: List[Dict], sector: str) -> Dict:
        if sector == "korea":
            names = ["Samsung", "SK Hynix"]
        elif sector == "chip":
            names = ["TSMC", "NVIDIA", "AMD", "Intel"]
        else:
            names = []
        alerts = [r for r in sent_rows if r.get("Sentinelle") in names and r.get("Alerte") == "⚠"]
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

# -----------------------------------------------------------------------------
# MODULE 13 : STRATEGIC ENGINE (inchangé)
# -----------------------------------------------------------------------------
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
        if total >= 4:
            verdict, verdict_cls = "✅ Conditions très favorables --- Maintien recommandé", "verdict-green"
        elif total >= 3:
            verdict, verdict_cls = "🟡 Conditions correctes --- Maintien avec surveillance", "verdict-orange"
        elif total >= 2:
            verdict, verdict_cls = "🟠 Conditions mitigées --- Prudence conseillée", "verdict-orange"
        else:
            verdict, verdict_cls = "🔴 Conditions défavorables --- Réduction recommandée", "verdict-red"
        return {"total": total, "details": details, "verdict": verdict, "verdict_cls": verdict_cls}

# -----------------------------------------------------------------------------
# MODULE 14 : FISCAL
# -----------------------------------------------------------------------------
def net_apres_impots(enveloppe: str, montant: float, val_poche: float, gain_poche: float) -> Tuple[float, str]:
    if montant <= 0:
        return 0.0, ""
    if montant > val_poche:
        return 0.0, "⚠ Montant supérieur à la valeur de la poche"
    ratio_gain = gain_poche / val_poche if val_poche else 0
    gain_retrait = montant * ratio_gain
    now_tz = datetime.now(ZoneInfo("Europe/Paris"))
    if enveloppe == "PEA":
        limite = datetime(2031, 4, 1, tzinfo=ZoneInfo("Europe/Paris"))
        if now_tz < limite:
            return 0.0, "⚠ Retrait PEA impossible avant le 01/04/2031 (fermeture enveloppe)"
        return montant - 0.172 * gain_retrait, ""
    if enveloppe == "AV":
        if now_tz < datetime(2033, 9, 17, tzinfo=ZoneInfo("Europe/Paris")):
            return montant - 0.30 * gain_retrait, ""
        ps = 0.172 * gain_retrait
        ir = 0.128 * max(0, gain_retrait - 9200)
        return montant - ps - ir, ""
    return montant, ""

# =============================================================================
# MODULE 18 : INDICATOR ENGINE (indicateurs complets pour Decision Engine)
# =============================================================================
class IndicatorEngine:
    def __init__(self, dm: DataManager):
        self.dm = dm

    def _series(self, ticker: str) -> pd.Series:
        df = self.dm.data.get(ticker)
        if df is None or df.empty or "Close" not in df.columns:
            return pd.Series(dtype=float)
        return df["Close"].dropna().sort_index()

    def compute(self, ticker: str, world_ticker: str = None) -> Optional[Dict]:
        close = self._series(ticker)
        if close.empty or len(close) < 60:
            return None
        world = get_world_series(self.dm, exclude_ticker=ticker if ticker == BENCHMARK_WORLD_TICKER else None)
        common = close.index.intersection(world.index) if not world.empty else pd.Index([])

        def ret_n(s, n):
            return float(s.iloc[-1] / s.iloc[-n-1] - 1) if len(s) > n else None

        def alpha_n(n):
            if len(common) <= n:
                return None
            a = close.loc[common]; w = world.loc[common]
            ra = ret_n(a, n); rw = ret_n(w, n)
            return (ra - rw) if (ra is not None and rw is not None) else None

        sma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        sma100 = close.rolling(100).mean().iloc[-1] if len(close) >= 100 else None
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        price = float(close.iloc[-1])

        trend_score = 0
        if sma20 is not None and price > sma20: trend_score += 1
        if sma20 is not None and sma50 is not None and sma20 > sma50: trend_score += 1
        if sma50 is not None and sma200 is not None and sma50 > sma200: trend_score += 1
        if sma200 is not None and price > sma200: trend_score += 1

        # Relative Strength
        rs_ma20 = rs_ma50 = rs_val = None
        if len(common) >= 50:
            rs_series = (close.loc[common] / world.loc[common]).dropna()
            if len(rs_series) >= 50:
                rs_val = float(rs_series.iloc[-1])
                rs_ma20 = float(rs_series.rolling(20).mean().iloc[-1])
                rs_ma50 = float(rs_series.rolling(50).mean().iloc[-1])

        relative_trend_score = 0
        a20, a60 = alpha_n(20), alpha_n(60)
        if a20 is not None and a20 > 0: relative_trend_score += 1
        if a60 is not None and a60 > 0: relative_trend_score += 1
        if rs_val is not None and rs_ma20 is not None and rs_val > rs_ma20: relative_trend_score += 1
        if rs_ma20 is not None and rs_ma50 is not None and rs_ma20 > rs_ma50: relative_trend_score += 1

        # Momentum + accélération
        mom5 = ret_n(close, 5); mom20 = ret_n(close, 20); mom60 = ret_n(close, 60)
        mom20_5dago = None
        if len(close) > 25:
            past = close.iloc[:-5]
            mom20_5dago = ret_n(past, 20)
        mom_accel = (mom20 - mom20_5dago) if (mom20 is not None and mom20_5dago is not None) else None

        # Drawdown
        rmax = close.cummax()
        dd_series = (close / rmax - 1)
        dd_current = float(dd_series.iloc[-1])
        dd_5d = ret_n(close, 5)
        dd_10d = ret_n(close, 10)
        dd_max20 = float(dd_series.iloc[-20:].min()) if len(dd_series) >= 20 else None
        dd_max60 = float(dd_series.iloc[-60:].min()) if len(dd_series) >= 60 else None
        dd_max120 = float(dd_series.iloc[-120:].min()) if len(dd_series) >= 120 else None

        # Volatilité
        returns = close.pct_change().dropna()
        vol20 = float(returns.iloc[-20:].std() * np.sqrt(252)) if len(returns) >= 20 else None
        vol60 = float(returns.iloc[-60:].std() * np.sqrt(252)) if len(returns) >= 60 else None
        vol120 = float(returns.iloc[-120:].std() * np.sqrt(252)) if len(returns) >= 120 else None
        vol_ratio = (vol20 / vol60) if (vol20 and vol60) else None
        vol_shock = (vol20 / vol120) if (vol20 and vol120) else None

        # Beta / corrélation
        beta60 = corr20 = corr60 = corr120 = None
        if len(common) >= 60:
            r_a = close.loc[common].pct_change().dropna()
            r_w = world.loc[common].pct_change().dropna()
            common_r = r_a.index.intersection(r_w.index)
            if len(common_r) >= 60:
                a60_ = r_a.loc[common_r].iloc[-60:]; w60_ = r_w.loc[common_r].iloc[-60:]
                cov = np.cov(a60_, w60_)[0, 1]; var = np.var(w60_)
                beta60 = float(cov / var) if var > 1e-12 else None
            for n, name in [(20, "corr20"), (60, "corr60"), (120, "corr120")]:
                if len(common_r) >= n:
                    c = r_a.loc[common_r].iloc[-n:].corr(r_w.loc[common_r].iloc[-n:])
                    if name == "corr20": corr20 = float(c) if pd.notna(c) else None
                    elif name == "corr60": corr60 = float(c) if pd.notna(c) else None
                    else: corr120 = float(c) if pd.notna(c) else None

        # Z-score
        z20 = None
        if len(returns) >= 21:
            r1d = returns.iloc[-1]
            mu = returns.iloc[-21:-1].mean(); sd = returns.iloc[-21:-1].std()
            z20 = float((r1d - mu) / sd) if sd > 1e-9 else None

        rsi14 = None
        if len(close) >= 15:
            delta = close.diff()
            gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
            rs_ = gain / loss.replace(0, np.nan)
            rsi14 = float((100 - 100/(1+rs_)).iloc[-1])

        return {
            "ticker": ticker, "price": price, "date": close.index[-1],
            "sma20": sma20, "sma50": sma50, "sma100": sma100, "sma200": sma200,
            "trend_score": trend_score,
            "alpha3": alpha_n(3), "alpha5": alpha_n(5), "alpha10": alpha_n(10),
            "alpha20": a20, "alpha60": a60, "alpha120": alpha_n(120),
            "rs": rs_val, "rs_ma20": rs_ma20, "rs_ma50": rs_ma50,
            "relative_trend_score": relative_trend_score,
            "mom5": mom5, "mom20": mom20, "mom60": mom60, "mom_accel": mom_accel,
            "dd_current": dd_current, "dd_5d": dd_5d, "dd_10d": dd_10d,
            "dd_max20": dd_max20, "dd_max60": dd_max60, "dd_max120": dd_max120,
            "vol20": vol20, "vol60": vol60, "vol120": vol120,
            "vol_ratio": vol_ratio, "vol_shock": vol_shock,
            "beta60": beta60, "corr20": corr20, "corr60": corr60, "corr120": corr120,
            "z20": z20, "rsi14": rsi14,
            "n_history": len(close),
        }

# =============================================================================
# MODULE 19 : WORLD REGIME ENGINE (RISK_ON / NEUTRAL / RISK_OFF / CRASH)
# =============================================================================
class WorldRegimeEngine:
    def __init__(self, dm: DataManager, ie: IndicatorEngine):
        self.dm = dm
        self.ie = ie

    def get_regime(self) -> Dict:
        world_tk = None
        for wt in [BENCHMARK_WORLD_TICKER] + WORLD_TICKERS:
            df = self.dm.data.get(wt)
            if df is not None and not df.empty:
                world_tk = wt
                break
        if world_tk is None:
            return {"regime": "NEUTRAL", "reason": "Données World indisponibles", "indicators": {}}

        # indicateurs "bruts" du World lui-même (pas d'alpha, il est comparé à lui-même)
        close = self.dm.data[world_tk]["Close"].dropna()
        sma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        price = float(close.iloc[-1])
        returns = close.pct_change().dropna()
        vol20 = returns.iloc[-20:].std() * np.sqrt(252) if len(returns) >= 20 else None
        vol120 = returns.iloc[-120:].std() * np.sqrt(252) if len(returns) >= 120 else None
        vol_shock = (vol20 / vol120) if (vol20 and vol120) else 1.0
        rmax = close.cummax()
        dd_current = float((close / rmax - 1).iloc[-1])

        above20 = sma20 is not None and price > sma20
        above50 = sma50 is not None and price > sma50
        above200 = sma200 is not None and price > sma200
        sma50_above200 = sma50 is not None and sma200 is not None and sma50 > sma200

        if above200 and sma50_above200 and above20 and vol_shock < 1.2:
            regime = "RISK_ON"
        elif (not above50 and sma50 is not None and sma20 is not None and sma20 < sma50) or vol_shock > 1.3:
            regime = "RISK_OFF"
        else:
            regime = "NEUTRAL"

        if (not above200) and dd_current < -0.10 and vol_shock > 1.4:
            regime = "CRASH"

        return {
            "regime": regime, "price": price, "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "vol_shock": round(vol_shock, 2) if vol_shock else None,
            "drawdown": round(dd_current * 100, 2),
            "world_ticker": world_tk,
        }

# =============================================================================
# MODULE 20 : CRASH PROTECTION & UNDERPERFORMANCE ENGINES
# =============================================================================
class CrashProtectionEngine:
    def compute(self, ind: Dict, world_regime: str) -> Dict:
        score, reasons = 0, []
        if ind["sma20"] and ind["price"] < ind["sma20"]:
            score += 1; reasons.append("Prix < SMA20")
        if ind["sma20"] and ind["sma50"] and ind["sma20"] < ind["sma50"]:
            score += 1; reasons.append("SMA20 < SMA50")
        if ind["alpha20"] is not None and ind["alpha20"] < 0:
            score += 1; reasons.append(f"Alpha20 négatif ({ind['alpha20']*100:.1f}%)")
        if ind["alpha60"] is not None and ind["alpha60"] < 0:
            score += 1; reasons.append(f"Alpha60 négatif ({ind['alpha60']*100:.1f}%)")
        if ind["vol_ratio"] is not None and ind["vol_ratio"] > CRASH_THRESHOLDS["vol_ratio"]:
            score += 1; reasons.append(f"Vol20/Vol60 = {ind['vol_ratio']:.2f}")
        if ind["dd_5d"] is not None and ind["dd_5d"] < CRASH_THRESHOLDS["dd_5d"]:
            score += 1; reasons.append(f"Chute {ind['dd_5d']*100:.1f}% en 5j")
        if world_regime in ("RISK_OFF", "CRASH"):
            score += 1; reasons.append(f"World en régime {world_regime}")

        level = "LOW"
        for lo, hi, lbl in CRASH_LEVELS:
            if lo <= score <= hi:
                level = lbl
        return {"score": score, "level": level, "reasons": reasons}


class UnderperformanceEngine:
    def compute(self, ind: Dict) -> Dict:
        score, reasons = 0, []
        a20, a60, a120 = ind.get("alpha20"), ind.get("alpha60"), ind.get("alpha120")
        if a20 is not None and a20 < UNDERPERF_THRESHOLDS["alpha20"]:
            score += 1; reasons.append(f"Alpha20 = {a20*100:.1f}%")
        if a60 is not None and a60 < UNDERPERF_THRESHOLDS["alpha60"]:
            score += 1; reasons.append(f"Alpha60 = {a60*100:.1f}%")
        if a120 is not None and a120 < 0:
            score += 1; reasons.append(f"Alpha120 = {a120*100:.1f}%")
        if ind.get("relative_trend_score", 4) <= 1:
            score += 1; reasons.append("Force relative faible")
        return {"score": score, "max_score": 4, "reasons": reasons}

# =============================================================================
# MODULE 21 : EMPIRICAL ANALOG ENGINE (baseline historique — Priorité 2)
# =============================================================================
class EmpiricalAnalogEngine:
    """
    Recherche dans l'historique du ticker les jours où le crash_score (ou
    underperf_score) était dans la même fourchette qu'aujourd'hui, puis
    regarde ce qui s'est passé dans les N jours suivants (alpha vs World).
    Ne fait AUCUNE prédiction — affiche un fait statistique avec sa taille
    d'échantillon, comme demandé au point 29/33 de la spec.
    """
    def __init__(self, dm: DataManager, ie: IndicatorEngine):
        self.dm = dm
        self.ie = ie

    def analyze(self, ticker: str, current_score: int, score_type: str = "crash",
                horizon: int = 20, tolerance: int = 1) -> Dict:
        df = self.dm.data.get(ticker)
        world = get_world_series(self.dm, exclude_ticker=ticker)
        if df is None or df.empty or world.empty:
            return {"available": False}
        close = df["Close"].dropna()
        common = close.index.intersection(world.index)
        if len(common) < 250:
            return {"available": False}

        close_c = close.loc[common]
        world_c = world.loc[common]
        returns = close_c.pct_change()

        sma20 = close_c.rolling(20).mean()
        sma50 = close_c.rolling(50).mean()
        vol20 = returns.rolling(20).std() * np.sqrt(252)
        vol60 = returns.rolling(60).std() * np.sqrt(252)
        vol_ratio = vol20 / vol60
        alpha20 = (close_c / close_c.shift(20) - 1) - (world_c / world_c.shift(20) - 1)
        alpha60 = (close_c / close_c.shift(60) - 1) - (world_c / world_c.shift(60) - 1)
        dd_5d = close_c / close_c.shift(5) - 1

        # Reconstruction approximative du score historique jour par jour
        hist_score = pd.Series(0, index=common)
        hist_score += (close_c < sma20).astype(int)
        hist_score += (sma20 < sma50).astype(int)
        hist_score += (alpha20 < 0).astype(int)
        hist_score += (alpha60 < 0).astype(int)
        hist_score += (vol_ratio > CRASH_THRESHOLDS["vol_ratio"]).astype(int)
        hist_score += (dd_5d < CRASH_THRESHOLDS["dd_5d"]).astype(int)

        # Jours analogues (hors 20 derniers jours pour éviter chevauchement avec aujourd'hui)
        mask = (hist_score - current_score).abs() <= tolerance
        analog_dates = common[mask][:-horizon] if horizon < len(common) else common[mask]
        analog_dates = [d for d in analog_dates if d in common[:-horizon]]

        if len(analog_dates) < 15:
            return {"available": False, "n_samples": len(analog_dates)}

        future_alphas = []
        for d in analog_dates:
            try:
                idx = common.get_loc(d)
                if idx + horizon >= len(common):
                    continue
                d_future = common[idx + horizon]
                etf_ret = close_c.loc[d_future] / close_c.loc[d] - 1
                world_ret = world_c.loc[d_future] / world_c.loc[d] - 1
                future_alphas.append(etf_ret - world_ret)
            except Exception:
                continue

        if len(future_alphas) < 15:
            return {"available": False, "n_samples": len(future_alphas)}

        arr = np.array(future_alphas)
        hit_rate_neg = float((arr < 0).mean())
        expected_alpha = float(arr.mean())

        if len(arr) < 30:
            confidence = "LOW"
        elif len(arr) < 75:
            confidence = "MEDIUM"
        else:
            confidence = "HIGH"

        if hit_rate_neg < 0.40:
            proba_label = "FAIBLE"
        elif hit_rate_neg < 0.60:
            proba_label = "MODÉRÉE"
        else:
            proba_label = "ÉLEVÉE"

        return {
            "available": True, "n_samples": len(arr),
            "expected_alpha": expected_alpha, "hit_rate_negative": hit_rate_neg,
            "proba_label": proba_label, "confidence": confidence, "horizon": horizon,
        }

# =============================================================================
# MODULE 22 : LINXEA EXECUTION ENGINE
# =============================================================================
class LinxeaExecutionEngine:
    def __init__(self, dm: DataManager, analog: EmpiricalAnalogEngine):
        self.dm = dm
        self.analog = analog

    def compute_execution_date(self, signal_dt: datetime) -> Tuple[datetime, int]:
        """Retourne (date_effet_estimee, risk_latency_days)."""
        cutoff = signal_dt.replace(hour=LINXEA_CUTOFF_HOUR, minute=LINXEA_CUTOFF_MINUTE,
                                     second=0, microsecond=0)
        d = signal_dt.date()
        latency = 1 if signal_dt <= cutoff else 2  # avant cutoff = J+1, après = J+2
        # Ajustement week-end simplifié
        target = signal_dt + timedelta(days=latency)
        while target.weekday() >= 5:  # samedi=5, dimanche=6
            target += timedelta(days=1)
            latency += 1
        return target, latency

    def latency_risk(self, ticker: str, current_score: int, latency_days: int) -> Dict:
        """Perte moyenne historique observée sur une fenêtre = latency_days,
        conditionnée aux situations similaires (réutilise EmpiricalAnalogEngine)."""
        res = self.analog.analyze(ticker, current_score, horizon=max(latency_days, 1), tolerance=1)
        if not res.get("available"):
            return {"available": False}
        return {
            "available": True,
            "expected_loss_pct": res["expected_alpha"] * 100,
            "n_samples": res["n_samples"],
            "risk_label": "LOW" if res["expected_alpha"] > -0.005 else
                          "MODERATE" if res["expected_alpha"] > -0.02 else "HIGH",
        }

# =============================================================================
# MODULE 23 : DATA QUALITY & DECISION ENGINE
# =============================================================================
class DataQualityEngine:
    def score(self, ind: Optional[Dict], world_regime: Dict) -> Dict:
        if ind is None:
            return {"score": 0, "label": "NO_DECISION", "reasons": ["Aucune donnée"]}
        s, reasons = 100, []
        if ind["n_history"] < 250:
            s -= 30; reasons.append(f"Historique court ({ind['n_history']}j)")
        if ind["sma200"] is None:
            s -= 20; reasons.append("SMA200 indisponible")
        if ind["alpha20"] is None or ind["alpha60"] is None:
            s -= 25; reasons.append("Alpha indisponible")
        if not world_regime.get("world_ticker") and not world_regime.get("regime"):
            s -= 25; reasons.append("Benchmark World indisponible")
        label = "EXCELLENT" if s >= 90 else "BON" if s >= 80 else "ACCEPTABLE" if s >= 60 else "NO_DECISION"
        return {"score": max(0, s), "label": label, "reasons": reasons}


class DecisionEngine:
    """Combine tous les moteurs. Applique les vetos de sécurité et l'hystérésis."""
    DECISIONS = ["EXIT", "REDUCE_50", "REDUCE_25", "WATCH", "HOLD", "RE_ENTER"]

    def decide(self, ticker: str, ind: Dict, crash: Dict, underperf: Dict,
               world_regime: Dict, dq: Dict, latency: Dict,
               risk_contribution_pct: Optional[float] = None,
               previous_decision: Optional[str] = None) -> Dict:

        # --- VETO 1 : qualité de données ---
        if dq["label"] == "NO_DECISION":
            return {"decision": "NO_DECISION", "confidence": "NONE",
                    "reason": "Données insuffisantes : " + "; ".join(dq["reasons"])}

        # --- VETO 2 : World en CRASH ---
        if world_regime.get("regime") == "CRASH" and crash["score"] >= 4:
            return {"decision": "REDUCE_50", "confidence": "HIGH",
                    "reason": f"World en CRASH + Crash Score {crash['score']}/7"}

        # --- Hystérésis : seuils différents sortie / réentrée ---
        was_reduced_or_exit = previous_decision in ("REDUCE_25", "REDUCE_50", "EXIT")

        combined_risk = crash["score"] + underperf["score"]  # sur 11 max

        if crash["level"] == "CRITICAL" and world_regime.get("regime") in ("RISK_OFF", "CRASH"):
            decision, conf = "EXIT", "HIGH"
        elif crash["score"] >= DECISION_EXIT_SCORE:
            decision, conf = "REDUCE_50", "HIGH"
        elif crash["score"] >= 4 or underperf["score"] >= 3:
            decision, conf = "REDUCE_25", "MEDIUM"
        elif was_reduced_or_exit and combined_risk <= DECISION_REENTER_SCORE and ind["trend_score"] >= 3:
            decision, conf = "RE_ENTER", "MEDIUM"
        elif crash["score"] >= 2 or underperf["score"] >= 2:
            decision, conf = "WATCH", "MEDIUM"
        else:
            decision, conf = "HOLD", "HIGH" if dq["score"] >= 90 else "MEDIUM"

        # --- VETO 3 : risque de concentration portefeuille ---
        note_risk = None
        if risk_contribution_pct is not None and risk_contribution_pct > 40 and decision == "HOLD":
            decision, conf = "WATCH", "MEDIUM"
            note_risk = f"Contribution au risque portefeuille = {risk_contribution_pct:.0f}% (> 40%)"

        return {
            "decision": decision, "confidence": conf,
            "crash_score": crash["score"], "crash_level": crash["level"],
            "underperf_score": underperf["score"],
            "world_regime": world_regime.get("regime"),
            "data_quality": dq["label"],
            "latency_risk": latency.get("risk_label") if latency.get("available") else "N/A",
            "note_risk": note_risk,
            "reasons": crash["reasons"] + underperf["reasons"],
        }

# =============================================================================
# MODULE 24 : FEATURE ENGINEERING (vectorisé, pour ML + Backtest + Calibration)
# =============================================================================
def compute_world_regime_series(dm: DataManager) -> pd.Series:
    """Version vectorisée de WorldRegimeEngine, sur toute la série historique.
    Retourne une Series numérique : CRASH=-2, RISK_OFF=-1, NEUTRAL=0, RISK_ON=1."""
    world_tk = None
    for wt in [BENCHMARK_WORLD_TICKER] + WORLD_TICKERS:
        df = dm.data.get(wt)
        if df is not None and not df.empty:
            world_tk = wt
            break
    if world_tk is None:
        return pd.Series(dtype=float)

    close = dm.data[world_tk]["Close"].dropna()
    ret = close.pct_change()
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    vol20 = ret.rolling(20).std() * np.sqrt(252)
    vol120 = ret.rolling(120).std() * np.sqrt(252)
    vol_shock = vol20 / vol120
    dd = close / close.cummax() - 1

    above20 = close > sma20
    above50 = close > sma50
    above200 = close > sma200
    sma50_above200 = sma50 > sma200

    regime = pd.Series(0, index=close.index)  # NEUTRAL par défaut
    risk_on = above200 & sma50_above200 & above20 & (vol_shock < 1.2)
    risk_off = ((~above50) & (sma20 < sma50)) | (vol_shock > 1.3)
    crash = (~above200) & (dd < -0.10) & (vol_shock > 1.4)

    regime[risk_on] = 1
    regime[risk_off] = -1
    regime[crash] = -2  # priorité maximale : écrase les autres
    return regime


def build_feature_frame(dm: DataManager, ticker: str) -> pd.DataFrame:
    """Construit une DataFrame de features + targets (forward alpha) pour un ticker,
    alignée sur le benchmark World. Une ligne = un jour de l'historique."""
    df = dm.data.get(ticker)
    world = get_world_series(dm, exclude_ticker=ticker)
    if df is None or df.empty or world.empty:
        return pd.DataFrame()

    close = df["Close"].dropna()
    common = close.index.intersection(world.index)
    if len(common) < 300:
        return pd.DataFrame()

    close = close.loc[common]
    world_c = world.loc[common]
    ret = close.pct_change()
    world_ret = world_c.pct_change()

    feat = pd.DataFrame(index=common)
    feat["ret1"] = ret
    feat["ret5"] = close / close.shift(5) - 1
    feat["ret20"] = close / close.shift(20) - 1
    feat["ret60"] = close / close.shift(60) - 1

    world_ret5 = world_c / world_c.shift(5) - 1
    world_ret20 = world_c / world_c.shift(20) - 1
    world_ret60 = world_c / world_c.shift(60) - 1
    feat["alpha5"] = feat["ret5"] - world_ret5
    feat["alpha20"] = feat["ret20"] - world_ret20
    feat["alpha60"] = feat["ret60"] - world_ret60

    rs = close / world_c
    rs_ma20 = rs.rolling(20).mean()
    rs_ma50 = rs.rolling(50).mean()
    feat["rs_gap"] = rs - rs_ma20
    feat["rs_slope"] = rs_ma20 - rs_ma20.shift(10)
    feat["rs_trend"] = rs_ma20 - rs_ma50

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    feat["dist_sma20"] = close / sma20 - 1
    feat["dist_sma50"] = close / sma50 - 1
    feat["dist_sma200"] = close / sma200 - 1

    vol20 = ret.rolling(20).std() * np.sqrt(252)
    vol60 = ret.rolling(60).std() * np.sqrt(252)
    vol120 = ret.rolling(120).std() * np.sqrt(252)
    feat["vol20"] = vol20
    feat["vol_ratio"] = vol20 / vol60
    feat["vol_shock"] = vol20 / vol120

    dd = close / close.cummax() - 1
    feat["drawdown"] = dd
    feat["dd_5d"] = close / close.shift(5) - 1

    feat["mom5"] = feat["ret5"]
    feat["mom20"] = feat["ret20"]
    feat["mom_accel"] = feat["ret20"] - feat["ret20"].shift(5)

    regime_series = compute_world_regime_series(dm)
    feat["world_regime"] = regime_series.reindex(common).ffill().fillna(0)

    # --- Targets (forward alpha) ---
    for h in (3, 10, 20, 60):
        etf_fwd = close.shift(-h) / close - 1
        world_fwd = world_c.shift(-h) / world_c - 1
        feat[f"fwd_alpha_{h}"] = etf_fwd - world_fwd

    return feat.dropna(subset=["alpha20", "vol_ratio"])  # garde les lignes exploitables

# =============================================================================
# MODULE 25 : FORWARD ALPHA MODEL (Ridge + Walk-Forward, avec fallback baseline)
# =============================================================================
FEATURE_COLS = ["ret5", "ret20", "ret60", "alpha5", "alpha20", "alpha60",
                 "rs_gap", "rs_slope", "rs_trend", "dist_sma20", "dist_sma50",
                 "dist_sma200", "vol20", "vol_ratio", "vol_shock", "drawdown",
                 "dd_5d", "mom5", "mom20", "mom_accel", "world_regime"]

class ForwardAlphaModel:
    """
    Prédit fwd_alpha_H (H=20 par défaut). Toujours évalué en walk-forward
    (jamais entraîné et testé sur la même période — voir point 32 de la spec).
    Compare systématiquement Ridge vs baseline (moyenne historique constante).
    """
    def __init__(self, horizon: int = 20, n_folds: int = 4, ridge_alpha: float = 5.0):
        self.horizon = horizon
        self.n_folds = n_folds
        self.ridge_alpha = ridge_alpha

    def _splits(self, n: int) -> List[Tuple[slice, slice]]:
        """Découpage expanding window : train grandit, test = tranche suivante."""
        fold_size = n // (self.n_folds + 1)
        if fold_size < 30:
            return []
        splits = []
        for i in range(1, self.n_folds + 1):
            train_end = fold_size * i
            test_end = min(fold_size * (i + 1), n)
            if test_end <= train_end:
                continue
            splits.append((slice(0, train_end), slice(train_end, test_end)))
        return splits

    def walk_forward_evaluate(self, feat: pd.DataFrame) -> Dict:
        target_col = f"fwd_alpha_{self.horizon}"
        data = feat.dropna(subset=FEATURE_COLS + [target_col])
        if len(data) < 200:
            return {"available": False, "reason": "Historique insuffisant pour walk-forward"}

        X = data[FEATURE_COLS].values
        y = data[target_col].values
        splits = self._splits(len(data))
        if not splits:
            return {"available": False, "reason": "Pas assez de données pour découper en folds"}

        ridge_preds, baseline_preds, actuals = [], [], []

        for train_idx, test_idx in splits:
            X_train, y_train = X[train_idx], y[train_idx]
            X_test, y_test = X[test_idx], y[test_idx]
            if len(y_train) < 50:
                continue

            baseline_pred = np.full(len(y_test), y_train.mean())
            baseline_preds.extend(baseline_pred)

            if SKLEARN_OK:
                scaler = StandardScaler()
                X_train_s = scaler.fit_transform(X_train)
                X_test_s = scaler.transform(X_test)
                model = Ridge(alpha=self.ridge_alpha)
                model.fit(X_train_s, y_train)
                ridge_pred = model.predict(X_test_s)
            else:
                ridge_pred = baseline_pred  # dégradation propre si sklearn absent
            ridge_preds.extend(ridge_pred)
            actuals.extend(y_test)

        if len(actuals) < 30:
            return {"available": False, "reason": "Échantillon OOS trop petit"}

        actuals = np.array(actuals); ridge_preds = np.array(ridge_preds); baseline_preds = np.array(baseline_preds)

        def _metrics(preds):
            hit_rate = float((np.sign(preds) == np.sign(actuals)).mean())
            corr = float(np.corrcoef(preds, actuals)[0, 1]) if np.std(preds) > 1e-9 else 0.0
            mae = float(np.mean(np.abs(preds - actuals)))
            return {"hit_rate": hit_rate, "correlation": corr, "mae": mae}

        ridge_metrics = _metrics(ridge_preds)
        baseline_metrics = _metrics(baseline_preds)

        return {
            "available": True, "n_oos_samples": len(actuals),
            "ridge": ridge_metrics, "baseline": baseline_metrics,
            "ridge_better": ridge_metrics["correlation"] > baseline_metrics["correlation"],
        }

    def fit_production_model(self, feat: pd.DataFrame):
        """Modèle final entraîné sur TOUT l'historique dispo, pour prédire AUJOURD'HUI.
        Ne jamais utiliser ce modèle pour évaluer une performance (c'est du in-sample)."""
        target_col = f"fwd_alpha_{self.horizon}"
        data = feat.dropna(subset=FEATURE_COLS + [target_col])
        if len(data) < 100 or not SKLEARN_OK:
            return None, None
        X = data[FEATURE_COLS].values
        y = data[target_col].values
        scaler = StandardScaler()
        X_s = scaler.fit_transform(X)
        model = Ridge(alpha=self.ridge_alpha)
        model.fit(X_s, y)
        return model, scaler

    def predict_today(self, feat: pd.DataFrame, model, scaler) -> Optional[float]:
        if model is None or scaler is None or feat.empty:
            return None
        last_row = feat[FEATURE_COLS].iloc[[-1]].dropna()
        if last_row.empty:
            return None
        X_s = scaler.transform(last_row.values)
        return float(model.predict(X_s)[0])

# =============================================================================
# MODULE 26 : BACKTEST ENGINE (Stratégies A/B/C/D)
# =============================================================================
WEIGHT_MAP = {"HOLD": 1.0, "RE_ENTER": 1.0, "WATCH": 1.0,
              "REDUCE_25": 0.75, "REDUCE_50": 0.50, "EXIT": 0.0, "NO_DECISION": None}

class BacktestEngine:
    """
    Simule 4 stratégies sur l'historique d'un ETF :
      A - Buy & Hold
      B - Signal appliqué sans délai
      C - Signal + délai Linxea (J+1 avant cutoff, J+2 sinon — simplifié en jours de bourse)
      D - Signal + scénario stress (+1 séance de délai supplémentaire)
    """
    def __init__(self, crash_thresholds: Dict, underperf_thresholds: Dict,
                 exit_score: int = DECISION_EXIT_SCORE, reenter_score: int = DECISION_REENTER_SCORE):
        self.ct = crash_thresholds
        self.ut = underperf_thresholds
        self.exit_score = exit_score
        self.reenter_score = reenter_score

    def compute_decision_series(self, feat: pd.DataFrame) -> pd.Series:
        """Reconstruit crash_score + underperf_score jour par jour (vectorisé),
        puis applique l'hystérésis (boucle nécessaire ici, état séquentiel)."""
        close_proxy = None  # on travaille uniquement sur les features déjà calculées
        crash_score = pd.Series(0, index=feat.index)
        crash_score += (feat["dist_sma20"] < 0).astype(int)
        crash_score += ((feat["dist_sma20"] < 0) & (feat["rs_trend"] < 0)).astype(int)  # proxy SMA20<SMA50
        crash_score += (feat["alpha20"] < 0).astype(int)
        crash_score += (feat["alpha60"] < 0).astype(int)
        crash_score += (feat["vol_ratio"] > self.ct["vol_ratio"]).astype(int)
        crash_score += (feat["dd_5d"] < self.ct["dd_5d"]).astype(int)
        crash_score += (feat["world_regime"] <= -1).astype(int)  # RISK_OFF ou CRASH

        underperf_score = pd.Series(0, index=feat.index)
        underperf_score += (feat["alpha20"] < self.ut["alpha20"]).astype(int)
        underperf_score += (feat["alpha60"] < self.ut["alpha60"]).astype(int)

        combined = crash_score + underperf_score

        decisions = []
        was_reduced = False
        for i in range(len(feat)):
            cs = crash_score.iloc[i]
            comb = combined.iloc[i]
            wr = feat["world_regime"].iloc[i]
            trend_ok = feat["dist_sma20"].iloc[i] > 0

            if wr <= -2 and cs >= 4:
                d = "REDUCE_50"
            elif cs >= self.exit_score:
                d = "REDUCE_50"
            elif cs >= 4 or underperf_score.iloc[i] >= 3:
                d = "REDUCE_25"
            elif was_reduced and comb <= self.reenter_score and trend_ok:
                d = "HOLD"
            elif cs >= 2 or underperf_score.iloc[i] >= 2:
                d = "WATCH"
            else:
                d = "HOLD"
            was_reduced = d in ("REDUCE_25", "REDUCE_50")
            decisions.append(d)

        return pd.Series(decisions, index=feat.index)

    def run(self, dm: DataManager, ticker: str, feat: pd.DataFrame,
            latency_days_normal: int = 1, latency_days_stress: int = 2) -> Dict:
        df = dm.data.get(ticker)
        world = get_world_series(dm, exclude_ticker=ticker)
        close = df["Close"].loc[feat.index]
        world_c = world.loc[feat.index]
        etf_ret = close.pct_change().fillna(0)
        world_ret = world_c.pct_change().fillna(0)

        decisions = self.compute_decision_series(feat)
        weights = decisions.map(WEIGHT_MAP).fillna(1.0)

        strategies = {}

        # Stratégie A : Buy & Hold
        strategies["A_BuyHold"] = etf_ret.copy()

        # Stratégie B : signal sans délai (poids appliqué au rendement du jour même)
        strategies["B_SignalNoDelay"] = etf_ret * weights

        # Stratégie C : signal + délai Linxea (le poids d'hier s'applique au rendement d'aujourd'hui)
        weights_delayed_c = weights.shift(latency_days_normal).fillna(1.0)
        strategies["C_SignalLinxeaDelay"] = etf_ret * weights_delayed_c

        # Stratégie D : signal + scénario stress (délai supplémentaire)
        weights_delayed_d = weights.shift(latency_days_stress).fillna(1.0)
        strategies["D_SignalStress"] = etf_ret * weights_delayed_d

        results = {}
        for name, strat_ret in strategies.items():
            results[name] = self._compute_metrics(strat_ret, world_ret, weights if "Signal" in name else None)
        results["_decisions"] = decisions
        results["_weights"] = weights
        return results

    def _compute_metrics(self, strat_ret: pd.Series, world_ret: pd.Series,
                          weights: Optional[pd.Series]) -> Dict:
        n = len(strat_ret)
        if n < 30:
            return {"available": False}
        equity = (1 + strat_ret).cumprod()
        total_return = float(equity.iloc[-1] - 1)
        years = n / 252
        cagr = float((equity.iloc[-1]) ** (1 / years) - 1) if years > 0 and equity.iloc[-1] > 0 else np.nan
        ann_vol = float(strat_ret.std() * np.sqrt(252))
        rmax = equity.cummax()
        dd = equity / rmax - 1
        max_dd = float(dd.min())
        sharpe = float((cagr - 0.025) / ann_vol) if ann_vol > 0 else np.nan
        calmar = float(cagr / abs(max_dd)) if max_dd != 0 else np.nan

        world_equity = (1 + world_ret).cumprod()
        world_total = float(world_equity.iloc[-1] - 1)
        alpha_vs_world = total_return - world_total

        worst_day = float(strat_ret.min())
        worst_5d = float(strat_ret.rolling(5).sum().min())
        worst_10d = float(strat_ret.rolling(10).sum().min())

        n_trades = int((weights.diff().abs() > 0.01).sum()) if weights is not None else 0
        turnover = float(weights.diff().abs().sum()) if weights is not None else 0.0

        return {
            "available": True, "total_return_pct": total_return * 100, "cagr_pct": cagr * 100,
            "vol_pct": ann_vol * 100, "max_drawdown_pct": max_dd * 100,
            "sharpe": sharpe, "calmar": calmar, "alpha_vs_world_pct": alpha_vs_world * 100,
            "worst_day_pct": worst_day * 100, "worst_5d_pct": worst_5d * 100, "worst_10d_pct": worst_10d * 100,
            "n_trades": n_trades, "turnover": round(turnover, 2), "equity_curve": equity,
        }

# =============================================================================
# MODULE 27 : THRESHOLD CALIBRATION (grid search hors-échantillon)
# =============================================================================
class CalibrationEngine:
    """
    Teste plusieurs combinaisons de seuils sur la partie 'train' (70% des données),
    sélectionne celle qui maximise le Calmar (CAGR/MaxDD) SOUS CONTRAINTE que le
    CAGR ne soit pas détruit (garde-fou), puis valide le résultat sur les 30%
    restants (données jamais vues pendant la recherche) — cf. point 62 de la spec.
    """
    ALPHA20_GRID = [-0.01, -0.02, -0.03, -0.04, -0.05]
    VOL_RATIO_GRID = [1.1, 1.2, 1.3, 1.4, 1.5]
    DD5D_GRID = [-0.03, -0.05, -0.07, -0.10]

    def __init__(self, dm: DataManager):
        self.dm = dm

    def calibrate(self, ticker: str, feat: pd.DataFrame, train_frac: float = 0.7) -> Dict:
        n = len(feat)
        if n < 300:
            return {"available": False, "reason": "Historique insuffisant pour calibration"}

        split = int(n * train_frac)
        feat_train = feat.iloc[:split]
        feat_test = feat.iloc[split:]

        buyhold_cagr_train = self._buyhold_cagr(ticker, feat_train)

        best = None
        results_grid = []
        for a20 in self.ALPHA20_GRID:
            for vr in self.VOL_RATIO_GRID:
                for dd in self.DD5D_GRID:
                    ct = {"vol_ratio": vr, "dd_5d": dd}
                    ut = {"alpha20": a20, "alpha60": a20 * 0.7}
                    bt = BacktestEngine(ct, ut)
                    res = bt.run(self.dm, ticker, feat_train)
                    metric = res.get("C_SignalLinxeaDelay", {})
                    if not metric.get("available"):
                        continue
                    # Garde-fou : ne pas accepter un jeu de seuils qui détruit le CAGR
                    if buyhold_cagr_train and metric["cagr_pct"] < 0.4 * buyhold_cagr_train:
                        continue
                    calmar = metric.get("calmar", np.nan)
                    if np.isnan(calmar):
                        continue
                    entry = {"alpha20": a20, "vol_ratio": vr, "dd_5d": dd, "calmar": calmar,
                             "cagr_pct": metric["cagr_pct"], "max_dd_pct": metric["max_drawdown_pct"]}
                    results_grid.append(entry)
                    if best is None or calmar > best["calmar"]:
                        best = entry

        if best is None:
            return {"available": False, "reason": "Aucune combinaison n'a passé le garde-fou CAGR"}

        # Validation hors-échantillon avec les seuils retenus
        ct_best = {"vol_ratio": best["vol_ratio"], "dd_5d": best["dd_5d"]}
        ut_best = {"alpha20": best["alpha20"], "alpha60": best["alpha20"] * 0.7}
        bt_best = BacktestEngine(ct_best, ut_best)
        oos_res = bt_best.run(self.dm, ticker, feat_test)
        oos_metric = oos_res.get("C_SignalLinxeaDelay", {})

        default_bt = BacktestEngine(CRASH_THRESHOLDS, UNDERPERF_THRESHOLDS)
        default_oos = default_bt.run(self.dm, ticker, feat_test).get("C_SignalLinxeaDelay", {})

        return {
            "available": True, "n_combinations_tested": len(results_grid),
            "best_thresholds": best,
            "oos_validation": oos_metric,
            "default_thresholds_oos": default_oos,  # comparaison avec vos seuils actuels
            "improvement": (oos_metric.get("calmar", 0) - default_oos.get("calmar", 0))
                            if oos_metric.get("available") and default_oos.get("available") else None,
        }

    def _buyhold_cagr(self, ticker: str, feat: pd.DataFrame) -> Optional[float]:
        df = self.dm.data.get(ticker)
        if df is None:
            return None
        close = df["Close"].loc[feat.index]
        n = len(close)
        if n < 30:
            return None
        years = n / 252
        total = close.iloc[-1] / close.iloc[0]
        return float((total ** (1/years) - 1) * 100) if total > 0 else None

# -----------------------------------------------------------------------------
# MODULE 16 : STREAMLIT UI (avec intégration v2, backtest, calibration)
# -----------------------------------------------------------------------------
class StreamlitUI:
    def __init__(self, dm: DataManager, pm: PersistenceManager,
                 mre: MarketRegimeEngine, qre: QuantRiskEngine,
                 pe: PortfolioEngine, pde: PedagogicEngine,
                 se: StrategicEngine, qae: QuantAlertEngine,
                 pcm: "PortfolioConfigManager" = None,
                 te: "TransactionEngine" = None):
        self.dm = dm
        self.pm = pm
        self.mre = mre
        self.qre = qre
        self.pe = pe
        self.pde = pde
        self.se = se
        self.qae = qae
        self.pcm = pcm if pcm is not None else PortfolioConfigManager()
        self.te = te if te is not None else TransactionEngine()
        self.analytics = AnalyticsEngine(dm)
        self.signal = SignalEngine(dm, self.analytics)
        # Nouveaux moteurs (créés une fois)
        self.ie = IndicatorEngine(dm)
        self.wre = WorldRegimeEngine(dm, self.ie)
        self.cpe = CrashProtectionEngine()
        self.upe = UnderperformanceEngine()
        self.analog = EmpiricalAnalogEngine(dm, self.ie)
        self.lee = LinxeaExecutionEngine(dm, self.analog)
        self.dqe = DataQualityEngine()
        self.dec_engine = DecisionEngine()

    @staticmethod
    def _sign(v: float) -> str:
        return "+" if v >= 0 else ""

    def render_sidebar(self) -> Tuple[bool, List[Dict], float, float, float]:
        st.sidebar.markdown("## ⚙ Paramètres v6.9")
        mode_direct = st.sidebar.toggle("🔌 Mode Direct (Vue Brute)", value=False)
        st.sidebar.markdown("---")
        cap = st.sidebar.number_input("Capital investi (€)", value=st.session_state["cfg_capital_reel"], step=100.0, format="%.2f", key="input_capital_reel")
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
            cls = "save-box" if fb.startswith("✅") else "alert-box"
            st.sidebar.markdown(f'<div class="{cls}">{fb}</div>', unsafe_allow_html=True)
        st.sidebar.markdown("---")

        with st.sidebar.expander("⚙ Configuration des Positions", expanded=False):
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
        st.sidebar.markdown("### 🗑 Supprimer un ETF")
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
            st.sidebar.markdown(f'<div class="persist-warn">⚠ {self.pm.warning_msg}</div>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<div class="persist-warn">📂 SQLite local</div>', unsafe_allow_html=True)

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📦 Positions (session)")
        st.sidebar.caption("Modification en live. Utilisez '⚙ Configuration' pour persister.")
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

    def render_header(self, mode_direct: bool, live_ok: int, live_total: int):
        now = datetime.now(ZoneInfo("Europe/Paris"))
        st.markdown('<div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:.2rem;">'
                    '<span style="font-family:Space Mono;font-size:1.6rem;font-weight:700;color:#D4AF37;">◈</span>'
                    '<span style="font-size:1.5rem;font-weight:700;color:#E2E8F0;">COCKPIT DÉCISIONNEL</span>'
                    '<span style="font-family:Space Mono;font-size:.9rem;color:#6B7585;">v6.9 · ALERTE QUANT</span></div>', unsafe_allow_html=True)
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
        with st.expander("ℹ Comment lire la météo des marchés ?", expanded=False):
            reg_trans = self.pde.translate_regime(regime)
            col_exp, col_comp = st.columns([1, 2])
            with col_exp:
                level_color = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}.get(reg_trans["level"], "#6B7585")
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

        st.markdown("### 📊 Mes positions")
        col_t, col_p = st.columns([3, 2])
        with col_t:
            rows = []
            for p2 in ptf["positions"]:
                if p2["prix"] is not None and p2["perf_pct"] is not None:
                    gain_unit = p2.get("gain_unit", 0)
                    parts = p2.get("parts", 0)
                    perf_euro = gain_unit * parts if 'gain_unit' in p2 else 0
                    perf_euro_str = f"{self._sign(perf_euro)}{perf_euro:,.2f}€"
                else:
                    perf_euro_str = "N/A"
                perf_f = f"{self._sign(p2['perf_pct'])}{p2['perf_pct']:.2f}%" if p2["perf_pct"] is not None else "N/A"
                vj_f = f"{self._sign(p2['var_jour_pct'])}{p2['var_jour_pct']:.2f}%" if p2["var_jour_pct"] else "--"
                vje_f = f"{self._sign(p2['var_jour_eur'])}{p2['var_jour_eur']:,.2f}€" if p2["var_jour_eur"] else "--"
                prix_f = f"{p2['prix']:.3f}€" if p2["prix"] else "N/A"
                rows.append({
                    "Position": p2["nom"], "Env.": p2["enveloppe"], "Prix": prix_f,
                    "Valeur (€)": f"{p2['valeur']:,.2f}", "Perf. (%)": perf_f,
                    "Perf. (€)": perf_euro_str, "Δ Jour (%)": vj_f, "Δ Jour (€)": vje_f
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if not mode_direct:
            st.markdown(f'<div class="info-box">Ajustement patrimonial inclus : +{ptf["ajustement_pat"]:,.2f}€</div>', unsafe_allow_html=True)
        with col_p:
            donut = [p2 for p2 in ptf["positions"] if p2["valeur"] > 0]
            if donut:
                colors_pie = ["#007BFF", "#6366F1", "#D4AF37", "#F97316", "#22C55E", "#A855F7", "#FF6B6B"]
                fig_pie = go.Figure(go.Pie(
                    labels=[d["nom"] for d in donut],
                    values=[d["valeur"] for d in donut],
                    hole=0.6, textinfo="percent",
                    marker=dict(colors=colors_pie[:len(donut)], line=dict(color="#1C1F26", width=2))
                ))
                vt = ptf["valeur_totale"]
                fig_pie.update_layout(
                    **_PLOTLY_BASE, margin=dict(t=10, b=10, l=10, r=10), height=270,
                    legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                    annotations=[dict(text=f"{vt:,.0f}€", x=.5, y=.5, font=dict(size=13, color="#D4AF37", family="Space Mono"), showarrow=False)]
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        mwr_adj = bench.get("perf_bench_adj")
        if mwr_adj is not None:
            gap = bench.get("gap", 0.0) or 0.0
            gc = "#22C55E" if gap >= 0 else "#FF3131"
            st.markdown(f'<div class="pedagogy-box"><div class="pedagogy-title">🆕 v6.9 --- Benchmark MWR Cash-Flow Adjusted</div>'
                        f'Le "Gap vs World" est calculé en simulant l\'achat de MWRD.PA aux mêmes dates et montants que vos flux réels. '
                        f'<b>World MWR = {s(mwr_adj)}{mwr_adj:.2f}%</b> · '
                        f'<b style="color:{gc};">Votre Alpha = {s(gap)}{gap:.2f}%</b></div>', unsafe_allow_html=True)

    # ---- NOUVELLE SECTION : Performance hebdomadaire du portefeuille vs World ----
    def render_portfolio_leadership_comparison(self, ptf: Dict):
        st.markdown("## 📈 Performance du Portefeuille vs MSCI World")
        positions = ptf["positions"]
        labels, port_perfs, world_perfs = self.pde.get_portfolio_weekly_performances(self.dm, positions, n_weeks=5)
        if not labels:
            st.info("Données hebdomadaires insuffisantes pour le portefeuille (besoin d'au moins 2 semaines de données historiques).")
            return

        # Graphique
        fig = plot_weekly_leadership(labels, port_perfs, world_perfs, "Portefeuille", color_sat="#D4AF37")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Verdict
        gaps = [p - w for p, w in zip(port_perfs, world_perfs)]
        verdict = self.pde.translate_leadership("Portefeuille", gaps)
        level_color = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}.get(verdict["level"], "#6B7585")
        level_bg = {"green": "rgba(34,197,94,.1)", "orange": "rgba(249,115,22,.1)", "red": "rgba(255,49,49,.1)"}.get(verdict["level"], "rgba(107,117,133,.1)")
        st.markdown(f'<div style="background:{level_bg};border:1px solid {level_color};border-radius:10px;padding:1rem;margin:.5rem 0;">'
                    f'<div style="font-weight:700;font-size:1.1rem;color:{level_color};">{verdict["message"]}</div>'
                    f'<div style="font-size:.9rem;color:#8892AA;margin:.4rem 0;">{verdict["detail"]}</div>'
                    f'<div style="font-size:.9rem;color:#CBD5E1;">💡 {verdict["action"]}</div></div>', unsafe_allow_html=True)
    # ---- Fin nouvelle section ----

    def render_equity_curve_section(self, ptf: Dict, regime: Dict, positions_conf: List[Dict]):
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
            krw_v = next((p["valeur"] for p in ptf["positions"] if p["nom"] == "MSCI Korea"), 0)
            chip_v = next((p["valeur"] for p in ptf["positions"] if p["nom"] == "MSCI Semiconductors"), 0)
            poids_sat = (krw_v + chip_v) / vt * 100 if vt else 0
            st.markdown(f'<div style="font-size:.82rem;color:#6B7585;line-height:1.8;"><b>Capital :</b> {vt:,.2f}€<br>'
                        f'<b>Aujourd\'hui :</b> {pj:+.2f}%<br><b>Total :</b> {pc:+.2f}%<br>'
                        f'<b>Régime :</b> {regime["confirmed_label"]}<br><b>Satellites :</b> {poids_sat:.1f}%</div>', unsafe_allow_html=True)
            if st.button("📸 Enregistrer Snapshot", use_container_width=True, type="primary"):
                ok = self.pm.save_snapshot(vt, vt, round(pj, 4), round(pc, 4), regime["confirmed_label"],
                                           regime["confirmed_score"], round(poids_sat, 4))
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

    def render_leadership_comparison(self, nom: str, ticker_key: str, color_sat: str = "#D4AF37"):
        st.markdown(f"### 📊 {nom} vs MSCI World --- Leadership hebdomadaire")
        with st.container():
            st.markdown('<div class="leadership-header"><div style="font-size:.8rem;color:#6B7585;">POURQUOI CE GRAPHIQUE EST IMPORTANT</div>'
                        '<div style="color:#E2E8F0;line-height:1.6;">Ce graphique compare chaque semaine la performance de votre ETF vs le MSCI World. '
                        '<b>Si l\'ETF fait régulièrement moins bien que le World</b>, il perd sa raison d\'être.</div></div>', unsafe_allow_html=True)
        labels, sat_perfs, world_perfs = self.pde.get_weekly_performances(self.dm, ticker_key)
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
                level_color = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}.get(verdict["level"], "#6B7585")
                level_bg = {"green": "rgba(34,197,94,.1)", "orange": "rgba(249,115,22,.1)", "red": "rgba(255,49,49,.1)"}.get(verdict["level"], "rgba(107,117,133,.1)")
                st.markdown(f'<div style="background:{level_bg};border:1px solid {level_color};border-radius:10px;padding:1rem;margin-top:.5rem;">'
                            f'<div style="font-weight:700;font-size:1rem;color:{level_color};">{verdict["message"]}</div>'
                            f'<div style="font-size:.8rem;color:#8892AA;margin:.4rem 0;">{verdict["detail"]}</div>'
                            f'<div style="font-size:.85rem;color:#CBD5E1;margin-top:.5rem;">💡 {verdict["action"]}</div></div>', unsafe_allow_html=True)
        else:
            st.info("Données hebdomadaires insuffisantes. Revenez après quelques semaines.")

    def render_risk_dashboard(self, ptf: Dict):
        st.markdown("## ⚠ Gestion des risques")
        with st.expander("❓ Comment lire les indicateurs de risque ?", expanded=False):
            st.markdown('<div class="pedagogy-box"><div class="pedagogy-title">Guide de lecture des risques</div>'
                        '<b>Agitation (Volatilité)</b> : mesure les oscillations quotidiennes. Plus c\'est élevé, plus l\'ETF peut monter ou baisser brutalement.<br><br>'
                        '<b>Sensibilité (Beta)</b> : si le marché baisse de 10% et Beta=1.5, l\'ETF peut baisser de 15%.<br><br>'
                        '<b>Recul depuis le sommet (Drawdown)</b> : distance depuis le dernier pic. -20% signifie une perte de 20%.</div>', unsafe_allow_html=True)
        st.markdown("### 🔍 Analyse de risque par ETF")
        risk_assets = []
        for pos in ptf["positions"]:
            if pos.get("ticker") and pos["valeur"] > 0:
                ticker = pos["ticker"]
                name = pos["nom"]
                color_map = {
                    "WMMS.DE": "#D4AF37",
                    "DCAM.PA": "#007BFF",
                    "MWRD.PA": "#3B82F6",
                    "KRW.PA": "#F97316",
                    "CHIP.PA": "#A855F7"
                }
                color = color_map.get(ticker, "#6366F1")
                risk_assets.append((ticker, name, color, None))
        cols = st.columns(min(len(risk_assets), 4))
        for i, (tk, name, color, custom_df) in enumerate(risk_assets):
            with cols[i % len(cols)]:
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
                level_colors = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}
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
            tickers_ptf = [pos["ticker"] for pos in ptf["positions"] if pos.get("ticker") and pos["valeur"] > 0]
            positions_map = {p["nom"]: p for p in ptf["positions"]}
            vt = ptf["valeur_totale"]
            with col_corr:
                if len(tickers_ptf) >= 2:
                    corr_df = self.qre.correlation_matrix(tickers_ptf, 60)
                    if corr_df is not None:
                        st.plotly_chart(plot_correlation_heatmap(corr_df), use_container_width=True, config={"displayModeBar": False})
                        st.markdown('<div class="pedagogy-box">Une corrélation proche de +1 signifie que les deux ETFs bougent ensemble. Idéalement, ils ne devraient pas tous monter et baisser en même temps.</div>', unsafe_allow_html=True)
                    else:
                        st.info("Données insuffisantes (< 60j).")
                else:
                    st.info("Ajoutez au moins 2 ETF pour voir la corrélation.")
            with col_rc:
                weights_ptf, valid_tk = [], []
                for tk in tickers_ptf:
                    df = self.dm.data.get(tk, pd.DataFrame())
                    if not df.empty:
                        nom = next((p["nom"] for p in ptf["positions"] if p.get("ticker") == tk), "")
                        val = positions_map.get(nom, {}).get("valeur", 0.0)
                        valid_tk.append(tk)
                        weights_ptf.append(val)
                if valid_tk and sum(weights_ptf) > 0 and len(valid_tk) >= 2:
                    rc = self.qre.risk_contribution(valid_tk, weights_ptf, 60)
                    if rc:
                        fig_rc = plot_risk_contribution(rc)
                        if fig_rc:
                            st.plotly_chart(fig_rc, use_container_width=True, config={"displayModeBar": False})
                        flags = [tk for tk, v in rc.items() if v["flag"]]
                        if flags:
                            short = {
                                "WMMS.DE": "WMMS", "MWRD.PA": "World",
                                "DCAM.PA": "W-PEA", "KRW.PA": "Korea", "CHIP.PA": "CHIP"
                            }
                            f_names = ", ".join([short.get(f, f) for f in flags])
                            st.markdown(f'<div class="alert-box">🚨 <b>Trop de risque concentré</b> : {f_names} représente plus de 40% du risque total. Rééquilibrez.</div>', unsafe_allow_html=True)

    def render_satellite_card_pedagogic(self, nom: str, ticker_key: str, unified: Dict, target_weight: Dict,
                                        regime: Dict, sent_rows: List[Dict], sector: str, gap_vs_world: Optional[float] = None):
        color_map = {"korea": "#F97316", "chip": "#A855F7", "value": "#D4AF37"}
        color = color_map.get(sector, "#D4AF37")
        strat_full = self.se.compute(ticker_key, unified, regime)
        simple_score = self.pde.translate_simple_score(unified["total"])
        st.markdown(f'<div class="card" style="border-top:3px solid {color};padding:0;overflow:hidden;">', unsafe_allow_html=True)
        c_score, c_action = st.columns([2, 3])
        with c_score:
            gap_str = f"{gap_vs_world:+.2f}%" if gap_vs_world is not None else "N/A"
            st.markdown(f'<div style="padding:1.4rem 1.4rem .8rem 1.4rem;"><div class="kpi-label">{nom} --- Score Global</div>'
                        f'<div class="simple-score-ring {simple_score["ring_cls"]}" style="margin:1rem auto;">{strat_full["total"]}/5</div>'
                        f'<div style="text-align:center;margin:.4rem 0;"><span style="font-size:1.3rem;">{simple_score["stars"]}</span></div>'
                        f'<div style="text-align:center;font-weight:700;color:#E2E8F0;">{simple_score["label"]}</div>'
                        f'<div style="text-align:center;font-size:.82rem;color:#8892AA;">{simple_score["explain"]}</div>'
                        f'<div style="text-align:center;font-size:.82rem;color:#6B7585;margin-top:.4rem;">Écart vs World (15j) : {gap_str}</div>'
                        f'</div>', unsafe_allow_html=True)
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
        self.render_leadership_comparison(nom, ticker_key, color)
        sent_verdict = self.pde.translate_sentinelles(sent_rows, sector)
        lv_color = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}.get(sent_verdict["level"], "#6B7585")
        lv_bg = {"green": "rgba(34,197,94,.1)", "orange": "rgba(249,115,22,.1)", "red": "rgba(255,49,49,.1)"}.get(sent_verdict["level"], "rgba(107,117,133,.1)")
        st.markdown(f'<div style="background:{lv_bg};border-left:4px solid {lv_color};border-radius:8px;padding:.8rem 1rem;margin:.5rem 0;">'
                    f'<b>Santé du secteur :</b> {sent_verdict["emoji"]} {sent_verdict["message"]}<br>'
                    f'<span style="font-size:.82rem;">{sent_verdict["detail"]}</span><br>'
                    f'<span style="font-size:.84rem;">💡 {sent_verdict["action"]}</span></div>', unsafe_allow_html=True)
        with st.expander("⚙ Allocation cible & ajustement", expanded=False):
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
            fig_a = plot_alpha_bars(self.dm, ticker_key, nom)
            if fig_a:
                st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})
                st.caption("Chaque barre = journée où l'ETF a fait mieux (vert) ou moins bien (rouge) que le MSCI World.")
            fig_r = plot_relative_perf(self.dm, ticker_key, nom)
            if fig_r:
                st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})
                st.caption("Courbe au-dessus de 0 = l'ETF surperforme le World depuis le début du suivi.")

    def render_sentinelles_macro(self, ptf: Dict):
        st.markdown("## 🛰 Radar Sectoriel & Macro-économie")
        st.markdown("### 📌 Valeurs de référence sectorielles")
        st.markdown("#### 🌍 World (NVIDIA, Apple, Alphabet, Microsoft, Amazon)")
        world_stocks = [
            ("NVIDIA", "NVDA"), ("Apple", "AAPL"), ("Alphabet A", "GOOGL"),
            ("Alphabet C", "GOOG"), ("Microsoft", "MSFT"), ("Amazon", "AMZN")
        ]
        world_rows = []
        for name, tk in world_stocks:
            info = self.dm.analyze_ticker(tk)
            prix = info["prix"] if info else None
            var = None
            if info and info["prix"] and info.get("sma20"):
                var = ((info["prix"] - info["sma20"]) / info["sma20"]) * 100
            world_rows.append({
                "Action": name,
                "Dernier cours (€)": f"{prix:.2f}" if prix else "N/A",
                "Variation vs SMA20": f"{self._sign(var)}{var:.2f}%" if var is not None else "N/A"
            })
        st.dataframe(pd.DataFrame(world_rows), use_container_width=True, hide_index=True)
        st.markdown("#### 🇰🇷 Korea (Samsung, SK Hynix)")
        korea_stocks = [("Samsung", "005930.KS"), ("SK Hynix", "000660.KS")]
        korea_rows = []
        for name, tk in korea_stocks:
            info = self.dm.analyze_ticker(tk)
            prix = info["prix"] if info else None
            var = None
            if info and info["prix"] and info.get("sma20"):
                var = ((info["prix"] - info["sma20"]) / info["sma20"]) * 100
            korea_rows.append({
                "Action": name,
                "Dernier cours": f"{prix:.2f}" if prix else "N/A",
                "Variation vs SMA20": f"{self._sign(var)}{var:.2f}%" if var is not None else "N/A"
            })
        st.dataframe(pd.DataFrame(korea_rows), use_container_width=True, hide_index=True)
        st.markdown("#### 🔬 Semiconductors (TSMC, NVIDIA, AMD, Intel)")
        chip_stocks = [("TSMC", "TSM"), ("NVIDIA", "NVDA"), ("AMD", "AMD"), ("Intel", "INTC")]
        chip_rows = []
        for name, tk in chip_stocks:
            info = self.dm.analyze_ticker(tk)
            prix = info["prix"] if info else None
            var = None
            if info and info["prix"] and info.get("sma20"):
                var = ((info["prix"] - info["sma20"]) / info["sma20"]) * 100
            chip_rows.append({
                "Action": name,
                "Dernier cours (€)": f"{prix:.2f}" if prix else "N/A",
                "Variation vs SMA20": f"{self._sign(var)}{var:.2f}%" if var is not None else "N/A"
            })
        st.dataframe(pd.DataFrame(chip_rows), use_container_width=True, hide_index=True)

        s_msg, s_col, sent_rows = self.pe.evaluate_sentinelles()
        col_s, col_m = st.columns([3, 2])
        with col_s:
            st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
            st.markdown("### 📡 Indicateurs avancés sectoriels")
            st.caption("Sentinelles : sous SMA20 = alerte.")
            if "OK" in s_msg:
                st.success(s_msg)
            else:
                st.warning(s_msg)
            st.dataframe(pd.DataFrame(sent_rows), use_container_width=True, hide_index=True)
            st.markdown("---")
            st.markdown("#### ⚖ Poids Satellites actuel (Korea + Semiconductors)")
            vt = ptf["valeur_totale"]
            krw_v = next((p["valeur"] for p in ptf["positions"] if p["nom"] == "MSCI Korea"), 0)
            chip_v = next((p["valeur"] for p in ptf["positions"] if p["nom"] == "MSCI Semiconductors"), 0)
            poids_sat = (krw_v + chip_v) / vt * 100 if vt else 0
            delta_ps = poids_sat - 29.3
            st.metric("Korea + Semiconductors", f"{poids_sat:.1f}%", delta=f"{self._sign(delta_ps)}{delta_ps:.1f}% vs objectif 29.3%")
            bc = "#FF3131" if poids_sat > 35 else "#22C55E"
            st.markdown(f'<div style="background:#1C1F26;border-radius:6px;height:8px;"><div style="background:{bc};width:{min(poids_sat,100):.1f}%;height:8px;border-radius:6px;"></div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if vt > 0:
                sat_alert = poids_sat > 35
                if sat_alert:
                    excess = (poids_sat - 29.3) / 100 * vt
                    st.markdown(f'<div class="arb-sell" style="margin-top:1rem;">'
                                f'<b>🔴 Alerte : Satellites > 35% du portefeuille</b><br>'
                                f'Montant excédentaire : {excess:,.0f}€ ({(poids_sat-29.3):.1f}% du portefeuille)<br>'
                                f'💡 <b>Action suggérée</b> : Réduire les satellites pour renforcer le World.</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="arb-neutral">✅ Poids satellites dans la limite (≤35%).</div>', unsafe_allow_html=True)

        with col_m:
            st.markdown('<div class="card card-gold">', unsafe_allow_html=True)
            st.markdown("### 🌍 Indicateurs Macro <span class='live-badge'>LIVE</span>", unsafe_allow_html=True)
            st.caption("Contexte économique mondial.")
            FMT = {"NQ=F": ".2f", "ES=F": ".2f", "^TNX": ".3f", "EURUSD=X": ".4f",
                   "BZ=F": ".2f", "GC=F": ".2f", "DX-Y.NYB": ".2f", "MCHI": ".2f"}
            SFX = {"^TNX": "%", "BZ=F": "$", "GC=F": "$"}
            st.markdown("#### 📡 Signaux ETF (Prix > SMA200)")
            for etf_name, etf_ticker in [("WMMS", "WMMS.DE"), ("MWRD World", "MWRD.PA"),
                                         ("DCAM PEA", "DCAM.PA"), ("Korea", "KRW.PA"), ("CHIP", "CHIP.PA")]:
                info = self.dm.analyze_ticker(etf_ticker)
                if info and info["prix"] and info["sma200"]:
                    signal = "Favorable" if info["prix"] > info["sma200"] else "Défavorable"
                    color = "#22C55E" if signal == "Favorable" else "#FF3131"
                    st.markdown(f"**{etf_name}** : <span style='color:{color};font-weight:bold;'>{signal}</span> "
                                f"(Prix {info['prix']:.2f}€ vs SMA200 {info['sma200']:.2f}€)", unsafe_allow_html=True)
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

    # ========================================================================
    # NOUVELLE méthode render_quant_alert_v2 (remplace l'ancienne appel)
    # ========================================================================
    def render_quant_alert_v2(self, ptf: Dict, positions_conf: List[Dict]):
        st.markdown("## 🧭 Alerte Quantitative — Decision Engine v2")
        st.caption("Combine Trend, Relative Strength, Crash Protection, Underperformance, "
                   "Régime World et latence Linxea. Aucun signal isolé ne déclenche une décision seul.")

        world_regime = self.wre.get_regime()
        now = datetime.now(ZoneInfo("Europe/Paris"))

        regime_colors = {"RISK_ON": "#22C55E", "NEUTRAL": "#3B82F6", "RISK_OFF": "#F97316", "CRASH": "#FF3131"}
        rc = regime_colors.get(world_regime["regime"], "#6B7585")
        st.markdown(f'<div class="regime-banner" style="background:{rc}22;border:1px solid {rc};">'
                    f'🌍 World Regime : <b style="color:{rc};">{world_regime["regime"]}</b> · '
                    f'Vol Shock : {world_regime.get("vol_shock","N/A")} · '
                    f'Drawdown : {world_regime.get("drawdown","N/A")}%</div>', unsafe_allow_html=True)

        if "_last_decisions" not in st.session_state:
            st.session_state["_last_decisions"] = {}

        for pos in ptf["positions"]:
            ticker = pos.get("ticker")
            if not ticker or pos["valeur"] <= 0:
                continue

            ind = self.ie.compute(ticker)
            crash = self.cpe.compute(ind, world_regime["regime"]) if ind else {"score": 0, "level": "N/A", "reasons": []}
            underperf = self.upe.compute(ind) if ind else {"score": 0, "max_score": 4, "reasons": []}
            dq = self.dqe.score(ind, world_regime)

            exec_date, latency_days = self.lee.compute_execution_date(now)
            latency = self.lee.latency_risk(ticker, crash["score"], latency_days) if ind else {"available": False}

            rc_pct = None  # à brancher avec qre.risk_contribution si déjà calculé

            prev_decision = st.session_state["_last_decisions"].get(ticker)
            result = self.dec_engine.decide(ticker, ind or {}, crash, underperf, world_regime, dq,
                                            latency, risk_contribution_pct=rc_pct,
                                            previous_decision=prev_decision)
            st.session_state["_last_decisions"][ticker] = result["decision"]

            nom = ETF_LIBRARY.get(ticker, {}).get("nom", ticker)
            decision_colors = {"HOLD": "#22C55E", "WATCH": "#F97316", "REDUCE_25": "#F97316",
                               "REDUCE_50": "#FF3131", "EXIT": "#FF3131", "RE_ENTER": "#3B82F6",
                               "NO_DECISION": "#6B7585"}
            dcol = decision_colors.get(result["decision"], "#6B7585")

            with st.container():
                st.markdown(f'<div class="card" style="border-left:4px solid {dcol};">', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([2, 3, 2])
                with c1:
                    st.markdown(f"**{nom}**")
                    st.markdown(f'<span style="color:{dcol};font-weight:800;font-size:1.3rem;">'
                                f'{result["decision"]}</span>', unsafe_allow_html=True)
                    st.caption(f"Confiance : {result['confidence']}")
                with c2:
                    if ind:
                        st.write(f"Trend {ind['trend_score']}/4 · Force relative {ind['relative_trend_score']}/4")
                        st.write(f"Alpha20 : {ind['alpha20']*100:+.1f}%" if ind['alpha20'] is not None else "Alpha20 : N/A")
                        st.write(f"Crash Score : {crash['score']}/7 ({crash['level']}) · "
                                 f"Underperf : {underperf['score']}/4")
                    else:
                        st.warning("Indicateurs indisponibles")
                with c3:
                    st.write(f"Qualité données : {dq['label']} ({dq['score']}/100)")
                    st.write(f"Exécution estimée : {exec_date.strftime('%d/%m %H:%M')} (J+{latency_days})")
                    if latency.get("available"):
                        st.write(f"Risque latence : {latency['risk_label']} "
                                 f"({latency['expected_loss_pct']:+.2f}%, n={latency['n_samples']})")

                if result.get("note_risk"):
                    st.info(result["note_risk"])
                if result["reasons"]:
                    with st.expander("Détail des signaux"):
                        for r in result["reasons"]:
                            st.write(f"• {r}")
                st.markdown('</div>', unsafe_allow_html=True)

    # ========================================================================
    # NOUVEAU : Onglet Backtest & Calibration
    # ========================================================================
    def render_backtest_calibration_tab(self, ptf: Dict):
        st.markdown("## 🧪 Backtest & Calibration (Priorité 3)")
        st.caption("Walk-forward, comparaison de stratégies, calibration des seuils "
                   "hors-échantillon. Aucun résultat ici ne doit être pris comme une "
                   "garantie — c'est un outil d'aide à la décision statistique.")

        if not SKLEARN_OK:
            st.warning("⚠ scikit-learn n'est pas installé — le modèle Ridge est désactivé, "
                       "seule la baseline historique est disponible. "
                       "`pip install scikit-learn --break-system-packages`")

        held_tickers = [p.get("ticker") for p in ptf["positions"] if p.get("ticker") and p["valeur"] > 0]
        if not held_tickers:
            st.info("Aucune position détenue à analyser.")
            return
        ticker = st.selectbox("ETF à analyser", held_tickers,
                              format_func=lambda t: ETF_LIBRARY.get(t, {}).get("nom", t))

        with st.spinner("Construction des features et calculs..."):
            feat = build_feature_frame(self.dm, ticker)

        if feat.empty:
            st.error("Historique insuffisant pour cet ETF (minimum ~300 jours communs avec le World).")
            return

        st.markdown(f"📊 **{len(feat)}** jours de données exploitables pour `{ticker}`")

        # --- Section 1 : Walk-Forward Ridge vs Baseline ---
        st.markdown("### 1️⃣ Walk-Forward : Ridge vs Baseline historique")
        model = ForwardAlphaModel(horizon=20, n_folds=4)
        wf_result = model.walk_forward_evaluate(feat)
        if wf_result.get("available"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Baseline (moyenne historique)**")
                st.metric("Hit Rate (sens correct)", f"{wf_result['baseline']['hit_rate']*100:.1f}%")
                st.metric("Corrélation", f"{wf_result['baseline']['correlation']:.3f}")
            with c2:
                st.markdown("**Ridge (walk-forward)**")
                st.metric("Hit Rate (sens correct)", f"{wf_result['ridge']['hit_rate']*100:.1f}%")
                st.metric("Corrélation", f"{wf_result['ridge']['correlation']:.3f}")
            st.caption(f"Échantillon OOS : {wf_result['n_oos_samples']} observations "
                       f"réparties sur {model.n_folds} folds walk-forward.")
            if wf_result["ridge_better"]:
                st.success("✅ Ridge apporte un gain mesurable vs la baseline sur cette période.")
            else:
                st.info("ℹ Ridge n'apporte pas de gain net vs la baseline simple sur cette période "
                        "— la baseline reste un choix raisonnable pour cet ETF.")

            # Prédiction du jour (modèle final, entraîné sur tout l'historique)
            prod_model, scaler = model.fit_production_model(feat)
            pred_today = model.predict_today(feat, prod_model, scaler)
            if pred_today is not None:
                st.markdown(f"**Alpha attendu à 20 jours (aujourd'hui) : {pred_today*100:+.2f}%** "
                            f"<span style='color:#6B7585;font-size:.8rem;'>(modèle de production, à titre indicatif)</span>",
                            unsafe_allow_html=True)
        else:
            st.warning(wf_result.get("reason", "Walk-forward indisponible."))

        # --- Section 2 : Backtest A/B/C/D ---
        st.markdown("### 2️⃣ Backtest comparatif — Stratégies A/B/C/D")
        bt = BacktestEngine(CRASH_THRESHOLDS, UNDERPERF_THRESHOLDS)
        bt_results = bt.run(self.dm, ticker, feat)

        rows = []
        for name, label in [("A_BuyHold", "A — Buy & Hold"), ("B_SignalNoDelay", "B — Signal sans délai"),
                            ("C_SignalLinxeaDelay", "C — Signal + délai Linxea"),
                            ("D_SignalStress", "D — Signal + stress (+1 séance)")]:
            m = bt_results.get(name, {})
            if not m.get("available"):
                continue
            rows.append({
                "Stratégie": label, "Rendement total": f"{m['total_return_pct']:+.1f}%",
                "CAGR": f"{m['cagr_pct']:+.1f}%", "Volatilité": f"{m['vol_pct']:.1f}%",
                "Max Drawdown": f"{m['max_drawdown_pct']:.1f}%", "Sharpe": f"{m['sharpe']:.2f}",
                "Calmar": f"{m['calmar']:.2f}", "Alpha vs World": f"{m['alpha_vs_world_pct']:+.1f}%",
                "Pire jour": f"{m['worst_day_pct']:.1f}%", "Pire 5j": f"{m['worst_5d_pct']:.1f}%",
                "Nb trades": m['n_trades'],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        fig = go.Figure()
        colors = {"A_BuyHold": "#6B7585", "B_SignalNoDelay": "#3B82F6",
                  "C_SignalLinxeaDelay": "#D4AF37", "D_SignalStress": "#FF3131"}
        for name, color in colors.items():
            m = bt_results.get(name, {})
            if m.get("available"):
                st.session_state.setdefault("_bt_curves", {})
                ec = m["equity_curve"]
                fig.add_trace(go.Scatter(x=ec.index, y=(ec - 1) * 100, name=name, line=dict(color=color)))
        fig.update_layout(**_PLOTLY_BASE, height=320, margin=dict(t=30, b=30, l=50, r=20),
                           yaxis=dict(title="Performance cumulée (%)", gridcolor="#2E3340"),
                           xaxis=dict(gridcolor="#2E3340"),
                           legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # --- Section 3 : Calibration des seuils ---
        st.markdown("### 3️⃣ Calibration des seuils (grid search hors-échantillon)")
        st.caption("Recherche sur 70% de l'historique (train), validation sur les 30% restants "
                   "jamais vus pendant la recherche (test). Garde-fou : un jeu de seuils qui "
                   "détruit le CAGR de plus de 60% vs Buy & Hold est automatiquement rejeté.")
        if st.button("🔍 Lancer la calibration (peut prendre 10-30 secondes)", key=f"calib_{ticker}"):
            with st.spinner("Grid search en cours (jusqu'à 100 combinaisons testées)..."):
                calib = CalibrationEngine(self.dm)
                calib_res = calib.calibrate(ticker, feat)
            if calib_res.get("available"):
                best = calib_res["best_thresholds"]
                st.success(f"✅ {calib_res['n_combinations_tested']} combinaisons valides testées.")
                c1, c2, c3 = st.columns(3)
                c1.metric("Seuil Alpha20 optimal", f"{best['alpha20']*100:.0f}%")
                c2.metric("Seuil Vol Ratio optimal", f"{best['vol_ratio']:.2f}")
                c3.metric("Seuil DD 5j optimal", f"{best['dd_5d']*100:.0f}%")

                oos = calib_res["oos_validation"]
                default_oos = calib_res["default_thresholds_oos"]
                if oos.get("available") and default_oos.get("available"):
                    cA, cB = st.columns(2)
                    with cA:
                        st.markdown("**Seuils actuels (par défaut) — validation OOS**")
                        st.write(f"Calmar : {default_oos['calmar']:.2f} · CAGR : {default_oos['cagr_pct']:+.1f}% "
                                 f"· Max DD : {default_oos['max_drawdown_pct']:.1f}%")
                    with cB:
                        st.markdown("**Seuils calibrés — validation OOS**")
                        st.write(f"Calmar : {oos['calmar']:.2f} · CAGR : {oos['cagr_pct']:+.1f}% "
                                 f"· Max DD : {oos['max_drawdown_pct']:.1f}%")
                    if calib_res["improvement"] and calib_res["improvement"] > 0:
                        st.success(f"📈 Amélioration du Calmar hors-échantillon : "
                                  f"{calib_res['improvement']:+.2f}")
                    else:
                        st.info("Pas d'amélioration nette hors-échantillon — "
                               "gardez vos seuils par défaut pour cet ETF.")
            else:
                st.warning(calib_res.get("reason", "Calibration indisponible."))

    def render_long_term_cockpit(self, ptf: Dict, analytics_engine: AnalyticsEngine, regime: Dict):
        st.markdown("## 📈 Cockpit Décisionnel Long Terme — Analyse de tous les ETF disponibles")
        st.caption("Résumé des métriques clés pour l'ensemble des ETF de la bibliothèque (même ceux non détenus).")

        all_tickers = list(ETF_LIBRARY.keys())
        etf_metrics = {}
        for ticker in all_tickers:
            meta = ETF_LIBRARY.get(ticker, {})
            yf_ticker = meta.get("yf", ticker)
            if yf_ticker in self.dm.data:
                etf_metrics[ticker] = analytics_engine.compute_all_metrics(yf_ticker)
            else:
                etf_metrics[ticker] = analytics_engine.compute_all_metrics(ticker)

        def relative_perf_3w(ticker):
            meta = ETF_LIBRARY.get(ticker, {})
            yf_tk = meta.get("yf", ticker)
            df = self.dm.data.get(yf_tk)
            world = get_world_series(self.dm, exclude_ticker=ticker)
            if df is None or world.empty:
                return None
            close = df["Close"].dropna()
            common = close.index.intersection(world.index)
            if len(common) < 15:
                return None
            period = min(15, len(common)-1)
            if period < 1:
                return None
            asset_ret = (close.iloc[-1] / close.iloc[-period-1] - 1) * 100 if len(close) >= period+1 else 0
            world_ret = (world.loc[common[-1]] / world.loc[common[-period-1]] - 1) * 100 if len(world) >= period+1 else 0
            return asset_ret - world_ret

        data = []
        for ticker in all_tickers:
            meta = ETF_LIBRARY.get(ticker, {})
            metrics = etf_metrics.get(ticker, {})
            if not metrics:
                continue
            name = meta.get("nom", ticker)
            mom6 = metrics.get("mom_6m", np.nan)
            rel_str = metrics.get("rel_strength", np.nan)
            vol = metrics.get("volatility", np.nan)
            sharpe = metrics.get("sharpe", np.nan)
            corr1m = metrics.get("corr_1m", np.nan)
            corr3m = metrics.get("corr_3m", np.nan)
            gap3w = relative_perf_3w(ticker)

            def fmt(val, low_thresh=0, high_thresh=5, invert=False):
                if np.isnan(val):
                    return "N/A", "gray"
                if invert:
                    if val <= low_thresh:
                        return f"{val:.2f}", "green"
                    elif val >= high_thresh:
                        return f"{val:.2f}", "red"
                    else:
                        return f"{val:.2f}", "orange"
                else:
                    if val >= high_thresh:
                        return f"{val:.2f}", "green"
                    elif val <= low_thresh:
                        return f"{val:.2f}", "red"
                    else:
                        return f"{val:.2f}", "orange"

            mom_str, mom_col = fmt(mom6, low_thresh=5, high_thresh=15)
            rel_str2, rel_col = fmt(rel_str, low_thresh=0, high_thresh=5)
            vol_str, vol_col = fmt(vol, low_thresh=15, high_thresh=25, invert=True)
            sharpe_str, sharpe_col = fmt(sharpe, low_thresh=0.5, high_thresh=1.2)
            corr1m_str, corr1m_col = fmt(corr1m, low_thresh=0.5, high_thresh=0.8)
            corr3m_str, corr3m_col = fmt(corr3m, low_thresh=0.5, high_thresh=0.8)
            gap_str = f"{gap3w:+.1f}%" if gap3w is not None else "N/A"
            gap_color = "#22C55E" if (gap3w or 0) > 0 else "#FF3131" if (gap3w or 0) < 0 else "#6B7585"

            data.append({
                "ETF": name,
                "Momentum 6M": f"<span style='color:{mom_col};'>{mom_str}</span>",
                "Force Relative vs World": f"<span style='color:{rel_col};'>{rel_str2}</span>",
                "Volatilité (%)": f"<span style='color:{vol_col};'>{vol_str}</span>",
                "Sharpe": f"<span style='color:{sharpe_col};'>{sharpe_str}</span>",
                "Corrélation 1M": f"<span style='color:{corr1m_col};'>{corr1m_str}</span>",
                "Corrélation 3M": f"<span style='color:{corr3m_col};'>{corr3m_str}</span>",
                "Gap 3 sem. vs World": f"<span style='color:{gap_color};'>{gap_str}</span>"
            })

        st.markdown(pd.DataFrame(data).to_html(escape=False, index=False), unsafe_allow_html=True)
        st.caption("Légende : 🟢 OK (vert) / 🟠 À surveiller (orange) / 🔴 Dégradé (rouge).")

    def render_fiscal_simulator(self, ptf: Dict):
        st.markdown("## 🧮 Simulateur Fiscal")
        st.caption("Calculez le montant net après impôts en cas de vente.")
        col_pea, col_av = st.columns(2)
        val_env, gan_env = ptf["val_env"], ptf["gain_env"]
        with col_pea:
            st.markdown('<div class="card card-blue"><h4>🏦 PEA</h4>', unsafe_allow_html=True)
            net, avert = net_apres_impots("PEA", val_env["PEA"], val_env["PEA"], gan_env["PEA"])
            if avert:
                st.warning(avert)
                st.metric("Valeur brute PEA", f"{val_env['PEA']:,.2f}€")
            else:
                st.metric("Net après prélèvements (17.2%)", f"{net:,.2f}€")
            st.caption(f"Gain latent PEA : {self._sign(gan_env['PEA'])}{gan_env['PEA']:,.2f}€")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_av:
            st.markdown('<div class="card card-blue"><h4>🛡 Assurance-Vie</h4>', unsafe_allow_html=True)
            net, avert = net_apres_impots("AV", val_env["AV"], val_env["AV"], gan_env["AV"])
            if avert:
                st.warning(avert)
                st.metric("Valeur brute AV", f"{val_env['AV']:,.2f}€")
            else:
                st.metric("Net après fiscalité AV", f"{net:,.2f}€")
            st.caption(f"Gain latent AV : {self._sign(gan_env['AV'])}{gan_env['AV']:,.2f}€")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💸 Simulez un retrait partiel")
        sc1, sc2 = st.columns([2, 1])
        with sc2:
            env_sim = st.selectbox("Enveloppe", ["AV", "PEA"])
        with sc1:
            max_val = float(max(val_env.get(env_sim, 0), 1000))
            montant_sim = st.slider("Montant à retirer (€)", 0.0, max_val, min(1000.0, max_val), step=100.0)
        net_sim, avert_sim = net_apres_impots(env_sim, montant_sim, val_env.get(env_sim, 0), gan_env.get(env_sim, 0))
        if avert_sim:
            st.warning(avert_sim)
        elif montant_sim > 0:
            vp, gp = val_env.get(env_sim, 0), gan_env.get(env_sim, 0)
            gain_sim = montant_sim * (gp / vp if vp else 0)
            imp_sim = montant_sim - net_sim
            st.markdown(f'<div class="net-box" style="display:flex;gap:2.5rem;flex-wrap:wrap;">'
                        f'<div><div class="kpi-label">Vous retirez</div><div class="kpi-value">{montant_sim:,.2f}€</div></div>'
                        f'<div style="color:#6B7585;">→</div>'
                        f'<div><div class="kpi-label">Part gains imposables</div><div class="kpi-value" style="color:#D4AF37;">{gain_sim:,.2f}€</div></div>'
                        f'<div><div class="kpi-label">Impôts / PS</div><div class="kpi-value" style="color:#FF3131;">{imp_sim:,.2f}€</div></div>'
                        f'<div><div class="kpi-label">Vous recevez</div><div class="kpi-value" style="color:#22C55E;">{net_sim:,.2f}€</div></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    def render_transactions_tab(self):
        st.markdown("## 📈 Journal des Transactions")
        st.caption("Enregistrez vos ordres BUY/SELL. Le moteur reconstruit automatiquement le portefeuille.")
        with st.expander("➕ Enregistrer un nouvel ordre", expanded=True):
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
            with c1:
                tx_type = st.selectbox("Type", ["BUY", "SELL"], key="tx_type")
            with c2:
                etf_options = {f"{ticker} - {meta['nom']}": ticker for ticker, meta in ETF_LIBRARY.items()}
                selected_display = st.selectbox("Actif", list(etf_options.keys()), key="tx_ticker")
                tx_ticker = etf_options[selected_display]
            with c3:
                tx_parts = st.number_input("Parts", min_value=0.0, value=0.0, format="%.4f", step=0.0001, key="tx_parts")
            with c4:
                meta_sel = ETF_LIBRARY.get(tx_ticker, {})
                live_px = self.dm.live.get(meta_sel.get("yf", ""), {}).get("prix")
                default_p = float(live_px) if live_px else 0.0
                tx_price = st.number_input("Prix unitaire (€)", min_value=0.0, value=default_p, format="%.4f", step=0.01, key="tx_price")
            with c5:
                tx_date = st.date_input("Date", value=datetime.now().date(), key="tx_date")
            tx_note = st.text_input("Note (optionnel)", key="tx_note", placeholder="ex: DCA mensuel")
            col_btn, col_info = st.columns([1, 3])
            with col_btn:
                if st.button("✅ Enregistrer l'ordre", type="primary", use_container_width=True):
                    if tx_parts > 0 and tx_price > 0:
                        tx_record = {
                            "date": str(tx_date), "type": tx_type, "ticker": tx_ticker,
                            "parts": tx_parts, "price": tx_price,
                            "montant": round(tx_parts * tx_price, 2), "note": tx_note
                        }
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
                        st.warning("⚠ Parts et Prix doivent être > 0")
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
        for tx in sorted(txs, key=lambda x: x.get("date", ""), reverse=True):
            meta_t = ETF_LIBRARY.get(tx.get("ticker", ""), {})
            rows.append({
                "Date": tx.get("date", ""), "Type": tx.get("type", ""),
                "ETF": meta_t.get("nom", tx.get("ticker", "")),
                "Parts": f"{tx.get('parts', 0):.4f}", "Prix": f"{tx.get('price', 0):.4f}€",
                "Montant": f"{tx.get('montant', 0):,.2f}€", "Note": tx.get("note", "")
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown("### 📊 Positions reconstruites (TransactionEngine)")
        rebuilt = self.te.rebuild_portfolio_at_date()
        if rebuilt:
            r_rows = []
            for tk_id, data in rebuilt.items():
                if data["parts"] <= 0:
                    continue
                prm = data["total_cost"] / data["parts"] if data["parts"] > 0 else 0
                meta = ETF_LIBRARY.get(tk_id, {})
                r_rows.append({
                    "Ticker": tk_id, "Nom": meta.get("nom", tk_id),
                    "Parts": f"{data['parts']:.4f}", "PRMin (€)": f"{prm:.4f}",
                    "Investi (€)": f"{data['total_cost']:,.2f}", "Enveloppe": meta.get("enveloppe", "?")
                })
            st.dataframe(pd.DataFrame(r_rows), use_container_width=True, hide_index=True)
        if st.button("🔄 Synchroniser → portfolio_positions.json", type="secondary"):
            new_pos = self.te.get_portfolio_as_positions()
            if new_pos:
                self.pcm.save_positions(new_pos)
                st.session_state["raw_positions"] = new_pos
                st.session_state["positions"] = enrich_positions(new_pos)
                st.success("✅ portfolio_positions.json mis à jour depuis les transactions !")
                st.rerun()

    def render_screener_tab(self):
        st.markdown("## 🔍 Screener Quantitatif d'ETFs")
        # Diagnostic des tickers sans données
        failures = st.session_state.get("_data_failures", [])
        if failures:
            with st.expander(f"⚠ {len(failures)} ticker(s) sans données — diagnostic", expanded=False):
                st.write(failures)
        st.caption("Scoring multi-facteurs (0-100) basé sur momentum 6M, force relative, Sharpe, volatilité, drawdown, RSI, tendance.")
        with st.spinner("Calcul des scores en cours... (peut prendre quelques secondes)"):
            scores = []
            for ticker, meta in ETF_LIBRARY.items():
                yf_ticker = meta.get("yf", ticker)
                res = self.signal.compute_score(yf_ticker)
                # Si pas de données, on met N/A
                if res.get("status") == "NO_DATA" or not res.get("metrics"):
                    scores.append({
                        "Ticker": ticker,
                        "Nom": meta.get("nom", ""),
                        "Catégorie": meta.get("category", ""),
                        "Thème": meta.get("theme", ""),
                        "Score": "N/A",
                        "Momentum 6M": "N/A",
                        "Force Relative": "N/A",
                        "Volatilité": "N/A",
                        "Sharpe": "N/A",
                        "Drawdown": "N/A",
                        "Corr 1M": "N/A",
                        "Corr 3M": "N/A",
                        "Corr 6M": "N/A",
                        "Corr 1Y": "N/A",
                        "Statut": "⚠ Données indisponibles"
                    })
                else:
                    m = res["metrics"]
                    scores.append({
                        "Ticker": ticker,
                        "Nom": meta.get("nom", ""),
                        "Catégorie": meta.get("category", ""),
                        "Thème": meta.get("theme", ""),
                        "Score": res["score"],
                        "Momentum 6M": f"{m.get('mom_6m', 0):.1f}%",
                        "Force Relative": f"{m.get('rel_strength', 0):.1f}%",
                        "Volatilité": f"{m.get('volatility', 0):.1f}%",
                        "Sharpe": f"{m.get('sharpe', 0):.2f}",
                        "Drawdown": f"{m.get('max_drawdown_1y', 0):.1f}%",
                        "Corr 1M": f"{m.get('corr_1m', 0):.2f}" if m.get('corr_1m') is not None else "N/A",
                        "Corr 3M": f"{m.get('corr_3m', 0):.2f}" if m.get('corr_3m') is not None else "N/A",
                        "Corr 6M": f"{m.get('corr_6m', 0):.2f}" if m.get('corr_6m') is not None else "N/A",
                        "Corr 1Y": f"{m.get('corr_1y', 0):.2f}" if m.get('corr_1y') is not None else "N/A",
                        "Statut": "✅ Analysé"
                    })
            df_scores = pd.DataFrame(scores)
            # Trier : mettre les N/A en dernier
            df_scores["Score_num"] = pd.to_numeric(df_scores["Score"], errors="coerce")
            df_scores = df_scores.sort_values(["Score_num", "Statut"], ascending=[False, True]).drop(columns=["Score_num"])

        if df_scores.empty:
            st.warning("Aucun ETF n'a pu être analysé (données manquantes). Vérifiez votre connexion ou les tickers.")
            return
        max_val = len(df_scores)
        min_val = min(5, max_val)
        top_n = st.slider("Nombre d'ETFs à afficher", min_value=min_val, max_value=max_val, value=min(20, max_val), step=5)
        st.dataframe(df_scores.head(top_n), use_container_width=True, hide_index=True)
        if st.button("📊 Afficher tous les ETFs", use_container_width=True):
            st.dataframe(df_scores, use_container_width=True, hide_index=True)

    def render_position_sizing(self, ptf: Dict, regime_label: str):
        st.markdown("### ⚖ Position Sizing Modeler")
        st.caption("Poids cibles optimaux suggérés en fonction du régime macro.")
        total_val = ptf["valeur_totale"]
        if total_val <= 0:
            st.warning("Portefeuille vide.")
            return
        regime_factor = 1.0
        if regime_label in ("Stress", "Contraction"):
            regime_factor = 0.6
        elif regime_label == "Neutre":
            regime_factor = 0.8
        suggestions = []
        for pos in ptf["positions"]:
            ticker = pos.get("ticker")
            if not ticker:
                continue
            meta = next((m for m in ETF_LIBRARY.values() if m["yf"] == ticker), None)
            if not meta:
                continue
            cat = meta.get("category", "Satellite")
            if pos["nom"] == "Amundi MSCI World IMI Value Advanced":
                base_target = 0.37
            elif pos["nom"] == "MSCI World PEA":
                base_target = 0.183
            elif pos["nom"] == "MSCI World AV":
                base_target = 0.154
            elif pos["nom"] == "MSCI Korea":
                base_target = 0.155
            elif pos["nom"] == "MSCI Semiconductors":
                base_target = 0.138
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

    def render_arbitrage_widget(self):
        if "positions" not in st.session_state:
            return
        holdings = [p.get("_tk_id", p.get("ticker")) for p in st.session_state["positions"] if p.get("valeur", 0) > 0]
        holdings = list(dict.fromkeys([h for h in holdings if h in ETF_LIBRARY]))
        opps = self.signal.get_arbitrage_opportunities(holdings)
        if opps:
            st.markdown("### 🔄 Alertes d'arbitrage")
            for opp in opps:
                st.markdown(f'<div class="arb-sell">🚨 <b>Opportunité de rotation</b><br>'
                            f'Vendre <b>{opp["sell_name"]}</b> (score actuel) → Acheter <b>{opp["buy_name"]}</b><br>'
                            f'Gain potentiel estimé : +{opp["gain_potential"]} points de score</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="arb-neutral">✅ Aucune opportunité d\'arbitrage significative détectée.</div>', unsafe_allow_html=True)

    def render_footer(self, mode_direct: bool, capital: float, score_em: int, regime_label: str, live_ok: int, live_total: int):
        st.markdown("---")
        col_f1, col_f2 = st.columns([4, 1])
        with col_f1:
            s = self._sign
            mode_txt = "🔌 MODE DIRECT" if mode_direct else "Ajust. patrimonial actif"
            persist = "GitHub Gist + SQLite" if self.pm.status == "github" else "SQLite local"
            st.caption(f"◈ Cockpit v6.9 · Alerte Quant · {mode_txt} · "
                       f"Régime : {regime_label} · Capital {capital:,.2f}€ · Persistance : {persist} · {live_ok}/{live_total} prix live · "
                       f"Benchmark : MWR Cash-Flow Adjusted · Outil personnel --- Ne constitue pas un conseil en investissement")
        with col_f2:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

# -----------------------------------------------------------------------------
# MODULE 15 : VISUALISATIONS (corrigées avec get_world_series)
# -----------------------------------------------------------------------------
_PLOTLY_BASE = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#CBD5E1", family="DM Sans"))

def plot_equity_curve(history: pd.DataFrame) -> Optional[go.Figure]:
    if history.empty or "capital_cloture" not in history.columns:
        return None
    df = history.dropna(subset=["capital_cloture"]).copy()
    if len(df) < 2:
        return None
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_dt"]).sort_values("date_dt")
    fig = go.Figure()
    regime_colors = {
        "Euphorie": "rgba(168,85,247,.10)", "Expansion": "rgba(34,197,94,.10)",
        "Neutre": "rgba(59,130,246,.08)", "Stress": "rgba(245,158,11,.10)",
        "Contraction": "rgba(255,49,49,.12)"
    }
    if "regime" in df.columns:
        prev = None
        x0 = df["date_dt"].iloc[0]
        for _, row in df.iterrows():
            if row.get("regime") != prev and prev is not None:
                fig.add_vrect(x0=x0, x1=row["date_dt"], fillcolor=regime_colors.get(prev, "rgba(255,255,255,.03)"), layer="below", line_width=0)
                x0 = row["date_dt"]
            prev = row.get("regime")
        if prev:
            fig.add_vrect(x0=x0, x1=df["date_dt"].iloc[-1], fillcolor=regime_colors.get(prev, "rgba(255,255,255,.03)"), layer="below", line_width=0)
    fig.add_trace(go.Scatter(x=df["date_dt"], y=df["capital_cloture"], mode="lines+markers",
                            line=dict(color="#D4AF37", width=2.5), marker=dict(size=5), name="Capital Clôture"))
    if "perf_cumul" in df.columns and df["perf_cumul"].notna().any():
        fig.add_trace(go.Scatter(x=df["date_dt"], y=df["perf_cumul"], mode="lines",
                                line=dict(color="#3B82F6", width=1.5, dash="dot"), name="Perf Cumul (%)", yaxis="y2"))
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text="<b>Évolution de votre capital</b>", font=dict(size=13, color="#6B7585")),
        margin=dict(t=40, b=30, l=60, r=60), height=280,
        legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)", x=0, y=1.15, orientation="h"),
        xaxis=dict(gridcolor="#2E3340", showgrid=True),
        yaxis=dict(gridcolor="#2E3340", showgrid=True, ticksuffix="€", title="Capital (€)"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%", title="Perf (%)")
    )
    return fig

def plot_weekly_leadership(labels: List[str], sat_perfs: List[float], world_perfs: List[float],
                           sat_name: str, color_sat: str = "#D4AF37") -> go.Figure:
    fig = go.Figure()
    bar_colors_sat = ["#22C55E" if v > 0 else "#FF3131" for v in sat_perfs]
    fig.add_trace(go.Bar(x=labels, y=sat_perfs, name=sat_name, marker_color=bar_colors_sat,
                         text=[f"{v:+.1f}%" for v in sat_perfs], textposition="outside"))
    bar_colors_world = ["rgba(59,130,246,.7)" if v > 0 else "rgba(59,130,246,.4)" for v in world_perfs]
    fig.add_trace(go.Bar(x=labels, y=world_perfs, name="MSCI World", marker_color=bar_colors_world,
                         text=[f"{v:+.1f}%" for v in world_perfs], textposition="outside"))
    fig.add_hline(y=0, line_dash="dot", line_color="#4B5563", opacity=0.8)
    fig.update_layout(
        **_PLOTLY_BASE, barmode="group", bargap=0.20, bargroupgap=0.05,
        title=dict(text=f"<b>Leadership hebdomadaire : {sat_name} vs MSCI World</b>", font=dict(size=13, color="#6B7585")),
        margin=dict(t=50, b=40, l=50, r=30), height=300,
        legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)", x=0, y=1.12, orientation="h"),
        xaxis=dict(gridcolor="#2E3340", showgrid=False), yaxis=dict(gridcolor="#2E3340", ticksuffix="%", zeroline=False)
    )
    return fig

def plot_correlation_heatmap(corr_df: pd.DataFrame) -> go.Figure:
    short = {
        "WMMS.DE": "WMMS", "MWRD.PA": "World", "DCAM.PA": "W-PEA",
        "KRW.PA": "Korea", "CHIP.PA": "CHIP", "LYXTNOW.PA": "InfoTech", "IJPE.PA": "JapSC",
        "CV9.PA": "EuVal", "LYXFINW.PA": "Fin"
    }
    labels = [short.get(c, c) for c in corr_df.columns]
    fig = go.Figure(go.Heatmap(
        z=corr_df.values.round(2), x=labels, y=labels,
        colorscale=[[0, "#FF3131"], [0.5, "#252932"], [1, "#22C55E"]],
        zmid=0, zmin=-1, zmax=1,
        text=corr_df.values.round(2), texttemplate="%{text:.2f}",
        hovertemplate="<b>%{y} / %{x}</b><br>ρ = %{z:.2f}<extra></extra>",
        showscale=True,
        colorbar=dict(tickfont=dict(color="#CBD5E1", size=9), thickness=12, len=0.8, bgcolor="rgba(0,0,0,0)")
    ))
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text="<b>Corrélation Pearson (60j)</b>", font=dict(size=12, color="#6B7585")),
        margin=dict(t=40, b=10, l=60, r=20), height=220
    )
    return fig

def plot_risk_contribution(rc: Dict) -> Optional[go.Figure]:
    if not rc:
        return None
    short = {
        "WMMS.DE": "WMMS", "MWRD.PA": "World", "DCAM.PA": "W-PEA",
        "KRW.PA": "Korea", "CHIP.PA": "CHIP"
    }
    names = [short.get(tk, tk) for tk in rc]
    values = [rc[tk]["rc_pct"] for tk in rc]
    colors = ["#FF3131" if rc[tk]["flag"] else "#007BFF" for tk in rc]
    fig = go.Figure(go.Bar(x=values, y=names, orientation="h", marker_color=colors,
                           hovertemplate="%{y}: <b>%{x:.1f}%</b>"))
    fig.add_vline(x=40, line_dash="dash", line_color="#FF3131",
                  annotation_text="Seuil 40%", annotation_font=dict(color="#FF3131", size=9))
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text="<b>Risk Contribution (%)</b>", font=dict(size=12, color="#6B7585")),
        margin=dict(t=40, b=10, l=80, r=20), height=200,
        xaxis=dict(gridcolor="#2E3340", ticksuffix="%"), yaxis=dict(gridcolor="rgba(0,0,0,0)")
    )
    return fig

def plot_weight_indicator(current_pct: float, target_pct: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=round(current_pct, 1),
        number={"suffix": "%", "font": {"size": 26, "color": "#CBD5E1", "family": "Space Mono"}},
        delta={"reference": target_pct, "relative": False, "increasing": {"color": "#F97316"},
               "decreasing": {"color": "#22C55E"}, "suffix": "%", "valueformat": ".1f"},
        title={"text": "Poids Actuel<br><span style='font-size:.8em;color:#6B7585'>vs Cible (or)</span>",
               "font": {"size": 11, "color": "#8892AA"}},
        gauge={
            "axis": {"range": [0, 35], "tickcolor": "#6B7585", "tickfont": {"size": 9}, "nticks": 8},
            "bar": {"color": "#007BFF", "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [
                {"range": [0, 5], "color": "rgba(255,49,49,.18)"},
                {"range": [5, 15], "color": "rgba(249,115,22,.12)"},
                {"range": [15, 25], "color": "rgba(34,197,94,.12)"},
                {"range": [25, 35], "color": "rgba(212,175,55,.10)"}
            ],
            "threshold": {"line": {"color": "#D4AF37", "width": 4}, "thickness": 0.85,
                          "value": round(target_pct, 1)}
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font={"color": "#CBD5E1", "family": "DM Sans"},
        margin={"t": 50, "b": 10, "l": 20, "r": 20}, height=230
    )
    return fig

def plot_alpha_bars(dm: DataManager, ticker: str, nom: str) -> Optional[go.Figure]:
    """Écart quotidien vs le vrai World (via get_world_series)"""
    world = get_world_series(dm, exclude_ticker=ticker)
    if world.empty:
        return None
    sat_df = dm.data.get(ticker, pd.DataFrame())
    if sat_df is None or sat_df.empty:
        return None
    wc = world
    sc = sat_df["Close"].dropna()
    common = sc.index.intersection(wc.index)
    if len(common) < 17:
        return None
    common = common[-16:]
    alpha = ((sc[common].pct_change() - wc[common].pct_change()) * 100).dropna().iloc[-15:]
    if alpha.empty:
        return None
    fig = go.Figure(go.Bar(
        x=[d.strftime("%d/%m") for d in alpha.index],
        y=alpha.values,
        marker_color=["#22C55E" if v > 0 else "#FF3131" for v in alpha.values]
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=.6)
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text=f"<b>Écart quotidien</b> : {nom} vs MSCI World --- 15 derniers jours",
                   font=dict(size=11, color="#6B7585")),
        margin=dict(t=35, b=25, l=55, r=15), height=200,
        showlegend=False, xaxis=dict(gridcolor="#2E3340", showgrid=False),
        yaxis=dict(gridcolor="#2E3340", ticksuffix="%")
    )
    return fig

def plot_relative_perf(dm: DataManager, ticker: str, nom: str) -> Optional[go.Figure]:
    """Performance relative vs le vrai World (via get_world_series)"""
    world = get_world_series(dm, exclude_ticker=ticker)
    if world.empty:
        return None
    sat_df = dm.data.get(ticker, pd.DataFrame())
    if sat_df is None or sat_df.empty:
        return None
    wc = world
    sc = sat_df["Close"].dropna()
    common = sc.index.intersection(wc.index)
    if len(common) < 20:
        return None
    cutoff = max(DATE_DEBUT.date(), (datetime.now() - timedelta(days=120)).date())
    common_f = [d for d in common if d.date() >= cutoff] or list(common[-90:])
    ratio = sc[common_f] / wc[common_f]
    rel = (ratio / ratio.iloc[0] - 1) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values.clip(min=0), fill="tozeroy",
                             fillcolor="rgba(212,175,55,.12)", line=dict(color="rgba(0,0,0,0)"), showlegend=False))
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values.clip(max=0), fill="tozeroy",
                             fillcolor="rgba(255,49,49,.12)", line=dict(color="rgba(0,0,0,0)"), showlegend=False))
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values, line=dict(color="#D4AF37", width=2), name=f"{nom}/World"))
    if len(rel) >= 14:
        last14 = rel.iloc[-14:]
        fig.add_vrect(x0=last14.index[0], x1=last14.index[-1], fillcolor="rgba(0,123,255,.06)", layer="below", line_width=0)
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=.7)
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text=f"Performance relative : {nom} vs World (base 100)", font=dict(size=11, color="#6B7585")),
        margin=dict(t=20, b=20, l=50, r=20), height=200,
        showlegend=False, xaxis=dict(gridcolor="#2E3340"), yaxis=dict(gridcolor="#2E3340", ticksuffix="%")
    )
    return fig

# -----------------------------------------------------------------------------
# MODULE 17 : MAIN
# -----------------------------------------------------------------------------
def _load_config() -> Dict:
    defaults = {"capital_reel": _DEFAULT_CAPITAL_REEL, "ajustement_pat": _DEFAULT_AJUSTEMENT_PAT,
                "bonus_fortuneo": _DEFAULT_BONUS_FORTUNEO}
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
    # --- FORCE LE CHARGEMENT DES POSITIONS ---
    pcm = PortfolioConfigManager()
    raw = pcm.load_positions()
    pcm.save_positions(raw)
    st.session_state["raw_positions"] = raw
    st.session_state["positions"] = enrich_positions(raw)
    
    tickers_in_positions = {pos["ticker"] for pos in st.session_state["positions"]}
    if "KRW.PA" not in tickers_in_positions or "CHIP.PA" not in tickers_in_positions:
        st.error("❌ KRW.PA ou CHIP.PA manquant dans les positions. Réinitialisation forcée.")
        default_positions = [
            {"ticker": "WMMS.DE", "parts": 461.9561, "prm": 13.582, "account": "AV"},
            {"ticker": "DCAM.PA", "parts": 508.0000, "prm": 4.983, "account": "PEA"},
            {"ticker": "MWRD.PA", "parts": 16.6229, "prm": 149.718, "account": "AV"},
            {"ticker": "KRW.PA", "parts": 14.8501, "prm": 142.370, "account": "AV"},
            {"ticker": "CHIP.PA", "parts": 21.4922, "prm": 99.159, "account": "AV"},
        ]
        pcm.save_positions(default_positions)
        st.session_state["raw_positions"] = default_positions
        st.session_state["positions"] = enrich_positions(default_positions)
        st.rerun()

    if "config_loaded" not in st.session_state:
        cfg = _load_config()
        st.session_state["cfg_capital_reel"] = cfg["capital_reel"]
        st.session_state["cfg_ajustement_pat"] = cfg["ajustement_pat"]
        st.session_state["cfg_bonus_fortuneo"] = cfg["bonus_fortuneo"]
        st.session_state["config_loaded"] = True
        st.session_state["save_feedback"] = ""

    with st.spinner("📡 Chargement des données de marché..."):
        dm = DataManager()
        if not dm.live:
            st.error("❌ Aucun prix live. Vérifiez votre connexion.")
            st.stop()
        te = TransactionEngine()
        pm = PersistenceManager(static_capital=st.session_state["cfg_capital_reel"])
        mre = MarketRegimeEngine(dm)
        qre = QuantRiskEngine(dm)
        pe = PortfolioEngine(dm, mre, qre)
        pde = PedagogicEngine()
        se = StrategicEngine(dm, mre, qre)
        qae = QuantAlertEngine(dm)
        ui = StreamlitUI(dm, pm, mre, qre, pe, pde, se, qae, pcm=pcm, te=te)

    mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo = ui.render_sidebar()

    with st.spinner("⚙ Calcul des indicateurs..."):
        ptf = pe.compute_portfolio(positions_conf, capital_reel, ajustement_pat, bonus_fortuneo)
        bench = pe.compute_benchmark(positions_conf, ptf["perf_tot_pct"])
        regime = mre.get_full_regime()

        # ---- Calcul de wmms_gap (corrigé : comparaison de performance) ----
        wmms_gap = compute_relative_gap(dm, "WMMS.DE", days=15)

        etf_analyses = {}
        for pos in positions_conf:
            ticker = pos.get("ticker")
            if ticker:
                meta_tk = ETF_LIBRARY.get(ticker, {})
                yf_ticker = meta_tk.get("yf", ticker)
                info = dm.analyze_ticker(yf_ticker)
                etf_analyses[ticker] = info
        if etf_analyses is None:
            etf_analyses = {}

        unified_scores = {}
        target_weights = {}
        for pos in positions_conf:
            ticker = pos.get("ticker")
            if ticker:
                unified_scores[ticker] = pe.compute_unified_score(ticker)
                target_weights[ticker] = pe.compute_target_weight(pos["nom"], ticker, ptf["valeur_totale"], ptf["positions"])
        ld_alerts = pe.check_leadership_alerts()
        phase_text, phase_color = pe.determine_phase(bench.get("gap"), etf_analyses or {})
        _, _, sent_rows = pe.evaluate_sentinelles()
        live_ok = sum(1 for v in dm.live.values() if v.get("prix"))
        live_total = len(dm.live)

    tab_dashboard, tab_transactions, tab_screener, tab_backtest = st.tabs(
        ["📊 Dashboard", "📈 Transactions", "🔍 Screener", "🧪 Backtest & Calibration"]
    )

    with tab_dashboard:
        ui.render_header(mode_direct, live_ok, live_total)
        ui.render_regime_banner(regime)
        for al in ld_alerts:
            gv, nom_al, sp, wp = al["gap"], al["nom"], al["sat_perf"], al["world_perf"]
            s = StreamlitUI._sign
            if gv < -5:
                cls, ico = "alert-critical", "🚨"
            elif gv < -2:
                cls, ico = "alert-leadership", "⚠"
            else:
                continue
            st.markdown(f'<div class="{cls}">{ico} <b>ALERTE : {nom_al}</b> --- {abs(gv):.1f}% en retard sur le World sur 14 jours '
                        f'({nom_al} : {s(sp)}{sp:.1f}% | World : {s(wp)}{wp:.1f}%)<br>'
                        f'<span style="font-size:.85rem;">→ Vérifiez la section Leadership ci-dessous.</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="phase-banner" style="background:{phase_color};color:white;">{phase_text}</div>', unsafe_allow_html=True)
        ui.render_command_center(ptf, bench, mode_direct, pm)
        
        # ---- Performance hebdomadaire du portefeuille vs World ----
        ui.render_portfolio_leadership_comparison(ptf)
        
        ui.render_equity_curve_section(ptf, regime, positions_conf)
        ui.render_risk_dashboard(ptf)
        st.markdown("## 🧠 Analyse des ETF Satellites")

        wmms_pos = next((p for p in positions_conf if p.get("ticker") == "WMMS.DE"), None)
        if wmms_pos:
            ticker = "WMMS.DE"
            wmms_unified = unified_scores.get(ticker, {})
            wmms_target = target_weights.get(ticker, {})
            wmms_info = etf_analyses.get(ticker)
            if wmms_info:
                border = "#22C55E" if (wmms_info.get("sma20") and wmms_info.get("prix") and wmms_info["prix"] > wmms_info["sma20"]) else "#D4AF37"
                gap_display = f"{wmms_gap:+.2f}%" if wmms_gap is not None else "N/A"
                st.markdown(f'<div class="card" style="border-left:4px solid {border};margin-bottom:.5rem;">'
                            f'<b>📈 Amundi MSCI World IMI Value Advanced (WMMS) - Écart vs World (15j) : {gap_display}</b></div>', unsafe_allow_html=True)
                with st.container():
                    st.markdown("### 📈 Amundi MSCI World IMI Value Advanced (WMMS)")
                    ui.render_satellite_card_pedagogic("WMMS Value", "WMMS.DE", wmms_unified, wmms_target, regime, sent_rows, "value", gap_vs_world=wmms_gap)
            else:
                st.markdown('<div class="card card-orange"><div class="kpi-label">WMMS Value</div>'
                            '<div class="small">Données indisponibles pour cet ETF pour le moment (vérifiez le ticker Yahoo Finance WMMS.DE).</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        krw_pos = next((p for p in positions_conf if p.get("ticker") == "KRW.PA"), None)
        if krw_pos:
            ticker = "KRW.PA"
            krw_unified = unified_scores.get(ticker, {})
            krw_target = target_weights.get(ticker, {})
            krw_info = etf_analyses.get(ticker)
            if krw_info:
                border = "#22C55E" if (krw_info.get("sma20") and krw_info.get("prix") and krw_info["prix"] > krw_info["sma20"]) else "#F97316"
                st.markdown(f'<div class="card" style="border-left:4px solid {border};margin-bottom:.5rem;">'
                            f'<b>🇰🇷 MSCI Korea (KRW.PA)</b></div>', unsafe_allow_html=True)
                with st.container():
                    st.markdown("### 🇰🇷 MSCI Korea (KRW.PA)")
                    krw_gap = compute_relative_gap(dm, "KRW.PA", days=15)
                    ui.render_satellite_card_pedagogic("MSCI Korea", "KRW.PA", krw_unified, krw_target, regime, sent_rows, "korea", gap_vs_world=krw_gap)
        st.markdown("<br>", unsafe_allow_html=True)

        chip_pos = next((p for p in positions_conf if p.get("ticker") == "CHIP.PA"), None)
        if chip_pos:
            ticker = "CHIP.PA"
            chip_unified = unified_scores.get(ticker, {})
            chip_target = target_weights.get(ticker, {})
            chip_info = etf_analyses.get(ticker)
            if chip_info:
                border = "#22C55E" if (chip_info.get("sma20") and chip_info.get("prix") and chip_info["prix"] > chip_info["sma20"]) else "#A855F7"
                st.markdown(f'<div class="card" style="border-left:4px solid {border};margin-bottom:.5rem;">'
                            f'<b>🔬 MSCI Semiconductors (CHIP.PA)</b></div>', unsafe_allow_html=True)
                with st.container():
                    st.markdown("### 🔬 MSCI Semiconductors (CHIP.PA)")
                    chip_gap = compute_relative_gap(dm, "CHIP.PA", days=15)
                    ui.render_satellite_card_pedagogic("MSCI Semiconductors", "CHIP.PA", chip_unified, chip_target, regime, sent_rows, "chip", gap_vs_world=chip_gap)

        ui.render_sentinelles_macro(ptf)
        # Nouvelle alerte quant v2
        ui.render_quant_alert_v2(ptf, positions_conf)
        ui.render_long_term_cockpit(ptf, AnalyticsEngine(dm), regime)
        ui.render_fiscal_simulator(ptf)
        ui.render_position_sizing(ptf, regime["confirmed_label"])
        ui.render_arbitrage_widget()
        ui.render_footer(mode_direct, capital_reel, 0, regime["confirmed_label"], live_ok, live_total)

    with tab_transactions:
        ui.render_transactions_tab()

    with tab_screener:
        ui.render_screener_tab()

    with tab_backtest:
        ui.render_backtest_calibration_tab(ptf)

if __name__ == "__main__" or True:
    main()
