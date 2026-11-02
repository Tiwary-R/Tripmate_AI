"""Travel theme for TripMate AI (Streamlit) - painted mountain edition.

Usage, right after st.set_page_config(...):

    from travel_agent.ui_theme import apply_travel_theme, login_hero, chat_hero
    apply_travel_theme()

    login_hero()            # on the login screen, above the tabs
    chat_hero(user_name)    # on the planner screen, replaces st.title(...)

The hero scene and the background watermark are inline SVGs (data URIs), so
they render fully offline.
"""

import urllib.parse

import streamlit as st


# --------------------------------------------------------------------------
# Painted landscape (SVG). Rough edges come from a turbulence displacement
# filter, which makes the flat shapes look like watercolor washes.
# --------------------------------------------------------------------------
def _landscape_svg() -> str:
    return """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 520' preserveAspectRatio='xMidYMax slice'>
<defs>
  <linearGradient id='sky' x1='0' y1='0' x2='0' y2='1'>
    <stop offset='0' stop-color='#12394F'/>
    <stop offset='0.45' stop-color='#2F7F95'/>
    <stop offset='0.8' stop-color='#9CCFD0'/>
    <stop offset='1' stop-color='#F8D9A0'/>
  </linearGradient>
  <linearGradient id='far' x1='0' y1='0' x2='0' y2='1'>
    <stop offset='0' stop-color='#A3C7D7'/><stop offset='1' stop-color='#6FA3B8'/>
  </linearGradient>
  <linearGradient id='mid' x1='0' y1='0' x2='0' y2='1'>
    <stop offset='0' stop-color='#5E9DB0'/><stop offset='1' stop-color='#3D7F95'/>
  </linearGradient>
  <linearGradient id='near' x1='0' y1='0' x2='0' y2='1'>
    <stop offset='0' stop-color='#25677C'/><stop offset='1' stop-color='#17495C'/>
  </linearGradient>
  <radialGradient id='halo'>
    <stop offset='0' stop-color='#FFE2A8' stop-opacity='0.9'/>
    <stop offset='1' stop-color='#FFE2A8' stop-opacity='0'/>
  </radialGradient>
  <filter id='paint' x='-5%' y='-5%' width='110%' height='110%'>
    <feTurbulence type='fractalNoise' baseFrequency='0.013' numOctaves='3' seed='4' result='n'/>
    <feDisplacementMap in='SourceGraphic' in2='n' scale='18' xChannelSelector='R' yChannelSelector='G' result='d'/>
    <feGaussianBlur in='d' stdDeviation='0.7'/>
  </filter>
  <filter id='cloud' x='-20%' y='-100%' width='140%' height='300%'>
    <feTurbulence type='fractalNoise' baseFrequency='0.02' numOctaves='2' seed='9' result='n'/>
    <feDisplacementMap in='SourceGraphic' in2='n' scale='26' xChannelSelector='R' yChannelSelector='G' result='d'/>
    <feGaussianBlur in='d' stdDeviation='5'/>
  </filter>
  <filter id='grain' x='0' y='0' width='100%' height='100%'>
    <feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='8'/>
    <feColorMatrix type='matrix' values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  1.3 0 0 0 -0.5'/>
  </filter>
</defs>

<rect width='1600' height='520' fill='url(#sky)'/>
<circle cx='1180' cy='262' r='170' fill='url(#halo)'/>
<circle cx='1180' cy='262' r='58' fill='#F5A524' filter='url(#paint)' opacity='0.95'/>

<g filter='url(#cloud)' fill='#FFFFFF'>
  <ellipse cx='420' cy='120' rx='190' ry='13' opacity='0.28'/>
  <ellipse cx='930' cy='85'  rx='230' ry='11' opacity='0.22'/>
  <ellipse cx='1380' cy='150' rx='170' ry='12' opacity='0.30'/>
  <ellipse cx='700' cy='200' rx='140' ry='9' opacity='0.20'/>
</g>

<g filter='url(#paint)'>
  <path fill='url(#far)' d='M-40,600 L-40,300 L120,250 L210,285 L330,190 L440,270 L520,235 L640,310 L760,220 L880,300 L990,200 L1100,285 L1220,238 L1340,300 L1450,215 L1640,290 L1640,600 Z'/>
  <g fill='#FFFFFF' opacity='0.85'>
    <path d='M296,216 L330,190 L366,220 L344,213 L330,228 L314,214 Z'/>
    <path d='M730,244 L760,220 L792,248 L772,242 L760,256 L746,243 Z'/>
    <path d='M958,226 L990,200 L1024,230 L1004,224 L990,240 L974,226 Z'/>
    <path d='M1420,238 L1450,215 L1482,242 L1464,237 L1450,252 L1436,238 Z'/>
  </g>
  <path fill='url(#mid)' d='M-40,600 L-40,385 L150,322 L260,372 L400,300 L520,366 L650,332 L780,392 L930,312 L1060,378 L1200,326 L1330,388 L1480,332 L1640,372 L1640,600 Z'/>
  <path fill='url(#near)' d='M-40,600 L-40,445 L180,392 L320,444 L470,386 L620,448 L800,412 L960,458 L1120,402 L1280,452 L1440,407 L1640,444 L1640,600 Z'/>
  <path fill='#0B2E3F' d='M-40,600 L-40,492 Q400,458 800,488 T1640,474 L1640,600 Z'/>
  <g fill='#0B2E3F'>
    <path d='M1340,500 L1362,430 L1384,500 Z'/><path d='M1380,500 L1406,418 L1432,500 Z'/>
    <path d='M1428,500 L1450,436 L1472,500 Z'/><path d='M130,500 L152,440 L174,500 Z'/>
    <path d='M170,500 L196,426 L222,500 Z'/>
  </g>
</g>

<rect width='1600' height='520' filter='url(#grain)' opacity='0.35'/>
</svg>"""


def _watermark_svg() -> str:
    """Seamless tile of line-art travel icons, drawn very faintly."""
    return """<svg xmlns='http://www.w3.org/2000/svg' width='420' height='420' viewBox='0 0 420 420'>
<g fill='none' stroke='#0F8B8D' stroke-opacity='0.13' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>

  <!-- dashed flight path -->
  <path d='M118,70 Q175,10 225,58' stroke-dasharray='2 7'/>
  <path d='M290,330 Q360,380 400,300' stroke-dasharray='2 7'/>

  <!-- airplane -->
  <g transform='translate(85,95) rotate(-35) scale(1.25)'>
    <path d='M0,-22 L4,-6 L22,6 L22,10 L4,5 L3,16 L8,20 L8,23 L0,21 L-8,23 L-8,20 L-3,16 L-4,5 L-22,10 L-22,6 L-4,-6 Z'/>
  </g>

  <!-- compass -->
  <g transform='translate(255,70)'>
    <circle r='19'/><path d='M0,-12 L5,0 L0,12 L-5,0 Z'/>
    <path d='M0,-19 L0,-23 M0,19 L0,23 M-19,0 L-23,0 M19,0 L23,0'/>
  </g>

  <!-- map pin -->
  <g transform='translate(372,150) rotate(10)'>
    <path d='M0,-20 C-11,-20 -16,-11 -16,-5 C-16,6 0,22 0,22 C0,22 16,6 16,-5 C16,-11 11,-20 0,-20 Z'/>
    <circle cx='0' cy='-6' r='5'/>
  </g>

  <!-- suitcase -->
  <g transform='translate(150,238) rotate(-8) scale(1.2)'>
    <rect x='-17' y='-10' width='34' height='25' rx='4'/>
    <path d='M-6,-10 L-6,-16 L6,-16 L6,-10 M-7,-10 L-7,15 M7,-10 L7,15'/>
  </g>

  <!-- camera -->
  <g transform='translate(330,285) rotate(8) scale(1.2)'>
    <rect x='-18' y='-10' width='36' height='24' rx='5'/>
    <circle cx='0' cy='2' r='7'/>
    <path d='M-6,-10 L-4,-15 L4,-15 L6,-10'/>
  </g>

  <!-- globe -->
  <g transform='translate(62,350) scale(1.1)'>
    <circle r='18'/><ellipse rx='7' ry='18'/><path d='M-18,0 L18,0 M-15,-9 L15,-9 M-15,9 L15,9'/>
  </g>

  <!-- mountains -->
  <g transform='translate(215,372) scale(1.2)'>
    <path d='M-20,14 L-6,-10 L2,2 L8,-6 L20,14 Z'/><path d='M-9,-4 L-6,-10 L-3,-5'/>
  </g>

  <!-- small stars / dots to fill the gaps -->
  <g stroke-opacity='0.10'>
    <path d='M25,200 l0,10 M20,205 l10,0'/><path d='M395,40 l0,10 M390,45 l10,0'/>
    <path d='M190,150 l0,8 M186,154 l8,0'/><path d='M300,200 l0,8 M296,204 l8,0'/>
  </g>
</g>
</svg>"""


def _data_uri(svg: str) -> str:
    return "url(\"data:image/svg+xml," + urllib.parse.quote(svg) + "\")"


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=DM+Sans:wght@400;500;700&display=swap');

:root {
  --ink:    #0B2E3F;
  --lagoon: #0F8B8D;
  --lagoon-dark: #0A6C6E;
  --mist:   #EAF6FB;
  --sunset: #F5A524;
  --line:   #CFE3EA;
  --scene:  __SCENE__;
  --watermark: __WATERMARK__;
}

/* ---------- Base ---------- */
html, body, [class*="css"], .stApp { font-family: 'DM Sans', sans-serif; color: var(--ink); }
[data-testid="stAppViewContainer"] {
  background-image: var(--watermark), linear-gradient(180deg, var(--mist) 0%, #FFFFFF 60%);
  background-size: 420px 420px, 100% 100%;
  background-repeat: repeat, no-repeat;
  background-attachment: fixed, fixed;
}
[data-testid="stHeader"] { background: transparent; }
h1, h2, h3 {
  font-family: 'Bricolage Grotesque', sans-serif !important;
  color: var(--ink);
  letter-spacing: -0.02em;
}

[data-testid="stBottom"] > div { background: transparent; }

/* ---------- Painted hero banner (login + planner) ---------- */
.tm-hero {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  padding: 64px 40px 150px;
  margin-bottom: 28px;
  color: #fff;
  background-image: var(--scene);
  background-size: cover;
  background-position: center bottom;
  background-color: #12394F;
}
.tm-hero::before {     /* keeps the headline readable on the left */
  content: "";
  position: absolute; inset: 0;
  background: linear-gradient(100deg, rgba(11,46,63,.55) 0%, rgba(11,46,63,.15) 55%, rgba(11,46,63,0) 100%);
}
.tm-hero > * { position: relative; }
.tm-hero h1 {
  color: #fff;
  font-size: clamp(2rem, 4.5vw, 3.4rem);
  line-height: 1.05;
  margin: 0 0 12px;
  padding: 0;
}
.tm-hero p { margin: 0; max-width: 34rem; font-size: 1.1rem; color: rgba(255,255,255,.95); }
.tm-hero.compact { padding: 36px 36px 120px; background-position: center 38%; }
.tm-hero.compact h1 { font-size: clamp(1.6rem, 3vw, 2.4rem); }

/* ---------- Tabs: pill style (login + result tabs) ---------- */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px; padding: 6px; border: 1px solid var(--line); border-radius: 999px;
  background: rgba(255,255,255,.85);
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab"] {
  height: auto; padding: 8px 16px; border-radius: 999px;
  font-weight: 500; color: var(--ink); background: transparent;
  transition: background .15s ease;
}
.stTabs [data-baseweb="tab"] p { color: var(--ink); font-weight: 500; margin: 0; }
.stTabs [data-baseweb="tab"]:hover { background: var(--mist); }
.stTabs [aria-selected="true"] { background: var(--lagoon) !important; }
.stTabs [aria-selected="true"] p { color: #FFFFFF !important; font-weight: 700; }
.stTabs [data-baseweb="tab"]:focus-visible { outline: 3px solid var(--sunset); outline-offset: 2px; }

/* The content under each result tab reads like a travel document */
.stTabs [data-baseweb="tab-panel"] {
  background: #FFFFFF; border: 1px solid var(--line); border-radius: 18px;
  margin-top: 14px; padding: 22px 26px; box-shadow: 0 10px 28px rgba(11,46,63,.06);
}
.stTabs [data-baseweb="tab-panel"] h1, .stTabs [data-baseweb="tab-panel"] h2,
.stTabs [data-baseweb="tab-panel"] h3 {
  padding-bottom: 6px; border-bottom: 3px solid var(--sunset); display: inline-block;
}

/* ---------- Login card ---------- */
[data-testid="stForm"] {
  background: #FFFFFF;
  border: 1.5px solid var(--line);
  border-top: 6px solid var(--lagoon);
  border-radius: 18px;
  padding: 26px 28px 24px;
  box-shadow: 0 12px 32px rgba(11,46,63,.08);
}

/* ---------- Inputs ---------- */
[data-baseweb="input"], [data-baseweb="base-input"] {
  border-radius: 12px !important;
  background: var(--mist) !important;
}
[data-baseweb="input"]:focus-within {
  border-color: var(--lagoon) !important;
  box-shadow: 0 0 0 3px rgba(15,139,141,.18);
}

/* ---------- Buttons ---------- */
.stButton > button, [data-testid="stFormSubmitButton"] > button, .stDownloadButton > button {
  background: var(--lagoon); color: #fff; border: none; border-radius: 12px;
  font-weight: 700; padding: .6rem 1rem; transition: background .15s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover, .stDownloadButton > button:hover {
  background: var(--lagoon-dark); color: #fff;
}
.stButton > button:focus-visible, [data-testid="stFormSubmitButton"] > button:focus-visible,
.stDownloadButton > button:focus-visible {
  outline: 3px solid var(--sunset); outline-offset: 2px;
}

/* ---------- Alerts: info = tip, plus success / warning / error ---------- */
[data-testid="stAlert"] {
  background: #FFF8EA; border: 1px solid #F6DDA8; border-left: 5px solid var(--sunset);
  border-radius: 12px; color: var(--ink);
}
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) {
  background: #E9F7F1; border-color: #BFE5D5; border-left-color: #1E9E6A;
}
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) {
  background: #FFF3DC; border-color: #F2CD85; border-left-color: #E08A00;
}
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {
  background: #FDECEA; border-color: #F3C2BC; border-left-color: #D64545;
}
[data-testid="stAlert"] * { color: var(--ink) !important; }

/* ---------- Chat ---------- */
[data-testid="stChatInput"] > div {
  background: #fff; border: 1.5px solid var(--line); border-radius: 999px;
  box-shadow: 0 6px 20px rgba(11,46,63,.08);
}
[data-testid="stChatInput"] > div:focus-within { border-color: var(--lagoon); }
[data-testid="stChatMessage"] {
  background: #fff; border: 1px solid var(--line); border-radius: 18px; padding: 14px 18px;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--mist); border-color: #BFDDE8;
}

/* ---------- Sidebar: deep ocean ---------- */
[data-testid="stSidebar"] { background: var(--ink); }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,  [data-testid="stSidebar"] span,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] li,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] { color: #E6F3F7; }
[data-testid="stSidebar"] code { background: rgba(255,255,255,.12); color: var(--sunset); }
[data-testid="stSidebar"] .stButton > button {
  background: transparent; color: #fff; border: 1.5px solid rgba(255,255,255,.35);
  text-align: left; justify-content: flex-start;
}
[data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,.12); border-color: #fff; }

/* ---------- Result widgets: budget numbers, details, tables ---------- */
[data-testid="stMetric"] {
  background: #fff; border: 1px solid var(--line); border-left: 5px solid var(--lagoon);
  border-radius: 14px; padding: 14px 18px;
}
[data-testid="stMetricLabel"] p { color: #3F6272; font-weight: 500; }
[data-testid="stMetricValue"] {
  font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; color: var(--ink);
}
[data-testid="stExpander"] {
  background: #fff; border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
}
[data-testid="stExpander"] summary:hover { background: var(--mist); }
[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
}
[data-testid="stSpinner"] i, [data-testid="stSpinner"] svg { border-top-color: var(--lagoon) !important; }
[data-testid="stProgress"] > div > div > div > div { background-color: var(--lagoon); }
hr { border-color: var(--line); }
a { color: var(--lagoon); }
a:hover { color: var(--lagoon-dark); }

/* Slim, on-theme scrollbars */
* { scrollbar-width: thin; scrollbar-color: #9CC9D2 transparent; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: #9CC9D2; border-radius: 8px; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
@media (max-width: 640px) {
  .tm-hero { padding: 40px 22px 110px; }
  .tm-hero.compact { padding: 28px 22px 90px; }
  .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
  /* Streamlit columns don't reflow on their own — force them to stack so the
     trip banner, score badge, export + HITL button rows aren't crushed. */
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 0.4rem; }
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    flex: 1 1 100% !important;
    min-width: 100% !important;
    width: 100% !important;
  }
}
</style>
"""


CHROME_CSS = """
<style>
[data-testid="stAppDeployButton"], .stDeployButton, footer { display: none !important; }
</style>
"""


def apply_travel_theme(hide_streamlit_chrome: bool = True) -> None:
    """Inject the travel theme CSS. Call once per run, after set_page_config.

    hide_streamlit_chrome: hides the "Deploy" button and footer (the three-dot menu stays).
    """
    css = CSS.replace("__SCENE__", _data_uri(_landscape_svg())).replace("__WATERMARK__", _data_uri(_watermark_svg()))
    st.markdown(css, unsafe_allow_html=True)
    if hide_streamlit_chrome:
        st.markdown(CHROME_CSS, unsafe_allow_html=True)


# Backwards-compatible alias for the previous entry point.
inject_css = apply_travel_theme


def login_hero() -> None:
    """Painted mountain banner for the login screen."""
    st.markdown(
        """
        <div class="tm-hero">
          <h1>Where to next?</h1>
          <p>TripMate AI plans your flights, hotels, weather and budget in one
             itinerary, for trips worldwide. Sign in to start.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chat_hero(user_name: str) -> None:
    """Slimmer painted banner for the planner screen."""
    st.markdown(
        f"""
        <div class="tm-hero compact">
          <h1>Hi {user_name}, where are we going? 🌍</h1>
          <p>Tell me your destination, origin, dates, budget and what you love.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
