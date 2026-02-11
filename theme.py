"""
StormOps Tactical Theme
Shared CSS theme for all pages
"""


def get_theme_css():
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    :root {
        --background: 0 0% 0%;
        --foreground: 0 0% 100%;
        --amber: #f59e0b;
        --zinc-900: #09090b;
        --zinc-800: #18181b;
        --zinc-700: #27272a;
        --zinc-600: #3f3f46;
        --zinc-500: #52525b;
        --zinc-400: #71717a;
        --zinc-300: #a1a1aa;
    }
    
    .stApp {
        background-color: #000;
        background-image: 
            repeating-linear-gradient(
                45deg,
                transparent,
                transparent 2px,
                rgba(24, 24, 27, 0.4) 2px,
                rgba(24, 24, 27, 0.4) 4px
            ),
            repeating-linear-gradient(
                -45deg,
                transparent,
                transparent 2px,
                rgba(24, 24, 27, 0.4) 2px,
                rgba(24, 24, 27, 0.4) 4px
            ),
            linear-gradient(
                to bottom,
                #09090b,
                #18181b
            );
        background-attachment: fixed;
        font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }
    
    html, body, [class*="css"] {
        font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
    }
    
    .carbon-plate {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        box-shadow: 
            inset 0 1px 0 rgba(251, 191, 36, 0.1),
            inset 0 -1px 0 rgba(0, 0, 0, 0.5),
            0 2px 4px rgba(0, 0, 0, 0.3);
        border: 1px solid #27272a;
    }
    
    .carbon-plate-deep {
        background: linear-gradient(135deg, #09090b 0%, #000 100%);
        box-shadow: 
            inset 0 2px 4px rgba(0, 0, 0, 0.6),
            inset 0 -1px 0 rgba(251, 191, 36, 0.05),
            0 4px 8px rgba(0, 0, 0, 0.4);
        border: 1px solid #27272a;
    }
    
    .main-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: -0.02em;
        text-transform: uppercase;
        font-style: italic;
    }
    
    .section-header {
        font-size: 0.7rem;
        font-weight: 700;
        color: #71717a;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        padding: 1rem;
    }
    
    .metric-card:hover {
        border-color: #f59e0b;
    }
    
    .action-card {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
    }
    
    .action-card:hover {
        border-color: #f59e0b;
    }
    
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 0;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .status-healthy {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid #10b981;
        color: #10b981;
    }
    
    .status-degraded {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid #f59e0b;
        color: #f59e0b;
    }
    
    .status-offline {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid #ef4444;
        color: #ef4444;
    }
    
    .sidebar-section {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        padding: 1rem;
    }
    
    .tier-badge {
        display: inline-block;
        padding: 2px 8px;
        font-size: 0.6rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-radius: 0;
    }
    
    .tier-a { 
        background: rgba(220, 38, 38, 0.15); 
        border: 1px solid #dc2626; 
        color: #dc2626; 
    }
    .tier-b { 
        background: rgba(249, 115, 22, 0.15); 
        border: 1px solid #f97316; 
        color: #f97316; 
    }
    .tier-c { 
        background: rgba(234, 179, 8, 0.15); 
        border: 1px solid #eab308; 
        color: #eab308; 
    }
    .tier-d { 
        background: rgba(34, 197, 94, 0.15); 
        border: 1px solid #22c55e; 
        color: #22c55e; 
    }
    
    .stButton > button {
        border-radius: 0;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        transition: all 0.15s ease;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        padding: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 0;
        font-weight: 600;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background: transparent;
        border: 1px solid transparent;
        color: #71717a;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: rgba(245, 158, 11, 0.15);
        border: 1px solid #f59e0b;
        color: #f59e0b;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.25rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #71717a;
    }
    
    .lead-card {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        padding: 1rem;
    }
    
    .lead-card:hover {
        border-color: #f59e0b;
    }
    
    .divider {
        border-top: 1px solid #27272a;
        margin: 1.5rem 0;
    }
    
    .caption-text {
        color: #71717a;
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .stSelectbox > div > div {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        border-radius: 0;
    }
    
    .stNumberInput > div > div {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        border-radius: 0;
    }
    
    .stMultiSelect > div > div {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        border-radius: 0;
    }
    
    .stSlider [data-baseweb="slider"] {
        background: #27272a;
    }
    
    .stSlider [data-baseweb="slider"] > div > div {
        background: #f59e0b;
    }
    
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #09090b;
        border-left: 1px solid #27272a;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #3f3f46 0%, #27272a 100%);
        border: 1px solid #18181b;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #52525b 0%, #3f3f46 100%);
    }
    
    .stDataFrame {
        border: 1px solid #27272a;
        border-radius: 0;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #09090b 0%, #000 100%);
        border-right: 1px solid #27272a;
    }
    
    .stAlert {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        border-radius: 0;
        color: #a1a1aa;
    }
    
    [data-testid="stExpander"] {
        background: linear-gradient(135deg, #18181b 0%, #09090b 100%);
        border: 1px solid #27272a;
        border-radius: 0;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #fff !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    .stMarkdown {
        color: #a1a1aa;
    }
    
    .stMarkdown p {
        color: #a1a1aa;
    }
</style>
"""


def apply_theme(st):
    st.markdown(get_theme_css(), unsafe_allow_html=True)
