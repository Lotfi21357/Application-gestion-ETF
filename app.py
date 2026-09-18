# =============================================================================
# COCKPIT DÉCISIONNEL BOURSIER v8.4 — STRATEGIC DECISION ENGINE
# =============================================================================
# v8.3 : Corrections ciblées sur V8.2 :
#   1. Raison "Signaux non convergents" détaillée (compteurs explicites)
#   2. Score Semiconductor vs World affiché en principal (score rattrapage vs Korea secondaire)
#   3. Risk Contribution : verdict par poche concentrée (assumé vs candidat réduction)
#   4. Section dédiée uniformisée : "Chaque poche active vs MSCI World"
#   5. Position Sizing renormalisé pour atteindre 100%
#   6. Dashboard réordonné + camembert répartition
#   7. Carte satellite alignée sur le leadership hebdomadaire (fin des contradictions)
#   8. Synthèse en pied de position sizing (ajustement le plus significatif)
# v8.4 : Ajout courbe de performance du portefeuille + point haut
#         + Sauvegarde automatique quotidienne d'un snapshot (aucun clic requis)
# =============================================================================

# -----------------------------------------------------------------------------
# MODULE 0 : IMPORTS
# -----------------------------------------------------------------------------
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json, os, sqlite3, io, csv, warnings, tempfile
from typing import Optional, Dict, List, Tuple
import requests_cache
from scipy import stats
from scipy.optimize import minimize
import ta
import time
import io as _io
import requests as _requests

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

st.set_page_config(page_title="Cockpit v8.4", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

# -----------------------------------------------------------------------------
# MODULE 1 : CSS
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
.regime-contraction{ background:linear-gradient(135deg,#450A0A,#7F1D1D); color:#FCA5A5; border:1px solid #FF3131; }
.regime-pending { background:linear-gradient(135deg,#1C1F26,#22252E); color:#6B7585; border:1px dashed #374151; }
.arb-sell { background:linear-gradient(135deg,#350808,#420B0B); border:1px solid #FF3131; border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0; font-family:'Space Mono',monospace; }
.arb-buy { background:linear-gradient(135deg,#083508,#0B4A0B); border:1px solid #22C55E; border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0; font-family:'Space Mono',monospace; }
.arb-neutral { background:linear-gradient(135deg,#1A1F26,#1E242D); border:1px solid #32363F; border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0; font-family:'Space Mono',monospace; }
.pedagogy-box { background: linear-gradient(145deg, #0D1928, #111D30); border: 1px solid #1E3A5F; border-left: 4px solid #3B82F6; border-radius: 10px; padding: 1rem 1.2rem; margin: .6rem 0; font-size: .88rem; color: #93C5FD; line-height: 1.6; }
.live-badge { display:inline-block; background:#22C55E; color:#0B0E15; border-radius:4px; font-size:.62rem; font-weight:800; padding:.1rem .4rem; vertical-align:middle; margin-left:.4rem; }
.mwr-badge { display: inline-block; background: linear-gradient(135deg, #0D2035, #112845); border: 1px solid #3B82F6; border-radius: 6px; padding: .15rem .5rem; font-size: .62rem; font-weight: 800; color: #93C5FD; }
.alert-box { background: linear-gradient(135deg, #3B0A0A, #5C1111); border: 1px solid #FF3131; border-radius: 10px; padding: 1rem; margin: .5rem 0; color: #FCA5A5; }
.signal-buy { background: linear-gradient(135deg, #0A2E0A, #0F4A0F); border: 1px solid #22C55E; border-radius: 10px; padding: 1rem; margin: .5rem 0; color: #86EFAC; }
.signal-sell { background: linear-gradient(135deg, #3B0A0A, #5C1111); border: 1px solid #FF3131; border-radius: 10px; padding: 1rem; margin: .5rem 0; color: #FCA5A5; }
.signal-neutral { background: linear-gradient(135deg, #1A1F26, #222A33); border: 1px solid #4B5563; border-radius: 10px; padding: 1rem; margin: .5rem 0; color: #CBD5E1; }
@media (max-width: 768px) { .kpi-value { font-size: 1.5rem; } .card { padding: 1rem; } .stButton button { min-height: 48px !important; } }
@media print { section[data-testid="stSidebar"] { display: none !important; } .stTabs [data-baseweb="tab-list"] { display: none !important; } .main .block-container { max-width: 100% !important; } .stButton { display: none !important; } }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MODULE 2 : CONSTANTES & CONFIGURATION
# -----------------------------------------------------------------------------
_ANCHOR_DATE = "2026-09-08"
_ANCHOR_PERF = 17.15
HISTORICAL_DAYS = 3650
BENCHMARK_WORLD_TICKER = "MWRD.PA"

PRIMARY_BENCHMARK = "WORLD"
BENCHMARK_LABEL = "MSCI World"
SECONDARY_RELATIVE_COMPARISONS = {
    "CHIP.PA": ["KRW.PA"],
    "KRW.PA": ["CHIP.PA"],
}

LINXEA_CUTOFF_HOUR = 16
LINXEA_CUTOFF_MINUTE = 30
CRASH_THRESHOLDS = {"vol_ratio": 1.3, "dd_5d": -0.05}
CRASH_LEVELS = [(0, 1, "LOW"), (2, 3, "MODERATE"), (4, 5, "HIGH"), (6, 7, "CRITICAL")]
UNDERPERF_THRESHOLDS = {"alpha20": -0.03, "alpha60": -0.02}
DECISION_EXIT_SCORE = 5
DECISION_REENTER_SCORE = 2

WORLD_CORE_TICKERS = ["DCAM.PA", "MWRD.PA"]
WORLD_VALUE_TICKERS = ["WMMS.DE"]
SATELLITE_TICKERS = ["KRW.PA", "CHIP.PA"]

WORLD_CORE_MIN = 0.30
WORLD_CORE_NEUTRAL_MIN = 0.33
WORLD_CORE_NEUTRAL_MAX = 0.40
VALUE_MIN = 0.25
VALUE_NEUTRAL_MIN = 0.30
VALUE_NEUTRAL_MAX = 0.40
VALUE_MAX = 0.45
SATELLITE_MAX = 0.35
MIN_CONFIRMATIONS = 3
REGIME_CONFIRMATION_DAYS = 15
RELATIVE_STRONG = 0.03
RELATIVE_WEAK = -0.03
SEMICONDUCTOR_CATCHUP_GAP = -0.05
HIGH_RISK_CONTRIBUTION = 40.0
FINAL_TARGET_WORLD = 1.00

STRATEGIC_TARGETS = {
    "world_core": {"min": 0.30, "neutral_min": 0.33, "neutral_max": 0.40, "max": 0.50},
    "world_value": {"min": 0.25, "neutral_min": 0.30, "neutral_max": 0.40, "max": 0.45},
    "satellites": {"min": 0.00, "neutral_min": 0.15, "neutral_max": 0.30, "max": 0.35},
}
FISCALALLY_LOCKED_GROUPS = {"world_core": ["DCAM.PA", "MWRD.PA"]}
DECISION_PRIORITY = {"EXIT_TO_WORLD": 0, "REDUCE_SATELLITES": 1, "REDUCE_VALUE": 2, "REDUCE_ACTIVE": 3, "MAINTAIN": 4, "INCREASE_ACTIVE": 5, "NO_DECISION": 6}

SOX_COMPONENTS_PROXY = ["NVDA", "AVGO", "AMD", "TSM", "QCOM", "TXN", "INTC", "MU", "ADI", "LRCX", "KLAC", "AMAT", "MRVL", "NXPI", "MCHP", "ON", "SWKS", "QRVO", "ASML", "STM"]

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
    "EBUY.DE": {"isin": "LU2023678878", "name": "Amundi MSCI Digital Economy UCITS ETF Acc", "category": "Digital Economy"},
    "LYP6.DE": {"isin": "LU0908500753", "name": "Amundi Core Stoxx Europe 600 UCITS ETF Acc", "category": "Europe"},
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

EXISTING_ETFS = {
    "DCAM.PA": {"isin": "", "nom": "MSCI World PEA", "name": "Amundi MSCI World UCITS PEA", "yf": "DCAM.PA", "yf_fallbacks": ["DCAM.PA", "CW8.PA"], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "PEA", "initial_target": 0.183},
    "MWRD.PA": {"isin": "", "nom": "MSCI World AV", "name": "Amundi MSCI World UCITS DR USD", "yf": "MWRD.PA", "yf_fallbacks": ["MWRD.PA", "IWDA.AS", "EUNL.DE", "CW8.PA"], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.154},
    "KRW.PA": {"isin": "LU1900066975", "nom": "MSCI Korea", "name": "Amundi MSCI Korea UCITS", "yf": "KRW.PA", "yf_fallbacks": ["KRW.PA", "EWY"], "category": "Satellite", "theme": "Korea", "region": "Asia", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.155},
    "CHIP.PA": {"isin": "LU1900066033", "nom": "MSCI Semiconductors", "name": "Amundi MSCI Semiconductors UCITS", "yf": "CHIP.PA", "yf_fallbacks": ["CHIP.PA", "SOXX"], "category": "Satellite", "theme": "Tech", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.138},
    "WMMS.DE": {"isin": "IE000AZV0AS3", "nom": "Amundi MSCI World IMI Value Advanced", "name": "Amundi MSCI World IMI Value Advanced UCITS ETF Acc", "yf": "WMMS.DE", "yf_fallbacks": ["WMMS.DE", "WMMS.XETRA"], "category": "Core", "theme": "Value", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.37},
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
    "IUSN.DE": {"isin": "IE00B3F81R35", "nom": "World Small Cap", "name": "iShares MSCI World Small Cap UCITS", "yf": "IUSN.DE", "yf_fallbacks": ["IUSN.DE", "WSML.DE"], "category": "Core", "theme": "Small Cap", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "WLDHC.PA": {"isin": "FR0014003N93", "nom": "World Monthly Hedged", "name": "Lyxor MSCI World UCITS Monthly Hedged", "yf": "WLDHC.PA", "yf_fallbacks": ["WLDHC.PA", "WLDH.DE"], "category": "Core", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
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
    "AEEM.PA": {"isin": "LU1681045370", "nom": "MSCI EM", "name": "Amundi ETF MSCI Emerging Markets", "yf": "AEEM.PA", "yf_fallbacks": ["AEEM.PA", "EEM"], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXLEM.PA": {"isin": "LU1681045370", "nom": "MSCI EM Swap", "name": "Amundi MSCI Em Mkts Swap II UCIT", "yf": "LYXLEM.PA", "yf_fallbacks": ["LYXLEM.PA", "EEM"], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "AUEM.PA": {"isin": "LU1681045370", "nom": "MSCI EM USD", "name": "Amundi ETF MSCI Emerging Markets USD", "yf": "AUEM.PA", "yf_fallbacks": ["AUEM.PA", "EEM"], "category": "Emerging", "theme": "Blended", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXTNOW.PA": {"isin": "LU0533033667", "nom": "World Info Tech", "name": "Amundi MSCI World Information Technology", "yf": "LYPG.DE", "yf_fallbacks": ["LYPG.DE", "LYXTNOW.PA"], "category": "Sector", "theme": "Tech", "region": "Global", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "IJPE.PA": {"isin": "IE00B4K48X80", "nom": "Japan Small Cap", "name": "iShares MSCI Japan Small Cap Acc", "yf": "IJPE.PA", "yf_fallbacks": ["IJPE.PA", "JSC.DE"], "category": "Core", "theme": "Small Cap", "region": "Japan", "risk_type": "HighVol", "enveloppe": "AV", "initial_target": 0.0},
    "CV9.PA": {"isin": "", "nom": "Europe Value", "name": "Amundi MSCI Europe Value Factor", "yf": "CV9.PA", "yf_fallbacks": ["CV9.PA", "VEUR.DE"], "category": "Factor", "theme": "Value", "region": "Europe", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
    "LYXFINW.PA": {"isin": "LU0533032859", "nom": "World Financials", "name": "Amundi MSCI World Financials UCITS", "yf": "LYPD.DE", "yf_fallbacks": ["LYPD.DE", "LYXFINW.PA"], "category": "Sector", "theme": "Finance", "region": "Global", "risk_type": "Standard", "enveloppe": "AV", "initial_target": 0.0},
}

def infer_region(category: str) -> str:
    c = category.lower()
    if any(x in c for x in ["world", "global", "international", "developed"]): return "Global"
    if any(x in c for x in ["usa", "nasdaq", "sp500", "s&p 500", "america"]): return "USA"
    if "europe" in c or "euro" in c or "stoxx" in c or "emu" in c: return "Europe"
    if "france" in c or "cac" in c: return "France"
    if "germany" in c or "dax" in c: return "Germany"
    if "uk" in c or "ftse 100" in c: return "UK"
    if "japan" in c: return "Japan"
    if "china" in c: return "China"
    if "korea" in c: return "South Korea"
    if "india" in c: return "India"
    if "brazil" in c: return "Brazil"
    if "latin america" in c: return "LatAm"
    if "pacific" in c: return "Pacific"
    if "emerging" in c: return "Emerging"
    if "switzerland" in c: return "Switzerland"
    if "nordic" in c: return "Nordic"
    if "australia" in c: return "Australia"
    return "Global"

def infer_theme(category: str) -> str:
    c = category.lower()
    if "semiconductor" in c: return "Semiconductors"
    if "robotics" in c or "ai" in c or "artificial intelligence" in c: return "Robotics & AI"
    if "cybersecurity" in c or "security" in c: return "Cybersecurity"
    if "automation" in c: return "Automation"
    if "digital economy" in c: return "Digital Economy"
    if "digitalisation" in c: return "Digitalisation"
    if "electric vehicle" in c or "ev" in c: return "Electric Vehicles"
    if "hydrogen" in c: return "Hydrogen"
    if "water" in c: return "Water"
    if "smart city" in c or "smart cities" in c: return "Smart Cities"
    if "luxury" in c: return "Luxury"
    if "circular economy" in c: return "Circular Economy"
    if "blue economy" in c: return "Blue Economy"
    if "clean energy" in c or "new energy" in c: return "Clean Energy"
    if "gold" in c: return "Gold"
    if "real estate" in c or "epra" in c: return "Real Estate"
    if "infrastructure" in c: return "Infrastructure"
    if "banks" in c: return "Banks"
    if "healthcare" in c: return "Healthcare"
    if "financial" in c: return "Finance"
    if "technology" in c: return "Technology"
    if "energy" in c: return "Energy"
    if "industrial" in c: return "Industrials"
    if "consumer" in c or "millennials" in c: return "Consumer"
    if "quality income" in c: return "Quality Income"
    if "dividend" in c: return "Dividend"
    if "value" in c: return "Value"
    if "growth" in c: return "Growth"
    if "small cap" in c: return "Small Cap"
    if "mid cap" in c: return "Mid Cap"
    if "large cap" in c: return "Large Cap"
    if "esg" in c or "sri" in c or "climate" in c: return "Sustainability"
    if "hedged" in c: return "Hedged"
    if "leveraged" in c: return "Leveraged"
    if "islamic" in c: return "Islamic"
    return "Blended"

def normalize_etf_library(library: Dict) -> Dict:
    by_isin = {}
    for ticker, meta in library.items():
        isin = meta.get("isin")
        if not isin: by_isin[ticker] = {"ticker": ticker, "meta": meta}; continue
        if isin not in by_isin: by_isin[isin] = {"ticker": ticker, "meta": meta}
        else:
            current = by_isin[isin]
            if ticker.endswith(".DE") and not current["ticker"].endswith(".DE"):
                by_isin[isin] = {"ticker": ticker, "meta": meta}
    result = {}
    for key, entry in by_isin.items():
        ticker = entry["ticker"]; meta = entry["meta"].copy()
        if "isin" not in meta and (key.startswith("IE") or key.startswith("FR") or key.startswith("LU")):
            meta["isin"] = key
        result[ticker] = meta
    return result

temp_library = dict(EXISTING_ETFS)
existing_tickers = set(temp_library.keys())
existing_isins = {meta.get("isin") for meta in temp_library.values() if meta.get("isin")}
for ticker, info in ETF_UNIVERSE.items():
    if ticker in existing_tickers: continue
    isin = info.get("isin")
    if isin and isin in existing_isins: continue
    category = info.get("category", "Unknown")
    region = infer_region(category); theme = infer_theme(category)
    risk_type = "HighVol" if any(x in category.lower() for x in ["leveraged", "high vol", "volatile"]) else \
                "Defensive" if any(x in category.lower() for x in ["defensive", "low carbon", "esg", "sri"]) else "Standard"
    enveloppe = "PEA" if "pea" in info.get("name", "").lower() else "AV"
    temp_library[ticker] = {"nom": info["name"], "name": info["name"], "yf": ticker, "yf_fallbacks": [],
                             "category": category, "theme": theme, "region": region, "risk_type": risk_type,
                             "enveloppe": enveloppe, "initial_target": 0.0, "isin": isin}
ETF_LIBRARY = normalize_etf_library(temp_library)

def get_world_series(dm: "DataManager", exclude_ticker: str = None) -> pd.Series:
    candidates = [BENCHMARK_WORLD_TICKER, "CW8.PA", "IWDA.AS", "EUNL.DE", "DCAM.PA"]
    seen = set(); unique_candidates = []
    for t in candidates:
        if t not in seen and t != exclude_ticker and t != "WMMS.DE":
            seen.add(t); unique_candidates.append(t)
    if exclude_ticker == BENCHMARK_WORLD_TICKER and "CW8.PA" not in unique_candidates:
        unique_candidates.insert(0, "CW8.PA")
    for ticker in unique_candidates:
        df = dm.data.get(ticker, pd.DataFrame())
        if df is not None and not df.empty and "Close" in df.columns:
            s = df["Close"].dropna()
            if len(s) >= 20: return s
    for ticker, df in dm.data.items():
        if ticker == exclude_ticker or ticker == "WMMS.DE": continue
        if ticker in ["MWRD.PA", "CW8.PA", "IWDA.AS", "EUNL.DE", "DCAM.PA"]:
            if "Close" in df.columns:
                s = df["Close"].dropna()
                if len(s) >= 20: return s
    return pd.Series(dtype=float)

def compute_relative_gap(dm: "DataManager", ticker: str, days: int = 15) -> Optional[float]:
    asset = dm.data.get(ticker, pd.DataFrame())
    if asset.empty or "Close" not in asset.columns: return None
    world = get_world_series(dm, exclude_ticker=ticker)
    if world.empty: return None
    asset_close = asset["Close"].dropna()
    common = asset_close.index.intersection(world.index)
    if len(common) < days + 1: return None
    common = common.sort_values()
    asset_ret = (asset_close.loc[common[-1]] / asset_close.loc[common[-days-1]] - 1) * 100
    world_ret = (world.loc[common[-1]] / world.loc[common[-days-1]] - 1) * 100
    return asset_ret - world_ret

WORLD_TICKERS = ["MWRD.PA", "CW8.PA", "IWDA.AS", "EUNL.DE", "DCAM.PA"]
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
_CONFIG_PATH = os.path.join(tempfile.gettempdir(), "cockpit_config_perso.json")
_DB_PATH = os.path.join(tempfile.gettempdir(), "cockpit_local.db")
_PORTFOLIO_JSON = os.path.join(tempfile.gettempdir(), "portfolio_positions.json")
_TRANSACTIONS_JSON = os.path.join(tempfile.gettempdir(), "transactions.json")

# -----------------------------------------------------------------------------
# MODULE 3 : DATA MANAGER
# -----------------------------------------------------------------------------
requests_cache.install_cache('yfinance_cache', expire_after=86400)

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        try:
            tickers = df.columns.get_level_values(1).unique().tolist()
            if tickers: df = df.xs(tickers[0], axis=1, level=1)
        except Exception:
            df = df.copy(); df.columns = df.columns.get_level_values(0)
    df = df.dropna(axis=1, how="all").copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={"Adj Close": "Close", "Adj_Close": "Close", "adj close": "Close"})
    df = df.rename(columns={c: c.title() for c in df.columns})
    if "Close" not in df.columns: return pd.DataFrame()
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.ffill().dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index)
    return df.sort_index()

def _fetch_live_price(tk: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        fi = yf.Ticker(tk).fast_info
        prix = getattr(fi, "last_price", None); prev = getattr(fi, "previous_close", None)
        if prix and float(prix) > 0: return float(prix), float(prev) if prev else None
    except Exception: pass
    try:
        info = yf.Ticker(tk).info
        prix = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("navPrice")
        prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
        if prix and float(prix) > 0: return float(prix), float(prev) if prev else None
    except Exception: pass
    return None, None

def chunks(lst, size):
    for i in range(0, len(lst), size): yield lst[i:i+size]

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
    batch_size = 20
    for batch in chunks(all_tickers, batch_size):
        try:
            raw = yf.download(batch, start=start, group_by="ticker", auto_adjust=True, progress=False, threads=True)
            if not raw.empty and isinstance(raw.columns, pd.MultiIndex):
                for tk in batch:
                    try:
                        df = _normalize_df(raw[tk].copy())
                        if not df.empty: result[tk] = df
                    except Exception: pass
            elif not raw.empty and len(batch) == 1:
                df = _normalize_df(raw.copy())
                if not df.empty: result[batch[0]] = df
        except Exception: pass
        time.sleep(0.2)
    missing = [tk for tk in all_tickers if tk not in result]
    for tk in missing:
        meta = next((m for m in ETF_LIBRARY.values() if m.get("yf") == tk), None)
        if meta:
            candidates = [meta.get("yf")] + meta.get("yf_fallbacks", [])
            candidates = list(dict.fromkeys([c for c in candidates if c]))
            for c in candidates:
                if c in result: break
                try:
                    df = _normalize_df(yf.download(c, start=start, auto_adjust=True, progress=False))
                    if not df.empty:
                        result[c] = df
                        if c != tk: result[tk] = df
                        break
                except Exception: continue
        else:
            try:
                df = _normalize_df(yf.download(tk, start=start, auto_adjust=True, progress=False))
                if not df.empty: result[tk] = df
            except Exception: pass
    final_failures = [tk for tk in all_tickers if tk not in result]
    st.session_state["_data_failures"] = final_failures
    return result

def get_working_ticker(meta: Dict) -> Optional[str]:
    candidates = []
    if meta.get("yf"): candidates.append(meta["yf"])
    for fb in meta.get("yf_fallbacks", []):
        if fb not in candidates: candidates.append(fb)
    for ticker in candidates:
        try:
            data = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
            if data is not None and not data.empty and "Close" in data.columns: return ticker
        except Exception: continue
    return None

def _collect_all_yf_tickers() -> List[str]:
    tickers = []
    for meta in ETF_LIBRARY.values():
        yf_ticker = meta.get("yf")
        if yf_ticker: tickers.append(yf_ticker)
        for fb in meta.get("yf_fallbacks", []):
            if fb and fb not in tickers: tickers.append(fb)
    tickers.extend(MACRO_TICKERS.keys()); tickers.extend(REGIME_TICKERS); tickers.extend(PROXIES_KR); tickers.extend(PROXIES_CHIP)
    tickers.extend(["NVDA", "AAPL", "GOOGL", "GOOG", "MSFT", "AMZN"])
    for tlist in SENTINELLES.values(): tickers.extend(tlist)
    tickers.extend(["^VIX3M", "KRW=X"]); tickers.extend(SOX_COMPONENTS_PROXY)
    return list(dict.fromkeys(tickers))

class DataManager:
    def __init__(self):
        self.live = _cached_live_prices()
        self.data = _cached_historical_data()
        self._log_returns_cache = None
        self._analyze_cache = {}

    def get_price_info(self, tickers: List[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        for tk in tickers:
            info = self.live.get(tk, {})
            prix = info.get("prix"); prev = info.get("prev")
            if prix and float(prix) > 0: return float(prix), float(prev) if prev else None, tk
        return None, None, None

    def compute_log_returns(self) -> Dict[str, pd.Series]:
        if self._log_returns_cache is not None: return self._log_returns_cache
        result = {}
        for tk, df in self.data.items():
            if "Close" not in df.columns or len(df) < 2: continue
            close = df["Close"].dropna()
            if len(close) < 2: continue
            lr = np.log(close / close.shift(1)).dropna()
            if not lr.empty: result[tk] = lr
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
        if ticker in self._analyze_cache: return self._analyze_cache[ticker]
        result = self._analyze_ticker_impl(ticker)
        self._analyze_cache[ticker] = result
        return result

    def _analyze_ticker_impl(self, ticker: str) -> Optional[Dict]:
        lp = self.live.get(ticker, {}); prix = lp.get("prix")
        df = self.data.get(ticker, pd.DataFrame())
        if df.empty or "Close" not in df.columns:
            meta = {"yf": ticker, "yf_fallbacks": []}
            working = get_working_ticker(meta)
            if working:
                df = self.data.get(working, pd.DataFrame())
                lp = self.live.get(working, {}); prix = lp.get("prix")
        if df.empty or "Close" not in df.columns:
            return {"ticker": ticker, "prix": prix, "sma20": None, "sma50": None, "sma200": None, "rsi": None, "adx": None, "ath30": None} if prix else None
        close = df["Close"].dropna()
        prix_live = float(prix) if (prix and float(prix) > 0) else float(close.iloc[-1])
        return {"ticker": ticker, "prix": prix_live, "sma20": self.sma(close, 20), "sma50": self.sma(close, 50),
                "sma200": self.sma(close, 200), "rsi": self.rsi(close), "adx": None,
                "ath30": float(close.rolling(30, min_periods=1).max().iloc[-1])}

    def relative_strength_slope(self, ticker: str, days: int = 14) -> Optional[float]:
        df = self.data.get(ticker)
        if df is None or df.empty or "Close" not in df.columns: return None
        world = get_world_series(self, exclude_ticker=ticker)
        if world.empty: return None
        close = df["Close"].dropna()
        common = close.index.intersection(world.index)
        if len(common) < days + 5: return None
        rs = (close.loc[common] / world.loc[common]).iloc[-days:]
        if len(rs) < days: return None
        x = np.arange(len(rs))
        try: slope, _ = np.polyfit(x, rs.values, 1); return float(slope)
        except Exception: return None

# -----------------------------------------------------------------------------
# MODULE 4 : ANALYTICS ENGINE
# -----------------------------------------------------------------------------
class AnalyticsEngine:
    WINDOW_1M = 21; WINDOW_3M = 63; WINDOW_6M = 126; WINDOW_1Y = 252; WINDOW_3Y = 756
    RISK_FREE_RATE = 0.025
    def __init__(self, dm: DataManager):
        self.dm = dm
        self.benchmark_ticker = BENCHMARK_WORLD_TICKER
        self.benchmark_df = dm.data.get(self.benchmark_ticker)
        if self.benchmark_df is None or self.benchmark_df.empty:
            for wt in WORLD_TICKERS:
                self.benchmark_df = dm.data.get(wt)
                if self.benchmark_df is not None and not self.benchmark_df.empty:
                    self.benchmark_ticker = wt; break
    def _get_price_column(self, df): return "Adj Close" if "Adj Close" in df.columns else "Close"
    def _get_asset_series(self, ticker):
        df = self.dm.data.get(ticker)
        if df is None or df.empty: return pd.Series(dtype=float)
        pc = self._get_price_column(df)
        return df[pc].dropna().sort_index()
    def _align_with_benchmark(self, ticker):
        asset = self._get_asset_series(ticker)
        if asset.empty: return pd.Series(dtype=float), pd.Series(dtype=float)
        bench = self._get_asset_series(self.benchmark_ticker) if self.benchmark_df is not None else pd.Series(dtype=float)
        if bench.empty: return asset, pd.Series(dtype=float)
        common_idx = asset.index.intersection(bench.index)
        if len(common_idx) == 0: return asset, pd.Series(dtype=float)
        return asset.loc[common_idx], bench.loc[common_idx]
    def _compute_momentum(self, close, window):
        if len(close) < window + 1: return np.nan
        return (close.iloc[-1] / close.iloc[-window] - 1.0) * 100.0
    def compute_momentum_1m(self, t): return self._compute_momentum(self._get_asset_series(t), self.WINDOW_1M)
    def compute_momentum_3m(self, t): return self._compute_momentum(self._get_asset_series(t), self.WINDOW_3M)
    def compute_momentum_6m(self, t): return self._compute_momentum(self._get_asset_series(t), self.WINDOW_6M)
    def compute_relative_strength(self, ticker):
        asset, bench = self._align_with_benchmark(ticker)
        if bench.empty or len(asset) < self.WINDOW_6M + 1 or len(bench) < self.WINDOW_6M + 1: return np.nan
        etf_ratio = asset.iloc[-1] / asset.iloc[-self.WINDOW_6M]
        bench_ratio = bench.iloc[-1] / bench.iloc[-self.WINDOW_6M]
        if bench_ratio <= 0 or etf_ratio <= 0: return np.nan
        return np.log(etf_ratio / bench_ratio) * 100.0
    def compute_volatility(self, ticker, window=WINDOW_1Y):
        close = self._get_asset_series(ticker)
        if len(close) < window + 1: return np.nan
        r = close.pct_change().dropna().iloc[-window:]
        if len(r) < 10: return np.nan
        return r.std() * np.sqrt(252) * 100.0
    def compute_sharpe(self, ticker):
        close = self._get_asset_series(ticker)
        if len(close) < 10: return np.nan
        n = min(len(close) - 1, self.WINDOW_1Y)
        if n <= 0: return np.nan
        ret = close.iloc[-1] / close.iloc[-n] - 1.0
        ann = (1.0 + ret) ** (252.0 / n) - 1.0
        r = close.pct_change().dropna().iloc[-n:]
        if len(r) < 10: return np.nan
        av = r.std() * np.sqrt(252)
        if av == 0 or np.isnan(av): return np.nan
        return (ann - self.RISK_FREE_RATE) / av
    def compute_sortino(self, ticker):
        close = self._get_asset_series(ticker)
        if len(close) < 10: return np.nan
        n = min(len(close) - 1, self.WINDOW_1Y)
        if n <= 0: return np.nan
        ret = close.iloc[-1] / close.iloc[-n] - 1.0
        ann = (1.0 + ret) ** (252.0 / n) - 1.0
        r = close.pct_change().dropna().iloc[-n:]
        if len(r) < 10: return np.nan
        drf = (1.0 + self.RISK_FREE_RATE) ** (1.0 / 252) - 1.0
        dn = np.minimum(r - drf, 0)
        dd = np.sqrt(np.mean(dn**2)) * np.sqrt(252)
        if dd == 0 or np.isnan(dd): return np.nan
        return (ann - self.RISK_FREE_RATE) / dd
    def compute_information_ratio(self, ticker):
        asset, bench = self._align_with_benchmark(ticker)
        if bench.empty or len(asset) < 10 or len(bench) < 10: return np.nan
        n = min(min(len(asset)-1, len(bench)-1), self.WINDOW_1Y)
        if n <= 0: return np.nan
        ret_asset = asset.iloc[-1] / asset.iloc[-n] - 1.0
        ann_a = (1.0 + ret_asset) ** (252.0 / n) - 1.0
        ret_bench = bench.iloc[-1] / bench.iloc[-n] - 1.0
        ann_b = (1.0 + ret_bench) ** (252.0 / n) - 1.0
        ar = asset.pct_change().dropna().iloc[-n:]; br = bench.pct_change().dropna().iloc[-n:]
        common = ar.index.intersection(br.index)
        if len(common) < 10: return np.nan
        diff = ar.loc[common] - br.loc[common]
        te = diff.std() * np.sqrt(252)
        if te == 0 or np.isnan(te): return np.nan
        return (ann_a - ann_b) / te
    def _compute_max_drawdown(self, series, window=None):
        if len(series) < 2: return np.nan
        if window is not None: series = series.iloc[-window:]
        return ((series / series.cummax() - 1.0)).min() * 100.0
    def compute_max_drawdown_1y(self, t): return self._compute_max_drawdown(self._get_asset_series(t), self.WINDOW_1Y)
    def compute_max_drawdown_3y(self, t): return self._compute_max_drawdown(self._get_asset_series(t), self.WINDOW_3Y)
    def compute_max_drawdown_since_inception(self, t): return self._compute_max_drawdown(self._get_asset_series(t), None)
    def compute_rsi(self, ticker, period=14):
        close = self._get_asset_series(ticker)
        if len(close) < period + 1: return np.nan
        d = close.diff()
        gain = d.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-d.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty and not np.isnan(rsi.iloc[-1]) else np.nan
    def compute_distance_sma(self, ticker, window):
        close = self._get_asset_series(ticker)
        if len(close) < window: return np.nan
        sma = close.rolling(window).mean().iloc[-1]
        if np.isnan(sma) or sma == 0: return np.nan
        return ((close.iloc[-1] / sma) - 1.0) * 100.0
    def compute_correlation(self, ticker, window=126):
        asset, bench = self._align_with_benchmark(ticker)
        if asset.empty or bench.empty or len(asset) < window + 1 or len(bench) < window + 1: return np.nan
        ar = np.log(asset / asset.shift(1)); br = np.log(bench / bench.shift(1))
        df = pd.concat([ar, br], axis=1, join="inner").dropna()
        if len(df) < window: return np.nan
        df = df.iloc[-window:]
        c = df.iloc[:, 0].corr(df.iloc[:, 1])
        return float(c) if pd.notna(c) else np.nan
    def compute_all_metrics(self, ticker):
        close = self._get_asset_series(ticker)
        if close.empty: return {}
        return {"price": close.iloc[-1], "mom_1m": self.compute_momentum_1m(ticker),
                "mom_3m": self.compute_momentum_3m(ticker), "mom_6m": self.compute_momentum_6m(ticker),
                "rel_strength": self.compute_relative_strength(ticker),
                "volatility": self.compute_volatility(ticker), "sharpe": self.compute_sharpe(ticker),
                "sortino": self.compute_sortino(ticker), "information_ratio": self.compute_information_ratio(ticker),
                "max_drawdown_1y": self.compute_max_drawdown_1y(ticker),
                "max_drawdown_3y": self.compute_max_drawdown_3y(ticker),
                "max_drawdown_since": self.compute_max_drawdown_since_inception(ticker),
                "max_drawdown": self.compute_max_drawdown_1y(ticker),
                "rsi": self.compute_rsi(ticker), "dist_sma20": self.compute_distance_sma(ticker, 20),
                "dist_sma50": self.compute_distance_sma(ticker, 50),
                "corr_1m": self.compute_correlation(ticker, self.WINDOW_1M),
                "corr_3m": self.compute_correlation(ticker, self.WINDOW_3M),
                "corr_6m": self.compute_correlation(ticker, self.WINDOW_6M),
                "corr_1y": self.compute_correlation(ticker, self.WINDOW_1Y)}

# -----------------------------------------------------------------------------
# MODULE 5 : SIGNAL ENGINE
# -----------------------------------------------------------------------------
class SignalEngine:
    def __init__(self, dm, analytics): self.dm = dm; self.analytics = analytics
    def compute_score(self, ticker):
        m = self.analytics.compute_all_metrics(ticker)
        if not m: return {"score": 0, "metrics": {}, "status": "NO_DATA"}
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
        sh = m.get("sharpe", 0)
        if sh > 1.5: score += 15
        elif sh > 0.8: score += 10
        elif sh > 0.3: score += 5
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
    def get_arbitrage_opportunities(self, holdings):
        all_scores = {}
        for ticker in self.dm.data.keys():
            if ticker in ETF_LIBRARY: all_scores[ticker] = self.compute_score(ticker)["score"]
        best_others = sorted([(t, s) for t, s in all_scores.items() if t not in holdings], key=lambda x: -x[1])[:5]
        opps = []
        for held in holdings:
            hs = all_scores.get(held, 0)
            for cand, cs in best_others:
                if cs > hs + 15:
                    opps.append({"sell": held, "buy": cand, "gain_potential": cs - hs,
                                 "buy_name": ETF_LIBRARY.get(cand, {}).get("nom", cand),
                                 "sell_name": ETF_LIBRARY.get(held, {}).get("nom", held)})
                    break
        return opps

# -----------------------------------------------------------------------------
# MODULE 6 : PERSISTENCE MANAGER
# -----------------------------------------------------------------------------
_CSV_COLS = ["date", "capital_cloture", "valeur_titres", "perf_jour", "perf_cumul", "regime", "score_regime", "poids_sat"]

class PersistenceManager:
    def __init__(self, static_capital):
        self.static_capital = static_capital
        self._github_ok = False; self._gist = None; self._github_warning = ""
        self._history_cache: Optional[pd.DataFrame] = None
        try:
            self._conn = sqlite3.connect(_DB_PATH, check_same_thread=False); self._init_db()
        except Exception:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False); self._init_db()
        if PYGITHUB_OK:
            try:
                token = st.secrets.get("GITHUB_TOKEN", ""); gist_id = st.secrets.get("GIST_ID", "")
                if token and gist_id:
                    gh = Github(token); self._gist = gh.get_gist(gist_id)
                    self._github_ok = True; self._sync_from_github()
            except Exception as e:
                self._github_warning = f"GitHub Gist indisponible : {str(e)[:80]}"
        else:
            self._github_warning = "PyGithub non installé --- mode SQLite uniquement."
    def _init_db(self):
        self._conn.execute("""CREATE TABLE IF NOT EXISTS snapshots (
            date TEXT PRIMARY KEY, capital_cloture REAL NOT NULL, valeur_titres REAL,
            perf_jour REAL, perf_cumul REAL, regime TEXT, score_regime INTEGER, poids_sat REAL,
            created_at TEXT DEFAULT (datetime('now')))""")
        self._conn.commit()
    def _sync_from_github(self):
        if not self._gist: return
        try:
            files = self._gist.files
            if "history.csv" not in files: return
            content = files["history.csv"].content or ""
            if not content.strip(): return
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                self._conn.execute("""INSERT OR REPLACE INTO snapshots
                (date,capital_cloture,valeur_titres,perf_jour,perf_cumul,regime,score_regime,poids_sat) VALUES (?,?,?,?,?,?,?,?)""",
                (row.get("date",""), float(row.get("capital_cloture") or 0), float(row.get("valeur_titres") or 0),
                 float(row.get("perf_jour") or 0), float(row.get("perf_cumul") or 0), row.get("regime",""),
                 int(float(row.get("score_regime") or 0)), float(row.get("poids_sat") or 0)))
            self._conn.commit()
        except Exception: pass
    def _push_to_github(self, df):
        if not self._gist: return
        try:
            buf = io.StringIO(); df.to_csv(buf, index=False, columns=_CSV_COLS)
            self._gist.edit(files={"history.csv": InputFileContent(buf.getvalue())})
        except Exception: pass
    def save_snapshot(self, capital_cloture, valeur_titres, perf_jour, perf_cumul, regime, score_regime, poids_sat):
        today = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
        try:
            self._conn.execute("""INSERT OR REPLACE INTO snapshots
            (date,capital_cloture,valeur_titres,perf_jour,perf_cumul,regime,score_regime,poids_sat) VALUES (?,?,?,?,?,?,?,?)""",
            (today, round(capital_cloture, 2), round(valeur_titres, 2), round(perf_jour, 4), round(perf_cumul, 4), regime, score_regime, round(poids_sat, 4)))
            self._conn.commit(); self._history_cache = None
            if self._github_ok: self._push_to_github(self.load_history())
            return True, ""
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
    def load_history(self):
        if self._history_cache is not None: return self._history_cache
        try:
            df = pd.read_sql("SELECT * FROM snapshots ORDER BY date ASC", self._conn)
            for col in _CSV_COLS:
                if col not in df.columns: df[col] = None
            self._history_cache = df[_CSV_COLS].copy()
            return self._history_cache
        except Exception:
            return pd.DataFrame(columns=_CSV_COLS)
    def get_last_snapshot(self):
        hist = self.load_history()
        if hist.empty: return None
        row = hist.iloc[-1]
        return {c: row[c] for c in _CSV_COLS}
    def get_initial_capital(self):
        hist = self.load_history()
        if not hist.empty and hist["capital_cloture"].notna().any():
            return float(hist["capital_cloture"].dropna().iloc[0])
        return self.static_capital
    def compute_daily_performance(self, current_value):
        last = self.get_last_snapshot(); initial = self.get_initial_capital()
        base = float(last["capital_cloture"]) if last else self.static_capital
        if base <= 0: base = self.static_capital
        pj = (current_value / base - 1) * 100 if base > 0 else 0.0
        pc = (current_value / initial - 1) * 100 if initial > 0 else 0.0
        return pj, pc, base
    @property
    def status(self):
        if self._github_ok: return "github"
        if self._github_warning: return "warn"
        return "local"
    @property
    def warning_msg(self): return self._github_warning

# -----------------------------------------------------------------------------
# MODULE 7 : PORTFOLIO CONFIG MANAGER & TRANSACTION ENGINE
# -----------------------------------------------------------------------------
class PortfolioConfigManager:
    def __init__(self, file_path=_PORTFOLIO_JSON): self.file_path = file_path
    def load_positions(self):
        default_positions = [
            {"ticker": "WMMS.DE", "parts": 461.9561, "prm": 13.582, "account": "AV"},
            {"ticker": "DCAM.PA", "parts": 508.0000, "prm": 4.983, "account": "PEA"},
            {"ticker": "MWRD.PA", "parts": 16.6229, "prm": 149.718, "account": "AV"},
            {"ticker": "KRW.PA", "parts": 14.8501, "prm": 142.370, "account": "AV"},
            {"ticker": "CHIP.PA", "parts": 21.4922, "prm": 99.159, "account": "AV"},
        ]
        try:
            if os.path.exists(self.file_path) and os.stat(self.file_path).st_size > 0:
                with open(self.file_path, "r", encoding="utf-8") as f: data = json.load(f)
                if isinstance(data, list) and data:
                    existing = {pos["ticker"] for pos in data}
                    for dp in default_positions:
                        if dp["ticker"] not in existing: data.append(dp)
                    return data
        except Exception: pass
        return default_positions
    def save_positions(self, positions):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f: json.dump(positions, f, indent=4, ensure_ascii=False)
            return True
        except Exception: return False

class TransactionEngine:
    def __init__(self, file_path=_TRANSACTIONS_JSON): self.file_path = file_path
    def load_transactions(self):
        try:
            if not os.path.exists(self.file_path): return []
            with open(self.file_path, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: return []
    def save_transaction(self, tx):
        try:
            txs = self.load_transactions(); txs.append(tx)
            with open(self.file_path, "w", encoding="utf-8") as f: json.dump(txs, f, indent=4, ensure_ascii=False)
            return True
        except Exception: return False
    def rebuild_portfolio_at_date(self, target_date=None):
        txs = self.load_transactions(); positions = {}
        for tx in txs:
            if target_date and tx.get("date", "") > target_date: continue
            tk = tx.get("ticker", "")
            if not tk: continue
            if tk not in positions: positions[tk] = {"parts": 0.0, "total_cost": 0.0}
            if tx.get("type") == "BUY":
                positions[tk]["parts"] += float(tx.get("parts", 0))
                positions[tk]["total_cost"] += float(tx.get("parts", 0)) * float(tx.get("price", 0))
            elif tx.get("type") == "SELL":
                positions[tk]["parts"] -= float(tx.get("parts", 0))
                if positions[tk]["parts"] <= 0: positions[tk] = {"parts": 0.0, "total_cost": 0.0}
        return positions
    def get_portfolio_as_positions(self):
        rebuilt = self.rebuild_portfolio_at_date(); result = []
        for tk_id, data in rebuilt.items():
            if data["parts"] <= 0: continue
            prm = data["total_cost"] / data["parts"] if data["parts"] > 0 else 0.0
            meta = ETF_LIBRARY.get(tk_id, {})
            result.append({"ticker": tk_id, "parts": round(data["parts"], 6), "prm": round(prm, 4), "account": meta.get("enveloppe", "AV")})
        return result

# -----------------------------------------------------------------------------
# MODULE 8 : MARKET REGIME ENGINE
# -----------------------------------------------------------------------------
_REGIME_LABELS = [(4, 5, "Euphorie", "regime-euphorie", "#A855F7"), (2, 3, "Expansion", "regime-expansion", "#22C55E"),
                  (0, 1, "Neutre", "regime-neutre", "#3B82F6"), (-3,-1, "Stress", "regime-stress", "#F59E0B"),
                  (-5,-4, "Contraction", "regime-contraction", "#FF3131")]
REGIME_MULTIPLIERS = {"Euphorie": 1.00, "Expansion": 1.00, "Neutre": 0.85, "Stress": 0.70, "Contraction": 0.20}

class MarketRegimeEngine:
    def __init__(self, dm): self.dm = dm
    def _compute_score_at(self, offset=0):
        score = 0; data = self.dm.data
        def _get_close(tickers):
            for tk in tickers:
                df = data.get(tk, pd.DataFrame())
                if not df.empty and "Close" in df.columns:
                    cl = df["Close"].dropna()
                    if len(cl) > offset + 10: return cl.iloc[:len(cl) - offset] if offset > 0 else cl
            return None
        cl = _get_close(["ES=F", "SPY"])
        if cl is not None and len(cl) >= 201: score += 1 if float(cl.iloc[-1]) > float(cl.rolling(200).mean().iloc[-1]) else -1
        cl = _get_close(["QQQ", "NQ=F"])
        if cl is not None and len(cl) >= 51: score += 1 if float(cl.iloc[-1]) > float(cl.rolling(50).mean().iloc[-1]) else -1
        cl = _get_close(["^VIX"])
        if cl is not None: score += 1 if float(cl.iloc[-1]) < 20 else -1
        cl = _get_close(["^TNX"])
        if cl is not None and len(cl) >= 21: score += 1 if float(cl.iloc[-1]) < float(cl.rolling(20).mean().iloc[-1]) else -1
        cl = _get_close(["DX-Y.NYB"])
        if cl is not None and len(cl) >= 51: score += 1 if float(cl.iloc[-1]) < float(cl.rolling(50).mean().iloc[-1]) else -1
        return max(-5, min(5, score))
    def _score_to_label(self, score):
        for lo, hi, label, css, color in _REGIME_LABELS:
            if lo <= score <= hi: return label, css, color
        return "Neutre", "regime-neutre", "#3B82F6"
    def get_full_regime(self):
        scores_3d = []
        for offset in range(3):
            try: scores_3d.append(self._compute_score_at(offset))
            except Exception: scores_3d.append(0)
        cs = scores_3d[0]
        label_0, css_0, color_0 = self._score_to_label(cs)
        labels_3d = [self._score_to_label(s)[0] for s in scores_3d]
        if len(set(labels_3d)) == 1 or labels_3d[0] == labels_3d[1]:
            confirmed = True; cl, cc, ccol = label_0, css_0, color_0; csc = cs
        else:
            confirmed = False; cl, cc, ccol = "En attente", "regime-pending", "#6B7585"; csc = cs
        return {"current_score": cs, "confirmed_score": csc, "confirmed_label": cl, "confirmed_css": cc,
                "confirmed_color": ccol, "is_confirmed": confirmed, "scores_3d": scores_3d, "labels_3d": labels_3d,
                "components": self._get_component_details(), "multiplier": REGIME_MULTIPLIERS.get(cl, 0.85)}
    def _get_component_details(self):
        data = self.dm.data; detail = []
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
        else: detail.append({"name": "Trend (SMA200)", "bull": None, "val": "N/A"})
        cl = _last(["QQQ", "NQ=F"])
        if cl is not None and len(cl) >= 51:
            sma = float(cl.rolling(50).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Breadth (SMA50)", "bull": v > sma, "val": f"{v:.1f} vs {sma:.1f}"})
        else: detail.append({"name": "Breadth (SMA50)", "bull": None, "val": "N/A"})
        cl = _last(["^VIX"])
        if cl is not None:
            v = float(cl.iloc[-1])
            detail.append({"name": "Volatilité (VIX)", "bull": v < 20, "val": f"{v:.2f} (seuil 20)"})
        else: detail.append({"name": "Volatilité (VIX)", "bull": None, "val": "N/A"})
        cl = _last(["^TNX"])
        if cl is not None and len(cl) >= 21:
            sma = float(cl.rolling(20).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Taux (US10Y SMA20)", "bull": v < sma, "val": f"{v:.3f}% vs {sma:.3f}%"})
        else: detail.append({"name": "Taux (US10Y SMA20)", "bull": None, "val": "N/A"})
        cl = _last(["DX-Y.NYB"])
        if cl is not None and len(cl) >= 51:
            sma = float(cl.rolling(50).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Liquidité (DXY)", "bull": v < sma, "val": f"{v:.2f} vs {sma:.2f}"})
        else: detail.append({"name": "Liquidité (DXY)", "bull": None, "val": "N/A"})
        return detail

# -----------------------------------------------------------------------------
# MODULE 9 : QUANT RISK ENGINE
# -----------------------------------------------------------------------------
class QuantRiskEngine:
    def __init__(self, dm): self.dm = dm; self._log_returns = dm.compute_log_returns()
    def rolling_volatility(self, ticker, window=30):
        lr = self._log_returns.get(ticker)
        if lr is None or len(lr) < window: return None
        return float(lr.iloc[-window:].std() * np.sqrt(252))
    def rolling_volatility_from_df(self, df, window=30):
        if df is None or df.empty or "Close" not in df.columns: return None
        close = df["Close"].dropna()
        if len(close) < window + 1: return None
        lr = np.log(close / close.shift(1)).dropna()
        if len(lr) < window: return None
        return float(lr.iloc[-window:].std() * np.sqrt(252))
    def rolling_beta(self, ticker, benchmark="MWRD.PA", window=60):
        lr_a = self._log_returns.get(ticker); lr_b = self._log_returns.get(benchmark)
        if lr_b is None:
            for wt in WORLD_TICKERS:
                lr_b = self._log_returns.get(wt)
                if lr_b is not None: break
        if lr_a is None or lr_b is None: return None
        common = lr_a.index.intersection(lr_b.index)
        if len(common) < window: return None
        a = lr_a[common].iloc[-window:].values; b = lr_b[common].iloc[-window:].values
        cov = np.cov(a, b)[0, 1]; var = np.var(b)
        return float(cov / var) if var > 1e-12 else None
    def rolling_beta_from_df(self, df, benchmark="MWRD.PA", window=60):
        if df is None or df.empty or "Close" not in df.columns: return None
        close = df["Close"].dropna()
        if len(close) < window + 1: return None
        lr_a = np.log(close / close.shift(1)).dropna()
        lr_b = self._log_returns.get(benchmark)
        if lr_b is None:
            for wt in WORLD_TICKERS:
                lr_b = self._log_returns.get(wt)
                if lr_b is not None: break
        if lr_b is None: return None
        common = lr_a.index.intersection(lr_b.index)
        if len(common) < window: return None
        a = lr_a[common].iloc[-window:].values; b = lr_b[common].iloc[-window:].values
        cov = np.cov(a, b)[0, 1]; var = np.var(b)
        return float(cov / var) if var > 1e-12 else None
    def drawdown_metrics(self, ticker, window=252):
        df = self.dm.data.get(ticker, pd.DataFrame())
        if df.empty or "Close" not in df.columns: return {"current_dd": None, "max_dd": None}
        close = df["Close"].dropna()
        if len(close) < 10: return {"current_dd": None, "max_dd": None}
        recent = close.iloc[-window:]; peak = recent.cummax(); dd = (recent / peak - 1)
        return {"current_dd": float(dd.iloc[-1]) * 100, "max_dd": float(dd.min()) * 100}
    def drawdown_metrics_from_df(self, df, window=252):
        if df is None or df.empty or "Close" not in df.columns: return {"current_dd": None, "max_dd": None}
        close = df["Close"].dropna()
        if len(close) < 10: return {"current_dd": None, "max_dd": None}
        recent = close.iloc[-window:]; peak = recent.cummax(); dd = (recent / peak - 1)
        return {"current_dd": float(dd.iloc[-1]) * 100, "max_dd": float(dd.min()) * 100}
    def correlation_matrix(self, tickers, window=60):
        sd = {}
        for tk in tickers:
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window: sd[tk] = lr.iloc[-window:]
        if len(sd) < 2: return None
        df_all = pd.concat(sd.values(), axis=1); df_all.columns = list(sd.keys()); df_all = df_all.dropna()
        if len(df_all) < 20: return None
        return df_all.corr()
    def risk_contribution(self, tickers, weights, window=60):
        vt, vlr, vw = [], [], []
        for tk, w in zip(tickers, weights):
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                vt.append(tk); vlr.append(lr); vw.append(w)
        if len(vt) < 2: return {}
        df_all = pd.concat(vlr, axis=1); df_all.columns = vt; df_all = df_all.dropna().iloc[-window:]
        if len(df_all) < 20: return {}
        w = np.array(vw, dtype=float); w /= w.sum()
        cov = df_all.cov().values * 252
        port_v = float(w @ cov @ w); mrc = cov @ w; rc = w * mrc
        trc = rc.sum()
        rc_pct = rc / trc * 100 if trc > 0 else rc * 0
        result = {}
        for i, tk in enumerate(vt):
            result[tk] = {"weight_pct": w[i] * 100, "rc_absolute": float(rc[i]),
                          "rc_pct": float(rc_pct[i]), "flag": float(rc_pct[i]) > 40}
        return result
    def portfolio_volatility(self, tickers, weights, window=60):
        vt, vlr, vw = [], [], []
        for tk, w in zip(tickers, weights):
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                vt.append(tk); vlr.append(lr); vw.append(w)
        if len(vt) < 2: return None
        df_all = pd.concat(vlr, axis=1); df_all.columns = vt; df_all = df_all.dropna().iloc[-window:]
        if len(df_all) < 20: return None
        w = np.array(vw) / sum(vw)
        cov = df_all.cov().values * 252
        return float(np.sqrt(w @ cov @ w))

# -----------------------------------------------------------------------------
# MODULE 9bis : PORTFOLIO OPTIMIZER ENGINE
# -----------------------------------------------------------------------------
class PortfolioOptimizerEngine:
    def __init__(self, dm):
        self.dm = dm
        self._log_returns = dm.compute_log_returns()
    def strategic_optimization_is_diagnostic_only(self) -> bool: return True
    def _returns_matrix(self, tickers, window=252):
        series = {t: self._log_returns[t].iloc[-window:] for t in tickers
                  if t in self._log_returns and len(self._log_returns[t]) >= window}
        if len(series) < 2: return None
        df = pd.concat(series.values(), axis=1); df.columns = list(series.keys())
        return df.dropna()
    def _risk_contributions(self, w, cov):
        port_var = w @ cov @ w
        if port_var <= 1e-12: return np.zeros_like(w)
        mrc = cov @ w; rc = w * mrc
        return rc / port_var
    def _strategic_sleeve_returns(self, window: int = 252) -> Optional[pd.DataFrame]:
        result = {}
        world_candidates = ["MWRD.PA", "DCAM.PA", "CW8.PA", "IWDA.AS"]
        for ticker in world_candidates:
            if ticker in self._log_returns:
                s = self._log_returns[ticker].dropna()
                if len(s) >= window:
                    result["WORLD_CORE"] = s.iloc[-window:].copy(); break
        if "WMMS.DE" in self._log_returns:
            s = self._log_returns["WMMS.DE"].dropna()
            if len(s) >= window: result["WORLD_VALUE"] = s.iloc[-window:]
        if "KRW.PA" in self._log_returns:
            s = self._log_returns["KRW.PA"].dropna()
            if len(s) >= window: result["KOREA"] = s.iloc[-window:]
        if "CHIP.PA" in self._log_returns:
            s = self._log_returns["CHIP.PA"].dropna()
            if len(s) >= window: result["SEMICONDUCTOR"] = s.iloc[-window:]
        if len(result) < 2: return None
        df = pd.concat(result.values(), axis=1); df.columns = list(result.keys())
        return df.dropna()
    def max_sharpe_sleeve_weights(self, window: int = 252, risk_free: float = 0.025, bounds=(0.02, 0.60)):
        rets = self._strategic_sleeve_returns(window)
        if rets is None or len(rets) < 60: return None
        mu = rets.mean().values * 252; cov = rets.cov().values * 252; n = len(mu)
        def neg_sharpe(w):
            vol = np.sqrt(w @ cov @ w)
            if vol <= 1e-9: return 1e6
            return -((w @ mu) - risk_free) / vol
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        res = minimize(neg_sharpe, np.full(n, 1 / n), method="SLSQP", bounds=[bounds] * n, constraints=constraints,
                       options={"maxiter": 500, "ftol": 1e-9})
        if not res.success: return None
        return {ticker: float(weight) for ticker, weight in zip(rets.columns, res.x)}
    def risk_parity_sleeve_weights(self, window: int = 252, bounds=(0.02, 0.60)):
        rets = self._strategic_sleeve_returns(window)
        if rets is None or len(rets) < 60: return None
        cov = rets.cov().values * 252; n = len(rets.columns)
        def objective(w):
            rc = self._risk_contributions(w, cov)
            target = 1 / n
            return np.sum((rc - target) ** 2)
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        res = minimize(objective, np.full(n, 1 / n), method="SLSQP", bounds=[bounds] * n, constraints=constraints,
                       options={"maxiter": 500, "ftol": 1e-9})
        if not res.success: return None
        return {ticker: float(weight) for ticker, weight in zip(rets.columns, res.x)}
    def max_sharpe_weights(self, tickers, window=252, risk_free=0.025, bounds=(0.02, 0.40)):
        rets = self._returns_matrix(tickers, window)
        if rets is None or len(rets) < 60: return None
        mu = rets.mean().values * 252; cov = rets.cov().values * 252; n = len(mu)
        def neg_sharpe(w):
            vol = np.sqrt(w @ cov @ w)
            return 1e6 if vol <= 1e-9 else -((w @ mu) - risk_free) / vol
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        res = minimize(neg_sharpe, np.full(n, 1/n), method="SLSQP", bounds=[bounds]*n, constraints=cons, options={"maxiter": 500, "ftol": 1e-9})
        return {tk: float(w) for tk, w in zip(rets.columns, res.x)} if res.success else None
    def risk_parity_weights(self, tickers, window=252, bounds=(0.02, 0.50)):
        rets = self._returns_matrix(tickers, window)
        if rets is None or len(rets) < 60: return None
        cov = rets.cov().values * 252; n = cov.shape[0]
        def rc_obj(w):
            vol = np.sqrt(w @ cov @ w)
            if vol < 1e-9: return 1e6
            rc = w * (cov @ w) / vol
            return np.sum((rc - vol/n) ** 2)
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        res = minimize(rc_obj, np.full(n, 1/n), method="SLSQP", bounds=[bounds]*n, constraints=cons)
        return {tk: float(w) for tk, w in zip(rets.columns, res.x)} if res.success else None
    def min_variance_weights(self, tickers, window=252, bounds=(0.02, 0.40)):
        rets = self._returns_matrix(tickers, window)
        if rets is None or len(rets) < 60: return None
        cov = rets.cov().values * 252; n = cov.shape[0]
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        res = minimize(lambda w: w @ cov @ w, np.full(n, 1/n), method="SLSQP", bounds=[bounds]*n, constraints=cons)
        return {tk: float(w) for tk, w in zip(rets.columns, res.x)} if res.success else None
    def max_sharpe_weights_rc_constrained(self, tickers, window=252, risk_free=0.025, bounds=(0.02, 0.40), rc_max=0.30):
        rets = self._returns_matrix(tickers, window)
        if rets is None or len(rets) < 60: return None
        mu = rets.mean().values * 252; cov = rets.cov().values * 252; n = len(mu)
        def neg_sharpe(w):
            vol = np.sqrt(w @ cov @ w)
            return 1e6 if vol <= 1e-9 else -((w @ mu) - risk_free) / vol
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        for i in range(n):
            cons.append({"type": "ineq", "fun": (lambda w, idx=i: rc_max - self._risk_contributions(w, cov)[idx])})
        res = minimize(neg_sharpe, np.full(n, 1/n), method="SLSQP", bounds=[bounds]*n, constraints=cons, options={"maxiter": 500, "ftol": 1e-9})
        return {tk: float(w) for tk, w in zip(rets.columns, res.x)} if res.success else None
    def _solve_weights(self, mu, cov, method, bounds, rc_max=0.30):
        n = len(mu)
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        if method == "minvar": obj = lambda w: w @ cov @ w
        elif method == "rp":
            def obj(w):
                vol = np.sqrt(w @ cov @ w)
                if vol < 1e-9: return 1e6
                rc = w * (cov @ w) / vol
                return np.sum((rc - vol/n) ** 2)
        else:
            def obj(w):
                vol = np.sqrt(w @ cov @ w)
                return 1e6 if vol <= 1e-9 else -((w @ mu) - 0.025) / vol
        x0 = np.full(n, 1/n)
        res = minimize(obj, x0, method="SLSQP", bounds=[bounds]*n, constraints=cons, options={"maxiter": 400, "ftol": 1e-9})
        return res.x if res.success else None
    def walk_forward_backtest(self, tickers, method="sharpe", lookback=252, rebalance_every=20, bounds=(0.02, 0.40), transaction_cost_bps=0.0010, rc_max=0.30):
        series = {t: self._log_returns[t] for t in tickers if t in self._log_returns}
        if len(series) < 2: return {"available": False, "reason": "Moins de 2 tickers."}
        df = pd.concat(series.values(), axis=1).dropna(); df.columns = list(series.keys())
        n_total = len(df)
        if n_total < lookback + rebalance_every * 3: return {"available": False, "reason": "Historique insuffisant."}
        n_assets = len(df.columns); equal_w = np.full(n_assets, 1.0 / n_assets)
        rebalance_dates_idx = list(range(lookback, n_total, rebalance_every))
        if not rebalance_dates_idx: return {"available": False, "reason": "Pas de rebalancement."}
        strat_returns, world_dates_all = [], []
        current_weights = equal_w.copy(); prev_weights_for_cost = equal_w.copy()
        n_rebalances = 0; weights_history = []
        for start_test in rebalance_dates_idx:
            end_test = min(start_test + rebalance_every, n_total)
            train = df.iloc[start_test - lookback:start_test]; test = df.iloc[start_test:end_test]
            if len(test) == 0: continue
            mu = train.mean().values * 252; cov = train.cov().values * 252
            new_weights = self._solve_weights(mu, cov, method, bounds, rc_max=rc_max)
            if new_weights is None: new_weights = current_weights
            turnover = np.sum(np.abs(new_weights - prev_weights_for_cost))
            cost = turnover * transaction_cost_bps
            period_ret = test.values @ new_weights
            if len(period_ret) > 0:
                period_ret = period_ret.copy(); period_ret[0] -= cost
            strat_returns.extend(period_ret.tolist()); world_dates_all.extend(test.index.tolist())
            weights_history.append({"date": df.index[start_test], **{tk: w for tk, w in zip(df.columns, new_weights)}})
            prev_weights_for_cost = new_weights; current_weights = new_weights; n_rebalances += 1
        if len(strat_returns) < 60: return {"available": False, "reason": "Échantillon trop petit."}
        strat_ret_series = pd.Series(strat_returns, index=world_dates_all)
        return {"available": True, "returns": strat_ret_series, "n_rebalances": n_rebalances,
                "weights_history": weights_history, "tickers": list(df.columns)}

def compute_wf_metrics(returns):
    if len(returns) < 30: return {"available": False}
    equity = (1 + returns).cumprod(); n = len(returns); years = n / 252
    cagr = float(equity.iloc[-1] ** (1/years) - 1) if years > 0 and equity.iloc[-1] > 0 else np.nan
    vol = float(returns.std() * np.sqrt(252))
    rmax = equity.cummax(); dd = equity / rmax - 1; max_dd = float(dd.min())
    sharpe = (cagr - 0.025) / vol if vol > 0 else np.nan
    calmar = cagr / abs(max_dd) if max_dd != 0 else np.nan
    return {"available": True, "cagr_pct": cagr*100, "vol_pct": vol*100, "max_dd_pct": max_dd*100, "sharpe": sharpe, "calmar": calmar, "equity_curve": equity}

# -----------------------------------------------------------------------------
# MODULE 10 : PORTFOLIO ENGINE
# -----------------------------------------------------------------------------
def enrich_positions(raw_positions):
    result = []
    for pos in raw_positions:
        tk_id = pos.get("ticker")
        meta = ETF_LIBRARY.get(tk_id)
        if meta is None: continue
        result.append({"nom": meta["nom"], "tickers": [meta["yf"]] + meta.get("yf_fallbacks", []),
                       "parts": float(pos.get("parts", 0.0)), "prm": float(pos.get("prm", 0.0)),
                       "enveloppe": pos.get("account", meta["enveloppe"]), "_tk_id": tk_id, "ticker": tk_id})
    return result

class PortfolioEngine:
    def __init__(self, dm, re, qre): self.dm = dm; self.re = re; self.qre = qre
    def compute_adjusted_benchmark(self):
        df = self.dm.data.get(BENCHMARK_WORLD_TICKER)
        if df is None or df.empty:
            for wt in WORLD_TICKERS:
                df = self.dm.data.get(wt)
                if df is not None and not df.empty: break
        if df is None or df.empty or "Close" not in df.columns: return None
        close = df["Close"].dropna()
        anchor_dt = pd.to_datetime(_ANCHOR_DATE)
        idx_anchor = close.index[close.index <= anchor_dt]
        if len(idx_anchor) == 0: return None
        prix_anchor = float(close.loc[idx_anchor[-1]])
        prix_actuel, _, _ = self.dm.get_price_info([BENCHMARK_WORLD_TICKER] + WORLD_TICKERS)
        prix_actuel = float(prix_actuel) if prix_actuel else float(close.iloc[-1])
        if prix_anchor <= 0: return None
        return ((1 + _ANCHOR_PERF / 100) * (prix_actuel / prix_anchor) - 1) * 100
    def compute_portfolio(self, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo):
        positions_calc = []; valeur_totale = valeur_veille = 0.0
        val_env = {"PEA": 0.0, "AV": 0.0}; gan_env = {"PEA": 0.0, "AV": 0.0}
        for pos in positions_conf:
            prix, prev, tk_used = self.dm.get_price_info(pos["tickers"])
            env = pos["enveloppe"]
            if prix is None:
                positions_calc.append({"nom": pos["nom"], "ticker": None, "prix": None, "valeur": 0.0,
                                       "perf_pct": None, "var_jour_pct": 0.0, "var_jour_eur": 0.0,
                                       "enveloppe": env, "parts": pos["parts"], "prm": pos["prm"], "gain_unit": 0})
                continue
            valeur = pos["parts"] * prix
            gain_unit = prix - pos["prm"]
            perf_pct = gain_unit / pos["prm"] * 100 if pos["prm"] != 0 else 0.0
            gain_total = gain_unit * pos["parts"]
            var_j_pct = (prix - prev) / prev * 100 if prev and prev != 0 else 0.0
            var_j_eur = (prix - prev) * pos["parts"] if prev else 0.0
            positions_calc.append({"nom": pos["nom"], "ticker": tk_used, "prix": prix, "valeur": valeur,
                                   "perf_pct": perf_pct, "var_jour_pct": var_j_pct, "var_jour_eur": var_j_eur,
                                   "enveloppe": env, "parts": pos["parts"], "prm": pos["prm"], "gain_unit": gain_unit})
            valeur_totale += valeur; val_env[env] += valeur; gan_env[env] += gain_total
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
    def compute_benchmark(self, positions_conf, perf_tot_pct):
        bench = next((p for p in positions_conf if p["nom"] == BENCHMARK_NOM), None)
        if not bench: return {}
        prix, prev, tk = self.dm.get_price_info(bench["tickers"])
        if not prix: return {}
        df_h = self.dm.data.get(tk, pd.DataFrame())
        if df_h.empty:
            for t in bench["tickers"]:
                df_h = self.dm.data.get(t, pd.DataFrame())
                if not df_h.empty: break
        if df_h.empty: return {"prix": prix}
        close = df_h["Close"].dropna()
        try: start_val = float(close.loc[DATE_DEBUT.strftime("%Y-%m-%d")])
        except KeyError:
            cands = close.loc[:DATE_DEBUT.strftime("%Y-%m-%d")]
            start_val = float(cands.iloc[-1]) if not cands.empty else float(close.iloc[0])
        perf_bench_ls = (prix / start_val - 1) * 100 if start_val else None
        perf_bench_adj = self.compute_adjusted_benchmark()
        gap_adj = perf_tot_pct - perf_bench_adj if perf_bench_adj is not None else None
        gap_ls = perf_tot_pct - perf_bench_ls if perf_bench_ls is not None else None
        perf_bench_j = (prix - prev) / prev * 100 if prev and prev != 0 else None
        return {"perf_bench": perf_bench_ls, "perf_bench_adj": perf_bench_adj, "gap": gap_adj,
                "gap_lumpsum": gap_ls, "prix": prix, "perf_bench_j": perf_bench_j}
    def compute_unified_score(self, ticker):
        info = self.dm.analyze_ticker(ticker)
        details = []; score = 0
        rsi_v = info["rsi"] if info else None
        if rsi_v is not None:
            if rsi_v >= 70: ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Tendu"
            elif rsi_v <= 45: ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Faible"
            else: ms, mb, md = 1, "bull", f"RSI={rsi_v:.1f} Sain"
        else: ms, mb, md = 0, "neut", "RSI indisponible"
        details.append({"name": "Momentum", "score": ms, "badge": mb, "desc": md}); score += ms
        if info and info["sma20"] is not None:
            if info["prix"] > info["sma20"]: ss, sb, sd = 1, "bull", f"Prix {info['prix']:.2f} > SMA20 {info['sma20']:.2f}"
            else: ss, sb, sd = -1, "bear", f"Prix {info['prix']:.2f} < SMA20 {info['sma20']:.2f}"
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
    def compute_strategic_score_4c(self, ticker, regime):
        info = self.dm.analyze_ticker(ticker); trend_raw = 0.0
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
    def compute_confidence_factor(self, tickers, weights):
        pv = self.qre.portfolio_volatility(tickers, weights, 60)
        if pv is None: return 0.85
        if pv < 0.10: return 1.00
        elif pv < 0.15: return 0.90
        elif pv < 0.20: return 0.75
        else: return 0.60
    def compute_target_weight(self, nom, ticker, valeur_totale, positions_calc, unified_precomputed=None):
        current_val = next((p["valeur"] for p in positions_calc if p.get("ticker") == ticker or p.get("nom") == nom), 0.0)
        current_pct = (current_val / valeur_totale * 100) if valeur_totale > 0 else 0.0
        if ticker in WORLD_CORE_TICKERS:
            return {"nom": nom, "ticker": ticker, "action": "MAINTENIR", "target_type": "STRATEGIC_SLEEVE",
                    "sleeve": "world_core", "target_min_pct": 30.0, "target_neutral_min_pct": 33.0,
                    "target_neutral_max_pct": 40.0, "current_pct": current_pct, "delta_pct": 0.0, "delta_eur": 0.0,
                    "target_pct": current_pct, "target_eur": current_val, "locked": True,
                    "reason": "DCAM.PA et MWRD.PA = même poche World Core."}
        if ticker in WORLD_VALUE_TICKERS:
            return {"nom": nom, "ticker": ticker, "action": "STRATEGIC_ENGINE", "target_type": "RANGE",
                    "sleeve": "world_value_tilt", "target_min_pct": 25.0, "target_neutral_min_pct": 30.0,
                    "target_neutral_max_pct": 40.0, "current_pct": current_pct, "delta_pct": 0.0, "delta_eur": 0.0,
                    "target_pct": current_pct, "target_eur": current_val, "locked": False,
                    "reason": "La taille dépend du régime Value/World."}
        if ticker in SATELLITE_TICKERS:
            return {"nom": nom, "ticker": ticker, "action": "STRATEGIC_ENGINE", "target_type": "RISK_BUDGET",
                    "sleeve": "satellites_boost", "target_min_pct": 0.0, "target_neutral_min_pct": 15.0,
                    "target_neutral_max_pct": 30.0, "target_max_pct": 35.0, "current_pct": current_pct,
                    "delta_pct": 0.0, "delta_eur": 0.0, "target_pct": current_pct, "target_eur": current_val,
                    "locked": False, "reason": "Budget de risque actif plafonné à 35%."}
        return {"nom": nom, "ticker": ticker, "action": "MAINTENIR", "target_type": "NON_STRATEGIC",
                "current_pct": current_pct, "target_pct": current_pct, "target_eur": current_val,
                "delta_pct": 0.0, "delta_eur": 0.0, "locked": False, "reason": "ETF hors stratégie active."}
    def evaluate_sentinelles(self):
        alerts, rows = [], []
        for name, tickers in SENTINELLES.items():
            info = None
            for tk in tickers:
                info = self.dm.analyze_ticker(tk)
                if info: break
            alerte = ""
            if info and info["sma20"] and info["prix"] and info["prix"] < info["sma20"]:
                alerte = "⚠"; alerts.append(name)
            rows.append({"Sentinelle": name, "Prix": f"{info['prix']:.2f}" if info and info['prix'] else "N/A",
                         "SMA20": f"{info['sma20']:.2f}" if (info and info["sma20"]) else "N/A",
                         "RSI": f"{info['rsi']:.1f}" if (info and info["rsi"]) else "N/A", "Alerte": alerte})
        msg = " | ".join([f"⚠ {a} sous SMA20" for a in alerts]) if alerts else "✅ Sentinelles OK"
        return msg, "orange" if alerts else "green", rows
    def check_leadership_alerts(self):
        alerts = []; world_close = None
        for wt in WORLD_TICKERS:
            df = self.dm.data.get(wt, pd.DataFrame())
            if not df.empty and "Close" in df.columns: world_close = df["Close"].dropna(); break
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
    def determine_phase(self, gap, etf_infos):
        if gap is None: return "⏳ Phase indéterminée --- Données insuffisantes", "#374151"
        if gap < 0: return "📉 Phase 1 : Reconquête --- Revenir à l'équilibre vs World AV", "#7F1D1D"
        signals = []
        safe_infos = etf_infos or {}
        for ticker, info in safe_infos.items():
            if info and info.get("sma20") and info.get("prix") and info["prix"] < info["sma20"]:
                short_name = ETF_LIBRARY.get(ticker, {}).get("nom", ticker)[:8]
                signals.append(f"{short_name}<SMA20")
        if signals: return f"🔄 Phase 3 : Rotation --- Sécuriser les gains ({', '.join(signals)})", "#78350F"
        return "🚀 Phase 2 : Alpha --- Battre le MSCI World", "#14532D"
    def _compute_cagr_for_ticker(self, ticker, start_date=DATE_DEBUT):
        df = self.dm.data.get(ticker)
        if df is None or df.empty or "Close" not in df.columns: return 0.07, True
        close = df["Close"].dropna()
        if len(close) < 2: return 0.07, True
        sds = start_date.strftime("%Y-%m-%d")
        if sds in close.index: price_start = close.loc[sds]; sde = start_date
        else:
            idx = close.index[close.index >= sds]
            if len(idx) == 0: price_start = close.iloc[0]; sde = close.index[0]
            else: price_start = close.loc[idx[0]]; sde = idx[0]
        price_end = close.iloc[-1]
        if price_start <= 0 or price_end <= 0: return 0.07, True
        days = (close.index[-1] - sde).days
        if days <= 0: return 0.07, True
        years = days / 365.25
        if years <= 0: return 0.07, True
        cagr = (price_end / price_start) ** (1.0 / years) - 1.0
        if np.isnan(cagr) or cagr <= 0.01: return 0.07, True
        return cagr, False
    def compute_envelope_cagr(self, envelope, positions_calc):
        env_pos = [p for p in positions_calc if p.get("enveloppe") == envelope and p.get("valeur", 0) > 0]
        if not env_pos: return 0.07, True
        if envelope == "PEA":
            pea_tk = None
            for p in env_pos:
                if p.get("ticker") and "DCAM.PA" in p["ticker"]: pea_tk = "DCAM.PA"; break
            if not pea_tk: pea_tk = env_pos[0].get("ticker")
            if pea_tk: return self._compute_cagr_for_ticker(pea_tk, DATE_DEBUT)
            else: return 0.07, True
        else:
            tv = sum(p["valeur"] for p in env_pos)
            if tv <= 0: return 0.07, True
            wc = 0.0; af = False
            for pos in env_pos:
                tk = pos.get("ticker")
                if not tk: continue
                w = pos["valeur"] / tv
                c, fb = self._compute_cagr_for_ticker(tk, DATE_DEBUT)
                if fb: af = True
                wc += w * c
            if wc <= 0.01: return 0.07, True
            return wc, af

# -----------------------------------------------------------------------------
# MODULE 12 : PEDAGOGIC ENGINE
# -----------------------------------------------------------------------------
class PedagogicEngine:
    def translate_volatility(self, vol, asset_name):
        if vol is None: return {"value": "N/A", "emoji": "❓", "level": "orange", "title": f"Agitation de {asset_name}", "explain": "Donnée indisponible.", "scale": [], "action": "Revérifier."}
        pct = vol * 100
        if pct < 15: emoji, level, msg, action = "😌", "green", "L'ETF est calme.", "Aucune vigilance."
        elif pct < 25: emoji, level, msg, action = "😐", "orange", "L'ETF bouge normalement.", "Surveillez."
        else: emoji, level, msg, action = "😰", "red", "L'ETF est agité.", "Réduisez éventuellement."
        return {"value": f"{pct:.1f}%", "emoji": emoji, "level": level, "title": f"Agitation de {asset_name}", "explain": msg, "scale": [], "action": action}
    def translate_beta(self, beta, asset_name):
        if beta is None: return {"value": "N/A", "emoji": "❓", "level": "orange", "title": "Sensibilité", "explain": "Indisponible.", "scale": [], "action": "Revérifier."}
        if beta < 0.8: emoji, level, msg, action = "🛡", "green", "Défensif.", "Protège bien."
        elif beta < 1.2: emoji, level, msg, action = "⚖", "green", "Neutre.", "Équilibré."
        elif beta < 1.8: emoji, level, msg, action = "⚡", "orange", "Offensif.", "Limitez."
        else: emoji, level, msg, action = "🌋", "red", "Très sensible.", "Risqué."
        return {"value": f"{beta:.2f}×", "emoji": emoji, "level": level, "title": f"Sensibilité de {asset_name}", "explain": msg, "scale": [], "action": action}
    def translate_drawdown(self, current_dd, max_dd, asset_name):
        if current_dd is None: return {"value": "N/A", "emoji": "❓", "level": "orange", "title": "Recul", "explain": "Indisponible.", "scale": [], "action": "Revérifier."}
        abs_dd = abs(current_dd)
        if abs_dd < 3: emoji, level, msg, action = "🏔", "green", "Proche du sommet.", "Aucune alerte."
        elif abs_dd < 8: emoji, level, msg, action = "📉", "orange", "Repli normal.", "Surveillance."
        elif abs_dd < 15: emoji, level, msg, action = "⚠", "orange", "Correction.", "Vérifiez."
        else: emoji, level, msg, action = "🚨", "red", "Perte importante.", "Réduire."
        return {"value": f"{current_dd:.1f}%", "emoji": emoji, "level": level, "title": f"Recul de {asset_name}", "explain": msg, "scale": [], "action": action}
    def translate_regime(self, regime):
        translations = {
            "Euphorie": {"emoji": "🚀", "level": "green", "explain": "Euphorie.", "action": "Vigilance.", "conseil": "Préparez vos stops."},
            "Expansion": {"emoji": "📈", "level": "green", "explain": "Croissance.", "action": "Renforcements possibles.", "conseil": "Core+Satellites."},
            "Neutre": {"emoji": "⚖", "level": "orange", "explain": "Pas de direction.", "action": "Réduisez un peu.", "conseil": "Attendez."},
            "Stress": {"emoji": "😟", "level": "orange", "explain": "Fatigue.", "action": "Réduisez satellites.", "conseil": "Capital."},
            "Contraction": {"emoji": "🚨", "level": "red", "explain": "Crise.", "action": "Réduisez fortement.", "conseil": "Protégez."},
            "En attente": {"emoji": "⏳", "level": "orange", "explain": "Contradictoire.", "action": "Attendez.", "conseil": "Pas de décision."}
        }
        info = translations.get(regime["confirmed_label"], translations["En attente"])
        return {"label": regime["confirmed_label"], "score": regime["confirmed_score"], "emoji": info["emoji"],
                "level": info["level"], "explain": info["explain"], "action": info["action"], "conseil": info["conseil"]}
    def get_weekly_performances(self, dm, ticker_key, n_weeks=5):
        meta = ETF_LIBRARY.get(ticker_key, {})
        possible = [meta.get("yf")] + meta.get("yf_fallbacks", [])
        possible = [t for t in possible if t]
        sat_df = None
        for t in possible:
            df = dm.data.get(t)
            if df is not None and not df.empty and "Close" in df.columns: sat_df = df; break
        if sat_df is None: return [], [], []
        world = get_world_series(dm, exclude_ticker=ticker_key)
        if world.empty: return [], [], []
        sat_close = sat_df["Close"].dropna()
        common = sat_close.index.intersection(world.index)
        if len(common) < 10: return [], [], []
        sat_w = sat_close[common].resample("W").last(); world_w = world[common].resample("W").last()
        common_w = sat_w.index.intersection(world_w.index)
        if len(common_w) < 2: return [], [], []
        sat_w = sat_w[common_w]; world_w = world_w[common_w]
        sat_ret = sat_w.pct_change().dropna() * 100; world_ret = world_w.pct_change().dropna() * 100
        n = min(n_weeks, len(sat_ret))
        if n == 0: return [], [], []
        sat_ret = sat_ret.iloc[-n:]; world_ret = world_ret.iloc[-n:]
        labels = ["En cours" if i == n-1 else f"S-{n-1-i}" for i in range(n)]
        return labels, list(sat_ret.values), list(world_ret.values)
    def get_portfolio_weekly_performances(self, dm, positions, n_weeks=5):
        price_series = {}
        for pos in positions:
            ticker = pos.get('ticker')
            if not ticker: continue
            meta = ETF_LIBRARY.get(ticker, {})
            candidates = [meta.get('yf')] + meta.get('yf_fallbacks', [])
            candidates = [t for t in candidates if t]
            for t in candidates:
                df = dm.data.get(t)
                if df is not None and not df.empty and 'Close' in df.columns:
                    price_series[ticker] = df['Close'].dropna(); break
        if not price_series: return [], [], []
        common_dates = None
        for s in price_series.values():
            if common_dates is None: common_dates = s.index
            else: common_dates = common_dates.intersection(s.index)
        if common_dates is None or len(common_dates) < 10: return [], [], []
        total_value = pd.Series(0.0, index=common_dates)
        for ticker, s in price_series.items():
            parts = next((pos['parts'] for pos in positions if pos.get('ticker') == ticker), 0)
            if parts == 0: continue
            total_value += s.loc[common_dates] * parts
        if total_value.empty: return [], [], []
        port_weekly = total_value.resample('W').last()
        world = get_world_series(dm, exclude_ticker=None)
        if world.empty: return [], [], []
        world_weekly = world.resample('W').last()
        common_weeks = port_weekly.index.intersection(world_weekly.index)
        if len(common_weeks) < 2: return [], [], []
        port_weekly = port_weekly.loc[common_weeks]; world_weekly = world_weekly.loc[common_weeks]
        port_ret = port_weekly.pct_change().dropna() * 100; world_ret = world_weekly.pct_change().dropna() * 100
        n = min(n_weeks, len(port_ret))
        if n == 0: return [], [], []
        port_ret = port_ret.iloc[-n:]; world_ret = world_ret.iloc[-n:]
        labels = ["En cours" if i == n-1 else f"S-{n-1-i}" for i in range(n)]
        return labels, list(port_ret.values), list(world_ret.values)
    def translate_leadership(self, nom, weekly_gaps):
        if not weekly_gaps: return {"emoji": "❓", "level": "orange", "message": "Données insuffisantes.", "detail": "", "action": "Revérifiez."}
        pos = sum(1 for g in weekly_gaps if g > 0); neg = sum(1 for g in weekly_gaps if g < 0)
        avg = sum(weekly_gaps) / len(weekly_gaps); n = len(weekly_gaps)
        consec_neg = 0
        for g in reversed(weekly_gaps):
            if g < 0: consec_neg += 1
            else: break
        if pos >= n * 0.6 and avg > 0:
            return {"emoji": "🟢", "level": "green", "message": f"{nom} conserve son leadership.", "detail": f"{pos}/{n} positives · Moy {avg:+.1f}%", "action": "Conserver."}
        elif consec_neg >= 3:
            return {"emoji": "🔴", "level": "red", "message": "Le World devient plus intéressant.", "detail": f"{consec_neg} semaines consécutives", "action": "Envisagez de réduire."}
        elif neg > pos:
            return {"emoji": "🟠", "level": "orange", "message": f"{nom} perd son avantage.", "detail": f"{neg}/{n} négatives · Moy {avg:+.1f}%", "action": "Surveillance."}
        else:
            return {"emoji": "🟡", "level": "orange", "message": f"{nom} à égalité.", "detail": f"Moy {avg:+.1f}%", "action": "Maintien."}
    def translate_simple_score(self, score_raw):
        mapping = {-4:0, -3:0, -2:1, -1:2, 0:2, 1:3, 2:3, 3:4, 4:5}
        simple = mapping.get(max(-4, min(4, score_raw)), 2)
        msgs = {5: ("⭐⭐⭐⭐⭐", "Très fort", "ring-5", "Tout vert.", "Maintenez."),
                4: ("⭐⭐⭐⭐☆", "Sain", "ring-4", "Progresse.", "Renforcez."),
                3: ("⭐⭐⭐☆☆", "Neutre", "ring-3", "Stable.", "Maintenez."),
                2: ("⭐⭐☆☆☆", "Fragilité", "ring-2", "Faiblesse.", "Prudence."),
                1: ("⭐☆☆☆☆", "Risque", "ring-1", "Difficultés.", "Réduire."),
                0: ("☆☆☆☆☆", "Danger", "ring-0", "Dégradé.", "Réduction forte.")}
        stars, label, ring_cls, explain, action = msgs[simple]
        return {"score": simple, "stars": stars, "label": label, "ring_cls": ring_cls, "explain": explain, "action": action}
    def translate_sentinelles(self, sent_rows, sector):
        if sector == "korea": names = ["Samsung", "SK Hynix"]
        elif sector == "chip": names = ["TSMC", "NVIDIA", "AMD", "Intel"]
        else: names = []
        alerts = [r for r in sent_rows if r.get("Sentinelle") in names and r.get("Alerte") == "⚠"]
        total = sum(1 for r in sent_rows if r.get("Sentinelle") in names)
        if not alerts: return {"emoji": "🟢", "level": "green", "message": "Leaders solides.", "detail": f"Aucune alerte sur {total}.", "action": "Pas d'action."}
        elif len(alerts) == 1: return {"emoji": "🟠", "level": "orange", "message": "Un leader faible.", "detail": f"{alerts[0]['Sentinelle']} sous SMA20.", "action": "Surveillance."}
        else: return {"emoji": "🔴", "level": "red", "message": "Décrochage des leaders.", "detail": f"{', '.join([a['Sentinelle'] for a in alerts])} sous SMA20.", "action": "Réduction conseillée."}

# -----------------------------------------------------------------------------
# MODULE 13 : STRATEGIC ENGINE
# -----------------------------------------------------------------------------
class StrategicEngine:
    def __init__(self, dm, mre, qre): self.dm = dm; self.mre = mre; self.qre = qre
    def compute(self, ticker, unified_score, regime):
        details = []
        rsi = unified_score.get("rsi_raw")
        if rsi is not None and 45 < rsi < 70: mom_score, mom_label, mom_value = 1, "✅ Bonne dynamique", f"RSI {rsi:.0f}"
        elif rsi is not None: mom_score, mom_label, mom_value = 0, "❌ Faible", f"RSI {rsi:.0f}"
        else: mom_score, mom_label, mom_value = 0, "❓ Indisponible", "N/A"
        details.append({"dim": "Momentum", "score": mom_score, "label": mom_label, "value": mom_value})
        struct_score = 1 if unified_score.get("structure", -1) > 0 else 0
        info = self.dm.analyze_ticker(ticker)
        if info and info["sma20"] and info["prix"]:
            st_label = "✅ Prix > SMA20" if struct_score == 1 else "❌ Prix < SMA20"
            st_value = f"{info['prix']:.2f}€ vs {info['sma20']:.2f}€"
        else: st_label, st_value = "❓ Indisponible", "N/A"
        details.append({"dim": "Structure", "score": struct_score, "label": st_label, "value": st_value})
        lead_score = 1 if unified_score.get("leadership", -2) > 0 else 0
        rs = self.dm.relative_strength_slope(ticker, 14)
        if rs is not None:
            lead_label = "✅ Surperforme" if lead_score == 1 else "❌ Sous-performe"
            lead_value = f"Pente : {rs:+.5f}"
        else: lead_label, lead_value = "❓ Indisponible", "N/A"
        details.append({"dim": "Leadership", "score": lead_score, "label": lead_label, "value": lead_value})
        reg_score = regime.get("confirmed_score", 0)
        macro_label = f"✅ Favorable ({regime['confirmed_label']})" if reg_score >= 1 else f"❌ Difficile ({regime['confirmed_label']})"
        details.append({"dim": "Macro", "score": 1 if reg_score >= 1 else 0, "label": macro_label, "value": f"Score {reg_score:+d}/5"})
        vol = self.qre.rolling_volatility(ticker, 30)
        if vol is not None:
            risk_label = f"✅ OK ({vol*100:.1f}%)" if vol < 0.25 else f"❌ Agité ({vol*100:.1f}%)"
            risk_value = f"{vol*100:.1f}% ann."
        else: risk_label, risk_value = "❓ Indisponible", "N/A"
        details.append({"dim": "Risque", "score": 1 if (vol is not None and vol < 0.25) else 0, "label": risk_label, "value": risk_value})
        total = sum(d["score"] for d in details)
        if total >= 4: verdict, verdict_cls = "✅ Favorable --- Maintien", "verdict-green"
        elif total >= 3: verdict, verdict_cls = "🟡 Correct --- Maintien", "verdict-orange"
        elif total >= 2: verdict, verdict_cls = "🟠 Mitigé --- Prudence", "verdict-orange"
        else: verdict, verdict_cls = "🔴 Défavorable --- Réduction", "verdict-red"
        return {"total": total, "details": details, "verdict": verdict, "verdict_cls": verdict_cls}

# -----------------------------------------------------------------------------
# MODULE 14 : SIMULATEUR FISCAL FRANCE 2026
# -----------------------------------------------------------------------------
FISCAL_PS_2026 = 0.186
FISCAL_IR_PFU = 0.128
AV_IR_BEFORE_8Y = 0.128
AV_IR_AFTER_8Y = 0.075
AV_IR_AFTER_8Y_HIGH = 0.128
AV_ABATTEMENT_SINGLE = 4600.0
AV_ABATTEMENT_COUPLE = 9200.0
AV_PREMIUM_THRESHOLD = 150000.0

def _safe_gain_ratio(value, gain):
    if value <= 0: return 0.0
    return max(0.0, min(1.0, gain / value))

def calculate_pea_tax(withdrawal, current_value, gain, opening_date, withdrawal_date):
    if withdrawal <= 0 or current_value <= 0:
        return {"tax": 0.0, "ps": 0.0, "ir": 0.0, "net": 0.0, "status": "Aucun retrait"}
    opening_date = pd.Timestamp(opening_date)
    withdrawal_date = pd.Timestamp(withdrawal_date)
    five_year_date = opening_date + pd.DateOffset(years=5)
    gain_ratio = _safe_gain_ratio(current_value, gain)
    gain_withdrawn = max(0.0, withdrawal * gain_ratio)
    before_5y = withdrawal_date < five_year_date
    if before_5y:
        ir = gain_withdrawn * FISCAL_IR_PFU; ps = gain_withdrawn * FISCAL_PS_2026
        return {"tax": ir + ps, "ps": ps, "ir": ir, "gain_taxable": gain_withdrawn,
                "net": withdrawal - ir - ps, "status": "Retrait avant 5 ans", "five_year_date": five_year_date}
    ir = 0.0; ps = gain_withdrawn * FISCAL_PS_2026
    return {"tax": ps, "ps": ps, "ir": ir, "gain_taxable": gain_withdrawn,
            "net": withdrawal - ps, "status": "Retrait après 5 ans — IR exonéré", "five_year_date": five_year_date}

def calculate_av_tax(withdrawal, current_value, gain, opening_date, withdrawal_date, premiums_total, household="couple"):
    if withdrawal <= 0 or current_value <= 0:
        return {"tax": 0.0, "ps": 0.0, "ir": 0.0, "net": 0.0, "status": "Aucun retrait"}
    opening_date = pd.Timestamp(opening_date)
    withdrawal_date = pd.Timestamp(withdrawal_date)
    eight_year_date = opening_date + pd.DateOffset(years=8)
    gain_ratio = _safe_gain_ratio(current_value, gain)
    gain_withdrawn = max(0.0, withdrawal * gain_ratio)
    abatement = AV_ABATTEMENT_SINGLE if household == "single" else AV_ABATTEMENT_COUPLE
    if withdrawal_date < eight_year_date:
        ir = gain_withdrawn * AV_IR_BEFORE_8Y; ps = gain_withdrawn * FISCAL_PS_2026
        return {"tax": ir + ps, "ps": ps, "ir": ir, "gain_taxable": gain_withdrawn,
                "net": withdrawal - ir - ps, "status": "Contrat de moins de 8 ans",
                "eight_year_date": eight_year_date, "abatement": 0.0}
    if premiums_total <= AV_PREMIUM_THRESHOLD:
        gain_rate = AV_IR_AFTER_8Y
    else:
        eligible_ratio = AV_PREMIUM_THRESHOLD / premiums_total
        gain_rate = eligible_ratio * AV_IR_AFTER_8Y + (1 - eligible_ratio) * AV_IR_AFTER_8Y_HIGH
    taxable_gain_ir = max(0.0, gain_withdrawn - abatement)
    ir = taxable_gain_ir * gain_rate; ps = gain_withdrawn * FISCAL_PS_2026
    return {"tax": ir + ps, "ps": ps, "ir": ir, "gain_taxable": gain_withdrawn,
            "gain_taxable_ir": taxable_gain_ir, "net": withdrawal - ir - ps,
            "status": "Contrat de 8 ans ou plus", "eight_year_date": eight_year_date,
            "abatement": abatement, "ir_rate": gain_rate}

# =============================================================================
# MODULE 18 : INDICATOR ENGINE
# =============================================================================
class IndicatorEngine:
    def __init__(self, dm): self.dm = dm
    def _series(self, ticker):
        df = self.dm.data.get(ticker)
        if df is None or df.empty or "Close" not in df.columns: return pd.Series(dtype=float)
        return df["Close"].dropna().sort_index()
    def compute_underperf_streak(self, ticker):
        close = self._series(ticker)
        if close.empty or len(close) < 2: return 0
        world = get_world_series(self.dm, exclude_ticker=ticker if ticker == BENCHMARK_WORLD_TICKER else None)
        if world.empty: return 0
        common = close.index.intersection(world.index)
        if len(common) < 2: return 0
        diff = (close.loc[common].pct_change() - world.loc[common].pct_change()).dropna()
        if diff.empty: return 0
        streak = 0
        for v in diff.iloc[::-1]:
            if v < 0: streak += 1
            else: break
        return streak
    def compute(self, ticker, world_ticker=None):
        close = self._series(ticker)
        if close.empty or len(close) < 60: return None
        world = get_world_series(self.dm, exclude_ticker=ticker if ticker == BENCHMARK_WORLD_TICKER else None)
        common = close.index.intersection(world.index) if not world.empty else pd.Index([])
        def ret_n(s, n): return float(s.iloc[-1] / s.iloc[-n-1] - 1) if len(s) > n else None
        def alpha_n(n):
            if len(common) <= n: return None
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
        rs_ma20 = rs_ma50 = rs_val = None
        if len(common) >= 50:
            rs_series = (close.loc[common] / world.loc[common]).dropna()
            if len(rs_series) >= 50:
                rs_val = float(rs_series.iloc[-1]); rs_ma20 = float(rs_series.rolling(20).mean().iloc[-1])
                rs_ma50 = float(rs_series.rolling(50).mean().iloc[-1])
        relative_trend_score = 0
        a20, a60 = alpha_n(20), alpha_n(60)
        if a20 is not None and a20 > 0: relative_trend_score += 1
        if a60 is not None and a60 > 0: relative_trend_score += 1
        if rs_val is not None and rs_ma20 is not None and rs_val > rs_ma20: relative_trend_score += 1
        if rs_ma20 is not None and rs_ma50 is not None and rs_ma20 > rs_ma50: relative_trend_score += 1
        mom5 = ret_n(close, 5); mom20 = ret_n(close, 20); mom60 = ret_n(close, 60)
        mom20_5dago = None
        if len(close) > 25:
            past = close.iloc[:-5]; mom20_5dago = ret_n(past, 20)
        mom_accel = (mom20 - mom20_5dago) if (mom20 is not None and mom20_5dago is not None) else None
        rmax = close.cummax(); dd_series = (close / rmax - 1)
        dd_current = float(dd_series.iloc[-1])
        dd_5d = ret_n(close, 5); dd_10d = ret_n(close, 10)
        dd_max20 = float(dd_series.iloc[-20:].min()) if len(dd_series) >= 20 else None
        dd_max60 = float(dd_series.iloc[-60:].min()) if len(dd_series) >= 60 else None
        dd_max120 = float(dd_series.iloc[-120:].min()) if len(dd_series) >= 120 else None
        returns = close.pct_change().dropna()
        vol20 = float(returns.iloc[-20:].std() * np.sqrt(252)) if len(returns) >= 20 else None
        vol60 = float(returns.iloc[-60:].std() * np.sqrt(252)) if len(returns) >= 60 else None
        vol120 = float(returns.iloc[-120:].std() * np.sqrt(252)) if len(returns) >= 120 else None
        vol_ratio = (vol20 / vol60) if (vol20 and vol60) else None
        vol_shock = (vol20 / vol120) if (vol20 and vol120) else None
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
        streak = self.compute_underperf_streak(ticker)
        return {"ticker": ticker, "price": price, "date": close.index[-1],
                "sma20": sma20, "sma50": sma50, "sma100": sma100, "sma200": sma200, "trend_score": trend_score,
                "alpha3": alpha_n(3), "alpha5": alpha_n(5), "alpha10": alpha_n(10),
                "alpha20": a20, "alpha60": a60, "alpha120": alpha_n(120),
                "rs": rs_val, "rs_ma20": rs_ma20, "rs_ma50": rs_ma50, "relative_trend_score": relative_trend_score,
                "mom5": mom5, "mom20": mom20, "mom60": mom60, "mom_accel": mom_accel,
                "dd_current": dd_current, "dd_5d": dd_5d, "dd_10d": dd_10d,
                "dd_max20": dd_max20, "dd_max60": dd_max60, "dd_max120": dd_max120,
                "vol20": vol20, "vol60": vol60, "vol120": vol120, "vol_ratio": vol_ratio, "vol_shock": vol_shock,
                "beta60": beta60, "corr20": corr20, "corr60": corr60, "corr120": corr120,
                "z20": z20, "rsi14": rsi14, "n_history": len(close), "underperf_streak": streak}

# =============================================================================
# MODULE 19 : WORLD REGIME ENGINE
# =============================================================================
class WorldRegimeEngine:
    def __init__(self, dm, ie): self.dm = dm; self.ie = ie
    def get_regime(self):
        world_tk = None
        for wt in [BENCHMARK_WORLD_TICKER] + WORLD_TICKERS:
            df = self.dm.data.get(wt)
            if df is not None and not df.empty: world_tk = wt; break
        if world_tk is None: return {"regime": "NEUTRAL", "reason": "Indisponible", "indicators": {}}
        close = self.dm.data[world_tk]["Close"].dropna()
        sma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
        price = float(close.iloc[-1])
        returns = close.pct_change().dropna()
        vol20 = returns.iloc[-20:].std() * np.sqrt(252) if len(returns) >= 20 else None
        vol120 = returns.iloc[-120:].std() * np.sqrt(252) if len(returns) >= 120 else None
        vol_shock = (vol20 / vol120) if (vol20 and vol120) else 1.0
        rmax = close.cummax(); dd_current = float((close / rmax - 1).iloc[-1])
        above20 = sma20 is not None and price > sma20
        above50 = sma50 is not None and price > sma50
        above200 = sma200 is not None and price > sma200
        sma50_above200 = sma50 is not None and sma200 is not None and sma50 > sma200
        if above200 and sma50_above200 and above20 and vol_shock < 1.2: regime = "RISK_ON"
        elif (not above50 and sma50 is not None and sma20 is not None and sma20 < sma50) or vol_shock > 1.3: regime = "RISK_OFF"
        else: regime = "NEUTRAL"
        if (not above200) and dd_current < -0.10 and vol_shock > 1.4: regime = "CRASH"
        return {"regime": regime, "price": price, "sma20": sma20, "sma50": sma50, "sma200": sma200,
                "vol_shock": round(vol_shock, 2) if vol_shock else None,
                "drawdown": round(dd_current * 100, 2), "world_ticker": world_tk}

# =============================================================================
# MODULE 20 : CRASH PROTECTION & UNDERPERFORMANCE ENGINES
# =============================================================================
class CrashProtectionEngine:
    def compute(self, ind, world_regime):
        score, reasons = 0, []
        if ind["sma20"] and ind["price"] < ind["sma20"]: score += 1; reasons.append("Prix < SMA20")
        if ind["sma20"] and ind["sma50"] and ind["sma20"] < ind["sma50"]: score += 1; reasons.append("SMA20 < SMA50")
        if ind["alpha20"] is not None and ind["alpha20"] < 0: score += 1; reasons.append(f"Alpha20 = {ind['alpha20']*100:.1f}%")
        if ind["alpha60"] is not None and ind["alpha60"] < 0: score += 1; reasons.append(f"Alpha60 = {ind['alpha60']*100:.1f}%")
        if ind["vol_ratio"] is not None and ind["vol_ratio"] > CRASH_THRESHOLDS["vol_ratio"]: score += 1; reasons.append(f"Vol ratio {ind['vol_ratio']:.2f}")
        if ind["dd_5d"] is not None and ind["dd_5d"] < CRASH_THRESHOLDS["dd_5d"]: score += 1; reasons.append(f"Chute {ind['dd_5d']*100:.1f}%")
        if world_regime in ("RISK_OFF", "CRASH"): score += 1; reasons.append(f"World {world_regime}")
        level = "LOW"
        for lo, hi, lbl in CRASH_LEVELS:
            if lo <= score <= hi: level = lbl
        return {"score": score, "level": level, "reasons": reasons}

class UnderperformanceEngine:
    def compute(self, ind):
        score, reasons = 0, []
        a20, a60, a120 = ind.get("alpha20"), ind.get("alpha60"), ind.get("alpha120")
        if a20 is not None and a20 < UNDERPERF_THRESHOLDS["alpha20"]: score += 1; reasons.append(f"Alpha20 {a20*100:.1f}%")
        if a60 is not None and a60 < UNDERPERF_THRESHOLDS["alpha60"]: score += 1; reasons.append(f"Alpha60 {a60*100:.1f}%")
        if a120 is not None and a120 < 0: score += 1; reasons.append(f"Alpha120 {a120*100:.1f}%")
        if ind.get("relative_trend_score", 4) <= 1: score += 1; reasons.append("Force relative faible")
        return {"score": score, "max_score": 4, "reasons": reasons}

# =============================================================================
# MODULE 21 : EMPIRICAL ANALOG ENGINE
# =============================================================================
class EmpiricalAnalogEngine:
    def __init__(self, dm, ie): self.dm = dm; self.ie = ie
    def analyze(self, ticker, current_score, score_type="crash", horizon=20, tolerance=1):
        df = self.dm.data.get(ticker); world = get_world_series(self.dm, exclude_ticker=ticker)
        if df is None or df.empty or world.empty: return {"available": False}
        close = df["Close"].dropna(); common = close.index.intersection(world.index)
        if len(common) < 250: return {"available": False}
        close_c = close.loc[common]; world_c = world.loc[common]
        returns = close_c.pct_change(); sma20 = close_c.rolling(20).mean(); sma50 = close_c.rolling(50).mean()
        vol20 = returns.rolling(20).std() * np.sqrt(252); vol60 = returns.rolling(60).std() * np.sqrt(252)
        vol_ratio = vol20 / vol60
        alpha20 = (close_c / close_c.shift(20) - 1) - (world_c / world_c.shift(20) - 1)
        alpha60 = (close_c / close_c.shift(60) - 1) - (world_c / world_c.shift(60) - 1)
        dd_5d = close_c / close_c.shift(5) - 1
        hist_score = pd.Series(0, index=common)
        hist_score += (close_c < sma20).astype(int); hist_score += (sma20 < sma50).astype(int)
        hist_score += (alpha20 < 0).astype(int); hist_score += (alpha60 < 0).astype(int)
        hist_score += (vol_ratio > CRASH_THRESHOLDS["vol_ratio"]).astype(int)
        hist_score += (dd_5d < CRASH_THRESHOLDS["dd_5d"]).astype(int)
        mask = (hist_score - current_score).abs() <= tolerance
        analog_dates = common[mask][:-horizon] if horizon < len(common) else common[mask]
        analog_dates = [d for d in analog_dates if d in common[:-horizon]]
        if len(analog_dates) < 15: return {"available": False, "n_samples": len(analog_dates)}
        future_alphas = []
        for d in analog_dates:
            try:
                idx = common.get_loc(d)
                if idx + horizon >= len(common): continue
                d_future = common[idx + horizon]
                etf_ret = close_c.loc[d_future] / close_c.loc[d] - 1
                world_ret = world_c.loc[d_future] / world_c.loc[d] - 1
                future_alphas.append(etf_ret - world_ret)
            except Exception: continue
        if len(future_alphas) < 15: return {"available": False, "n_samples": len(future_alphas)}
        arr = np.array(future_alphas); hit_rate_neg = float((arr < 0).mean()); expected_alpha = float(arr.mean())
        if len(arr) < 30: confidence = "LOW"
        elif len(arr) < 75: confidence = "MEDIUM"
        else: confidence = "HIGH"
        if hit_rate_neg < 0.40: proba_label = "FAIBLE"
        elif hit_rate_neg < 0.60: proba_label = "MODÉRÉE"
        else: proba_label = "ÉLEVÉE"
        return {"available": True, "n_samples": len(arr), "expected_alpha": expected_alpha,
                "hit_rate_negative": hit_rate_neg, "proba_label": proba_label, "confidence": confidence, "horizon": horizon}

# =============================================================================
# MODULE 22 : LINXEA EXECUTION ENGINE
# =============================================================================
class LinxeaExecutionEngine:
    def __init__(self, dm, analog): self.dm = dm; self.analog = analog
    def compute_execution_date(self, signal_dt):
        cutoff = signal_dt.replace(hour=LINXEA_CUTOFF_HOUR, minute=LINXEA_CUTOFF_MINUTE, second=0, microsecond=0)
        latency = 1 if signal_dt <= cutoff else 2
        target = signal_dt + timedelta(days=latency)
        while target.weekday() >= 5: target += timedelta(days=1); latency += 1
        return target, latency
    def latency_risk(self, ticker, current_score, latency_days):
        res = self.analog.analyze(ticker, current_score, horizon=max(latency_days, 1), tolerance=1)
        if not res.get("available"): return {"available": False}
        return {"available": True, "expected_loss_pct": res["expected_alpha"] * 100, "n_samples": res["n_samples"],
                "risk_label": "LOW" if res["expected_alpha"] > -0.005 else "MODERATE" if res["expected_alpha"] > -0.02 else "HIGH"}

# =============================================================================
# MODULE 23 : DATA QUALITY & DECISION ENGINE
# =============================================================================
class DataQualityEngine:
    def score(self, ind, world_regime):
        if ind is None: return {"score": 0, "label": "NO_DECISION", "reasons": ["Aucune donnée"]}
        s, reasons = 100, []
        if ind["n_history"] < 250: s -= 30; reasons.append(f"Historique court ({ind['n_history']}j)")
        if ind["sma200"] is None: s -= 20; reasons.append("SMA200 indisponible")
        if ind["alpha20"] is None or ind["alpha60"] is None: s -= 25; reasons.append("Alpha indisponible")
        if not world_regime.get("world_ticker") and not world_regime.get("regime"): s -= 25; reasons.append("Benchmark indisponible")
        label = "EXCELLENT" if s >= 90 else "BON" if s >= 80 else "ACCEPTABLE" if s >= 60 else "NO_DECISION"
        return {"score": max(0, s), "label": label, "reasons": reasons}

class DecisionEngine:
    def decide(self, ticker, ind, crash, underperf, world_regime, dq, latency, risk_contribution_pct=None, previous_decision=None):
        if dq["label"] == "NO_DECISION": return {"decision": "NO_DECISION", "confidence": "NONE", "reason": "Données insuffisantes"}
        if world_regime.get("regime") == "CRASH" and crash["score"] >= 4:
            return {"decision": "REDUCE_50", "confidence": "HIGH", "reason": f"CRASH + Crash Score {crash['score']}/7"}
        was_reduced_or_exit = previous_decision in ("REDUCE_25", "REDUCE_50", "EXIT")
        combined_risk = crash["score"] + underperf["score"]
        if crash["level"] == "CRITICAL" and world_regime.get("regime") in ("RISK_OFF", "CRASH"):
            decision, conf = "EXIT", "HIGH"
        elif crash["score"] >= DECISION_EXIT_SCORE: decision, conf = "REDUCE_50", "HIGH"
        elif crash["score"] >= 4 or underperf["score"] >= 3: decision, conf = "REDUCE_25", "MEDIUM"
        elif was_reduced_or_exit and combined_risk <= DECISION_REENTER_SCORE and ind.get("trend_score", 0) >= 3: decision, conf = "RE_ENTER", "MEDIUM"
        elif crash["score"] >= 2 or underperf["score"] >= 2: decision, conf = "WATCH", "MEDIUM"
        else: decision, conf = "HOLD", "HIGH" if dq["score"] >= 90 else "MEDIUM"
        note_risk = None
        if risk_contribution_pct is not None and risk_contribution_pct > 40 and decision == "HOLD":
            decision, conf = "WATCH", "MEDIUM"
            note_risk = f"Contribution risque {risk_contribution_pct:.0f}%"
        return {"decision": decision, "confidence": conf, "crash_score": crash["score"], "crash_level": crash["level"],
                "underperf_score": underperf["score"], "world_regime": world_regime.get("regime"),
                "data_quality": dq["label"], "latency_risk": latency.get("risk_label") if latency.get("available") else "N/A",
                "note_risk": note_risk, "reasons": crash["reasons"] + underperf["reasons"]}

# =============================================================================
# MODULE 23bis : DÉCISIONS ETF
# =============================================================================
def build_decision_sentence(nom, ind, crash, underperf, decision):
    action_map = {"EXIT": "Sortir", "REDUCE_50": "Réduire 50%", "REDUCE_25": "Réduire 25%",
                  "WATCH": "Surveiller", "HOLD": "Conserver", "RE_ENTER": "Ré-entrée", "NO_DECISION": "Indisponible"}
    color_map = {"EXIT": "#FF3131", "REDUCE_50": "#FF3131", "REDUCE_25": "#F97316",
                 "WATCH": "#F97316", "HOLD": "#22C55E", "RE_ENTER": "#3B82F6", "NO_DECISION": "#6B7585"}
    dec = decision.get("decision", "NO_DECISION")
    phrase = f"**{nom}** → {action_map.get(dec, dec)}"
    return phrase, color_map.get(dec, "#6B7585")

def compute_all_position_decisions(ui, ptf):
    world_regime = ui.wre.get_regime()
    now = datetime.now(ZoneInfo("Europe/Paris"))
    rc_map = {}
    try:
        tk_held = [p["ticker"] for p in ptf["positions"] if p.get("ticker") and p["valeur"] > 0]
        w_held = [p["valeur"] for p in ptf["positions"] if p.get("ticker") and p["valeur"] > 0]
        if len(tk_held) >= 2 and sum(w_held) > 0: rc_map = ui.qre.risk_contribution(tk_held, w_held, 60)
    except Exception: rc_map = {}
    if "_last_decisions" not in st.session_state: st.session_state["_last_decisions"] = {}
    results = []
    for pos in ptf["positions"]:
        ticker = pos.get("ticker")
        if not ticker or pos["valeur"] <= 0: continue
        ind = ui.ie.compute(ticker)
        crash = ui.cpe.compute(ind, world_regime["regime"]) if ind else {"score": 0, "level": "N/A", "reasons": []}
        underperf = ui.upe.compute(ind) if ind else {"score": 0, "max_score": 4, "reasons": []}
        dq = ui.dqe.score(ind, world_regime)
        exec_date, latency_days = ui.lee.compute_execution_date(now)
        latency = ui.lee.latency_risk(ticker, crash["score"], latency_days) if ind else {"available": False}
        rc_pct = rc_map.get(ticker, {}).get("rc_pct")
        prev_decision = st.session_state["_last_decisions"].get(ticker)
        result = ui.dec_engine.decide(ticker, ind or {}, crash, underperf, world_regime, dq, latency,
                                       risk_contribution_pct=rc_pct, previous_decision=prev_decision)
        st.session_state["_last_decisions"][ticker] = result["decision"]
        nom = ETF_LIBRARY.get(ticker, {}).get("nom", ticker)
        sentence, scolor = build_decision_sentence(nom, ind or {}, crash, underperf, result)
        results.append({"ticker": ticker, "nom": nom, "ind": ind, "crash": crash, "underperf": underperf, "dq": dq,
                        "exec_date": exec_date, "latency_days": latency_days, "latency": latency,
                        "world_regime": world_regime, "decision": result, "sentence": sentence, "color": scolor})
    return results

# =============================================================================
# MODULE 24 : FEATURE ENGINEERING
# =============================================================================
def compute_world_regime_series(dm):
    world_tk = None
    for wt in [BENCHMARK_WORLD_TICKER] + WORLD_TICKERS:
        df = dm.data.get(wt)
        if df is not None and not df.empty: world_tk = wt; break
    if world_tk is None: return pd.Series(dtype=float)
    close = dm.data[world_tk]["Close"].dropna(); ret = close.pct_change()
    sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean(); sma200 = close.rolling(200).mean()
    vol20 = ret.rolling(20).std() * np.sqrt(252); vol120 = ret.rolling(120).std() * np.sqrt(252)
    vol_shock = vol20 / vol120
    dd = close / close.cummax() - 1
    above20 = close > sma20; above50 = close > sma50; above200 = close > sma200
    sma50_above200 = sma50 > sma200
    regime = pd.Series(0, index=close.index)
    risk_on = above200 & sma50_above200 & above20 & (vol_shock < 1.2)
    risk_off = ((~above50) & (sma20 < sma50)) | (vol_shock > 1.3)
    crash = (~above200) & (dd < -0.10) & (vol_shock > 1.4)
    regime[risk_on] = 1; regime[risk_off] = -1; regime[crash] = -2
    return regime

def build_feature_frame(dm, ticker):
    df = dm.data.get(ticker); world = get_world_series(dm, exclude_ticker=ticker)
    if df is None or df.empty or world.empty: return pd.DataFrame()
    close = df["Close"].dropna(); common = close.index.intersection(world.index)
    if len(common) < 300: return pd.DataFrame()
    close = close.loc[common]; world_c = world.loc[common]
    ret = close.pct_change(); world_ret = world_c.pct_change()
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
    rs_ma20 = rs.rolling(20).mean(); rs_ma50 = rs.rolling(50).mean()
    feat["rs_gap"] = rs - rs_ma20; feat["rs_slope"] = rs_ma20 - rs_ma20.shift(10); feat["rs_trend"] = rs_ma20 - rs_ma50
    sma20 = close.rolling(20).mean(); sma50 = close.rolling(50).mean(); sma200 = close.rolling(200).mean()
    feat["dist_sma20"] = close / sma20 - 1; feat["dist_sma50"] = close / sma50 - 1; feat["dist_sma200"] = close / sma200 - 1
    vol20 = ret.rolling(20).std() * np.sqrt(252); vol60 = ret.rolling(60).std() * np.sqrt(252); vol120 = ret.rolling(120).std() * np.sqrt(252)
    feat["vol20"] = vol20; feat["vol_ratio"] = vol20 / vol60; feat["vol_shock"] = vol20 / vol120
    dd = close / close.cummax() - 1
    feat["drawdown"] = dd; feat["dd_5d"] = close / close.shift(5) - 1
    feat["mom5"] = feat["ret5"]; feat["mom20"] = feat["ret20"]
    feat["mom_accel"] = feat["ret20"] - feat["ret20"].shift(5)
    regime_series = compute_world_regime_series(dm)
    feat["world_regime"] = regime_series.reindex(common).ffill().fillna(0)
    for h in (3, 10, 20, 60):
        etf_fwd = close.shift(-h) / close - 1; world_fwd = world_c.shift(-h) / world_c - 1
        feat[f"fwd_alpha_{h}"] = etf_fwd - world_fwd
    return feat.dropna(subset=["alpha20", "vol_ratio"])

# =============================================================================
# MODULE 25 : FORWARD ALPHA MODEL
# =============================================================================
FEATURE_COLS = ["ret5", "ret20", "ret60", "alpha5", "alpha20", "alpha60", "rs_gap", "rs_slope", "rs_trend",
                "dist_sma20", "dist_sma50", "dist_sma200", "vol20", "vol_ratio", "vol_shock", "drawdown",
                "dd_5d", "mom5", "mom20", "mom_accel", "world_regime"]

class ForwardAlphaModel:
    def __init__(self, horizon=20, n_folds=4, ridge_alpha=5.0):
        self.horizon = horizon; self.n_folds = n_folds; self.ridge_alpha = ridge_alpha
    def _splits(self, n):
        fold_size = n // (self.n_folds + 1)
        if fold_size < 30: return []
        splits = []
        for i in range(1, self.n_folds + 1):
            train_end = fold_size * i
            purge = self.horizon
            train_end_purged = max(0, train_end - purge)
            test_start = train_end
            test_end = min(fold_size * (i + 1), n)
            if test_end <= test_start: continue
            if train_end_purged < 50: continue
            splits.append((slice(0, train_end_purged), slice(test_start, test_end)))
        return splits
    def walk_forward_evaluate(self, feat):
        target_col = f"fwd_alpha_{self.horizon}"
        data = feat.dropna(subset=FEATURE_COLS + [target_col])
        if len(data) < 200: return {"available": False, "reason": "Historique insuffisant"}
        X = data[FEATURE_COLS].values; y = data[target_col].values
        splits = self._splits(len(data))
        if not splits: return {"available": False, "reason": "Pas assez de données"}
        ridge_preds, baseline_preds, actuals = [], [], []
        for train_idx, test_idx in splits:
            X_train, y_train = X[train_idx], y[train_idx]
            X_test, y_test = X[test_idx], y[test_idx]
            if len(y_train) < 50: continue
            baseline_pred = np.full(len(y_test), y_train.mean())
            baseline_preds.extend(baseline_pred)
            if SKLEARN_OK:
                scaler = StandardScaler()
                X_train_s = scaler.fit_transform(X_train); X_test_s = scaler.transform(X_test)
                model = Ridge(alpha=self.ridge_alpha); model.fit(X_train_s, y_train)
                ridge_pred = model.predict(X_test_s)
            else: ridge_pred = baseline_pred
            ridge_preds.extend(ridge_pred); actuals.extend(y_test)
        if len(actuals) < 30: return {"available": False, "reason": "Échantillon OOS trop petit"}
        actuals = np.array(actuals); ridge_preds = np.array(ridge_preds); baseline_preds = np.array(baseline_preds)
        def _metrics(preds):
            preds = np.asarray(preds, dtype=float); actual = np.asarray(actuals, dtype=float)
            valid = np.isfinite(preds) & np.isfinite(actual)
            preds = preds[valid]; actual = actual[valid]
            if len(actual) < 30:
                return {"hit_rate": np.nan, "correlation": np.nan, "mae": np.nan, "rmse": np.nan, "directional_edge": np.nan, "mean_prediction": np.nan}
            hit_rate = float((np.sign(preds) == np.sign(actual)).mean())
            correlation = (float(np.corrcoef(preds, actual)[0, 1]) if np.std(preds) > 1e-9 and np.std(actual) > 1e-9 else 0.0)
            mae = float(np.mean(np.abs(preds - actual))); rmse = float(np.sqrt(np.mean((preds - actual) ** 2)))
            directional_edge = hit_rate - 0.50
            return {"hit_rate": hit_rate, "correlation": correlation, "mae": mae, "rmse": rmse,
                    "directional_edge": directional_edge, "mean_prediction": float(np.mean(preds))}
        rm = _metrics(ridge_preds); bm = _metrics(baseline_preds)
        ridge_better = (pd.notna(rm["hit_rate"]) and rm["hit_rate"] >= 0.55 and rm["directional_edge"] >= 0.05
                        and rm["correlation"] > 0.05 and pd.notna(bm["mae"]) and rm["mae"] <= bm["mae"] * 0.95)
        return {"available": True, "n_oos_samples": len(actuals), "ridge": rm, "baseline": bm, "ridge_better": bool(ridge_better)}
    def fit_production_model(self, feat):
        target_col = f"fwd_alpha_{self.horizon}"
        data = feat.dropna(subset=FEATURE_COLS + [target_col])
        if len(data) < 100 or not SKLEARN_OK: return None, None
        X = data[FEATURE_COLS].values; y = data[target_col].values
        scaler = StandardScaler(); X_s = scaler.fit_transform(X)
        model = Ridge(alpha=self.ridge_alpha); model.fit(X_s, y)
        return model, scaler
    def predict_today(self, feat, model, scaler):
        if model is None or scaler is None or feat.empty: return None
        last_row = feat[FEATURE_COLS].iloc[[-1]].dropna()
        if last_row.empty: return None
        X_s = scaler.transform(last_row.values)
        return float(model.predict(X_s)[0])

# =============================================================================
# MODULE 26 : BACKTEST ENGINE
# =============================================================================
WEIGHT_MAP = {"HOLD": 1.0, "RE_ENTER": 1.0, "WATCH": 1.0, "REDUCE_25": 0.75, "REDUCE_50": 0.50, "EXIT": 0.0, "NO_DECISION": None}

class BacktestEngine:
    def __init__(self, crash_thresholds, underperf_thresholds, exit_score=DECISION_EXIT_SCORE, reenter_score=DECISION_REENTER_SCORE):
        self.ct = crash_thresholds; self.ut = underperf_thresholds; self.exit_score = exit_score; self.reenter_score = reenter_score
    def compute_decision_series(self, feat):
        crash_score = pd.Series(0, index=feat.index)
        crash_score += (feat["dist_sma20"] < 0).astype(int)
        crash_score += ((feat["dist_sma20"] < 0) & (feat["rs_trend"] < 0)).astype(int)
        crash_score += (feat["alpha20"] < 0).astype(int)
        crash_score += (feat["alpha60"] < 0).astype(int)
        crash_score += (feat["vol_ratio"] > self.ct["vol_ratio"]).astype(int)
        crash_score += (feat["dd_5d"] < self.ct["dd_5d"]).astype(int)
        crash_score += (feat["world_regime"] <= -1).astype(int)
        underperf_score = pd.Series(0, index=feat.index)
        underperf_score += (feat["alpha20"] < self.ut["alpha20"]).astype(int)
        underperf_score += (feat["alpha60"] < self.ut["alpha60"]).astype(int)
        combined = crash_score + underperf_score
        decisions = []; was_reduced = False
        for i in range(len(feat)):
            cs = crash_score.iloc[i]; comb = combined.iloc[i]
            wr = feat["world_regime"].iloc[i]; trend_ok = feat["dist_sma20"].iloc[i] > 0
            if wr <= -2 and cs >= 4: d = "REDUCE_50"
            elif cs >= self.exit_score: d = "REDUCE_50"
            elif cs >= 4 or underperf_score.iloc[i] >= 3: d = "REDUCE_25"
            elif was_reduced and comb <= self.reenter_score and trend_ok: d = "HOLD"
            elif cs >= 2 or underperf_score.iloc[i] >= 2: d = "WATCH"
            else: d = "HOLD"
            was_reduced = d in ("REDUCE_25", "REDUCE_50")
            decisions.append(d)
        return pd.Series(decisions, index=feat.index)
    def run(self, dm, ticker, feat, latency_days_normal=1, latency_days_stress=2):
        df = dm.data.get(ticker); world = get_world_series(dm, exclude_ticker=ticker)
        close = df["Close"].loc[feat.index]; world_c = world.loc[feat.index]
        etf_ret = close.pct_change().fillna(0); world_ret = world_c.pct_change().fillna(0)
        decisions = self.compute_decision_series(feat); weights = decisions.map(WEIGHT_MAP).fillna(1.0)
        strategies = {}
        strategies["A_BuyHold"] = etf_ret.copy()
        strategies["B_SignalNoDelay"] = etf_ret * weights
        weights_delayed_c = weights.shift(latency_days_normal).fillna(1.0); strategies["C_SignalLinxeaDelay"] = etf_ret * weights_delayed_c
        weights_delayed_d = weights.shift(latency_days_stress).fillna(1.0); strategies["D_SignalStress"] = etf_ret * weights_delayed_d
        results = {}
        for name, strat_ret in strategies.items():
            results[name] = self._compute_metrics(strat_ret, world_ret, weights if "Signal" in name else None)
        results["_decisions"] = decisions; results["_weights"] = weights
        return results
    def _compute_metrics(self, strat_ret, world_ret, weights):
        n = len(strat_ret)
        if n < 30: return {"available": False}
        equity = (1 + strat_ret).cumprod()
        total_return = float(equity.iloc[-1] - 1); years = n / 252
        cagr = float((equity.iloc[-1]) ** (1 / years) - 1) if years > 0 and equity.iloc[-1] > 0 else np.nan
        ann_vol = float(strat_ret.std() * np.sqrt(252))
        rmax = equity.cummax(); dd = equity / rmax - 1; max_dd = float(dd.min())
        sharpe = float((cagr - 0.025) / ann_vol) if ann_vol > 0 else np.nan
        calmar = float(cagr / abs(max_dd)) if max_dd != 0 else np.nan
        world_equity = (1 + world_ret).cumprod(); world_total = float(world_equity.iloc[-1] - 1)
        alpha_vs_world = total_return - world_total
        worst_day = float(strat_ret.min()); worst_5d = float(strat_ret.rolling(5).sum().min()); worst_10d = float(strat_ret.rolling(10).sum().min())
        n_trades = int((weights.diff().abs() > 0.01).sum()) if weights is not None else 0
        turnover = float(weights.diff().abs().sum()) if weights is not None else 0.0
        return {"available": True, "total_return_pct": total_return * 100, "cagr_pct": cagr * 100,
                "vol_pct": ann_vol * 100, "max_drawdown_pct": max_dd * 100, "sharpe": sharpe, "calmar": calmar,
                "alpha_vs_world_pct": alpha_vs_world * 100, "worst_day_pct": worst_day * 100,
                "worst_5d_pct": worst_5d * 100, "worst_10d_pct": worst_10d * 100,
                "n_trades": n_trades, "turnover": round(turnover, 2), "equity_curve": equity}

# =============================================================================
# MODULE 27 : THRESHOLD CALIBRATION
# =============================================================================
class CalibrationEngine:
    ALPHA20_GRID = [-0.01, -0.02, -0.03, -0.04, -0.05]
    VOL_RATIO_GRID = [1.1, 1.2, 1.3, 1.4, 1.5]
    DD5D_GRID = [-0.03, -0.05, -0.07, -0.10]
    def __init__(self, dm): self.dm = dm
    def calibrate(self, ticker, feat, train_frac=0.7):
        n = len(feat)
        if n < 300: return {"available": False, "reason": "Historique insuffisant"}
        split = int(n * train_frac); feat_train = feat.iloc[:split]; feat_test = feat.iloc[split:]
        buyhold_cagr_train = self._buyhold_cagr(ticker, feat_train)
        best = None; results_grid = []
        for a20 in self.ALPHA20_GRID:
            for vr in self.VOL_RATIO_GRID:
                for dd in self.DD5D_GRID:
                    ct = {"vol_ratio": vr, "dd_5d": dd}; ut = {"alpha20": a20, "alpha60": a20 * 0.7}
                    bt = BacktestEngine(ct, ut); res = bt.run(self.dm, ticker, feat_train)
                    metric = res.get("C_SignalLinxeaDelay", {})
                    if not metric.get("available"): continue
                    if buyhold_cagr_train and metric["cagr_pct"] < 0.4 * buyhold_cagr_train: continue
                    calmar = metric.get("calmar", np.nan)
                    if np.isnan(calmar): continue
                    entry = {"alpha20": a20, "vol_ratio": vr, "dd_5d": dd, "calmar": calmar, "cagr_pct": metric["cagr_pct"], "max_dd_pct": metric["max_drawdown_pct"]}
                    results_grid.append(entry)
                    if best is None or calmar > best["calmar"]: best = entry
        if best is None: return {"available": False, "reason": "Pas de combinaison valide"}
        ct_best = {"vol_ratio": best["vol_ratio"], "dd_5d": best["dd_5d"]}
        ut_best = {"alpha20": best["alpha20"], "alpha60": best["alpha20"] * 0.7}
        bt_best = BacktestEngine(ct_best, ut_best)
        oos_res = bt_best.run(self.dm, ticker, feat_test); oos_metric = oos_res.get("C_SignalLinxeaDelay", {})
        default_bt = BacktestEngine(CRASH_THRESHOLDS, UNDERPERF_THRESHOLDS)
        default_oos = default_bt.run(self.dm, ticker, feat_test).get("C_SignalLinxeaDelay", {})
        return {"available": True, "n_combinations_tested": len(results_grid), "best_thresholds": best,
                "oos_validation": oos_metric, "default_thresholds_oos": default_oos,
                "improvement": (oos_metric.get("calmar", 0) - default_oos.get("calmar", 0)) if oos_metric.get("available") and default_oos.get("available") else None}
    def _buyhold_cagr(self, ticker, feat):
        df = self.dm.data.get(ticker)
        if df is None: return None
        close = df["Close"].loc[feat.index]; n = len(close)
        if n < 30: return None
        years = n / 252; total = close.iloc[-1] / close.iloc[0]
        return float((total ** (1/years) - 1) * 100) if total > 0 else None

# =============================================================================
# MODULE 28 : ETF SPECIALIZED RISK ENGINE v7.1
# =============================================================================
FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="

@st.cache_data(ttl=21600, show_spinner=False)
def fetch_fred_series(series_id):
    try:
        r = _requests.get(FRED_BASE + series_id, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(_io.StringIO(r.text))
        df.columns = ["date", "value"]; df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna().set_index("date")["value"]
    except Exception: return pd.Series(dtype=float)

def percentile_rank(series, window_years=10):
    s = series.dropna()
    if len(s) < 60: return None
    window = s.iloc[-min(len(s), window_years * 252):]
    return float((window <= window.iloc[-1]).mean() * 100)

def format_bps(pct_points): return f"{pct_points*100:.0f} bps ({pct_points:.2f}%)"

TSS_STRONG_CONTANGO = 0.015; TSS_NEUTRAL_MAX = 0.005; TSS_BACKWARD_STRESS = -0.010
VIX_CALM_LEVEL = 18.0; VIX_STRESS_LEVEL = 30.0
PERSISTENCE_CONFIG = {"korea": {"window": 5, "threshold": 0.60}, "semi": {"window": 5, "threshold": 0.60}, "world": {"window": 3, "threshold": 1.00}, "value": {"window": 10, "threshold": 0.70}}
DQ_BASE = {"korea": 0.45, "semi": 0.80, "world": 1.00, "value": 1.00}

def fetch_us_cyclical_proxy():
    s = fetch_fred_series("AMTMNO")
    if s.empty: return pd.Series(dtype=float), "INDISPONIBLE"
    yoy = s.pct_change(12) * 100
    return yoy.dropna(), "AMTMNO"

class KoreaRiskEngine:
    def __init__(self, dm): self.dm = dm
    def compute(self):
        details = {}; dq = DQ_BASE["korea"]
        krw_usd = self.dm.data.get("KRW=X", pd.DataFrame())
        credit_proxy_signal = False
        if not krw_usd.empty and "Close" in krw_usd.columns:
            close = krw_usd["Close"].dropna()
            if len(close) > 260:
                ret = close.pct_change().dropna()
                vol20 = ret.iloc[-20:].std() * np.sqrt(252); vol_series = ret.rolling(20).std() * np.sqrt(252)
                pctile = percentile_rank(vol_series)
                delta_4w = vol20 - float(vol_series.iloc[-20]) if len(vol_series) > 20 else 0
                credit_proxy_signal = (pctile is not None and pctile >= 75) and (delta_4w > 0)
                details["credit_proxy_pctile"] = pctile
        else: dq -= 0.10
        yoy_series, source_name = fetch_us_cyclical_proxy()
        us_cyclical_signal = False
        if not yoy_series.empty:
            yoy_now = float(yoy_series.iloc[-1]); yoy_3m_ago = float(yoy_series.iloc[-4]) if len(yoy_series) > 4 else yoy_now
            us_cyclical_signal = (yoy_now < 0) or ((yoy_now - yoy_3m_ago) < -2.0)
            details["us_cyclical_proxy_yoy_pct"] = round(yoy_now, 2)
        else: dq -= 0.15
        krw_etf = self.dm.data.get("KRW.PA", pd.DataFrame()); vol_confirm = False
        if not krw_etf.empty and "Close" in krw_etf.columns:
            close = krw_etf["Close"].dropna()
            if len(close) > 40:
                ret = close.pct_change().dropna()
                vol2w = ret.iloc[-10:].std() * np.sqrt(252); vol2w_prev = ret.iloc[-30:-20].std() * np.sqrt(252) if len(ret) > 30 else vol2w
                vol_confirm = (vol2w / vol2w_prev - 1) > 0.15 if vol2w_prev > 0 else False
        samsung_below = self._below_sma50("005930.KS"); hynix_below = self._below_sma50("000660.KS")
        macro_alert = credit_proxy_signal or us_cyclical_signal
        full_confirm = vol_confirm and bool(samsung_below) and bool(hynix_below)
        if macro_alert and full_confirm: score = 2
        elif macro_alert: score = 1
        else: score = 0
        details["capped_at_2_missing_foreign_flows"] = True
        return {"score": score, "dq": round(max(0.0, dq), 2), "details": details}
    def _below_sma50(self, ticker):
        df = self.dm.data.get(ticker, pd.DataFrame())
        if df.empty or "Close" not in df.columns: return None
        close = df["Close"].dropna()
        if len(close) < 50: return None
        return bool(close.iloc[-1] < close.rolling(50).mean().iloc[-1])

class SemiconductorRiskEngine:
    def __init__(self, dm): self.dm = dm
    def compute(self):
        dq = DQ_BASE["semi"]; above, total = 0, 0
        for tk in SOX_COMPONENTS_PROXY:
            df = self.dm.data.get(tk, pd.DataFrame())
            if df.empty or "Close" not in df.columns: continue
            close = df["Close"].dropna()
            if len(close) < 50: continue
            total += 1
            if close.iloc[-1] > close.rolling(50).mean().iloc[-1]: above += 1
        breadth = (above / total * 100) if total > 0 else None
        if total < 15: dq -= 0.20
        phlx_below_sma50 = None
        chip_df = self.dm.data.get("CHIP.PA", pd.DataFrame())
        if not chip_df.empty and "Close" in chip_df.columns:
            close = chip_df["Close"].dropna()
            if len(close) >= 50: phlx_below_sma50 = bool(close.iloc[-1] < close.rolling(50).mean().iloc[-1])
        vol_extreme = False
        if not chip_df.empty and "Close" in chip_df.columns:
            close = chip_df["Close"].dropna()
            if len(close) > 260:
                ret = close.pct_change().dropna(); vol20 = ret.rolling(20).std() * np.sqrt(252)
                pctile = percentile_rank(vol20); vol_extreme = pctile is not None and pctile >= 90
        if breadth is None: score = 0
        elif breadth < 10 and phlx_below_sma50 and vol_extreme: score = 3
        elif breadth < 20 and phlx_below_sma50: score = 2
        elif breadth < 40: score = 1
        else: score = 0
        return {"score": score, "dq": round(max(0.0, dq), 2), "details": {"breadth_pct": breadth, "n_components": total, "phlx_below_sma50": phlx_below_sma50, "vol_extreme": vol_extreme}}

class WorldRiskEngine:
    def __init__(self, dm): self.dm = dm
    def compute(self):
        vix_df = self.dm.data.get("^VIX", pd.DataFrame()); vix3m_df = self.dm.data.get("^VIX3M", pd.DataFrame())
        if vix_df.empty or vix3m_df.empty: return {"score": 0, "dq": 0.0, "details": {"note": "Indisponible"}}
        vix = vix_df["Close"].dropna(); vix3m = vix3m_df["Close"].dropna()
        common = vix.index.intersection(vix3m.index)
        if len(common) < 5: return {"score": 0, "dq": 0.0, "details": {"note": "Insuffisant"}}
        tss = (vix3m.loc[common] - vix.loc[common]) / vix.loc[common]
        tss_now = float(tss.iloc[-1]); vix_now = float(vix.loc[common[-1]])
        backwardation_3d = bool((tss.iloc[-3:] < 0).all()) if len(tss) >= 3 else False
        if tss_now < TSS_BACKWARD_STRESS and vix_now > VIX_STRESS_LEVEL: score = 3
        elif backwardation_3d: score = 2
        elif 0 <= tss_now <= TSS_NEUTRAL_MAX: score = 1
        elif tss_now > TSS_STRONG_CONTANGO and vix_now < VIX_CALM_LEVEL: score = 0
        else: score = 0
        return {"score": score, "dq": DQ_BASE["world"], "details": {"tss_pct": tss_now * 100, "vix": vix_now, "backwardation_3d": backwardation_3d}}

class WorldValueRiskEngine:
    def __init__(self, dm): self.dm = dm
    def compute(self):
        oas = fetch_fred_series("BAMLH0A0HYM2")
        if oas.empty: return {"score": 0, "dq": 0.0, "details": {"note": "FRED indisponible"}}
        oas_now = float(oas.iloc[-1]); ma60 = float(oas.iloc[-60:].mean()) if len(oas) >= 60 else oas_now
        d4w = oas_now - float(oas.iloc[-20]) if len(oas) > 20 else 0.0
        pctile = percentile_rank(oas, window_years=10)
        if oas_now > 6.0: score = 3
        elif oas_now > 5.0 and d4w > 0.5: score = 2
        elif oas_now > ma60 and (pctile is not None and pctile >= 70): score = 1
        else: score = 0
        return {"score": score, "dq": DQ_BASE["value"], "details": {"oas_display": format_bps(oas_now), "ma60_display": format_bps(ma60), "delta_4w_display": format_bps(d4w), "pctile_10y": pctile}}

class RiskEngineV71:
    REDUCTION_MAP = {0: 0.0, 1: 0.0, 2: 0.25, 3: 0.50}
    def __init__(self, dm):
        self.dm = dm
        self.engines = {"korea": KoreaRiskEngine(dm), "semi": SemiconductorRiskEngine(dm), "world": WorldRiskEngine(dm), "value": WorldValueRiskEngine(dm)}
    def _update_persistence(self, key, raw_score):
        cfg = PERSISTENCE_CONFIG[key]
        today = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
        store_key = f"_risk_v71_history_{key}"
        history = st.session_state.get(store_key, [])
        if not history or history[-1]["date"] != today:
            history.append({"date": today, "score": raw_score}); history = history[-cfg["window"]:]; st.session_state[store_key] = history
        else: history[-1]["score"] = raw_score; st.session_state[store_key] = history
        scores = [h["score"] for h in history]; n_confirmed = sum(1 for s in scores if s >= 2)
        persistence = n_confirmed / len(scores) if scores else 0.0
        confirmed_score = raw_score if (raw_score < 2 or persistence >= cfg["threshold"]) else max(0, raw_score - 1)
        n_days_tracked = len(scores); enough_history = n_days_tracked >= cfg["window"]
        return {"history": scores, "persistence_pct": persistence * 100, "confirmed_score": confirmed_score,
                "persistence_window": cfg["window"], "persistence_threshold_pct": cfg["threshold"] * 100,
                "n_days_tracked": n_days_tracked, "enough_history": enough_history}
    def compute_all(self, weights):
        confirmed = {}
        for k, engine in self.engines.items():
            res = engine.compute(); persist = self._update_persistence(k, res["score"])
            confirmed[k] = {**res, **persist, "reduction_pct": self.REDUCTION_MAP[persist["confirmed_score"]] * 100}
        sum_w = sum(weights.get(k, 0) for k in confirmed) or 1.0
        rsg_raw = sum(weights.get(k, 0) * confirmed[k]["confirmed_score"] for k in confirmed)
        rsg_q = sum(weights.get(k, 0) * confirmed[k]["confirmed_score"] * confirmed[k]["dq"] for k in confirmed) / sum_w
        def regime_of(rsg):
            if rsg < 0.70: return ("Normal", "#22C55E")
            elif rsg < 1.50: return ("Vigilance", "#F97316")
            elif rsg < 2.30: return ("Risque élevé", "#F97316")
            else: return ("Stress systémique", "#FF3131")
        regime_raw = regime_of(rsg_raw)
        return {"per_etf": confirmed, "rsg_raw": rsg_raw, "rsg_quality_weighted": rsg_q,
                "regime_label": regime_raw[0], "regime_color": regime_raw[1]}

# =============================================================================
# MODULE 29 : RISK ENGINE V7.1 — VALIDATION HISTORIQUE
# =============================================================================
RISK_HORIZONS = [5, 10, 20, 60]
KEY_PERSISTENCE_CONFIG = PERSISTENCE_CONFIG

def _forward_min_exclusive(series, window):
    shifted = series.shift(-1); rev = shifted.iloc[::-1]
    m = rev.rolling(window, min_periods=window).min()
    return m.iloc[::-1]

def compute_forward_stats(price, horizons=RISK_HORIZONS):
    out = {}
    for h in horizons:
        out[f"fwd_ret_{h}"] = price.shift(-h) / price - 1
        fwd_min = _forward_min_exclusive(price, h); out[f"fwd_mdd_{h}"] = fwd_min / price - 1
    return pd.DataFrame(out, index=price.index)

def apply_persistence(raw_score, window, threshold):
    confirmed_flag = (raw_score >= 2).rolling(window, min_periods=1).mean() >= threshold
    confirmed = raw_score.copy()
    downgrade_mask = (raw_score >= 2) & (~confirmed_flag)
    confirmed[downgrade_mask] = (raw_score[downgrade_mask] - 1).clip(lower=0)
    return confirmed

def compute_conditional_stats(score_confirmed, price):
    common = score_confirmed.index.intersection(price.index)
    if len(common) < 100: return pd.DataFrame()
    score_c = score_confirmed.loc[common]; price_c = price.loc[common]
    fwd = compute_forward_stats(price_c)
    df = pd.concat([score_c.rename("score"), fwd], axis=1).dropna(subset=["score"])
    rows = []
    for s in [0, 1, 2, 3]:
        sub = df[df["score"] == s]
        for h in RISK_HORIZONS:
            ret_col = sub[f"fwd_ret_{h}"].dropna(); mdd_col = sub[f"fwd_mdd_{h}"].dropna()
            if len(mdd_col) == 0: continue
            rows.append({"score": s, "horizon": h, "n": len(mdd_col),
                         "ret_mean": ret_col.mean(), "ret_median": ret_col.median(),
                         "ret_p05": ret_col.quantile(.05), "ret_p25": ret_col.quantile(.25),
                         "ret_p75": ret_col.quantile(.75), "ret_p95": ret_col.quantile(.95),
                         "mdd_mean": mdd_col.mean(), "mdd_median": mdd_col.median(),
                         "mdd_p05": mdd_col.quantile(.05),
                         "prob_mdd_lt_5": (mdd_col < -0.05).mean(), "prob_mdd_lt_10": (mdd_col < -0.10).mean()})
    return pd.DataFrame(rows)

def format_conditional_stats(stats_df):
    if stats_df.empty: return pd.DataFrame()
    def confidence_label(n):
        if n < 30: return "🔴 Très faible (n<30)"
        elif n < 100: return "🟠 Faible (n<100)"
        elif n < 300: return "🟡 Correcte"
        else: return "🟢 Bonne"
    out = pd.DataFrame()
    out["Score"] = stats_df["score"].map(lambda s: f"{s}/3")
    out["Horizon (j)"] = stats_df["horizon"]
    out["N"] = stats_df["n"]
    out["Fiabilité statistique"] = stats_df["n"].map(confidence_label)
    out["Rendement moyen"] = stats_df["ret_mean"].map(lambda v: f"{v*100:+.2f}%")
    out["Rendement médian"] = stats_df["ret_median"].map(lambda v: f"{v*100:+.2f}%")
    out["Rendement P05"] = stats_df["ret_p05"].map(lambda v: f"{v*100:+.2f}%")
    out["Rendement P95"] = stats_df["ret_p95"].map(lambda v: f"{v*100:+.2f}%")
    out["MDD moyen"] = stats_df["mdd_mean"].map(lambda v: f"{v*100:.2f}%")
    out["MDD médian"] = stats_df["mdd_median"].map(lambda v: f"{v*100:.2f}%")
    out["MDD P05 (pire 5%)"] = stats_df["mdd_p05"].map(lambda v: f"{v*100:.2f}%")
    out["P(MDD<-5%)"] = stats_df["prob_mdd_lt_5"].map(lambda v: f"{v*100:.0f}%")
    out["P(MDD<-10%)"] = stats_df["prob_mdd_lt_10"].map(lambda v: f"{v*100:.0f}%")
    return out

def compute_korea_score_series(dm):
    krw_usd = dm.data.get("KRW=X", pd.DataFrame()); krw_etf = dm.data.get("KRW.PA", pd.DataFrame())
    samsung = dm.data.get("005930.KS", pd.DataFrame()); hynix = dm.data.get("000660.KS", pd.DataFrame())
    if krw_etf.empty or "Close" not in krw_etf.columns: return pd.Series(dtype=int)
    idx = krw_etf["Close"].dropna().index
    credit_signal = pd.Series(False, index=idx)
    if not krw_usd.empty and "Close" in krw_usd.columns:
        c = krw_usd["Close"].dropna(); ret = c.pct_change()
        vol20 = ret.rolling(20).std() * np.sqrt(252)
        pctile = vol20.rolling(min(len(vol20), 1500), min_periods=250).rank(pct=True) * 100
        delta4w = vol20 - vol20.shift(20); sig = (pctile >= 75) & (delta4w > 0)
        credit_signal = sig.reindex(idx).ffill().fillna(False)
    us_cyclical_signal = pd.Series(False, index=idx)
    yoy_series, _ = fetch_us_cyclical_proxy()
    if not yoy_series.empty:
        yoy_now = yoy_series.reindex(idx, method="ffill"); yoy_3m_ago = yoy_series.shift(3).reindex(idx, method="ffill")
        us_cyclical_signal = ((yoy_now < 0) | ((yoy_now - yoy_3m_ago) < -2.0)).fillna(False)
    macro_alert = credit_signal | us_cyclical_signal
    close_k = krw_etf["Close"].dropna(); ret_k = close_k.pct_change()
    vol2w = ret_k.rolling(10).std() * np.sqrt(252); vol2w_prev = vol2w.shift(20)
    vol_confirm = ((vol2w / vol2w_prev - 1) > 0.15).reindex(idx).fillna(False)
    def below_sma50(df):
        if df.empty or "Close" not in df.columns: return pd.Series(False, index=idx)
        c = df["Close"].dropna(); s = c < c.rolling(50).mean()
        return s.reindex(idx, method="ffill").fillna(False)
    samsung_below = below_sma50(samsung); hynix_below = below_sma50(hynix)
    full_confirm = vol_confirm & samsung_below & hynix_below
    score = pd.Series(0, index=idx)
    score[macro_alert & ~full_confirm] = 1; score[macro_alert & full_confirm] = 2
    return score

def compute_semi_score_series(dm):
    chip = dm.data.get("CHIP.PA", pd.DataFrame())
    if chip.empty or "Close" not in chip.columns: return pd.Series(dtype=int)
    close_chip = chip["Close"].dropna(); idx = close_chip.index
    above_frames = []
    for tk in SOX_COMPONENTS_PROXY:
        df = dm.data.get(tk, pd.DataFrame())
        if df.empty or "Close" not in df.columns: continue
        c = df["Close"].dropna(); above = (c > c.rolling(50).mean()).reindex(idx, method="ffill")
        above_frames.append(above.rename(tk))
    if not above_frames: return pd.Series(0, index=idx)
    breadth = pd.concat(above_frames, axis=1).mean(axis=1) * 100
    sma50_chip = close_chip.rolling(50).mean(); phlx_below = close_chip < sma50_chip
    ret = close_chip.pct_change(); vol20 = ret.rolling(20).std() * np.sqrt(252)
    vol_pctile = vol20.rolling(min(len(vol20), 1500), min_periods=250).rank(pct=True) * 100; vol_extreme = vol_pctile >= 90
    score = pd.Series(0, index=idx)
    score[(breadth < 40)] = 1; score[(breadth < 20) & phlx_below] = 2; score[(breadth < 10) & phlx_below & vol_extreme] = 3
    return score

def compute_world_score_series(dm):
    vix = dm.data.get("^VIX", pd.DataFrame()); vix3m = dm.data.get("^VIX3M", pd.DataFrame())
    if vix.empty or vix3m.empty: return pd.Series(dtype=int)
    v = vix["Close"].dropna(); v3 = vix3m["Close"].dropna()
    idx = v.index.intersection(v3.index); v, v3 = v.loc[idx], v3.loc[idx]
    tss = (v3 - v) / v; backward_3d = (tss < 0).rolling(3).sum() == 3
    score = pd.Series(0, index=idx)
    score[(tss >= 0) & (tss <= TSS_NEUTRAL_MAX)] = 1; score[backward_3d] = 2
    score[(tss < TSS_BACKWARD_STRESS) & (v > VIX_STRESS_LEVEL)] = 3
    return score

def compute_value_score_series(dm):
    oas = fetch_fred_series("BAMLH0A0HYM2")
    if oas.empty: return pd.Series(dtype=int)
    ma60 = oas.rolling(60).mean(); d4w = oas - oas.shift(20)
    pctile = oas.rolling(min(len(oas), 2500), min_periods=250).rank(pct=True) * 100
    score = pd.Series(0, index=oas.index)
    score[(oas > ma60) & (pctile >= 70)] = 1; score[(oas > 5.0) & (d4w > 0.5)] = 2; score[(oas > 6.0)] = 3
    return score

class RiskEngineV71Backtester:
    ETF_PROXY = {"korea": "KRW.PA", "semi": "CHIP.PA", "world": "MWRD.PA", "value": "WMMS.DE"}
    SCORE_FUNCS = {"korea": compute_korea_score_series, "semi": compute_semi_score_series, "world": compute_world_score_series, "value": compute_value_score_series}
    def __init__(self, dm): self.dm = dm
    def run(self, key):
        raw_score = self.SCORE_FUNCS[key](self.dm)
        if raw_score.empty: return {"available": False, "reason": "Données insuffisantes"}
        cfg = KEY_PERSISTENCE_CONFIG[key]
        confirmed = apply_persistence(raw_score, window=cfg["window"], threshold=cfg["threshold"])
        proxy_tk = self.ETF_PROXY[key]
        df_price = self.dm.data.get(proxy_tk, pd.DataFrame())
        if df_price.empty and key == "world":
            for wt in WORLD_TICKERS:
                df_price = self.dm.data.get(wt, pd.DataFrame())
                if not df_price.empty: break
        if df_price.empty or "Close" not in df_price.columns: return {"available": False, "reason": f"Prix {proxy_tk} indisponible"}
        price = df_price["Close"].dropna()
        stats_numeric = compute_conditional_stats(confirmed, price)
        if stats_numeric.empty: return {"available": False, "reason": "Échantillon insuffisant"}
        return {"available": True, "stats_numeric": stats_numeric, "stats_display": format_conditional_stats(stats_numeric), "n_days": len(confirmed)}

@st.cache_data(ttl=21600, show_spinner=False)
def _cached_conditional_stats(_dm, key, cache_key):
    raw_score = RiskEngineV71Backtester.SCORE_FUNCS[key](_dm)
    if raw_score.empty: return pd.DataFrame()
    cfg = KEY_PERSISTENCE_CONFIG[key]
    confirmed = apply_persistence(raw_score, window=cfg["window"], threshold=cfg["threshold"])
    proxy_tk = RiskEngineV71Backtester.ETF_PROXY[key]
    df_price = _dm.data.get(proxy_tk, pd.DataFrame())
    if df_price.empty and key == "world":
        for wt in WORLD_TICKERS:
            df_price = _dm.data.get(wt, pd.DataFrame())
            if not df_price.empty: break
    if df_price.empty or "Close" not in df_price.columns: return pd.DataFrame()
    price = df_price["Close"].dropna()
    return compute_conditional_stats(confirmed, price)

# =============================================================================
# MODULE 30 : OPTIMISATION DE LA RÉDUCTION
# =============================================================================
REDUCTION_GRID = [0, 10, 15, 20, 25, 30, 40, 50]

def compute_eal(reduction_pct, expected_mdd_pct): return (reduction_pct / 100.0) * abs(expected_mdd_pct)

class ReductionOptimizer:
    def __init__(self, dm): self.dm = dm
    def run_for_engine(self, key, trigger_score=2):
        score_func = RiskEngineV71Backtester.SCORE_FUNCS[key]
        raw_score = score_func(self.dm)
        if raw_score.empty: return {"available": False, "reason": "Série indisponible"}
        cfg = KEY_PERSISTENCE_CONFIG[key]
        confirmed = apply_persistence(raw_score, window=cfg["window"], threshold=cfg["threshold"])
        proxy_tk = RiskEngineV71Backtester.ETF_PROXY[key]
        df_price = self.dm.data.get(proxy_tk, pd.DataFrame())
        if df_price.empty and key == "world":
            for wt in WORLD_TICKERS:
                df_price = self.dm.data.get(wt, pd.DataFrame())
                if not df_price.empty: break
        if df_price.empty or "Close" not in df_price.columns: return {"available": False, "reason": f"Prix indisponible"}
        price = df_price["Close"]; common = confirmed.index.intersection(price.index)
        if len(common) < 300: return {"available": False, "reason": "Historique insuffisant"}
        confirmed = confirmed.loc[common]; price = price.loc[common]
        ret = price.pct_change().fillna(0); active = (confirmed >= trigger_score).astype(float)
        buyhold_metrics = self._metrics(ret); rows = []
        for R in REDUCTION_GRID:
            weight = (1.0 - (R / 100.0) * active).shift(1).fillna(1.0)
            strat_ret = ret * weight; m = self._metrics(strat_ret)
            turnover = float(weight.diff().abs().sum()); n_episodes = int((active.diff() == 1).sum())
            rows.append({"Réduction": f"{R}%",
                         "CAGR (%)": round(m["cagr_pct"], 2) if not np.isnan(m["cagr_pct"]) else None,
                         "Max Drawdown (%)": round(m["max_dd_pct"], 2) if not np.isnan(m["max_dd_pct"]) else None,
                         "Sharpe": round(m["sharpe"], 2) if not np.isnan(m["sharpe"]) else None,
                         "Calmar": round(m["calmar"], 2) if not np.isnan(m["calmar"]) else None,
                         "Turnover": round(turnover, 1), "N épisodes signal": n_episodes,
                         "Alpha vs Buy&Hold (CAGR pts)": round(m["cagr_pct"] - buyhold_metrics["cagr_pct"], 2) if not (np.isnan(m["cagr_pct"]) or np.isnan(buyhold_metrics["cagr_pct"])) else None})
        df_grid = pd.DataFrame(rows)
        n_signal_days = int(active.sum()); MIN_N_TRUST = 50
        valid = df_grid.dropna(subset=["Calmar"])
        best_reduction = valid.loc[valid["Calmar"].idxmax(), "Réduction"] if not valid.empty else "N/A"
        reliable = n_signal_days >= MIN_N_TRUST
        return {"available": True, "grid": df_grid, "buyhold": buyhold_metrics, "best_reduction_by_calmar": best_reduction,
                "n_days": len(common), "n_signal_days": n_signal_days, "reliable": reliable, "trigger_score": trigger_score}
    def _metrics(self, ret):
        equity = (1 + ret).cumprod(); n = len(ret)
        if n < 30 or equity.iloc[-1] <= 0: return {"cagr_pct": np.nan, "max_dd_pct": np.nan, "sharpe": np.nan, "calmar": np.nan}
        years = n / 252; cagr = equity.iloc[-1] ** (1 / years) - 1
        vol = ret.std() * np.sqrt(252); rmax = equity.cummax(); dd = equity / rmax - 1; max_dd = dd.min()
        sharpe = (cagr - 0.025) / vol if vol > 0 else np.nan
        calmar = cagr / abs(max_dd) if max_dd != 0 else np.nan
        return {"cagr_pct": cagr * 100, "max_dd_pct": max_dd * 100, "sharpe": sharpe, "calmar": calmar}

# =============================================================================
# MODULE 31 : GLOSSAIRES PÉDAGOGIQUES
# =============================================================================
RISK_ENGINE_GLOSSARY = """
**Comment lire cette page si vous découvrez l'outil :**

- **SR (Score de Risque, 0 à 3)** : note de "météo" par famille d'ETF.
- **Persistance** : le signal doit se répéter plusieurs jours de suite.
- **DQ (Qualité des Données)** : fiabilité des données sous-jacentes.
- **MDD futur** : pire baisse observée après ce type de signal.
- **EAL** : économie potentielle de la réduction.
"""

BACKTEST_GLOSSARY = """
### 📖 Comment lire cette section ?

#### 🔄 Walk-Forward
Le modèle apprend sur les données passées puis est testé sur des données futures
qu'il n'a jamais vues.

#### 🤖 Ridge
Modèle statistique utilisé pour prévoir l'alpha futur. Horizon : 20 jours ouvrés.

#### 🟦 Baseline
Modèle de référence simple. Si Ridge ne fait pas mieux, l'app refuse de lui faire confiance.

#### 🎯 Hit Rate
% de fois où le modèle prévoit correctement la DIRECTION. 50% = hasard. 55% = début d'avantage.

#### 📐 Corrélation
Mesure si les prédictions évoluent dans le même sens que les résultats observés (-1 à +1).
⚠️ Une corrélation positive faible ne signifie pas que le modèle est fiable.

#### 📏 MAE — Mean Absolute Error
Erreur absolue moyenne. Mesure de combien la prédiction se trompe en moyenne.
**Plus le MAE est faible, mieux c'est.**

### 🟢 La bonne décision
Ridge est exploitable seulement si :
- Hit Rate ≥ 55%
- avantage directionnel ≥ 5 points
- corrélation > 0,05
- MAE au moins 5% meilleur que la Baseline
"""

RISK_ENGINE_MDD_GLOSSARY = """
**"MDD médian : -3.05% · MDD P05 : -13.67%"**

MDD = pire chute entre un jour et les 20 jours suivants.
- **MDD médian** : baisse "typique" après ce type de signal.
- **MDD P05 (pire 5%)** : dans les 5% des pires cas.
- **P(MDD<-5%)** : sur 100 fois, combien ont dépassé 5%.
"""

RSG_GLOSSARY = """
### 🛡 Comment lire le Risk Engine v7.1 ?

Le Risk Engine ne cherche pas à prédire le rendement futur.
Il répond à : **"Le risque de baisse justifie-t-il une réduction ?"**

## 🌡 RSG brut
Score global entre 0 et 3 combinant les poches pondérées.
| RSG | Situation |
|---:|---|
| 0 à <0,70 | 🟢 Normal |
| 0,70 à <1,50 | 🟠 Vigilance |
| 1,50 à <2,30 | 🟠 Risque élevé |
| ≥2,30 | 🔴 Stress systémique |

⚠️ Le RSG n'est PAS une probabilité de baisse.

## 🎯 SR /3
- SR 0/3 = risque faible
- SR 1/3 = vigilance
- SR 2/3 = risque élevé
- SR 3/3 = stress important

Le SR ne doit PAS être utilisé seul : combiner avec persistance, DQ, poids, RSG, validation.

## ⏳ Persistance
Combien de temps le signal reste présent.

## 🧪 DQ
Fiabilité des données (DQ 90% = solide, DQ 45% = incertain).
"""

VALIDATION_SECTION_GLOSSARY = """
## 🧪 Comment utiliser la Validation historique ?

**"Lorsque ce niveau de risque est apparu, que s'est-il passé ensuite ?"**

### 🎯 SR 0/1/2/3
- SR 0 : aucun signal
- SR 1 : vigilance
- SR 2 : risque élevé
- SR 3 : stress important

### 📊 À regarder
**1. Nombre de signaux** : <30 fragile, 30-100 indicatif, >100 intéressant.
**2. MDD médian** : baisse typique observée.
**3. MDD P05** : pire 5% historique.
**4. P(MDD<-5%)** : fréquence historique de baisse >5%.

### 🧭 Décision
1. SR actuel · 2. Persistance · 3. DQ · 4. Nombre d'occurrences
5. MDD médian · 6. P(MDD<-5%) · 7. RSG · 8. Poids de la poche

### Exemple
SR=3/3 mais 12 occurrences → ❌ pas de réduction automatique.
SR=3/3 + 120 occurrences + P élevée + MDD médian négatif + persistant → 🟠/🔴.
"""

OPTIMIZATION_SECTION_GLOSSARY = """
## 🎯 Comment utiliser "Optimisation de la réduction" ?

**"Quelle réduction aurait historiquement donné le meilleur compromis ?"**

### 🔢 Niveaux testés
0%, 10%, 15%, 20%, 25%, 30%, 40%, 50%

### 📈 Trois chiffres
**CAGR** : rendement annuel composé.
**MaxDD** : pire baisse historique.
**Calmar** = CAGR / |MaxDD|.

### 🧭 Comment choisir
🟢 Buy&Hold supérieur → conserver
🟡 10-20% réduit MaxDD sans sacrifier CAGR → réduction légère
🟠 25-30% améliore nettement → réduction intermédiaire
🔴 40-50% seulement si SR3 + échantillon suffisant + baisse historique importante

⚠️ Attention au sur-ajustement. Préférer une zone robuste (25-30%) plutôt qu'optimiser au %.

### 🧠 Ordre de priorité
1. Strategic Decision Engine · 2. RSG/SR · 3. Validation · 4. Optimisation · 5. décision
"""

SLEEVE_GLOSSARY = """
**Pourquoi raisonner par "poche" et pas par ticker ?**

L'optimiseur Markowitz voit 5 lignes. Il calcule DCAM/MWRD corrélés ~1.00 → redondants.
Faux pour vous : DCAM dans PEA, MWRD dans AV.
Deux enveloppes fiscales, un seul pari World.

**Poches :**
- **World Core** (DCAM + MWRD) = socle
- **World Value** (WMMS) = pari actif Value
- **Satellites** (Korea + CHIP) = paris concentrés plafonnés à 35%
"""

STRATEGIC_DECISION_GLOSSARY = """
**V8 — Décision par poche, pas par ETF**

Hiérarchie :
1. **Est-ce que ma stratégie active apporte de l'alpha vs World ?**
2. Si oui, **quelle poche mérite plus de capital ?**
3. Si non, **dois-je commencer la sortie vers 100% World ?**

**Kill Switch** : quand plusieurs signaux montrent que l'avantage disparaît,
l'app prépare le retour vers 100% World.
"""

def render_glossary_expander(glossary=None, title="📖 Je découvre l'outil", expanded=False):
    if glossary is None: glossary = RISK_ENGINE_GLOSSARY
    with st.expander(title, expanded=expanded): st.markdown(glossary)

# =============================================================================
# MODULE 32 : POCHES STRATÉGIQUES
# =============================================================================
STRATEGIC_SLEEVES = {
    "world_core": {"label": "🌍 Poche World (Core)", "tickers": WORLD_CORE_TICKERS,
                   "explain": "DCAM + MWRD = même pari World dans 2 enveloppes fiscales."},
    "world_value_tilt": {"label": "💎 Poche World Value", "tickers": WORLD_VALUE_TICKERS,
                         "explain": "Surpondération active du style Value."},
    "satellites_boost": {"label": "🚀 Poche Satellites", "tickers": SATELLITE_TICKERS,
                         "explain": "Paris concentrés plafonnés à 35%."},
}

def get_sleeve_of(ticker):
    for key, sleeve in STRATEGIC_SLEEVES.items():
        if ticker in sleeve["tickers"]: return key
    return None

class SleeveAnalysisEngine:
    def __init__(self, dm, qre): self.dm = dm; self.qre = qre
    def compute_sleeve_weights(self, ptf):
        vt = ptf["valeur_totale"]
        if vt <= 0: return {}
        def value_of(tickers): return sum(p["valeur"] for p in ptf["positions"] if p.get("ticker") in tickers)
        world_value = value_of(WORLD_CORE_TICKERS); value_value = value_of(WORLD_VALUE_TICKERS)
        korea_value = value_of(["KRW.PA"]); semi_value = value_of(["CHIP.PA"])
        return {
            "world_core": {"label": "🌍 World Core", "valeur": world_value, "pct": world_value / vt * 100,
                           "tickers": WORLD_CORE_TICKERS, "locked": True, "explain": "DCAM + MWRD = 1 exposition World."},
            "world_value_tilt": {"label": "💎 World Value", "valeur": value_value, "pct": value_value / vt * 100,
                                 "tickers": WORLD_VALUE_TICKERS, "locked": False, "explain": "Surpondération Value."},
            "korea": {"label": "🇰🇷 Korea", "valeur": korea_value, "pct": korea_value / vt * 100,
                      "tickers": ["KRW.PA"], "locked": False, "explain": "Satellite tactique."},
            "semiconductor": {"label": "🔬 Semiconductor", "valeur": semi_value, "pct": semi_value / vt * 100,
                              "tickers": ["CHIP.PA"], "locked": False, "explain": "Satellite tactique."},
            "satellites_boost": {"label": "🚀 Satellites", "valeur": korea_value + semi_value,
                                 "pct": (korea_value + semi_value) / vt * 100, "tickers": SATELLITE_TICKERS,
                                 "locked": False, "explain": "Budget plafonné à 35%."},
        }
    def analyze_world_value_tilt(self):
        world = get_world_series(self.dm); wmms = self.dm.data.get("WMMS.DE", pd.DataFrame())
        if world is None or world.empty or wmms is None or wmms.empty or "Close" not in wmms.columns:
            return {"available": False, "reason": "Données indisponibles"}
        world_close = world["Close"] if isinstance(world, pd.DataFrame) else world
        value_close = wmms["Close"]
        common = world_close.index.intersection(value_close.index).sort_values()
        if len(common) < 300: return {"available": False, "reason": "Historique insuffisant"}
        w = world_close.loc[common].astype(float); v = value_close.loc[common].astype(float)
        ratio = v / w
        horizons = {"20d": 20, "60d": 60, "3m": 63, "6m": 126, "12m": 252, "3y": 756, "5y": 1260}
        rel = {}
        for label, n in horizons.items():
            if len(common) > n: rel[label] = float((v.iloc[-1] / v.iloc[-n-1] - 1) - (w.iloc[-1] / w.iloc[-n-1] - 1))
            else: rel[label] = None
        ratio_sma20 = ratio.rolling(20).mean(); ratio_sma60 = ratio.rolling(60).mean(); ratio_sma200 = ratio.rolling(200).mean()
        ratio_now = float(ratio.iloc[-1])
        above_sma20 = ratio_now > float(ratio_sma20.iloc[-1])
        above_sma60 = ratio_now > float(ratio_sma60.iloc[-1])
        above_sma200 = ratio_now > float(ratio_sma200.iloc[-1])
        daily_rel = (v.pct_change() - w.pct_change()).dropna()
        persistence_20 = float((daily_rel.tail(20) > 0).mean()) if len(daily_rel) >= 20 else None
        persistence_60 = float((daily_rel.tail(60) > 0).mean()) if len(daily_rel) >= 60 else None
        score = 0; reasons = []
        if rel["20d"] is not None:
            if rel["20d"] > 0.015: score += 1; reasons.append("Value surperforme 20j")
            elif rel["20d"] < -0.015: score -= 1; reasons.append("Value sous-performe 20j")
        if rel["3m"] is not None:
            if rel["3m"] > RELATIVE_STRONG: score += 1; reasons.append("Value surperforme 3m")
            elif rel["3m"] < RELATIVE_WEAK: score -= 1; reasons.append("Value sous-performe 3m")
        if rel["6m"] is not None:
            if rel["6m"] > RELATIVE_STRONG: score += 1
            elif rel["6m"] < RELATIVE_WEAK: score -= 1
        if rel["12m"] is not None:
            if rel["12m"] > RELATIVE_STRONG: score += 1
            elif rel["12m"] < RELATIVE_WEAK: score -= 1
        if above_sma20: score += 1
        else: score -= 1
        if above_sma200: score += 1
        else: score -= 1
        if persistence_60 is not None:
            if persistence_60 >= 0.55: score += 1
            elif persistence_60 <= 0.45: score -= 1
        score = int(max(-7, min(7, score)))
        if score >= 5: regime = "VALUE_STRONGLY_DOMINANT"
        elif score >= 3: regime = "VALUE_DOMINANT"
        elif score >= 1: regime = "VALUE_DOMINANT_SLOWING"
        elif score <= -5: regime = "WORLD_LEADERSHIP_CONFIRMED"
        elif score <= -3: regime = "VALUE_INVERSION"
        else: regime = "TRANSITION"
        verdicts = {
            "VALUE_STRONGLY_DOMINANT": "Value structurellement dominant.",
            "VALUE_DOMINANT": "Value conserve son avantage.",
            "VALUE_DOMINANT_SLOWING": "Value ralentit. Conserver et surveiller.",
            "TRANSITION": "Transition. Aucune modification.",
            "VALUE_INVERSION": "Value sous-performe. Réduction envisageable si persiste.",
            "WORLD_LEADERSHIP_CONFIRMED": "World domine. Réduction de la surpondération Value.",
        }
        return {"available": True, "score": score, "regime": regime, "verdict": verdicts.get(regime, ""),
                "relative_performance": rel, "ratio": ratio_now, "above_sma20": above_sma20,
                "above_sma60": above_sma60, "above_sma200": above_sma200,
                "persistence_20d": persistence_20, "persistence_60d": persistence_60, "reasons": reasons}

    def analyze_semiconductor_thesis(self):
        krw = self.dm.data.get("KRW.PA", pd.DataFrame()); chip = self.dm.data.get("CHIP.PA", pd.DataFrame())
        if (krw is None or krw.empty or chip is None or chip.empty or "Close" not in krw.columns or "Close" not in chip.columns):
            return {"available": False, "reason": "Données indisponibles"}
        k = krw["Close"].dropna(); c = chip["Close"].dropna()
        common = k.index.intersection(c.index).sort_values()
        if len(common) < 300: return {"available": False, "reason": "Historique insuffisant"}
        k = k.loc[common]; c = c.loc[common]
        horizons = {"20d": 20, "60d": 60, "3m": 63, "6m": 126, "12m": 252}
        gap = {}
        for label, n in horizons.items():
            if len(common) > n: gap[label] = float((c.iloc[-1] / c.iloc[-n-1] - 1) - (k.iloc[-1] / k.iloc[-n-1] - 1))
            else: gap[label] = None
        ratio = c / k; sma20 = ratio.rolling(20).mean(); sma60 = ratio.rolling(60).mean(); sma200 = ratio.rolling(200).mean()
        ratio_now = float(ratio.iloc[-1])
        ratio_above20 = ratio_now > float(sma20.iloc[-1])
        ratio_above60 = ratio_now > float(sma60.iloc[-1])
        ratio_above200 = ratio_now > float(sma200.iloc[-1])
        ratio_ret20 = (ratio.iloc[-1] / ratio.iloc[-21] - 1) if len(ratio) > 21 else None
        ratio_ret60 = (ratio.iloc[-1] / ratio.iloc[-61] - 1) if len(ratio) > 61 else None
        daily_relative = (c.pct_change() - k.pct_change()).dropna()
        persistence_20 = float((daily_relative.tail(20) > 0).mean()) if len(daily_relative) >= 20 else None
        persistence_60 = float((daily_relative.tail(60) > 0).mean()) if len(daily_relative) >= 60 else None
        score = 0; reasons = []
        if gap["6m"] is not None:
            if gap["6m"] < -0.05: score += 1; reasons.append("Retard Semi 6 mois")
            elif gap["6m"] > 0.03: score -= 1; reasons.append("Semi a rattrapé Korea")
        if gap["20d"] is not None:
            if gap["20d"] > 0.02: score += 2; reasons.append("Rattrapage 20 jours")
            elif gap["20d"] < -0.02: score -= 2; reasons.append("Retard s'aggrave")
        if ratio_above20: score += 1
        else: score -= 1
        if ratio_above60: score += 1
        if ratio_ret20 is not None and ratio_ret20 > 0: score += 1
        elif ratio_ret20 is not None and ratio_ret20 < 0: score -= 1
        if persistence_20 is not None:
            if persistence_20 >= 0.60: score += 1
            elif persistence_20 <= 0.40: score -= 1
        score = int(max(-7, min(7, score)))
        if (gap["6m"] is not None and gap["6m"] < -0.05 and gap["20d"] is not None and gap["20d"] > 0.02
            and ratio_above20 and persistence_20 is not None and persistence_20 >= 0.55):
            thesis = "CATCHUP_CONFIRMED"
        elif (gap["6m"] is not None and gap["6m"] < -0.05 and gap["20d"] is not None and gap["20d"] > 0):
            thesis = "CATCHUP_EARLY"
        elif (gap["6m"] is not None and gap["6m"] < -0.05 and gap["20d"] is not None and gap["20d"] < -0.02):
            thesis = "THESIS_WEAKENING"
        elif (gap["6m"] is not None and gap["6m"] > 0.03): thesis = "THESIS_COMPLETED"
        else: thesis = "NEUTRAL"
        verdicts = {
            "CATCHUP_CONFIRMED": "Rattrapage confirmé.",
            "CATCHUP_EARLY": "Début de rattrapage.",
            "THESIS_WEAKENING": "Retard s'aggrave. Thèse affaiblie.",
            "THESIS_COMPLETED": "Rattrapage déjà effectué.",
            "NEUTRAL": "Pas de confirmation.",
        }
        world_score = 0
        if gap["3m"] is not None: world_score += 1 if gap["3m"] > 0 else -1
        if gap["6m"] is not None: world_score += 1 if gap["6m"] > 0 else -1
        if gap["12m"] is not None: world_score += 1 if gap["12m"] > 0 else -1
        world_regime = "SURPERFORME_WORLD" if world_score >= 1 else "SOUS_PERFORME_WORLD" if world_score <= -1 else "NEUTRE_WORLD"
        return {"available": True, "score": score, "thesis": thesis, "verdict": verdicts.get(thesis, ""),
                "gap": gap, "ratio": ratio_now, "ratio_ret20": ratio_ret20, "ratio_ret60": ratio_ret60,
                "ratio_above20": ratio_above20, "ratio_above60": ratio_above60, "ratio_above200": ratio_above200,
                "persistence_20d": persistence_20, "persistence_60d": persistence_60, "reasons": reasons,
                "world_score": world_score, "world_regime": world_regime}

# =============================================================================
# MODULE 32bis : ANALYSE SEMICONDUCTOR VS WORLD
# =============================================================================
def compute_semiconductor_relative_analysis(semi_series, world_series, korea_series=None):
    result = {"benchmark_primary": "MSCI World", "benchmark_secondary": "Korea", "vs_world": {}, "vs_korea": {}}
    semi_series = semi_series.dropna(); world_series = world_series.dropna()
    common = semi_series.index.intersection(world_series.index)
    if len(common) < 60:
        result["available"] = False; result["reason"] = "Historique commun insuffisant."
        return result
    semi = semi_series.loc[common]; world = world_series.loc[common]
    horizons = {"20d": 20, "60d": 60, "3m": 63, "6m": 126, "12m": 252}
    for label, n in horizons.items():
        if len(semi) <= n: result["vs_world"][label] = np.nan; continue
        semi_perf = semi.iloc[-1] / semi.iloc[-n-1] - 1
        world_perf = world.iloc[-1] / world.iloc[-n-1] - 1
        result["vs_world"][label] = float(semi_perf - world_perf)
    ratio_world = semi / world
    ratio_ma20 = ratio_world.rolling(20).mean(); ratio_ma60 = ratio_world.rolling(60).mean()
    result["vs_world"]["ratio_above_ma20"] = bool(ratio_world.iloc[-1] > ratio_ma20.iloc[-1])
    result["vs_world"]["ratio_above_ma60"] = bool(ratio_world.iloc[-1] > ratio_ma60.iloc[-1])
    if korea_series is not None and not korea_series.empty:
        common_k = semi_series.index.intersection(korea_series.index)
        if len(common_k) >= 60:
            semi_k = semi_series.loc[common_k]; korea_k = korea_series.loc[common_k]
            for label, n in horizons.items():
                if len(semi_k) <= n: result["vs_korea"][label] = np.nan; continue
                semi_perf = semi_k.iloc[-1] / semi_k.iloc[-n-1] - 1
                korea_perf = korea_k.iloc[-1] / korea_k.iloc[-n-1] - 1
                result["vs_korea"][label] = float(semi_perf - korea_perf)
    result["available"] = True
    return result

# =============================================================================
# MODULE 32ter : STRATEGIC DECISION ENGINE
# =============================================================================
class StrategicDecisionEngine:
    def __init__(self, dm, sae): self.dm = dm; self.sae = sae
    @staticmethod
    def _safe_pct(value, total):
        if total <= 0: return 0.0
        return float(value / total)
    def get_current_sleeves(self, ptf): return self.sae.compute_sleeve_weights(ptf)
    def analyze_korea(self):
        df = self.dm.data.get("KRW.PA", pd.DataFrame()); world = get_world_series(self.dm, exclude_ticker="KRW.PA")
        if (df is None or df.empty or world is None or world.empty or "Close" not in df.columns):
            return {"available": False, "score": 0, "regime": "UNKNOWN"}
        k = df["Close"].dropna(); w = world.dropna()
        common = k.index.intersection(w.index).sort_values()
        if len(common) < 250: return {"available": False, "score": 0, "regime": "UNKNOWN"}
        k = k.loc[common]; w = w.loc[common]
        score = 0; reasons = []
        for n, pts in [(20, 1), (60, 1), (126, 1)]:
            if len(k) > n:
                rel = (k.iloc[-1] / k.iloc[-n-1] - 1) - (w.iloc[-1] / w.iloc[-n-1] - 1)
                if rel > 0.03: score += pts
                elif rel < -0.03: score -= pts
        sma20 = k.rolling(20).mean().iloc[-1]; sma50 = k.rolling(50).mean().iloc[-1]; sma200 = k.rolling(200).mean().iloc[-1]
        price = k.iloc[-1]
        if price > sma20: score += 1; reasons.append("Prix > SMA20")
        else: score -= 1; reasons.append("Prix < SMA20")
        if price > sma200: score += 1
        else: score -= 1
        ret = k.pct_change().dropna()
        vol20 = float(ret.tail(20).std() * np.sqrt(252)) if len(ret) >= 20 else None
        if vol20 is not None:
            if vol20 > 0.50: score -= 1; reasons.append("Volatilité élevée")
            elif vol20 < 0.30: score += 1
        score = int(max(-6, min(6, score)))
        if score >= 4: regime = "STRONG"
        elif score >= 2: regime = "FAVORABLE"
        elif score <= -3: regime = "WEAK"
        else: regime = "NEUTRAL"
        return {"available": True, "score": score, "regime": regime, "vol20": vol20, "reasons": reasons}
    def compute_strategic_risk_weights(self, ptf):
        vt = ptf["valeur_totale"]
        if vt <= 0: return {}
        def value_of(tickers): return sum(p["valeur"] for p in ptf["positions"] if p.get("ticker") in tickers)
        return {"WORLD_CORE": value_of(WORLD_CORE_TICKERS) / vt, "WORLD_VALUE": value_of(WORLD_VALUE_TICKERS) / vt,
                "KOREA": value_of(["KRW.PA"]) / vt, "SEMICONDUCTOR": value_of(["CHIP.PA"]) / vt}
    def compute_exit_to_world_score(self, strategic_result, benchmark_gap):
        score = 0; reasons = []
        if benchmark_gap is not None:
            if benchmark_gap < -0.05: score += 2; reasons.append("Portefeuille derrière World")
            elif benchmark_gap < -0.02: score += 1; reasons.append("Légèrement derrière World")
        value_regime = strategic_result["value"].get("regime")
        if value_regime == "WORLD_LEADERSHIP_CONFIRMED": score += 2; reasons.append("Leadership World confirmé")
        elif value_regime == "VALUE_INVERSION": score += 1; reasons.append("Inversion Value/World")
        korea_score = strategic_result["korea"].get("score", 0)
        if korea_score <= -3: score += 1; reasons.append("Korea dégradé")
        semi_thesis = strategic_result["semiconductor"].get("thesis", "NEUTRAL")
        if semi_thesis == "THESIS_WEAKENING": score += 1; reasons.append("Thèse Semi affaiblie")
        if score >= 5: level = "EXIT_CONFIRMED"
        elif score >= 3: level = "EXIT_PREPARATION"
        elif score >= 2: level = "WATCH"
        else: level = "ACTIVE_STRATEGY"
        return {"score": score, "level": level, "reasons": reasons}
    def compute(self, ptf, benchmark_gap=None):
        sleeves = self.get_current_sleeves(ptf)
        value = self.sae.analyze_world_value_tilt()
        semiconductor = self.sae.analyze_semiconductor_thesis()
        korea = self.analyze_korea()
        satellite_pct = sleeves["satellites_boost"]["pct"] / 100 if "satellites_boost" in sleeves else 0
        world_pct = sleeves.get("world_core", {}).get("pct", 0) / 100
        value_pct = sleeves.get("world_value_tilt", {}).get("pct", 0) / 100
        value_score = value.get("score", 0) if value.get("available") else 0
        semi_score = semiconductor.get("score", 0) if semiconductor.get("available") else 0
        korea_score = korea.get("score", 0)
        satellite_risk = satellite_pct > SATELLITE_MAX
        semi_thesis = semiconductor.get("thesis", "NEUTRAL")
        positive_active = 0; negative_active = 0
        if korea_score >= 3: positive_active += 1
        elif korea_score <= -2: negative_active += 1
        if semi_score >= 2: positive_active += 1
        elif semi_score <= -2: negative_active += 1
        if value_score >= 3: positive_active += 1
        elif value_score <= -3: negative_active += 1
        exit_signals = 0; exit_reasons = []
        if benchmark_gap is not None and benchmark_gap < -0.05:
            exit_signals += 1; exit_reasons.append("Sous-performance significative vs World")
        if value.get("regime") == "WORLD_LEADERSHIP_CONFIRMED":
            exit_signals += 1; exit_reasons.append("Leadership World confirmé")
        if korea_score <= -3 and semi_score <= -2:
            exit_signals += 1; exit_reasons.append("Korea et Semi dégradés")
        if semi_thesis == "THESIS_WEAKENING":
            exit_signals += 1; exit_reasons.append("Thèse Semi affaiblie")
        if satellite_risk:
            action = "REDUCE_SATELLITES"; title = "Réduire les satellites"
            reason = "Plafond 35% dépassé."
        elif exit_signals >= 3:
            action = "EXIT_TO_WORLD"; title = "Préparer le retour vers 100% World"
            reason = "Stratégie active perd son avantage."
        elif value.get("regime") == "WORLD_LEADERSHIP_CONFIRMED":
            action = "REDUCE_VALUE"; title = "Réduire World Value"
            reason = "Inversion World/Value persistante."
        elif (semi_thesis == "CATCHUP_CONFIRMED" and korea_score >= 0 and satellite_pct < SATELLITE_MAX):
            action = "INCREASE_SEMICONDUCTOR"; title = "Renforcer Semiconductor"
            reason = "Thèse de rattrapage confirmée."
        elif (positive_active >= MIN_CONFIRMATIONS and satellite_pct < SATELLITE_MAX):
            action = "MAINTAIN_ACTIVE"; title = "Maintenir la stratégie active"
            reason = "Signaux de régime favorables."
        else:
            action = "MAINTAIN"; title = "Aucune modification"
            reason = (f"{positive_active} signal(aux) positif(s) et {negative_active} négatif(s) sur les 3 poches actives "
                      f"— Value {value_score:+d}, Korea {korea_score:+d}, Semiconductor {semi_score:+d}. "
                      f"Il faut au moins {MIN_CONFIRMATIONS} signaux positifs concordants pour justifier un renforcement : "
                      f"ce seuil n'est pas atteint, donc aucun changement n'est déclenché.")
        exit_to_world = self.compute_exit_to_world_score(
            {"value": value, "korea": korea, "semiconductor": semiconductor}, benchmark_gap)
        return {"action": action, "title": title, "reason": reason,
                "world_core_pct": world_pct, "value_pct": value_pct, "satellite_pct": satellite_pct,
                "value": value, "korea": korea, "semiconductor": semiconductor,
                "positive_active": positive_active, "negative_active": negative_active,
                "exit_signals": exit_signals, "exit_reasons": exit_reasons, "exit_to_world": exit_to_world}

def validate_satellite_budget(ptf):
    vt = ptf["valeur_totale"]
    if vt <= 0: return {"valid": False, "satellite_pct": 0.0, "excess_pct": 0.0, "excess_eur": 0.0}
    satellite_value = sum(p["valeur"] for p in ptf["positions"] if p.get("ticker") in SATELLITE_TICKERS)
    satellite_pct = satellite_value / vt
    return {"valid": satellite_pct <= SATELLITE_MAX, "satellite_pct": satellite_pct,
            "excess_pct": max(0.0, satellite_pct - SATELLITE_MAX),
            "excess_eur": max(0.0, satellite_value - vt * SATELLITE_MAX)}

# -----------------------------------------------------------------------------
# MODULE 15 : VISUALISATIONS
# -----------------------------------------------------------------------------
_PLOTLY_BASE = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#CBD5E1", family="DM Sans"))

def plot_weekly_leadership(labels, portfolio_perfs, world_perfs, portfolio_name="Portefeuille", color_sat=None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=portfolio_perfs, name=portfolio_name,
        text=[f"{v:+.2f}%" for v in portfolio_perfs],
        textposition="outside", texttemplate="%{text}", cliponaxis=False,
        marker_color=["#22C55E" if v >= 0 else "#FF3131" for v in portfolio_perfs],
        hovertemplate="<b>%{x}</b><br>Portefeuille : %{y:+.2f}%<extra></extra>"))
    fig.add_trace(go.Bar(
        x=labels, y=world_perfs, name="MSCI World",
        text=[f"{v:+.2f}%" for v in world_perfs],
        textposition="outside", texttemplate="%{text}", cliponaxis=False,
        marker_color="rgba(59,130,246,.6)",
        hovertemplate="<b>%{x}</b><br>MSCI World : %{y:+.2f}%<extra></extra>"))
    fig.add_hline(y=0, line_dash="dot", line_color="#4B5563")
    fig.update_layout(**_PLOTLY_BASE, barmode="group", height=360,
                      margin=dict(t=45, b=40, l=55, r=30),
                      yaxis=dict(title="Performance (%)", ticksuffix="%", gridcolor="#2E3340", zeroline=False),
                      xaxis=dict(gridcolor="#2E3340"),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
    return fig

def plot_risk_contribution(rc) -> Optional[go.Figure]:
    if not rc: return None
    short = {"WMMS.DE": "WMMS", "MWRD.PA": "World", "DCAM.PA": "W-PEA", "KRW.PA": "Korea", "CHIP.PA": "CHIP"}
    names = [short.get(tk, tk) for tk in rc]
    values = [rc[tk]["rc_pct"] for tk in rc]
    colors = ["#FF3131" if rc[tk]["flag"] else "#007BFF" for tk in rc]
    fig = go.Figure(go.Bar(x=values, y=names, orientation="h", marker_color=colors,
                           hovertemplate="%{y}: <b>%{x:.1f}%</b>"))
    fig.add_vline(x=40, line_dash="dash", line_color="#FF3131",
                  annotation_text="Seuil 40%", annotation_font=dict(color="#FF3131", size=9))
    fig.update_layout(**_PLOTLY_BASE,
        title=dict(text="<b>Risk Contribution (%)</b>", font=dict(size=12, color="#6B7585")),
        margin=dict(t=40, b=10, l=80, r=20), height=220,
        xaxis=dict(gridcolor="#2E3340", ticksuffix="%"), yaxis=dict(gridcolor="rgba(0,0,0,0)"))
    return fig

def plot_weight_indicator(current_pct: float, target_pct: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=round(current_pct, 1),
        number={"suffix": "%", "font": {"size": 26, "color": "#CBD5E1", "family": "Space Mono"}},
        delta={"reference": target_pct, "relative": False, "increasing": {"color": "#F97316"},
               "decreasing": {"color": "#22C55E"}, "suffix": "%", "valueformat": ".1f"},
        title={"text": "Poids Actuel<br><span style='font-size:.8em;color:#6B7585'>vs Cible (or)</span>",
               "font": {"size": 11, "color": "#8892AA"}},
        gauge={"axis": {"range": [0, 40], "tickcolor": "#6B7585", "tickfont": {"size": 9}, "nticks": 8},
               "bar": {"color": "#007BFF", "thickness": 0.28}, "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
               "steps": [{"range": [0, 5], "color": "rgba(255,49,49,.18)"},
                         {"range": [5, 15], "color": "rgba(249,115,22,.12)"},
                         {"range": [15, 25], "color": "rgba(34,197,94,.12)"},
                         {"range": [25, 40], "color": "rgba(212,175,55,.10)"}],
               "threshold": {"line": {"color": "#D4AF37", "width": 4}, "thickness": 0.85, "value": round(target_pct, 1)}}))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "#CBD5E1", "family": "DM Sans"},
        margin={"t": 50, "b": 10, "l": 20, "r": 20}, height=230)
    return fig

def plot_relative_perf(dm, ticker, nom):
    world = get_world_series(dm, exclude_ticker=ticker)
    if world.empty: return None
    sat_df = dm.data.get(ticker, pd.DataFrame())
    if sat_df is None or sat_df.empty: return None
    wc = world; sc = sat_df["Close"].dropna()
    common = sc.index.intersection(wc.index)
    if len(common) < 20: return None
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
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=.7)
    fig.update_layout(**_PLOTLY_BASE,
        title=dict(text=f"Performance relative : {nom} vs World (base 100)", font=dict(size=11, color="#6B7585")),
        margin=dict(t=20, b=20, l=50, r=20), height=200, showlegend=False,
        xaxis=dict(gridcolor="#2E3340"), yaxis=dict(gridcolor="#2E3340", ticksuffix="%"))
    return fig

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_long_term_table(_dm, cache_key):
    analytics = AnalyticsEngine(_dm); data = []
    for ticker in ETF_LIBRARY.keys():
        meta = ETF_LIBRARY.get(ticker, {}); yf_ticker = meta.get("yf", ticker)
        try: metrics = analytics.compute_all_metrics(yf_ticker if yf_ticker in _dm.data else ticker)
        except Exception: metrics = {}
        if not metrics: continue
        data.append({"ETF": meta.get("nom", ticker), "Momentum 6M": f"{metrics.get('mom_6m', 0):.1f}%",
                     "Sharpe": f"{metrics.get('sharpe', 0):.2f}", "Volatilité": f"{metrics.get('volatility', 0):.1f}%",
                     "Drawdown 1Y": f"{metrics.get('max_drawdown_1y', 0):.1f}%"})
    return pd.DataFrame(data)

def plot_equity_curve(history):
    if history.empty or "capital_cloture" not in history.columns: return None
    df = history.dropna(subset=["capital_cloture"]).copy()
    if len(df) < 2: return None
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce"); df = df.dropna(subset=["date_dt"]).sort_values("date_dt")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date_dt"], y=df["capital_cloture"], mode="lines+markers",
                             line=dict(color="#D4AF37", width=2.5), marker=dict(size=5), name="Capital"))
    fig.update_layout(**_PLOTLY_BASE, height=280, xaxis=dict(gridcolor="#2E3340"),
                      yaxis=dict(gridcolor="#2E3340", ticksuffix="€"))
    return fig

# =============================================================================
# NOUVELLES FONCTIONS v8.4 — Courbe de performance + point haut
# =============================================================================
def compute_portfolio_peak(history, current_value=None):
    """Point haut historique du capital (basé sur capital_cloture)."""
    if history is None or history.empty or "capital_cloture" not in history.columns:
        return None
    df = history.copy()
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df["capital"] = pd.to_numeric(df["capital_cloture"], errors="coerce")
    df = df.dropna(subset=["date_dt", "capital"]).sort_values("date_dt")
    if df.empty:
        return None
    idx_peak = df["capital"].idxmax()
    peak_capital = float(df.loc[idx_peak, "capital"])
    peak_date = df.loc[idx_peak, "date_dt"]
    capital_initial = float(df["capital"].iloc[0])
    peak_gain = peak_capital - capital_initial
    peak_perf = (peak_gain / capital_initial * 100) if capital_initial > 0 else None
    if current_value is None:
        current_value = float(df["capital"].iloc[-1])
    current_value = float(current_value)
    # Le point haut ne peut pas être inférieur à la valeur live actuelle
    peak_capital = max(peak_capital, current_value)
    if peak_capital == current_value:
        peak_date = df["date_dt"].iloc[-1]  # sommet = aujourd'hui
    distance_pct = (current_value / peak_capital - 1) * 100 if peak_capital > 0 else None
    distance_eur = current_value - peak_capital
    return {"date": peak_date, "capital": peak_capital, "gain": peak_gain,
            "performance_pct": peak_perf, "current_value": current_value,
            "distance_pct": distance_pct, "distance_eur": distance_eur}

def plot_portfolio_performance_curve(history, current_value=None):
    """Courbe de performance cumulée du portefeuille (%) basée sur capital_cloture."""
    if history is None or history.empty or "capital_cloture" not in history.columns:
        return None
    df = history.dropna(subset=["capital_cloture"]).copy()
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df["capital"] = pd.to_numeric(df["capital_cloture"], errors="coerce")
    df = df.dropna(subset=["date_dt", "capital"]).sort_values("date_dt").drop_duplicates("date_dt", keep="last")
    if len(df) < 2:
        return None
    capital_initial = float(df["capital"].iloc[0])
    if capital_initial <= 0:
        return None
    df["performance_pct"] = (df["capital"] / capital_initial - 1) * 100
    df["peak_capital"] = df["capital"].cummax()
    df["drawdown_pct"] = (df["capital"] / df["peak_capital"] - 1) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date_dt"], y=df["performance_pct"], mode="lines", name="Portefeuille",
        line=dict(color="#D4AF37", width=2.5),
        customdata=df[["capital", "performance_pct", "peak_capital", "drawdown_pct"]].values,
        hovertemplate=("<b>%{x|%d/%m/%Y}</b><br>Capital : %{customdata[0]:,.2f}€<br>"
                       "Performance : %{customdata[1]:+.2f}%<br>Point haut : %{customdata[2]:,.2f}€<br>"
                       "Écart au point haut : %{customdata[3]:+.2f}%<extra></extra>")))
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=.7)
    if current_value is not None:
        current_perf = (float(current_value) / capital_initial - 1) * 100
        fig.add_trace(go.Scatter(
            x=[df["date_dt"].iloc[-1]], y=[current_perf], mode="markers", name="Aujourd'hui",
            marker=dict(size=9, color="#FFFFFF", line=dict(color="#D4AF37", width=2)),
            hovertemplate=f"<b>Aujourd'hui</b><br>Capital : {float(current_value):,.2f}€<br>Performance : {current_perf:+.2f}%<extra></extra>"))
    fig.update_layout(**_PLOTLY_BASE, height=300, margin=dict(t=25, b=35, l=55, r=20),
                      xaxis=dict(gridcolor="#2E3340", title=None),
                      yaxis=dict(gridcolor="#2E3340", title="Performance cumulée", ticksuffix="%"),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                      hovermode="x unified")
    return fig

def plot_correlation_heatmap(corr_df):
    short = {"WMMS.DE": "WMMS", "MWRD.PA": "World AV", "DCAM.PA": "World PEA", "KRW.PA": "Korea", "CHIP.PA": "CHIP"}
    labels = [short.get(c, c) for c in corr_df.columns]
    fig = go.Figure(go.Heatmap(z=corr_df.values.round(2), x=labels, y=labels,
        colorscale=[[0, "#FF3131"], [0.5, "#252932"], [1, "#22C55E"]], zmid=0, zmin=-1, zmax=1,
        text=corr_df.values.round(2), texttemplate="%{text:.2f}"))
    fig.update_layout(**_PLOTLY_BASE, height=300, margin=dict(t=30, b=30, l=60, r=20))
    return fig

# -----------------------------------------------------------------------------
# MODULE 16 : STREAMLIT UI
# -----------------------------------------------------------------------------
class StreamlitUI:
    def __init__(self, dm, pm, mre, qre, pe, pde, se, pcm=None, te=None):
        self.dm = dm; self.pm = pm; self.mre = mre; self.qre = qre; self.pe = pe; self.pde = pde; self.se = se
        self.pcm = pcm if pcm is not None else PortfolioConfigManager()
        self.te = te if te is not None else TransactionEngine()
        self.analytics = AnalyticsEngine(dm); self.signal = SignalEngine(dm, self.analytics)
        self.ie = IndicatorEngine(dm); self.wre = WorldRegimeEngine(dm, self.ie)
        self.cpe = CrashProtectionEngine(); self.upe = UnderperformanceEngine()
        self.analog = EmpiricalAnalogEngine(dm, self.ie); self.lee = LinxeaExecutionEngine(dm, self.analog)
        self.dqe = DataQualityEngine(); self.dec_engine = DecisionEngine()
        self.sae = SleeveAnalysisEngine(dm, qre); self.sde = StrategicDecisionEngine(dm, self.sae)
    @staticmethod
    def _sign(v): return "+" if v >= 0 else ""

    def render_sidebar(self):
        st.sidebar.markdown("## ⚙ Paramètres v8.4")
        mode_direct = st.sidebar.toggle("🔌 Mode Direct", value=False)
        st.sidebar.markdown("---")
        cap = st.sidebar.number_input("Capital investi (€)", value=st.session_state["cfg_capital_reel"], step=100.0, format="%.2f", key="input_capital_reel")
        adj = st.sidebar.number_input("Ajustement patrimonial (€)", value=st.session_state["cfg_ajustement_pat"], step=1.0, format="%.2f", key="input_ajustement_pat")
        bonus = st.sidebar.number_input("Bonus Fortuneo (PRM PEA, €)", value=st.session_state["cfg_bonus_fortuneo"], step=10.0, format="%.2f", key="input_bonus_fortuneo")
        if st.sidebar.button("💾 Sauvegarder paramètres", use_container_width=True):
            ok = _save_config(cap, adj, bonus)
            st.session_state["cfg_capital_reel"] = cap; st.session_state["cfg_ajustement_pat"] = adj
            st.session_state["cfg_bonus_fortuneo"] = bonus
            st.session_state["save_feedback"] = "✅ Sauvegardé" if ok else "❌ Erreur"
        if st.session_state.get("save_feedback"):
            fb = st.session_state["save_feedback"]
            cls = "save-box" if fb.startswith("✅") else "alert-box"
            st.sidebar.markdown(f'<div class="{cls}">{fb}</div>', unsafe_allow_html=True)
        st.sidebar.markdown("---")
        with st.sidebar.expander("⚙ Configuration des Positions", expanded=False):
            raw_pos = st.session_state["raw_positions"]; new_raw = []
            for idx, pos in enumerate(raw_pos):
                tk_id = pos.get("ticker", ""); meta = ETF_LIBRARY.get(tk_id, {}); label = meta.get("nom", tk_id)
                st.markdown(f"**{label}** `{tk_id}`")
                c1, c2 = st.columns(2)
                n_parts = c1.number_input("Parts", value=float(pos.get("parts", 0)), key=f"auto_parts_{idx}_{tk_id}", format="%.4f", step=0.0001)
                n_prm = c2.number_input("PRM (€)", value=float(pos.get("prm", 0)), key=f"auto_prm_{idx}_{tk_id}", format="%.4f", step=0.01)
                new_raw.append({**pos, "parts": n_parts, "prm": n_prm})
            if new_raw != raw_pos:
                st.session_state["raw_positions"] = new_raw; st.session_state["positions"] = enrich_positions(new_raw)
                self.pcm.save_positions(new_raw); st.rerun()
            st.markdown("---")
            existing_tk = [p["ticker"] for p in raw_pos]; available = [k for k in ETF_LIBRARY if k not in existing_tk]
            if available:
                chosen = st.selectbox("ETF à ajouter", ["(choisir)"] + available, key="sidebar_add_etf")
                if chosen != "(choisir)" and st.button("➕ Ajouter", key="sidebar_add_btn"):
                    meta = ETF_LIBRARY[chosen]
                    new_raw.append({"ticker": chosen, "parts": 0.0, "prm": 0.0, "account": meta.get("enveloppe", "AV")})
                    st.session_state["raw_positions"] = new_raw; self.pcm.save_positions(new_raw); st.rerun()
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🗑 Supprimer un ETF")
        current_positions = self.pcm.load_positions()
        if current_positions:
            ticker_to_delete = st.sidebar.selectbox("Choisir l'ETF à retirer",
                options=[pos["ticker"] for pos in current_positions],
                format_func=lambda x: f"{x} — {ETF_LIBRARY.get(x, {}).get('nom', 'Inconnu')}", key="delete_etf_selector")
            if st.sidebar.button("❌ Supprimer définitivement", use_container_width=True, type="primary"):
                updated_positions = [pos for pos in current_positions if pos["ticker"] != ticker_to_delete]
                if self.pcm.save_positions(updated_positions):
                    st.session_state["raw_positions"] = updated_positions
                    st.session_state["positions"] = enrich_positions(updated_positions)
                    st.sidebar.success(f"🎯 {ticker_to_delete} supprimé !"); st.rerun()
        if self.pm.status == "github": st.sidebar.markdown('<div class="persist-ok">🔗 GitHub Gist actif</div>', unsafe_allow_html=True)
        elif self.pm.warning_msg: st.sidebar.markdown(f'<div class="persist-warn">⚠ {self.pm.warning_msg}</div>', unsafe_allow_html=True)
        else: st.sidebar.markdown('<div class="persist-warn">📂 SQLite local</div>', unsafe_allow_html=True)
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📦 Positions (session)")
        positions_conf = []
        for pos in st.session_state["positions"]:
            with st.sidebar.expander(pos["nom"]):
                parts = st.number_input("Parts", value=float(pos["parts"]), step=0.0001, format="%.4f", key=f"p_{pos['nom']}")
                prm = st.number_input("PRM (€)", value=float(pos["prm"]), step=0.0001, format="%.4f", key=f"r_{pos['nom']}")
                positions_conf.append({**pos, "parts": parts, "prm": prm})
        capital_reel = cap; ajustement_pat = 0.0 if mode_direct else adj; bonus_fortuneo = 0.0 if mode_direct else bonus
        for pos in positions_conf:
            if pos["nom"] == "MSCI World PEA" and pos["parts"] > 0: pos["prm"] -= bonus_fortuneo / pos["parts"]
        return mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo

    def render_header(self, mode_direct, live_ok, live_total):
        now = datetime.now(ZoneInfo("Europe/Paris"))
        st.markdown('<div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:.2rem;">'
                    '<span style="font-family:Space Mono;font-size:1.6rem;font-weight:700;color:#D4AF37;">◈</span>'
                    '<span style="font-size:1.5rem;font-weight:700;color:#E2E8F0;">COCKPIT v8.4</span>'
                    '<span style="font-family:Space Mono;font-size:.9rem;color:#6B7585;">STRATEGIC DECISION ENGINE</span></div>', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        with c1: st.caption(f"Prix live · {now.strftime('%d/%m/%Y %H:%M:%S')} (Paris)")
        with c2:
            pct = live_ok / live_total * 100 if live_total else 0
            bc = "#22C55E" if pct >= 80 else "#F97316" if pct >= 50 else "#FF3131"
            st.markdown(f'<div style="text-align:right;"><span style="background:{bc};color:#0B0E15;padding:.2rem .8rem;border-radius:20px;font-size:.72rem;">📡 {live_ok}/{live_total} LIVE</span></div>', unsafe_allow_html=True)

    def render_regime_banner(self, regime):
        sc = regime["confirmed_score"]; label = regime["confirmed_label"]; css = regime["confirmed_css"]
        conf = "✅ Confirmé" if regime["is_confirmed"] else "⏳ En attente"
        s3 = " → ".join([f"{s:+d}" for s in regime["scores_3d"]])
        st.markdown(f'<div class="regime-banner {css}"><div><span style="font-size:1.1rem;">🌍 Météo : <b>{label}</b></span>'
                    f'<span style="font-size:.82rem;margin-left:1rem;opacity:.8;">{conf}</span></div>'
                    f'<div style="font-family:Space Mono;font-size:1.2rem;">Score : <b>{sc:+d}/5</b></div>'
                    f'<div style="font-size:.78rem;opacity:.7;">3j : {s3}</div></div>', unsafe_allow_html=True)

    def render_command_center(self, ptf, bench, mode_direct, pm):
        st.markdown("## 🚀 Vue d'ensemble du portefeuille")
        perf_j_chain, perf_c_chain, base_cap = pm.compute_daily_performance(ptf["valeur_totale"])
        c1, c2, c3, c4 = st.columns(4); s = self._sign
        with c1:
            crd = "card card-purple" if mode_direct else "card card-gold"
            lbl = "Valeur Brute" if mode_direct else "Valeur Totale"
            vj, vjp = ptf["perf_j_eur"], ptf["perf_j_pct"]
            st.markdown(f'<div class="{crd}"><div class="kpi-label">{lbl}<span class="live-badge">LIVE</span></div>'
                        f'<div class="kpi-value">{ptf["solde_total"]:,.2f}€</div>'
                        f'<div class="kpi-delta-{"pos" if vj>=0 else "neg"}">{s(vj)}{vj:,.2f}€ ({s(vjp)}{vjp:.2f}%) vs hier</div></div>', unsafe_allow_html=True)
        with c2:
            gr = ptf["gain_reel"]; clr = "#22C55E" if gr >= 0 else "#FF3131"
            st.markdown(f'<div class="card card-blue"><div class="kpi-label">Gain / Perte total</div>'
                        f'<div class="kpi-value" style="color:{clr};">{s(gr)}{gr:,.2f}€</div>'
                        f'<div class="small">Investi : {ptf["capital_reel"]:,.2f}€</div></div>', unsafe_allow_html=True)
        with c3:
            p = ptf["perf_tot_pct"]; pc = "#22C55E" if p >= 0 else "#FF3131"
            gap = bench.get("gap"); gc = "#22C55E" if (gap or 0) >= 0 else "#FF3131"
            pcc = "#22C55E" if perf_c_chain >= 0 else "#FF3131"
            mwr_adj = bench.get("perf_bench_adj")
            if gap is not None and mwr_adj is not None:
                gap_html = f'<div class="small">Vs World MWR : <span style="color:{gc};font-weight:700;">{s(gap)}{gap:.2f}%</span><span class="mwr-badge">MWR</span></div>'
            else: gap_html = ""
            st.markdown(f'<div class="card card-blue"><div class="kpi-label">Performance</div>'
                        f'<div class="kpi-value" style="color:{pc};">{s(p)}{p:.2f}%</div>{gap_html}'
                        f'<div class="small">Chaîné : <span style="color:{pcc};font-weight:700;">{s(perf_c_chain)}{perf_c_chain:.2f}%</span></div></div>', unsafe_allow_html=True)
        with c4:
            pb = bench.get("perf_bench_adj"); pb_ls = bench.get("perf_bench"); pbj = bench.get("perf_bench_j")
            if pb is not None:
                pbc = "#22C55E" if pb >= 0 else "#FF3131"
                pbj_html = f'<div class="kpi-delta-{"pos" if pbj>=0 else "neg"}">{s(pbj)}{pbj:.2f}% vs hier</div>' if pbj is not None else ""
                ls_html = f'<div class="small" style="color:#4B5563;">LS : {s(pb_ls)}{pb_ls:.2f}%</div>' if pb_ls is not None else ""
                body_bench = f'<div class="kpi-value" style="color:{pbc};">{s(pb)}{pb:.2f}%</div>{pbj_html}{ls_html}'
            else: body_bench = '<div class="kpi-value">N/A</div>'
            st.markdown(f'<div class="card card-blue"><div class="kpi-label">MSCI World MWR<span class="mwr-badge">AJUSTÉ</span></div>{body_bench}</div>', unsafe_allow_html=True)

        # =====================================================================
        # v8.4 : Courbe de performance du portefeuille + point haut
        # =====================================================================
        st.markdown("### 📈 Évolution de la performance du portefeuille")
        history = self.pm.load_history()
        fig_perf = plot_portfolio_performance_curve(history, current_value=ptf["valeur_totale"])
        if fig_perf:
            st.plotly_chart(fig_perf, use_container_width=True, config={"displayModeBar": False})
            peak = compute_portfolio_peak(history, current_value=ptf["valeur_totale"])
            if peak and peak["distance_pct"] is not None:
                dp = peak["distance_pct"]
                peak_color = "#22C55E" if dp >= -0.01 else ("#F97316" if dp > -5 else "#FF3131")
                st.markdown(
                    f'<div class="pedagogy-box">🏔 <b>Point haut :</b> {peak["date"].strftime("%d/%m/%Y")} · '
                    f'{peak["capital"]:,.2f}€ · {peak["gain"]:+,.2f}€ ({peak["performance_pct"]:+.2f}%)<br>'
                    f'📉 <b>Depuis le point haut :</b> '
                    f'<span style="color:{peak_color};font-weight:700;">{dp:+.2f}%</span> '
                    f'({peak["distance_eur"]:+,.2f}€)</div>', unsafe_allow_html=True)
        else:
            st.info("Historique en cours de constitution (1 point par jour) — la courbe apparaîtra "
                     "au bout de quelques jours d'utilisation de l'application.")

        st.markdown("### 📊 Mes positions")
        rows = []
        for p2 in ptf["positions"]:
            if p2["prix"] is not None and p2["perf_pct"] is not None:
                gain_unit = p2.get("gain_unit", 0); parts = p2.get("parts", 0); perf_euro = gain_unit * parts
                perf_euro_str = f"{s(perf_euro)}{perf_euro:,.2f}€"
            else: perf_euro_str = "N/A"
            perf_f = f"{s(p2['perf_pct'])}{p2['perf_pct']:.2f}%" if p2["perf_pct"] is not None else "N/A"
            vj_f = f"{s(p2['var_jour_pct'])}{p2['var_jour_pct']:.2f}%" if p2["var_jour_pct"] else "--"
            rows.append({"Position": p2["nom"], "Env.": p2["enveloppe"], "Prix": f"{p2['prix']:.3f}€" if p2["prix"] else "N/A",
                         "Valeur (€)": f"{p2['valeur']:,.2f}", "Perf. (%)": perf_f, "Perf. (€)": perf_euro_str, "Δ Jour (%)": vj_f})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Camembert répartition du portefeuille
        st.markdown("### 🥧 Répartition du portefeuille")
        vals = [p["valeur"] for p in ptf["positions"] if p.get("valeur", 0) > 0]
        labels = [p["nom"] for p in ptf["positions"] if p.get("valeur", 0) > 0]
        if vals:
            fig_pie = go.Figure(go.Pie(labels=labels, values=vals, hole=0.55, textinfo="percent+label",
                marker=dict(line=dict(color="#1C1F26", width=2))))
            fig_pie.update_layout(**_PLOTLY_BASE, height=320, margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

    def render_portfolio_leadership_comparison(self, ptf):
        st.markdown("## 📈 Performance du Portefeuille vs MSCI World")
        labels, port_perfs, world_perfs = self.pde.get_portfolio_weekly_performances(self.dm, ptf["positions"], n_weeks=5)
        if not labels:
            st.info("Données hebdomadaires insuffisantes.")
            return
        fig = plot_weekly_leadership(labels, port_perfs, world_perfs, "Portefeuille")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        gaps = [p - w for p, w in zip(port_perfs, world_perfs)]
        verdict = self.pde.translate_leadership("Portefeuille", gaps)
        st.markdown(f'<div class="pedagogy-box"><b>{verdict["message"]}</b><br>{verdict["detail"]}<br>💡 {verdict["action"]}</div>', unsafe_allow_html=True)

    def render_sleeve_leadership_comparison(self, nom, ticker_key, color_sat="#D4AF37"):
        st.markdown(f"### 📊 {nom} vs MSCI World — Leadership hebdomadaire")
        labels, sat_perfs, world_perfs = self.pde.get_weekly_performances(self.dm, ticker_key)
        if labels and sat_perfs and world_perfs:
            col_chart, col_verdict = st.columns([2, 1])
            with col_chart:
                fig = plot_weekly_leadership(labels, sat_perfs, world_perfs, nom, color_sat)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with col_verdict:
                gaps = [s - w for s, w in zip(sat_perfs, world_perfs)]
                rows_lead = []
                for lbl, s_p, w_p in zip(labels, sat_perfs, world_perfs):
                    gap = s_p - w_p
                    winner = f"🟢 +{gap:.1f}%" if gap > 0 else f"🔴 {gap:.1f}% World"
                    rows_lead.append({"Semaine": lbl, f"{nom[:8]}": f"{s_p:+.1f}%", "World": f"{w_p:+.1f}%", "Résultat": winner})
                st.dataframe(pd.DataFrame(rows_lead), use_container_width=True, hide_index=True)
                verdict = self.pde.translate_leadership(nom, gaps)
                st.markdown(f'<div class="pedagogy-box"><b>{verdict["message"]}</b><br>{verdict["detail"]}<br>'
                            f'💡 {verdict["action"]}</div>', unsafe_allow_html=True)
            fig_rel = plot_relative_perf(self.dm, ticker_key, nom)
            if fig_rel:
                st.plotly_chart(fig_rel, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Données hebdomadaires insuffisantes.")

    def render_optimal_allocation_section(self, ptf):
        st.markdown("## 📐 Optimisation mathématique — outil diagnostique")
        st.info("⚠️ Ce module n'est pas utilisé pour décider de l'allocation réelle. "
                "Il traite les poches économiques, pas les tickers individuels. La décision stratégique "
                "provient du Strategic Decision Engine.")
        st.markdown(SLEEVE_GLOSSARY)
        opt = PortfolioOptimizerEngine(self.dm)
        w_sharpe = opt.max_sharpe_sleeve_weights(window=252)
        w_rp = opt.risk_parity_sleeve_weights(window=252)
        if not w_sharpe:
            st.warning("Historique insuffisant pour l'optimisation par poches.")
            return
        vt = ptf["valeur_totale"]
        current_sleeve_values = {"WORLD_CORE": 0.0, "WORLD_VALUE": 0.0, "KOREA": 0.0, "SEMICONDUCTOR": 0.0}
        for p in ptf["positions"]:
            ticker = p.get("ticker"); value = float(p.get("valeur", 0))
            if ticker in WORLD_CORE_TICKERS: current_sleeve_values["WORLD_CORE"] += value
            elif ticker in WORLD_VALUE_TICKERS: current_sleeve_values["WORLD_VALUE"] += value
            elif ticker == "KRW.PA": current_sleeve_values["KOREA"] += value
            elif ticker == "CHIP.PA": current_sleeve_values["SEMICONDUCTOR"] += value
        current_sleeve_weights = {k: v / vt if vt else 0 for k, v in current_sleeve_values.items()}
        sleeve_labels = {"WORLD_CORE": "🌍 World Core (PEA + AV)", "WORLD_VALUE": "💎 World Value",
                         "KOREA": "🇰🇷 Korea", "SEMICONDUCTOR": "💻 Semiconductor"}
        rows = []
        for key, label in sleeve_labels.items():
            current = current_sleeve_weights.get(key, 0); sharpe = w_sharpe.get(key, 0)
            rp = w_rp.get(key, 0) if w_rp else np.nan
            rows.append({"Poche stratégique": label, "Poids actuel": f"{current * 100:.1f}%",
                         "Optimal Sharpe": f"{sharpe * 100:.1f}%",
                         "Risk Parity": f"{rp * 100:.1f}%" if pd.notna(rp) else "N/A",
                         "Écart vs Sharpe": f"{(current - sharpe) * 100:+.1f} pts"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        fig = go.Figure()
        labels_chart = [sleeve_labels[k] for k in w_sharpe.keys()]
        fig.add_trace(go.Bar(x=labels_chart, y=[current_sleeve_weights.get(k, 0) * 100 for k in w_sharpe.keys()],
                             name="Actuel", text=[f"{current_sleeve_weights.get(k, 0) * 100:.1f}%" for k in w_sharpe.keys()], textposition="outside"))
        fig.add_trace(go.Bar(x=labels_chart, y=[w_sharpe[k] * 100 for k in w_sharpe.keys()],
                             name="Optimal Sharpe", text=[f"{w_sharpe[k] * 100:.1f}%" for k in w_sharpe.keys()], textposition="outside"))
        if w_rp:
            fig.add_trace(go.Bar(x=labels_chart, y=[w_rp.get(k, 0) * 100 for k in w_sharpe.keys()],
                                 name="Risk Parity", text=[f"{w_rp.get(k, 0) * 100:.1f}%" for k in w_sharpe.keys()], textposition="outside"))
        fig.update_layout(**_PLOTLY_BASE, barmode="group", height=430, margin=dict(t=50, b=80, l=50, r=30),
                          yaxis=dict(title="Poids (%)", ticksuffix="%", gridcolor="#2E3340"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.info("⚠️ L'optimiseur raisonne en poches économiques. World PEA et World AV sont regroupés "
                "dans une seule ligne World Core. Le résultat Sharpe/Risk Parity est uniquement diagnostique.")

    def render_sleeve_analysis(self, ptf):
        st.markdown("## 🧭 Vue par poche stratégique")
        sleeves = self.sae.compute_sleeve_weights(ptf)
        cols = st.columns(4)
        for i, k in enumerate(["world_core", "world_value_tilt", "korea", "semiconductor"]):
            if k not in sleeves: continue
            s = sleeves[k]
            with cols[i]:
                st.markdown(f'<div class="card"><div class="kpi-label">{s["label"]}</div>'
                            f'<div class="kpi-value">{s["pct"]:.1f}%</div>'
                            f'<div class="small" style="margin-top:.5rem;">{s["explain"]}</div></div>', unsafe_allow_html=True)
        if "satellites_boost" in sleeves:
            sat = sleeves["satellites_boost"]; sat_budget = validate_satellite_budget(ptf)
            sat_color = "#FF3131" if not sat_budget["valid"] else "#22C55E"
            st.markdown(f'<div class="card" style="border-left:4px solid {sat_color};">'
                        f'<div class="kpi-label">🚀 Satellites = Korea + Semiconductor</div>'
                        f'<div class="kpi-value" style="color:{sat_color};">{sat["pct"]:.1f}%</div>'
                        f'<div class="small">Plafond : {SATELLITE_MAX*100:.0f}%</div></div>', unsafe_allow_html=True)
            if not sat_budget["valid"]:
                st.error(f"🚨 Budget satellites dépassé : {sat_budget['satellite_pct']*100:.1f}%. "
                         f"Réduction nécessaire : ~{sat_budget['excess_eur']:,.0f}€.")
        corr_ks = self.qre.correlation_matrix(["KRW.PA", "CHIP.PA"], 60)
        if corr_ks is not None and "KRW.PA" in corr_ks.columns and "CHIP.PA" in corr_ks.columns:
            c = corr_ks.loc["KRW.PA", "CHIP.PA"]
            if pd.notna(c) and c > 0.80:
                st.warning(f"Korea et Semiconductor sont fortement corrélés ({c:.2f}) : "
                           "même complexe de risque au niveau du budget satellites.")
        st.markdown("---")
        st.markdown("### 📊 Leadership de chaque poche vs World")
        self.render_sleeve_leadership_comparison("World Value", "WMMS.DE", color_sat="#A855F7")
        self.render_sleeve_leadership_comparison("Korea", "KRW.PA", color_sat="#3B82F6")
        self.render_sleeve_leadership_comparison("Semiconductor", "CHIP.PA", color_sat="#F97316")

    def _get_base_weight(self, score: int, initial_target: float) -> float:
        if score >= 3: return initial_target
        elif score >= 1: return 0.20
        elif score >= -1: return 0.15
        else: return 0.05

    def render_position_sizing(self, ptf, decision_result):
        st.markdown("### ⚖ Position Sizing par poche (indicatif)")
        st.caption("Combine le score de chaque poche avec les bornes stratégiques (STRATEGIC_TARGETS) "
                   "pour proposer un poids cible. Ce n'est pas un ordre — c'est une base de discussion "
                   "à confronter avec le Strategic Decision Engine ci-dessus.")
        vt = ptf["valeur_totale"]
        if vt <= 0: return
        current_w = self.sde.compute_strategic_risk_weights(ptf)
        value = decision_result.get("value", {}) or {}
        korea = decision_result.get("korea", {}) or {}
        semi = decision_result.get("semiconductor", {}) or {}
        specs = [
            ("WORLD_CORE", "🌍 World Core", None, STRATEGIC_TARGETS["world_core"]["neutral_min"]),
            ("WORLD_VALUE", "💎 World Value", value.get("score", 0), STRATEGIC_TARGETS["world_value"]["neutral_min"]),
            ("KOREA", "🇰🇷 Korea", korea.get("score", 0), STRATEGIC_TARGETS["satellites"]["neutral_min"] / 2),
            ("SEMICONDUCTOR", "🔬 Semiconductor",
             semi.get("score", 0) if semi.get("available") else 0,
             STRATEGIC_TARGETS["satellites"]["neutral_min"] / 2),
        ]
        raw_targets = {}
        for key, label, score, initial_target in specs:
            raw_targets[key] = (STRATEGIC_TARGETS["world_core"]["neutral_min"] if key == "WORLD_CORE"
                                 else self._get_base_weight(score, initial_target))
        total_raw = sum(raw_targets.values()) or 1.0
        rows = []
        for key, label, score, initial_target in specs:
            cur_pct = current_w.get(key, 0) * 100
            target_pct = raw_targets[key] / total_raw * 100
            delta = cur_pct - target_pct
            action = "🔴 Réduire" if delta > 5 else "🟢 Renforcer" if delta < -5 else "⚪ Maintenir"
            rows.append({"Poche": label, "Score": score if score is not None else "—",
                         "Poids actuel": f"{cur_pct:.1f}%", "Poids cible": f"{target_pct:.1f}%",
                         "Écart": f"{delta:+.1f}%", "Action": action})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        sat_total = current_w.get("KOREA", 0) + current_w.get("SEMICONDUCTOR", 0)
        if sat_total > SATELLITE_MAX:
            st.warning(f"Budget satellites à {sat_total*100:.1f}% > plafond {SATELLITE_MAX*100:.0f}%.")
        col_gauge, _ = st.columns([1, 2])
        with col_gauge:
            st.plotly_chart(plot_weight_indicator(sat_total * 100, SATELLITE_MAX * 100),
                            use_container_width=True, config={"displayModeBar": False})
        try:
            worst = max(rows, key=lambda r: abs(float(r["Écart"].rstrip('%'))))
            st.info(f"🎯 En synthèse : l'ajustement le plus significatif concerne **{worst['Poche']}** "
                    f"({worst['Écart']} vs cible) → {worst['Action']}.")
        except Exception:
            pass

    def render_arbitrage_widget(self):
        if "positions" not in st.session_state: return
        holdings = [p.get("_tk_id", p.get("ticker")) for p in st.session_state["positions"] if p.get("valeur", 0) > 0]
        holdings = list(dict.fromkeys([h for h in holdings if h in ETF_LIBRARY]))
        opps = self.signal.get_arbitrage_opportunities(holdings)
        if opps:
            st.markdown("### 🔄 Alertes d'arbitrage (indicatif)")
            for opp in opps:
                st.markdown(f'<div class="arb-sell">🚨 Opportunité : vendre <b>{opp["sell_name"]}</b> → '
                            f'acheter <b>{opp["buy_name"]}</b></div>', unsafe_allow_html=True)

    def render_strategic_decision(self, ptf, benchmark_gap=None):
        result = self.sde.compute(ptf, benchmark_gap=benchmark_gap)
        action = result["action"]
        action_config = {
            "EXIT_TO_WORLD": ("🔴", "Retour progressif vers 100% World", "alert-box"),
            "REDUCE_SATELLITES": ("🟠", "Réduire les satellites", "signal-sell"),
            "REDUCE_VALUE": ("🟠", "Réduire progressivement World Value", "signal-sell"),
            "INCREASE_SEMICONDUCTOR": ("🟢", "Renforcer modérément Semiconductor", "signal-buy"),
            "MAINTAIN_ACTIVE": ("🟢", "Maintenir la stratégie active", "signal-buy"),
            "MAINTAIN": ("🔵", "Aucune modification", "signal-neutral"),
        }
        emoji, title, css_class = action_config.get(action, ("🔵", "Aucune décision", "signal-neutral"))
        st.markdown("## 🎯 DÉCISION STRATÉGIQUE")
        st.markdown(f'<div class="{css_class}"><div style="font-size:1.2rem;font-weight:800;">{emoji} {title}</div>'
                    f'<div style="margin-top:.6rem;">{result["reason"]}</div></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("🌍 World Core", f'{result["world_core_pct"] * 100:.1f}%')
        with c2: st.metric("💎 World Value", f'{result["value_pct"] * 100:.1f}%')
        with c3: st.metric("🚀 Satellites", f'{result["satellite_pct"] * 100:.1f}%')
        st.caption("World Core = DCAM.PA + MWRD.PA. Une seule exposition économique.")
        sat_budget = validate_satellite_budget(ptf)
        if not sat_budget["valid"]:
            st.error(f"🚨 Budget satellites dépassé : {sat_budget['satellite_pct']*100:.1f}% "
                     f"(max {SATELLITE_MAX*100:.0f}%). Réduction : ~{sat_budget['excess_eur']:,.0f}€.")

        st.markdown("### 📊 État des moteurs")
        value = result["value"]; korea = result["korea"]; semi = result["semiconductor"]
        rows = [
            {"Poche": "🌍 World Core", "Signal": "CORE", "Score": "—", "Régime": "Socle"},
            {"Poche": "💎 World Value", "Signal": "Value / World",
             "Score": value.get("score", 0) if value.get("available") else "N/A",
             "Régime": value.get("regime", "N/A")},
            {"Poche": "🇰🇷 Korea", "Signal": "Tactique", "Score": korea.get("score", 0),
             "Régime": korea.get("regime", "N/A")},
            {"Poche": "🔬 Semiconductor", "Signal": "vs World (principal)",
             "Score": semi.get("world_score", 0) if semi.get("available") else "N/A",
             "Régime": semi.get("world_regime", "N/A")},
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Score = nombre d'horizons (3m/6m/12m) où la poche bat le World : de -3 (jamais) à +3 (toujours). "
                   "Le rattrapage vs Korea (secondaire) reste visible dans 'Analyse des ETF Satellites'.")

        held = [p["ticker"] for p in ptf["positions"] if p.get("ticker") and p.get("valeur", 0) > 0]
        weights = [p["valeur"] / ptf["valeur_totale"] for p in ptf["positions"]
                   if p.get("ticker") in held]
        if len(held) >= 2 and ptf["valeur_totale"] > 0:
            rc_map = self.qre.risk_contribution(held, weights, 60)
            fig_rc = plot_risk_contribution(rc_map)
            if fig_rc:
                st.plotly_chart(fig_rc, use_container_width=True, config={"displayModeBar": False})
            for tk, info in rc_map.items():
                if info["flag"]:
                    lbl = {"KRW.PA": "Korea", "CHIP.PA": "Semiconductor", "WMMS.DE": "World Value"}.get(tk, tk)
                    sc = {"KRW.PA": korea.get("score", 0), "CHIP.PA": semi.get("world_score", 0),
                          "WMMS.DE": value.get("score", 0)}.get(tk, 0)
                    verdict = ("c'est aussi la poche au signal le plus favorable actuellement — risque concentré, mais assumé."
                               if sc > 0 else "et son signal ne compense pas cette concentration — candidat naturel à une réduction.")
                    st.warning(f"⚠️ {lbl} concentre {info['rc_pct']:.0f}% du risque (seuil 40%) — {verdict}")

        st.markdown("### 📊 Chaque poche active vs MSCI World (référence unique)")
        for label, tk in [("World Value", "WMMS.DE"), ("Korea", "KRW.PA"), ("Semiconductor", "CHIP.PA")]:
            df_tk = self.dm.data.get(tk, pd.DataFrame())
            if df_tk.empty or "Close" not in df_tk.columns: continue
            ws = get_world_series(self.dm, exclude_ticker=tk)
            analysis = compute_semiconductor_relative_analysis(df_tk["Close"].dropna(), ws)
            vw = analysis.get("vs_world", {})
            if vw:
                st.markdown(f"**{label} vs World**")
                cols = st.columns(5)
                for col, (h, val) in zip(cols, [("20j", vw.get("20d")), ("60j", vw.get("60d")),
                                                 ("3m", vw.get("3m")), ("6m", vw.get("6m")), ("12m", vw.get("12m"))]):
                    if val is not None and pd.notna(val): col.metric(h, f"{val*100:+.2f} pts")
        st.info("MSCI World est la référence unique ci-dessus. Semiconductor vs Korea reste disponible, "
                "à titre secondaire, dans 'Analyse des ETF Satellites'.")

        exit_info = result.get("exit_to_world", {})
        if exit_info:
            st.markdown("### 🏁 Sortie de la stratégie active")
            exit_labels = {"ACTIVE_STRATEGY": "🟢 Stratégie active justifiée", "WATCH": "🟡 Surveiller",
                           "EXIT_PREPARATION": "🟠 Préparer le retour vers World", "EXIT_CONFIRMED": "🔴 Retour vers 100% World confirmé"}
            st.info(f"{exit_labels.get(exit_info.get('level'), exit_info.get('level'))} — Score {exit_info.get('score', 0)}/5")
            for reason in exit_info.get("reasons", []): st.write(f"• {reason}")

        self.render_arbitrage_widget()
        self.render_position_sizing(ptf, result)
        return result

    def render_equity_curve_section(self, ptf, regime, positions_conf):
        st.markdown("## 📈 Historique de votre capital")
        history = self.pm.load_history()
        fig_eq = plot_equity_curve(history)
        if fig_eq: st.plotly_chart(fig_eq, use_container_width=True, config={"displayModeBar": False})
        if not history.empty:
            perf_j, perf_c, _ = self.pm.compute_daily_performance(ptf["valeur_totale"])
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Jours", f"{len(history)}"); mc2.metric("Perf jour", f"{perf_j:+.2f}%")
            mc3.metric("Perf totale", f"{perf_c:+.2f}%"); mc4.metric("Valeur", f"{ptf['valeur_totale']:,.0f}€")

    def render_risk_dashboard(self, ptf):
        st.markdown("## ⚠ Gestion des risques")
        risk_assets = [(p["ticker"], p["nom"], {"WMMS.DE": "#D4AF37", "DCAM.PA": "#007BFF", "MWRD.PA": "#3B82F6",
                                                 "KRW.PA": "#F97316", "CHIP.PA": "#A855F7"}.get(p["ticker"], "#6366F1"))
                       for p in ptf["positions"] if p.get("ticker") and p["valeur"] > 0]
        cols = st.columns(min(len(risk_assets), 4)) if risk_assets else []
        for i, (tk, name, color) in enumerate(risk_assets):
            with cols[i % len(cols)]:
                vol = self.qre.rolling_volatility(tk, 30); beta = self.qre.rolling_beta(tk); dd = self.qre.drawdown_metrics(tk, 252)
                vol_t = self.pde.translate_volatility(vol, name)
                level_colors = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}
                beta_str = f"{beta:.2f}×" if beta else "N/A"
                st.markdown(f'<div class="card" style="border-top:3px solid {color};">'
                            f'<div class="kpi-label">{name}</div>'
                            f'<div style="font-size:1.5rem;color:{level_colors[vol_t["level"]]};">{vol_t["emoji"]} {vol_t["value"]}</div>'
                            f'<div style="font-size:.8rem;color:#8892AA;">Beta : {beta_str}</div>'
                            f'<div style="font-size:.8rem;color:#8892AA;">DD : {dd.get("current_dd", 0):.1f}%</div></div>', unsafe_allow_html=True)
        with st.expander("🔬 Corrélation entre vos ETF", expanded=False):
            st.caption("**Corrélation entre vos ETF entre eux** (60 jours) — différente de la corrélation du Backtest, "
                       "qui mesure la fiabilité d'une prédiction.")
            tickers_ptf = [p["ticker"] for p in ptf["positions"] if p.get("ticker") and p["valeur"] > 0]
            if len(tickers_ptf) >= 2:
                corr_df = self.qre.correlation_matrix(tickers_ptf, 60)
                if corr_df is not None: st.plotly_chart(plot_correlation_heatmap(corr_df), use_container_width=True)

    def render_satellite_card_pedagogic(self, nom, ticker_key, unified, target_weight, regime, sent_rows, sector, gap_vs_world=None):
        color = {"korea": "#F97316", "chip": "#A855F7", "value": "#D4AF37"}.get(sector, "#D4AF37")
        labels_w, perfs_w, world_w = self.pde.get_weekly_performances(self.dm, ticker_key)
        if labels_w:
            gaps_w = [p - w for p, w in zip(perfs_w, world_w)]
            v = self.pde.translate_leadership(nom, gaps_w)
            stars, lbl = {"green": ("⭐⭐⭐⭐⭐", "Sain"), "orange": ("⭐⭐⭐☆☆", "Vigilance"),
                          "red": ("☆☆☆☆☆", "Dégradé")}.get(v["level"], ("⭐⭐⭐☆☆", "Neutre"))
            detail = v.get("detail", "")
        else:
            stars, lbl, detail = "⭐⭐⭐☆☆", "Données insuffisantes", ""
        st.markdown(f'<div class="card" style="border-top:3px solid {color};">'
                    f'<div class="kpi-label">{nom}</div>'
                    f'<div style="font-size:1.5rem;font-weight:700;">{stars} {lbl}</div>'
                    f'<div style="font-size:.85rem;color:#8892AA;">{detail} — cohérent avec le Leadership hebdomadaire ci-dessus.</div></div>', unsafe_allow_html=True)

    def render_sentinelles_macro(self, ptf):
        st.markdown("## 🛰 Radar Sectoriel")
        s_msg, _, sent_rows = self.pe.evaluate_sentinelles()
        if "OK" in s_msg: st.success(s_msg)
        else: st.warning(s_msg)
        st.dataframe(pd.DataFrame(sent_rows), use_container_width=True, hide_index=True)

    def render_quant_alert_v2(self, decisions):
        st.markdown("## 🧭 Alerte Quantitative (secondaire)")
        for d in decisions:
            st.markdown(f'<div style="border-left:4px solid {d["color"]};padding:.5rem 1rem;'
                        f'background:{d["color"]}15;border-radius:6px;margin-bottom:.3rem;font-size:.85rem;">{d["sentence"]}</div>', unsafe_allow_html=True)

    def render_backtest_calibration_tab(self, ptf):
        st.markdown("## 🧪 Backtest & Calibration")
        st.markdown(BACKTEST_GLOSSARY)
        if not SKLEARN_OK: st.warning("⚠ scikit-learn non installé.")
        held_tickers = [p.get("ticker") for p in ptf["positions"] if p.get("ticker") and p["valeur"] > 0]
        for ticker in held_tickers:
            nom = ETF_LIBRARY.get(ticker, {}).get("nom", ticker)
            st.markdown(f"---\n## 📌 {nom}")
            self._render_single_backtest(ticker)

    def _render_single_backtest(self, ticker):
        with st.spinner(f"Features pour {ticker}..."): feat = build_feature_frame(self.dm, ticker)
        if feat.empty: st.error("Historique insuffisant."); return
        st.markdown(f"📊 **{len(feat)}** jours exploitables")
        st.markdown("### 1️⃣ Walk-Forward : Ridge vs Baseline")
        model = ForwardAlphaModel(horizon=20, n_folds=4)
        wf_result = model.walk_forward_evaluate(feat)
        if wf_result.get("available"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Baseline**"); bm = wf_result['baseline']
                st.metric("Hit Rate", f"{bm['hit_rate']*100:.1f}%" if pd.notna(bm['hit_rate']) else "N/A")
                st.metric("Corrélation", f"{bm['correlation']:.3f}" if pd.notna(bm['correlation']) else "N/A")
                st.metric("MAE", f"{bm['mae']:.4f}" if pd.notna(bm['mae']) else "N/A")
            with c2:
                st.markdown("**Ridge**"); rm = wf_result['ridge']
                st.metric("Hit Rate", f"{rm['hit_rate']*100:.1f}%" if pd.notna(rm['hit_rate']) else "N/A")
                st.metric("Corrélation", f"{rm['correlation']:.3f}" if pd.notna(rm['correlation']) else "N/A")
                st.metric("MAE", f"{rm['mae']:.4f}" if pd.notna(rm['mae']) else "N/A")
            st.caption(f"Échantillon OOS : {wf_result['n_oos_samples']} observations.")
            if wf_result["ridge_better"] and wf_result["n_oos_samples"] >= 100:
                st.success("✅ Ridge robuste.")
                prod_model, scaler = model.fit_production_model(feat)
                pred_today = model.predict_today(feat, prod_model, scaler)
                if pred_today is not None: st.markdown(f"**Alpha attendu à 20 jours : {pred_today*100:+.2f}%**")
            else: st.error("⛔ **Aucune prédiction.** Critères V8 stricts non satisfaits.")
        else: st.warning(wf_result.get("reason", "Indisponible"))
        st.markdown("### 2️⃣ Backtest")
        bt = BacktestEngine(CRASH_THRESHOLDS, UNDERPERF_THRESHOLDS)
        bt_results = bt.run(self.dm, ticker, feat)
        rows = []
        for name, label in [("A_BuyHold", "A — Buy & Hold"), ("C_SignalLinxeaDelay", "C — Signal + délai")]:
            m = bt_results.get(name, {})
            if not m.get("available"): continue
            rows.append({"Stratégie": label, "CAGR": f"{m['cagr_pct']:+.1f}%", "Max DD": f"{m['max_drawdown_pct']:.1f}%",
                         "Sharpe": f"{m['sharpe']:.2f}", "Calmar": f"{m['calmar']:.2f}"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    def render_long_term_cockpit(self, ptf, analytics_engine, regime):
        st.markdown("## 📈 Cockpit Long Terme")
        cache_key = f"{datetime.now().strftime('%Y-%m-%d')}_{len(self.dm.data)}"
        df_table = _cached_long_term_table(self.dm, cache_key)
        if df_table.empty: st.info("Aucune donnée."); return
        st.markdown(df_table.to_html(escape=False, index=False), unsafe_allow_html=True)

    def render_fiscal_simulator(self, ptf):
        st.markdown("## 🧮 Simulateur Fiscal")
        st.info("Cette calculatrice estime la fiscalité d'un retrait en France. Elle distingue le PEA "
                "et l'Assurance-Vie, tient compte de la durée de détention et applique les règles fiscales "
                "paramétrées pour 2026. Le résultat reste une estimation : l'établissement financier et "
                "l'administration fiscale déterminent le montant final.")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🏦 PEA")
            pea_opening = st.date_input("Date du premier versement / ouverture du PEA",
                                        value=datetime(2026, 4, 8).date(), key="fiscal_pea_opening")
            pea_value = st.number_input("Valeur actuelle du PEA (€)", min_value=0.0,
                                        value=float(ptf["val_env"].get("PEA", 0)), step=100.0, key="fiscal_pea_value")
            pea_gain = st.number_input("Gain latent du PEA (€)", min_value=0.0,
                                       value=float(ptf["gain_env"].get("PEA", 0)), step=100.0, key="fiscal_pea_gain")
            pea_withdrawal = st.number_input("Montant du retrait PEA (€)", min_value=0.0,
                                             max_value=float(pea_value), value=min(1000.0, float(pea_value)),
                                             step=100.0, key="fiscal_pea_withdrawal")
            pea_date = st.date_input("Date envisagée du retrait", value=datetime.now().date(), key="fiscal_pea_withdrawal_date")
            pea_result = calculate_pea_tax(pea_withdrawal, pea_value, pea_gain, pea_opening, pea_date)
            st.metric("Impôts + PS", f"{pea_result['tax']:,.2f} €")
            st.metric("Net estimé", f"{pea_result['net']:,.2f} €")
            st.caption(f"IR : {pea_result['ir']:,.2f} € · PS : {pea_result['ps']:,.2f} €")
            st.info(f"Statut : **{pea_result['status']}**")
            if "five_year_date" in pea_result:
                st.caption(f"Date théorique des 5 ans : {pea_result['five_year_date'].strftime('%d/%m/%Y')}")
        with col2:
            st.markdown("### 🛡 Assurance-Vie")
            av_opening = st.date_input("Date d'ouverture du contrat", value=datetime(2025, 1, 1).date(), key="fiscal_av_opening")
            av_value = st.number_input("Valeur actuelle de l'AV (€)", min_value=0.0,
                                       value=float(ptf["val_env"].get("AV", 0)), step=100.0, key="fiscal_av_value")
            av_gain = st.number_input("Gain latent de l'AV (€)", min_value=0.0,
                                      value=float(ptf["gain_env"].get("AV", 0)), step=100.0, key="fiscal_av_gain")
            av_premiums = st.number_input("Total des primes versées (€)", min_value=0.0,
                                          value=max(0.0, float(av_value - av_gain)), step=100.0, key="fiscal_av_premiums")
            av_withdrawal = st.number_input("Montant du rachat (€)", min_value=0.0,
                                            max_value=float(av_value), value=min(1000.0, float(av_value)),
                                            step=100.0, key="fiscal_av_withdrawal")
            av_date = st.date_input("Date envisagée du rachat", value=datetime.now().date(), key="fiscal_av_withdrawal_date")
            household = st.radio("Foyer fiscal", ["Couple", "Célibataire"], horizontal=True, key="fiscal_household")
            household_code = "couple" if household == "Couple" else "single"
            av_result = calculate_av_tax(av_withdrawal, av_value, av_gain, av_opening, av_date, av_premiums, household_code)
            st.metric("Impôts + PS", f"{av_result['tax']:,.2f} €")
            st.metric("Net estimé", f"{av_result['net']:,.2f} €")
            st.caption(f"IR : {av_result['ir']:,.2f} € · PS : {av_result['ps']:,.2f} €")
            st.info(f"Statut : **{av_result['status']}**")
            if "eight_year_date" in av_result:
                st.caption(f"Date des 8 ans : {av_result['eight_year_date'].strftime('%d/%m/%Y')}")
                st.caption(f"Abattement utilisé : {av_result.get('abatement', 0):,.0f} €")

    def render_transactions_tab(self):
        st.markdown("## 📈 Journal des Transactions")
        with st.expander("➕ Enregistrer un ordre", expanded=True):
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
                tx_price = st.number_input("Prix (€)", min_value=0.0, value=float(live_px) if live_px else 0.0,
                                           format="%.4f", step=0.01, key="tx_price")
            with c5: tx_date = st.date_input("Date", value=datetime.now().date(), key="tx_date")
            tx_note = st.text_input("Note", key="tx_note")
            if st.button("✅ Enregistrer", type="primary"):
                if tx_parts > 0 and tx_price > 0:
                    tx_record = {"date": str(tx_date), "type": tx_type, "ticker": tx_ticker, "parts": tx_parts,
                                 "price": tx_price, "montant": round(tx_parts * tx_price, 2), "note": tx_note}
                    if self.te.save_transaction(tx_record):
                        rebuilt = self.te.get_portfolio_as_positions()
                        if rebuilt:
                            self.pcm.save_positions(rebuilt)
                            st.session_state["raw_positions"] = rebuilt
                            st.session_state["positions"] = enrich_positions(rebuilt)
                        st.success("✅ Enregistré !"); st.rerun()
        txs = self.te.load_transactions()
        if not txs: st.info("📭 Aucune transaction."); return
        rows = []
        for tx in sorted(txs, key=lambda x: x.get("date", ""), reverse=True):
            meta_t = ETF_LIBRARY.get(tx.get("ticker", ""), {})
            rows.append({"Date": tx.get("date", ""), "Type": tx.get("type", ""), "ETF": meta_t.get("nom", tx.get("ticker", "")),
                         "Parts": f"{tx.get('parts', 0):.4f}", "Prix": f"{tx.get('price', 0):.4f}€",
                         "Montant": f"{tx.get('montant', 0):,.2f}€", "Note": tx.get("note", "")})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    def render_screener_tab(self):
        st.markdown("## 🔍 Screener Quantitatif")
        with st.spinner("Calcul..."):
            scores = []
            for ticker, meta in ETF_LIBRARY.items():
                yf_ticker = meta.get("yf", ticker); res = self.signal.compute_score(yf_ticker)
                if res.get("status") == "NO_DATA" or not res.get("metrics"):
                    scores.append({"Ticker": ticker, "Nom": meta.get("nom", ""), "Score": "N/A",
                                   "Corrélation avec le World (1M)": "N/A", "Corrélation avec le World (3M)": "N/A",
                                   "Statut": "⚠ Indisponible"})
                else:
                    m = res["metrics"]
                    scores.append({"Ticker": ticker, "Nom": meta.get("nom", ""), "Score": res["score"],
                                   "Momentum 6M": f"{m.get('mom_6m', 0):.1f}%", "Sharpe": f"{m.get('sharpe', 0):.2f}",
                                   "Corrélation avec le World (1M)": f"{m.get('corr_1m', 0):.2f}" if m.get('corr_1m') is not None else "N/A",
                                   "Corrélation avec le World (3M)": f"{m.get('corr_3m', 0):.2f}" if m.get('corr_3m') is not None else "N/A",
                                   "Statut": "✅ Analysé"})
            df_scores = pd.DataFrame(scores)
            if "Score" in df_scores.columns:
                df_scores["Score_num"] = pd.to_numeric(df_scores["Score"], errors="coerce")
                df_scores = df_scores.sort_values(["Score_num", "Statut"], ascending=[False, True]).drop(columns=["Score_num"])
        st.dataframe(df_scores.head(30), use_container_width=True, hide_index=True)

    def render_risk_engine_v71(self, ptf):
        render_glossary_expander(RSG_GLOSSARY, title="📖 RSG brut vs RSG pondéré qualité")
        st.markdown("## 🛡 Risk Engine v7.1 — Scores en direct")
        st.markdown("""
        <div class="pedagogy-box">
        <b>🎯 Comment utiliser cette page ?</b><br><br>
        <b>SR /3</b> = niveau de risque de chaque poche.<br>
        0 = normal · 1 = vigilance · 2 = risque élevé · 3 = stress important.<br><br>
        <b>RSG brut</b> = niveau de stress global du portefeuille,
        pondéré par les poids réellement détenus.<br>
        Ce n'est <b>pas une probabilité de baisse</b>.<br><br>
        <b>Règle pratique :</b> un SR élevé doit être confirmé par la
        persistance, la qualité des données et la validation historique
        avant de déclencher une réduction importante.
        </div>
        """, unsafe_allow_html=True)
        vt = ptf["valeur_totale"]
        world_value = sum(p["valeur"] for p in ptf["positions"] if p.get("ticker") in WORLD_CORE_TICKERS)
        korea_value = sum(p["valeur"] for p in ptf["positions"] if p.get("ticker") == "KRW.PA")
        semi_value = sum(p["valeur"] for p in ptf["positions"] if p.get("ticker") == "CHIP.PA")
        value_value = sum(p["valeur"] for p in ptf["positions"] if p.get("ticker") in WORLD_VALUE_TICKERS)
        w_map = {"korea": korea_value / vt if vt else 0, "semi": semi_value / vt if vt else 0,
                 "world": world_value / vt if vt else 0, "value": value_value / vt if vt else 0}
        engine = RiskEngineV71(self.dm)
        with st.spinner("Calcul..."): result = engine.compute_all(w_map)
        c1, c2 = st.columns(2)
        c1.markdown(f'<div class="regime-banner" style="background:{result["regime_color"]}22;border:1px solid {result["regime_color"]};">'
                    f'🌐 RSG brut : <b>{result["rsg_raw"]:.2f}</b> — <b style="color:{result["regime_color"]};">{result["regime_label"]}</b></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="regime-banner regime-pending">⚖ RSG pondéré qualité : <b>{result["rsg_quality_weighted"]:.2f}</b></div>', unsafe_allow_html=True)
        labels = {"korea": "🇰🇷 Korea", "semi": "💻 Semiconductor", "world": "🌍 World", "value": "💎 World Value"}
        for key in ["korea", "semi", "world", "value"]:
            d = result["per_etf"][key]; weight_pct = w_map.get(key, 0) * 100
            score_color = {0: "#22C55E", 1: "#3B82F6", 2: "#F97316", 3: "#FF3131"}[d["confirmed_score"]]
            st.markdown(f'<div class="card" style="border-left:4px solid {score_color};">'
                        f'<div style="font-weight:700;font-size:1.05rem;">{labels[key]} — SR {d["confirmed_score"]}/3</div>'
                        f'<div style="margin-top:.4rem;">Exposition : <b>{weight_pct:.1f}%</b> · Réduction : <b>{d["reduction_pct"]:.0f}%</b></div>'
                        f'<div style="margin-top:.3rem;font-size:.78rem;color:#6B7585;">DQ : <b>{d["dq"]*100:.0f}%</b> · Persistance : {d["persistence_pct"]:.0f}%</div></div>', unsafe_allow_html=True)
        st.caption("⚠️ Les pourcentages de réduction affichés sont des scénarios de gestion du risque, "
                   "pas des probabilités ni des recommandations mathématiquement certaines. Leur pertinence "
                   "doit être vérifiée dans « Validation historique » et « Optimisation de la réduction ».")

    def render_risk_v71_validation(self):
        st.markdown("## 🧪 Validation historique")
        st.markdown(VALIDATION_SECTION_GLOSSARY)
        st.markdown(RISK_ENGINE_MDD_GLOSSARY)
        backtester = RiskEngineV71Backtester(self.dm)
        labels = {"korea": "🇰🇷 Korea", "semi": "💻 Semiconductor", "world": "🌍 World", "value": "💎 World Value"}
        for key, label in labels.items():
            st.markdown(f"### {label}")
            with st.spinner(f"Calcul — {label}..."): res = backtester.run(key)
            if not res.get("available"): st.warning(res.get("reason", "Indisponible")); continue
            st.caption(f"{res['n_days']} jours analysés")
            st.dataframe(res["stats_display"], use_container_width=True, hide_index=True)

    def render_risk_v71_optimizer(self, ptf):
        st.markdown("## 🎯 Optimisation de la réduction")
        st.markdown(OPTIMIZATION_SECTION_GLOSSARY)
        trigger = st.select_slider("Déclencher à partir du score :", options=[1, 2, 3], value=2)
        optimizer = ReductionOptimizer(self.dm)
        labels = {"korea": "🇰🇷 Korea", "semi": "💻 Semiconductor", "world": "🌍 World", "value": "💎 World Value"}
        for key, label in labels.items():
            st.markdown(f"### {label} — SR≥{trigger}")
            with st.spinner(f"Grid search — {label}..."): res = optimizer.run_for_engine(key, trigger_score=trigger)
            if not res.get("available"): st.warning(res.get("reason", "Indisponible")); continue
            st.dataframe(res["grid"], use_container_width=True, hide_index=True)
            bh = res["buyhold"]
            st.caption(f"Buy&Hold : CAGR {bh['cagr_pct']:.1f}% · MaxDD {bh['max_dd_pct']:.1f}% · Calmar {bh['calmar']:.2f}")
            if not res["reliable"]:
                st.error(f"🔴 Seulement {res['n_signal_days']} jours de signal sur {res['n_days']} jours.")
            else:
                st.success(f"✅ {res['n_signal_days']} jours de signal — échantillon suffisant.")
            grid = res["grid"].copy()
            if "Calmar" in grid.columns:
                calmar_numeric = pd.to_numeric(grid["Calmar"], errors="coerce")
                if calmar_numeric.notna().any():
                    best_idx = calmar_numeric.idxmax(); best_row = grid.loc[best_idx]
                    st.markdown(f'<div class="pedagogy-box"><b>🧭 Lecture automatique :</b><br><br>'
                                f'La meilleure zone historique selon le <b>Calmar</b> est : '
                                f'<b>{best_row.get("Réduction", "N/A")}</b>.<br><br>'
                                f'⚠️ Ce résultat ne constitue pas une recommandation automatique. '
                                f'Il doit être confirmé par le nombre de signaux, la validation historique, '
                                f'la persistance du SR et la qualité des données.</div>', unsafe_allow_html=True)

    def render_footer(self, mode_direct, capital, score_em, regime_label, live_ok, live_total):
        st.markdown("---")
        col_f1, col_f2 = st.columns([4, 1])
        with col_f1:
            mode_txt = "🔌 MODE DIRECT" if mode_direct else "Ajust. patrimonial actif"
            persist = "GitHub Gist + SQLite" if self.pm.status == "github" else "SQLite local"
            st.caption(f"◈ Cockpit v8.4 · Strategic Decision Engine · {mode_txt} · Régime : {regime_label} · "
                       f"Capital {capital:,.2f}€ · {persist} · {live_ok}/{live_total} prix live · "
                       "Benchmark : MWR Cash-Flow Adjusted · Outil personnel — Ne constitue pas un conseil en investissement")
        with col_f2:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.cache_data.clear(); st.rerun()

# -----------------------------------------------------------------------------
# MODULE 17 : MAIN
# -----------------------------------------------------------------------------
def _load_config():
    defaults = {"capital_reel": _DEFAULT_CAPITAL_REEL, "ajustement_pat": _DEFAULT_AJUSTEMENT_PAT, "bonus_fortuneo": _DEFAULT_BONUS_FORTUNEO}
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f: data = json.load(f)
            return {**defaults, **{k: float(v) for k, v in data.items() if k in defaults and not isinstance(v, list)}}
    except Exception: pass
    return defaults

def _save_config(capital_reel, ajustement_pat, bonus_fortuneo):
    try:
        existing = {}
        if os.path.exists(_CONFIG_PATH):
            try:
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f: existing = json.load(f)
            except Exception: pass
        existing["capital_reel"] = round(capital_reel, 2); existing["ajustement_pat"] = round(ajustement_pat, 2)
        existing["bonus_fortuneo"] = round(bonus_fortuneo, 2)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f: json.dump(existing, f, indent=2, ensure_ascii=False)
        return True
    except Exception: return False

def main():
    pcm = PortfolioConfigManager(); raw = pcm.load_positions(); pcm.save_positions(raw)
    st.session_state["raw_positions"] = raw; st.session_state["positions"] = enrich_positions(raw)
    tickers_in_positions = {pos["ticker"] for pos in st.session_state["positions"]}
    if "KRW.PA" not in tickers_in_positions or "CHIP.PA" not in tickers_in_positions:
        st.error("❌ KRW.PA ou CHIP.PA manquant. Réinitialisation forcée.")
        default_positions = [
            {"ticker": "WMMS.DE", "parts": 461.9561, "prm": 13.582, "account": "AV"},
            {"ticker": "DCAM.PA", "parts": 508.0000, "prm": 4.983, "account": "PEA"},
            {"ticker": "MWRD.PA", "parts": 16.6229, "prm": 149.718, "account": "AV"},
            {"ticker": "KRW.PA", "parts": 14.8501, "prm": 142.370, "account": "AV"},
            {"ticker": "CHIP.PA", "parts": 21.4922, "prm": 99.159, "account": "AV"},
        ]
        pcm.save_positions(default_positions); st.session_state["raw_positions"] = default_positions
        st.session_state["positions"] = enrich_positions(default_positions); st.rerun()
    if "config_loaded" not in st.session_state:
        cfg = _load_config()
        st.session_state["cfg_capital_reel"] = cfg["capital_reel"]
        st.session_state["cfg_ajustement_pat"] = cfg["ajustement_pat"]
        st.session_state["cfg_bonus_fortuneo"] = cfg["bonus_fortuneo"]
        st.session_state["config_loaded"] = True; st.session_state["save_feedback"] = ""
    with st.spinner("📡 Chargement..."):
        dm = DataManager()
        if not dm.live: st.error("❌ Aucun prix live."); st.stop()
        te = TransactionEngine(); pm = PersistenceManager(static_capital=st.session_state["cfg_capital_reel"])
        mre = MarketRegimeEngine(dm); qre = QuantRiskEngine(dm); pe = PortfolioEngine(dm, mre, qre)
        pde = PedagogicEngine(); se = StrategicEngine(dm, mre, qre)
        ui = StreamlitUI(dm, pm, mre, qre, pe, pde, se, pcm=pcm, te=te)
    mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo = ui.render_sidebar()
    with st.spinner("⚙ Calcul..."):
        ptf = pe.compute_portfolio(positions_conf, capital_reel, ajustement_pat, bonus_fortuneo)
        bench = pe.compute_benchmark(positions_conf, ptf["perf_tot_pct"])
        regime = mre.get_full_regime()

        # =====================================================================
        # v8.4 : SAUVEGARDE AUTOMATIQUE QUOTIDIENNE D'UN SNAPSHOT
        # Aucun clic requis. Une seule écriture par jour (SQLite + Gist).
        # =====================================================================
        try:
            today_str = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
            last_snap = pm.get_last_snapshot()
            if last_snap is None or last_snap.get("date") != today_str:
                pm.save_snapshot(
                    capital_cloture=ptf["valeur_totale"],
                    valeur_titres=ptf["valeur_totale"],
                    perf_jour=ptf["perf_j_pct"],
                    perf_cumul=ptf["perf_tot_pct"],
                    regime=regime["confirmed_label"],
                    score_regime=regime["confirmed_score"],
                    poids_sat=0.0,
                )
        except Exception:
            pass

        held_tickers = [p["ticker"] for p in positions_conf if p.get("ticker") and p["parts"] > 0]
        yf_held = []
        for tk_id in held_tickers:
            yf = ETF_LIBRARY.get(tk_id, {}).get("yf", tk_id)
            if yf and yf not in yf_held: yf_held.append(yf)
        opt_weights_cache = {"sharpe": {}, "sharpe_rc": {}, "minvar": {}, "rp": {}}
        if len(yf_held) >= 2:
            try:
                optimizer = PortfolioOptimizerEngine(dm)
                w_s = optimizer.max_sharpe_weights(yf_held); w_src = optimizer.max_sharpe_weights_rc_constrained(yf_held, rc_max=0.30)
                w_mv = optimizer.min_variance_weights(yf_held); w_rp = optimizer.risk_parity_weights(yf_held)
                yf_to_id = {ETF_LIBRARY[tid].get("yf", tid): tid for tid in held_tickers}
                if w_s: opt_weights_cache["sharpe"] = {yf_to_id.get(k, k): v for k, v in w_s.items()}
                if w_src: opt_weights_cache["sharpe_rc"] = {yf_to_id.get(k, k): v for k, v in w_src.items()}
                if w_mv: opt_weights_cache["minvar"] = {yf_to_id.get(k, k): v for k, v in w_mv.items()}
                if w_rp: opt_weights_cache["rp"] = {yf_to_id.get(k, k): v for k, v in w_rp.items()}
            except Exception as e: st.warning(f"Optimiseur : {type(e).__name__}: {e}")
        st.session_state["_opt_weights"] = opt_weights_cache
        wmms_gap = compute_relative_gap(dm, "WMMS.DE", days=15)
        etf_analyses = {}
        for pos in positions_conf:
            ticker = pos.get("ticker")
            if ticker:
                meta_tk = ETF_LIBRARY.get(ticker, {}); yf_ticker = meta_tk.get("yf", ticker)
                etf_analyses[ticker] = dm.analyze_ticker(yf_ticker)
        unified_scores = {}; target_weights = {}
        for pos in positions_conf:
            ticker = pos.get("ticker")
            if ticker:
                unified_scores[ticker] = pe.compute_unified_score(ticker)
                target_weights[ticker] = pe.compute_target_weight(pos["nom"], ticker, ptf["valeur_totale"],
                                                                    ptf["positions"], unified_precomputed=unified_scores[ticker])
        ld_alerts = pe.check_leadership_alerts(); phase_text, phase_color = pe.determine_phase(bench.get("gap"), etf_analyses or {})
        _, _, sent_rows = pe.evaluate_sentinelles()
        live_ok = sum(1 for v in dm.live.values() if v.get("prix")); live_total = len(dm.live)
        decisions = compute_all_position_decisions(ui, ptf)

    tab_dashboard, tab_transactions, tab_screener, tab_backtest, tab_risk_v71 = st.tabs(
        ["📊 Dashboard", "📈 Transactions", "🔍 Screener", "🧪 Backtest & Calibration", "🛡 Risk Engine v7.1"])

    with tab_dashboard:
        ui.render_header(mode_direct, live_ok, live_total)
        ui.render_command_center(ptf, bench, mode_direct, pm)
        ui.render_portfolio_leadership_comparison(ptf)
        st.markdown("---")
        render_glossary_expander(STRATEGIC_DECISION_GLOSSARY, title="📖 Comment lire la décision stratégique V8", expanded=False)
        strategic_decision = ui.render_strategic_decision(ptf, benchmark_gap=bench.get("gap"))
        ui.render_regime_banner(regime)
        for al in ld_alerts:
            gv, nom_al = al["gap"], al["nom"]; s = StreamlitUI._sign
            if gv < -5:
                st.markdown(f'<div class="alert-box">🚨 <b>ALERTE : {nom_al}</b> — {abs(gv):.1f}% en retard sur le World sur 14 jours</div>', unsafe_allow_html=True)
        ui.render_equity_curve_section(ptf, regime, positions_conf)
        ui.render_optimal_allocation_section(ptf)
        ui.render_sleeve_analysis(ptf)
        ui.render_risk_dashboard(ptf)
        st.markdown("## 🧠 Analyse des ETF Satellites")
        wmms_pos = next((p for p in positions_conf if p.get("ticker") == "WMMS.DE"), None)
        if wmms_pos:
            ticker = "WMMS.DE"
            ui.render_satellite_card_pedagogic("WMMS Value", "WMMS.DE", unified_scores.get(ticker, {}),
                                                target_weights.get(ticker, {}), regime, sent_rows, "value", gap_vs_world=wmms_gap)
        krw_pos = next((p for p in positions_conf if p.get("ticker") == "KRW.PA"), None)
        if krw_pos:
            krw_gap = compute_relative_gap(dm, "KRW.PA", days=15)
            ui.render_satellite_card_pedagogic("MSCI Korea", "KRW.PA", unified_scores.get("KRW.PA", {}),
                                                target_weights.get("KRW.PA", {}), regime, sent_rows, "korea", gap_vs_world=krw_gap)
        chip_pos = next((p for p in positions_conf if p.get("ticker") == "CHIP.PA"), None)
        if chip_pos:
            chip_gap = compute_relative_gap(dm, "CHIP.PA", days=15)
            ui.render_satellite_card_pedagogic("MSCI Semiconductors", "CHIP.PA", unified_scores.get("CHIP.PA", {}),
                                                target_weights.get("CHIP.PA", {}), regime, sent_rows, "chip", gap_vs_world=chip_gap)
        ui.render_sentinelles_macro(ptf)
        ui.render_quant_alert_v2(decisions)
        ui.render_long_term_cockpit(ptf, AnalyticsEngine(dm), regime)
        ui.render_fiscal_simulator(ptf)
        ui.render_footer(mode_direct, capital_reel, 0, regime["confirmed_label"], live_ok, live_total)

    with tab_transactions: ui.render_transactions_tab()
    with tab_screener: ui.render_screener_tab()
    with tab_backtest: ui.render_backtest_calibration_tab(ptf)
    with tab_risk_v71:
        sub_live, sub_valid, sub_optim = st.tabs(["📡 Scores en direct", "🧪 Validation historique", "🎯 Optimisation réduction"])
        with sub_live: ui.render_risk_engine_v71(ptf)
        with sub_valid: ui.render_risk_v71_validation()
        with sub_optim: ui.render_risk_v71_optimizer(ptf)

if __name__ == "__main__" or True:
    main()
