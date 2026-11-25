"""M1 design system. No external font or image downloads required."""
from __future__ import annotations

CSS = '''
<style>
:root { --bv-bg:#07111f; --bv-card:#111f32; --bv-cyan:#4fdbeb; --bv-text:#e9f3fa; --bv-muted:#93a7be; }
html,body,[class*="css"], [data-testid="stApp"] { font-family: "Segoe UI", Inter, system-ui, sans-serif; }
[data-testid="stApp"] { background:radial-gradient(1000px 500px at 85% -20%, #123b52 0%, transparent 70%),#07111f; color:#e9f3fa; }
[data-testid="stSidebar"] { background:#0a182a; border-right:1px solid #23354a; }
[data-testid="stSidebar"] * { color:#dbe9f5; }
h1,h2,h3,h4 { color:#f1f9ff!important; letter-spacing:-.03em; }
p,li,label { color:#cad9e9; }
.bv-brand { display:flex;gap:12px;align-items:center;font-size:1.1rem;font-weight:800;letter-spacing:.03em;margin:8px 0 22px; }
.bv-brandmark { border:1px solid #42cedd;border-radius:12px;padding:8px 12px;background:#0c2b39;color:#5deaff; }
.bv-hero { border:1px solid #284a63;border-radius:22px;padding:30px;margin-bottom:1rem;background:linear-gradient(120deg,#132f48,#0b1b30 66%,#0e2632); }
.bv-hero h1 { font-size:2.55rem;line-height:1.08;max-width:760px;margin:4px 0 14px; }
.bv-hero p { color:#b7cce0;max-width:800px;line-height:1.7; }
[data-testid="stMetric"] { background:#101f31;border:1px solid #21394e;border-radius:14px;padding:10px; }
[data-testid="stAlert"] { border-radius:12px; }
[data-testid="stFileUploader"] { border-radius:12px; }
.stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"] { border:0;border-radius:10px;background:linear-gradient(100deg,#20b4cd,#397cea);font-weight:750;color:white; }
.stButton>button, .stDownloadButton>button { border-radius:10px; }
.st-key-workspace_region { container-type:inline-size; }
.st-key-workspace_actions [data-testid="stElementContainer"],
.st-key-workspace_actions .stButton {
    display:flex;
    flex:1;
    min-width:0;
}
.st-key-workspace_actions .stButton>button {
    flex:1;
    min-height:5.5rem;
    padding:.85rem 1rem;
    border:1px solid #263b50;
    border-radius:12px;
    background:#101e2f;
    color:#81cfdf;
    text-align:left;
    transition:border-color .15s ease,background-color .15s ease;
}
.st-key-workspace_actions .stButton>button>div {
    width:100%;
}
.st-key-workspace_actions .stButton>button>div>span {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:.65rem;
    width:100%;
}
.st-key-workspace_actions .stButton>button>div>span>:last-child {
    flex-shrink:0;
}
.st-key-workspace_actions .stButton>button:is(:hover,:focus-visible) {
    border-color:#6393a6;
    background:#172b3e;
    color:#a3e6f0;
}
.st-key-workspace_actions .stButton>button:focus-visible {
    outline:2px solid #79e0ef;
    outline-offset:2px;
}
.st-key-workspace_actions [data-testid="stMarkdownContainer"] {
    min-width:0;
    text-align:left;
}
.st-key-workspace_actions .stButton>button p {
    display:block;
    margin:0;
    color:#afc0d1;
    font-size:.825rem;
    font-weight:400;
    line-height:1.35;
}
.st-key-workspace_actions .stButton>button p + p {
    margin-top:.375rem;
}
.st-key-workspace_actions .stButton>button strong {
    color:#eff6ff;
    font-size:1rem;
    font-weight:650;
}

@container (max-width:55rem) {
    .st-key-workspace_actions { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@container (max-width:27rem) {
    .st-key-workspace_actions { grid-template-columns:minmax(0,1fr); }
}
@media (max-width:700px) { .bv-hero{padding:20px}.bv-hero h1{font-size:1.85rem} }
</style>
'''
