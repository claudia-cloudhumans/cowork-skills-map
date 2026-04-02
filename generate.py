#!/usr/bin/env python3
"""
Gerador do Skills Map — Cloud Humans Cowork
Lê os SKILL.md de cada skill e gera o index.html atualizado.
"""

import os
import json
import re
import glob
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "index.html")

# ── Carregar config ─────────────────────────────────────────────────────────
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

SKILL_AREAS  = config["skill_areas"]
SKILL_META   = config["skill_meta"]
AREA_LABELS  = config["area_labels"]
SKILLS_BASE  = config["skills_base_path"]

# ── Descobrir e ler skills ──────────────────────────────────────────────────
def read_skill_md(skill_dir):
    """Lê o SKILL.md e extrai nome, descrição e trigger hints."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return None
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    # Extrai frontmatter
    name = ""
    description = ""
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        if name_match:
            name = name_match.group(1).strip()
        desc_match = re.search(r"^description:\s*[>|]?\s*\n((?:[ \t]+.+\n?)+)", fm, re.MULTILINE)
        if desc_match:
            raw = desc_match.group(1)
            description = " ".join(line.strip() for line in raw.strip().splitlines())
        else:
            desc_inline = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
            if desc_inline:
                description = desc_inline.group(1).strip()

    # Fallback: nome da pasta
    if not name:
        name = os.path.basename(skill_dir)

    # Extrair trigger hints da descrição (entre aspas)
    triggers = re.findall(r'"([^"]{5,60})"', description)[:3]

    # Limpar descrição para exibição (remover exemplos de trigger e cortar)
    clean_desc = re.sub(r'Use (?:esta skill |esta skill )?(?:SEMPRE|sempre) que[^\.]+\.', '', description)
    clean_desc = re.sub(r'(?:Trigger|Gatilho)[s]?[:\s][^\.]+\.', '', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
    # Pegar os primeiros ~220 chars
    if len(clean_desc) > 220:
        cut = clean_desc[:220].rsplit(' ', 1)[0]
        clean_desc = cut + "…"

    return {
        "name": name,
        "description": clean_desc or description[:200],
        "triggers": triggers,
    }


def collect_skills():
    """Retorna lista de dicts com todos os dados de cada skill."""
    skills = []

    if not os.path.isdir(SKILLS_BASE):
        print(f"[WARN] Diretório de skills não encontrado: {SKILLS_BASE}")
        return skills

    for entry in sorted(os.scandir(SKILLS_BASE), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        skill_key = entry.name
        skill_data = read_skill_md(entry.path)
        if not skill_data:
            continue

        areas = SKILL_AREAS.get(skill_key, ["gen"])
        meta  = SKILL_META.get(skill_key, {"icon": "⚡", "type": "Skill", "auto": False})

        skills.append({
            "key":         skill_key,
            "name":        skill_data["name"],
            "description": skill_data["description"],
            "triggers":    skill_data["triggers"],
            "areas":       areas,
            "icon":        meta.get("icon", "⚡"),
            "type":        meta.get("type", "Skill"),
            "auto":        meta.get("auto", False),
        })

    return skills


# ── Contar skills por área ──────────────────────────────────────────────────
def area_counts(skills):
    counts = {k: 0 for k in AREA_LABELS}
    for s in skills:
        for a in s["areas"]:
            if a in counts:
                counts[a] += 1
    return counts


# ── Renderizar card HTML ────────────────────────────────────────────────────
AREA_COLORS = {
    "am":  ("#eef2ff", "#6366f1"),
    "ob":  ("#f0fdf4", "#22c55e"),
    "sup": ("#fffbeb", "#f59e0b"),
    "com": ("#fdf2f8", "#ec4899"),
    "gen": ("#f8fafc", "#64748b"),
}

AREA_TAG_CLASS = {
    "am":  "tag-am",
    "ob":  "tag-ob",
    "sup": "tag-sup",
    "com": "tag-com",
    "gen": "tag-gen",
}

def render_card(skill):
    areas_str = " ".join(skill["areas"])
    primary_area = skill["areas"][0] if skill["areas"] else "gen"
    icon_bg, _ = AREA_COLORS.get(primary_area, ("#f1f5f9", "#64748b"))

    if skill["triggers"]:
        joined_triggers = " · ".join(f'"{t}"' for t in skill["triggers"])
        trigger_html = f'<div class="card-trigger">{joined_triggers}</div>'
    else:
        trigger_html = ""

    tags_html = "".join(
        f'<span class="tag {AREA_TAG_CLASS.get(a, "tag-gen")}">{AREA_LABELS.get(a, a)}</span>'
        for a in skill["areas"]
    )

    auto_badge = '<span class="card-auto-badge">Automatizável</span>' if skill["auto"] else ""

    return f"""
    <div class="skill-card" data-areas="{areas_str}">
      <div class="card-header">
        <div class="card-icon" style="background:{icon_bg};">{skill["icon"]}</div>
        <div class="card-meta">
          <div class="card-name">{skill["name"]}</div>
          {trigger_html}
        </div>
      </div>
      <div class="card-desc">{skill["description"]}</div>
      <div class="card-tags">{tags_html}</div>
      <div class="card-footer">
        <span class="card-type">{skill["type"]}</span>
        {auto_badge}
      </div>
    </div>"""


def render_section(area_key, skills):
    area_skills = [s for s in skills if area_key in s["areas"]]
    if not area_skills:
        return ""
    cards_html = "\n".join(render_card(s) for s in area_skills)
    return f"""
  <div class="section-title" data-section="{area_key}">{AREA_LABELS[area_key]}</div>
  <div class="skills-grid">
    {cards_html}
  </div>"""


# ── Gerar HTML completo ─────────────────────────────────────────────────────
def generate_html(skills):
    counts = area_counts(skills)
    total  = len(skills)
    auto_count = sum(1 for s in skills if s["auto"])
    now    = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%Mh UTC")

    sections_html = "\n".join(render_section(a, skills) for a in AREA_LABELS)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Claude Cowork — Mapa de Skills</title>
  <style>
    :root {{
      --am:#6366f1; --am-light:#eef2ff;
      --ob:#22c55e; --ob-light:#f0fdf4;
      --sup:#f59e0b; --sup-light:#fffbeb;
      --com:#ec4899; --com-light:#fdf2f8;
      --gen:#64748b; --gen-light:#f8fafc;
      --bg:#f1f5f9; --card-bg:#ffffff;
      --text:#1e293b; --muted:#64748b; --border:#e2e8f0; --radius:14px;
    }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }}

    .header {{ background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%); padding:40px 48px 36px; color:white; }}
    .header-inner {{ max-width:1280px; margin:0 auto; }}
    .header-logo {{ font-size:13px; font-weight:600; letter-spacing:.12em; text-transform:uppercase; color:#94a3b8; margin-bottom:10px; }}
    .header h1 {{ font-size:32px; font-weight:700; letter-spacing:-.5px; margin-bottom:8px; }}
    .header p {{ font-size:15px; color:#94a3b8; max-width:560px; line-height:1.6; }}
    .header-stats {{ display:flex; gap:32px; margin-top:28px; }}
    .stat {{ display:flex; flex-direction:column; }}
    .stat-num {{ font-size:28px; font-weight:700; color:white; line-height:1; }}
    .stat-label {{ font-size:12px; color:#94a3b8; margin-top:4px; }}
    .updated {{ font-size:11px; color:#475569; margin-top:20px; }}

    .filters-bar {{ background:white; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:100; }}
    .filters-inner {{ max-width:1280px; margin:0 auto; padding:0 48px; display:flex; gap:4px; overflow-x:auto; scrollbar-width:none; }}
    .filters-inner::-webkit-scrollbar {{ display:none; }}
    .filter-btn {{ display:flex; align-items:center; gap:8px; padding:14px 20px; border:none; background:transparent; font-size:14px; font-weight:500; color:var(--muted); cursor:pointer; white-space:nowrap; border-bottom:3px solid transparent; transition:all .18s; }}
    .filter-btn:hover {{ color:var(--text); }}
    .filter-btn.active.all {{ border-bottom-color:#0f172a; color:#0f172a; }}
    .filter-btn.active.am  {{ border-bottom-color:var(--am);  color:var(--am);  }}
    .filter-btn.active.ob  {{ border-bottom-color:var(--ob);  color:var(--ob);  }}
    .filter-btn.active.sup {{ border-bottom-color:var(--sup); color:var(--sup); }}
    .filter-btn.active.com {{ border-bottom-color:var(--com); color:var(--com); }}
    .filter-btn.active.gen {{ border-bottom-color:var(--gen); color:var(--gen); }}
    .filter-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
    .filter-count {{ background:#f1f5f9; color:#64748b; font-size:12px; font-weight:600; padding:1px 7px; border-radius:99px; }}

    .main {{ max-width:1280px; margin:0 auto; padding:36px 48px; }}
    .section-title {{ font-size:12px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:20px; margin-top:40px; display:flex; align-items:center; gap:10px; }}
    .section-title:first-of-type {{ margin-top:0; }}
    .section-title::after {{ content:''; flex:1; height:1px; background:var(--border); }}
    .skills-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:20px; }}

    .skill-card {{ background:var(--card-bg); border:1px solid var(--border); border-radius:var(--radius); padding:24px; display:flex; flex-direction:column; gap:14px; transition:box-shadow .2s,transform .2s; cursor:default; }}
    .skill-card:hover {{ box-shadow:0 8px 24px rgba(0,0,0,.09); transform:translateY(-2px); }}
    .skill-card.hidden {{ display:none; }}
    .card-header {{ display:flex; align-items:flex-start; gap:14px; }}
    .card-icon {{ width:44px; height:44px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:22px; flex-shrink:0; }}
    .card-meta {{ flex:1; min-width:0; }}
    .card-name {{ font-size:15px; font-weight:700; color:var(--text); line-height:1.3; }}
    .card-trigger {{ font-size:12px; color:var(--muted); margin-top:3px; font-style:italic; }}
    .card-desc {{ font-size:13.5px; color:#475569; line-height:1.6; }}
    .card-tags {{ display:flex; flex-wrap:wrap; gap:6px; }}
    .tag {{ font-size:11px; font-weight:600; padding:3px 10px; border-radius:99px; letter-spacing:.04em; }}
    .tag-am  {{ background:var(--am-light);  color:var(--am); }}
    .tag-ob  {{ background:var(--ob-light);  color:#15803d; }}
    .tag-sup {{ background:var(--sup-light); color:#b45309; }}
    .tag-com {{ background:var(--com-light); color:#be185d; }}
    .tag-gen {{ background:var(--gen-light); color:var(--gen); border:1px solid var(--border); }}
    .card-footer {{ display:flex; align-items:center; gap:8px; padding-top:2px; }}
    .card-type {{ font-size:11px; font-weight:600; padding:3px 10px; border-radius:6px; background:#f8fafc; color:#64748b; border:1px solid #e2e8f0; }}
    .card-auto-badge {{ font-size:11px; font-weight:600; padding:3px 10px; border-radius:6px; background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; }}

    .legend {{ background:white; border:1px solid var(--border); border-radius:var(--radius); padding:20px 24px; margin-bottom:32px; display:flex; flex-wrap:wrap; gap:20px; align-items:center; }}
    .legend-label {{ font-size:12px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; flex-shrink:0; }}
    .legend-items {{ display:flex; flex-wrap:wrap; gap:10px; }}
    .legend-item {{ display:flex; align-items:center; gap:7px; font-size:13px; color:var(--text); }}
    .legend-dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}
    .empty-state {{ text-align:center; padding:60px 20px; color:var(--muted); display:none; }}
    .empty-state.visible {{ display:block; }}

    @media (max-width:768px) {{
      .header {{ padding:28px 24px; }}
      .filters-inner {{ padding:0 24px; }}
      .main {{ padding:24px; }}
      .skills-grid {{ grid-template-columns:1fr; }}
      .header-stats {{ gap:20px; }}
      .header h1 {{ font-size:24px; }}
    }}
  </style>
</head>
<body>
<div class="header">
  <div class="header-inner">
    <div class="header-logo">Cloud Humans · ClaudIA Cowork</div>
    <h1>🗺️ Mapa de Skills</h1>
    <p>Tudo que o time pode automatizar ou delegar para o Claude Cowork. Filtre por área para ver as skills relevantes ao seu contexto.</p>
    <div class="header-stats">
      <div class="stat"><span class="stat-num">{total}</span><span class="stat-label">skills disponíveis</span></div>
      <div class="stat"><span class="stat-num">{len(AREA_LABELS)}</span><span class="stat-label">áreas cobertas</span></div>
      <div class="stat"><span class="stat-num">{auto_count}</span><span class="stat-label">automatizáveis</span></div>
    </div>
    <div class="updated">⟳ Atualizado automaticamente em {now}</div>
  </div>
</div>

<div class="filters-bar">
  <div class="filters-inner">
    <button class="filter-btn active all" data-filter="all" onclick="filterSkills('all',this)">
      <span class="filter-dot" style="background:#0f172a"></span> Todas as Áreas
      <span class="filter-count">{total}</span>
    </button>
    <button class="filter-btn am" data-filter="am" onclick="filterSkills('am',this)">
      <span class="filter-dot" style="background:var(--am)"></span> Account Management
      <span class="filter-count">{counts['am']}</span>
    </button>
    <button class="filter-btn ob" data-filter="ob" onclick="filterSkills('ob',this)">
      <span class="filter-dot" style="background:var(--ob)"></span> Onboarding
      <span class="filter-count">{counts['ob']}</span>
    </button>
    <button class="filter-btn sup" data-filter="sup" onclick="filterSkills('sup',this)">
      <span class="filter-dot" style="background:var(--sup)"></span> Suporte
      <span class="filter-count">{counts['sup']}</span>
    </button>
    <button class="filter-btn com" data-filter="com" onclick="filterSkills('com',this)">
      <span class="filter-dot" style="background:var(--com)"></span> Comercial
      <span class="filter-count">{counts['com']}</span>
    </button>
    <button class="filter-btn gen" data-filter="gen" onclick="filterSkills('gen',this)">
      <span class="filter-dot" style="background:var(--gen)"></span> Produtividade Geral
      <span class="filter-count">{counts['gen']}</span>
    </button>
  </div>
</div>

<div class="main">
  <div class="legend">
    <span class="legend-label">Áreas:</span>
    <div class="legend-items">
      <div class="legend-item"><span class="legend-dot" style="background:var(--am)"></span> Account Management</div>
      <div class="legend-item"><span class="legend-dot" style="background:var(--ob)"></span> Onboarding</div>
      <div class="legend-item"><span class="legend-dot" style="background:var(--sup)"></span> Suporte</div>
      <div class="legend-item"><span class="legend-dot" style="background:var(--com)"></span> Comercial</div>
      <div class="legend-item"><span class="legend-dot" style="background:var(--gen)"></span> Produtividade Geral</div>
    </div>
    <div class="legend-items" style="margin-left:auto">
      <div class="legend-item"><span style="background:#eff6ff;color:#2563eb;font-size:11px;font-weight:600;padding:3px 10px;border-radius:6px;border:1px solid #bfdbfe;">Automatizável</span> pode ser agendada</div>
    </div>
  </div>

  <div class="empty-state" id="empty-state">
    <div style="font-size:40px;margin-bottom:12px">🔍</div>
    <div style="font-size:15px">Nenhuma skill encontrada para essa área.</div>
  </div>

  {sections_html}
</div>

<script>
  function filterSkills(area, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const cards = document.querySelectorAll('.skill-card');
    const sections = document.querySelectorAll('.section-title');
    if (area === 'all') {{
      cards.forEach(c => c.classList.remove('hidden'));
      sections.forEach(s => {{ s.style.display=''; if(s.nextElementSibling) s.nextElementSibling.style.display=''; }});
      document.getElementById('empty-state').classList.remove('visible');
      return;
    }}
    cards.forEach(card => {{
      card.classList.toggle('hidden', !card.dataset.areas.split(' ').includes(area));
    }});
    sections.forEach(s => {{
      const grid = s.nextElementSibling;
      const vis  = grid ? grid.querySelectorAll('.skill-card:not(.hidden)').length : 0;
      s.style.display = vis ? '' : 'none';
      if (grid) grid.style.display = vis ? '' : 'none';
    }});
    document.getElementById('empty-state').classList.toggle(
      'visible', !document.querySelectorAll('.skill-card:not(.hidden)').length
    );
  }}
</script>
</body>
</html>"""


# ── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    skills = collect_skills()
    html   = generate_html(skills)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html gerado com {len(skills)} skills em {OUTPUT_PATH}")
