#!/usr/bin/env python3
"""
Gerador do Skills Map — Cloud Humans Cowork
Lê os SKILL.md de cada skill e gera o index.html atualizado.
"""

import os, json, re, html as html_module
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "index.html")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

SKILL_AREAS  = config["skill_areas"]
SKILL_META   = config["skill_meta"]
AREA_LABELS  = config["area_labels"]
SKILLS_BASE  = config["skills_base_path"]

# ── Detalhes para os modais ─────────────────────────────────────────────────
# output_type: plan | html-report | docx | slack | action | none
SKILL_DETAILS = {
  "ch-action-plan": {
    "prompt": "Plano de ação para o cliente [NOME DO CLIENTE]",
    "input": "Nome do cliente (o Claude busca no Metabase automaticamente) — ou cole métricas, suba um PDF do dashboard, ou descreva verbalmente a situação.",
    "output_label": "Plano de ação P0 / P1 / P2",
    "output_type": "plan",
    "output_preview": """
<div class="prev-plan">
  <div class="prev-plan-header">📋 Plano de Ação — <strong>Acme Corp</strong> <span class="prev-date">Semana 14</span></div>
  <div class="prev-plan-item p0">
    <div class="prev-priority">P0</div>
    <div class="prev-content">
      <strong>Taxa de Retenção N1 em 28% (abaixo do mínimo de 40%)</strong>
      <p>Ajustar FlowPrompt de "Cancelamento" — atualmente transfere para humano sem tentar reter. Ativar retentação automática com oferta de desconto no CloudBlocks.</p>
    </div>
  </div>
  <div class="prev-plan-item p1">
    <div class="prev-priority">P1</div>
    <div class="prev-content">
      <strong>18 motivos de N2 sem cobertura na IDS</strong>
      <p>Criar conteúdos para "Prazo de entrega expresso", "Rastreio internacional" e "Política de reembolso parcial". Estimativa de +6pp na retenção.</p>
    </div>
  </div>
  <div class="prev-plan-item p2">
    <div class="prev-priority">P2</div>
    <div class="prev-content">
      <strong>GenCX Score acima de 12%</strong>
      <p>Revisar 8 respostas marcadas como ruins na última semana. 3 delas estão num FlowPrompt desatualizado.</p>
    </div>
  </div>
</div>"""
  },
  "ch-qbr-review": {
    "prompt": "Preparar QBR do cliente [NOME DO CLIENTE] para o trimestre atual",
    "input": "Nome do cliente + trimestre (padrão: atual). Opcionalmente, pode enviar um PPTX existente para complementar.",
    "output_label": "Relatório QBR + PPTX atualizado",
    "output_type": "pptx",
    "output_preview": """
<div class="prev-slides">
  <div class="prev-slide active-slide">
    <div class="prev-slide-label">Slide gerado</div>
    <div class="prev-slide-title">Q1 2026 — Resultados</div>
    <div class="prev-slide-metrics">
      <div class="prev-metric"><span class="metric-val green">47%</span><span class="metric-lbl">Retenção N1</span></div>
      <div class="prev-metric"><span class="metric-val">4.6</span><span class="metric-lbl">CSAT médio</span></div>
      <div class="prev-metric"><span class="metric-val green">+12%</span><span class="metric-lbl">Vol. tickets</span></div>
    </div>
  </div>
  <div class="prev-slide-strip">
    <div class="strip-slide s1"></div>
    <div class="strip-slide s2"></div>
    <div class="strip-slide s3 sel"></div>
    <div class="strip-slide s4"></div>
  </div>
</div>"""
  },
  "ids-duplicate-analysis": {
    "prompt": "Analisar duplicatas na IDS do cliente [NOME]. Segue o CSV exportado da base.",
    "input": "Arquivo CSV exportado da IDS do cliente (do Hub ou Metabase) com colunas: id, title, response, type.",
    "output_label": "Relatório HTML com pares duplicados",
    "output_type": "html-report",
    "output_preview": """
<div class="prev-report">
  <div class="prev-report-header">🔍 IDS Duplicate Analysis — <strong>Acme Corp</strong></div>
  <div class="prev-report-stats">
    <span class="rst high">🔴 12 pares críticos</span>
    <span class="rst med">🟡 8 pares similares</span>
    <span class="rst low">⚪ 3 revisar</span>
  </div>
  <table class="prev-table">
    <tr><th>Conteúdo A</th><th>Conteúdo B</th><th>Score</th><th>Ação</th></tr>
    <tr><td>Como cancelar pedido?</td><td>Quero cancelar minha compra</td><td><span class="score high">97%</span></td><td><span class="act merge">Mesclar</span></td></tr>
    <tr><td>Prazo de entrega SP</td><td>Prazo de entrega capital</td><td><span class="score med">84%</span></td><td><span class="act review">Revisar</span></td></tr>
  </table>
</div>"""
  },
  "ids-gap-analysis": {
    "prompt": "Cruzar a IDS do cliente [NOME] com o diagnóstico. Segue o arquivo do diagnóstico.",
    "input": "IDS atual do cliente (CSV) + arquivo do Diagnóstico Comercial Automatizado (Curva ABC). Ambos obrigatórios.",
    "output_label": "Relatório de gaps com priorização",
    "output_type": "html-report",
    "output_preview": """
<div class="prev-report">
  <div class="prev-report-header">📐 IDS Gap Analysis — <strong>Acme Corp</strong></div>
  <div class="prev-report-stats">
    <span class="rst high">🔴 5 lacunas críticas</span>
    <span class="rst med">🟡 11 a adaptar</span>
    <span class="rst low">🟢 34 ok</span>
  </div>
  <table class="prev-table">
    <tr><th>Conteúdo Ideal (Diagnóstico)</th><th>Status na IDS</th><th>Impacto</th></tr>
    <tr><td>Rastreio de pedido internacional</td><td><span class="act merge">Ausente</span></td><td>Alto</td></tr>
    <tr><td>Política de troca sem nota fiscal</td><td><span class="act review">Desatualizado</span></td><td>Médio</td></tr>
    <tr><td>Parcelamento no boleto</td><td><span class="act ok">Presente</span></td><td>—</td></tr>
  </table>
</div>"""
  },
  "cs-task-gap-analysis": {
    "prompt": "Rodar o task gap analysis de CS — cruzar reuniões recentes com tasks abertas no Airtable",
    "input": "Sem input manual. O Claude acessa Fireflies (reuniões dos últimos 7 dias) e Airtable automaticamente.",
    "output_label": "Tasks criadas no Airtable + resumo",
    "output_type": "action",
    "output_preview": """
<div class="prev-action">
  <div class="prev-action-title">✅ Tasks criadas automaticamente</div>
  <div class="prev-action-item">
    <div class="act-badge created">Criada</div>
    <div class="act-text"><strong>Acme Corp</strong> — Ajustar FlowPrompt de cancelamento conforme combinado na reunião de 01/04 · Responsável: Marina · P1</div>
  </div>
  <div class="prev-action-item">
    <div class="act-badge created">Criada</div>
    <div class="act-text"><strong>Beta Ltda</strong> — Enviar acesso ao Hub para novo analista · Responsável: João · P2</div>
  </div>
  <div class="prev-action-item">
    <div class="act-badge skipped">Já existe</div>
    <div class="act-text"><strong>Gama SA</strong> — Revisão de IDS já registrada (#4821)</div>
  </div>
  <div class="prev-action-summary">3 reuniões analisadas · 2 tasks criadas · 1 já existia</div>
</div>"""
  },
  "daily-task-sync": {
    "prompt": "Rodar o daily task sync — atualizar tasks do Airtable com base nas reuniões e mensagens dos últimos 3 dias",
    "input": "Sem input. O Claude acessa Airtable, Fireflies e Slack automaticamente.",
    "output_label": "Tasks atualizadas + relatório no Slack",
    "output_type": "slack",
    "output_preview": """
<div class="prev-slack">
  <div class="prev-slack-header"><span class="slack-hash">#</span>ops-execucao-ia</div>
  <div class="prev-slack-msg">
    <div class="slack-avatar">🤖</div>
    <div class="slack-body">
      <span class="slack-name">ClaudIA</span><span class="slack-time">08:05</span>
      <div class="slack-text">📋 <strong>Daily Task Sync — 02/04</strong><br>
      ✅ 14 tasks verificadas<br>
      🔄 6 atualizadas com contexto de reuniões<br>
      🆕 2 novas tarefas identificadas<br>
      ⚠️ 1 cliente com task vencida: <strong>Acme Corp</strong></div>
    </div>
  </div>
</div>"""
  },
  "weekly-summary": {
    "prompt": "Gerar o relatório semanal da operação",
    "input": "Sem input. O Claude acessa Slack, Fireflies, Metabase e Airtable automaticamente para cobrir os últimos 7 dias.",
    "output_label": "Relatório executivo semanal (4 seções)",
    "output_type": "plan",
    "output_preview": """
<div class="prev-plan">
  <div class="prev-plan-header">📊 Weekly Summary — Semana 13 (24–30 Mar)</div>
  <div class="prev-plan-item p0" style="--pc:#6366f1">
    <div class="prev-priority" style="background:#eef2ff;color:#6366f1">📈</div>
    <div class="prev-content"><strong>Principais variações de métricas</strong><p>Retenção média da base: 44% (+2pp vs semana anterior). 3 clientes abaixo de 35%: Acme, Beta, Gama.</p></div>
  </div>
  <div class="prev-plan-item p1" style="--pc:#22c55e">
    <div class="prev-priority" style="background:#f0fdf4;color:#15803d">🏆</div>
    <div class="prev-content"><strong>Melhores conquistas</strong><p>Cliente Delta atingiu 60% de retenção pela 1ª vez. Novo onboarding do maior cliente do trimestre concluído.</p></div>
  </div>
  <div class="prev-plan-item p2" style="--pc:#f59e0b">
    <div class="prev-priority" style="background:#fffbeb;color:#b45309">🚨</div>
    <div class="prev-content"><strong>Problemas a priorizar</strong><p>Acme: queda de 15pp na retenção por bug no FlowPrompt. Beta: 3 reuniões sem follow-up registrado.</p></div>
  </div>
</div>"""
  },
  "aditivo-renovacao": {
    "prompt": "Fazer o aditivo de renovação do cliente [NOME]. [Cole o contrato original ou informe os dados manualmente]",
    "input": "PDF ou texto do contrato original (preferido) — ou informe manualmente: nome/CNPJ, valores vigentes, novo período, % IPCA, cláusula de fidelidade.",
    "output_label": "Documento .docx profissional",
    "output_type": "docx",
    "output_preview": """
<div class="prev-docx">
  <div class="prev-docx-header">
    <div class="docx-logo">CH</div>
    <div class="docx-title-block"><div class="docx-title">TERMO ADITIVO N.º 02</div><div class="docx-subtitle">Ao Contrato de Prestação de Serviços</div></div>
  </div>
  <div class="prev-docx-body">
    <p><strong>CONTRATANTE:</strong> Acme Corp Ltda, CNPJ 12.345.678/0001-99</p>
    <p><strong>CONTRATADA:</strong> Cloud Humans Tecnologia S.A.</p>
    <div class="docx-clause"><strong>Cláusula 1ª — Objeto:</strong> Prorrogação do contrato por 12 meses, de 01/05/2026 a 30/04/2027.</div>
    <div class="docx-clause"><strong>Cláusula 2ª — Reajuste:</strong> Valores reajustados em 5,83% (IPCA acum. 12 meses — Mar/26), passando de R$8.500 para <strong>R$8.995/mês</strong>.</div>
    <div class="docx-clause docx-clause-faded">Cláusula 3ª — Fidelidade · Cláusula 4ª — Rescisão · Assinaturas...</div>
  </div>
</div>"""
  },
  "cx-create-knowledge-base": {
    "prompt": "Criar KB a partir dos padrões de tickets das últimas 4 semanas",
    "input": "Período de análise (padrão: últimas 4 semanas). O Claude acessa o Unthread automaticamente.",
    "output_label": "Artigos KB prontos para subir na IDS",
    "output_type": "html-report",
    "output_preview": """
<div class="prev-report">
  <div class="prev-report-header">📚 KB gerada — <strong>12 novos conteúdos</strong></div>
  <div class="prev-report-stats">
    <span class="rst high">🔴 4 gaps críticos cobertos</span>
    <span class="rst med">🟡 8 melhorias</span>
  </div>
  <table class="prev-table">
    <tr><th>Pergunta gerada</th><th>Origem</th><th>Tipo</th></tr>
    <tr><td>Como rastrear pedido internacional?</td><td>47 tickets</td><td><span class="act ok">FAQ</span></td></tr>
    <tr><td>Prazo para estorno no cartão</td><td>31 tickets</td><td><span class="act ok">FAQ</span></td></tr>
    <tr><td>Pedido cancelado mas cobrado</td><td>18 tickets</td><td><span class="act merge">FlowPrompt</span></td></tr>
  </table>
</div>"""
  },
  "volumetry-alert": {
    "prompt": "Rodar o alerta de volumetria — checar se algum cliente caiu de volume hoje",
    "input": "Sem input. O Claude consulta o Metabase automaticamente (card 2080) e acessa os canais Slack dos clientes afetados.",
    "output_label": "Alerta no canal Slack do cliente (se houver queda)",
    "output_type": "slack",
    "output_preview": """
<div class="prev-slack">
  <div class="prev-slack-header"><span class="slack-hash">#</span>cs-acme-corp</div>
  <div class="prev-slack-msg">
    <div class="slack-avatar">🤖</div>
    <div class="slack-body">
      <span class="slack-name">ClaudIA</span><span class="slack-time">08:12</span>
      <div class="slack-text">⚠️ <strong>Alerta de volumetria</strong> — @marina<br>
      A Acme Corp recebeu <strong>142 tickets ontem</strong>, queda de <strong>-48%</strong> vs. média dos últimos 7 dias (274/dia).<br><br>
      🔍 <em>Investigação:</em> Retenção N1 estável (44%), sem erros de integração, CSAT normal.<br>
      📌 <strong>Possível causa:</strong> Feriado regional ou queda no tráfego do e-commerce.</div>
    </div>
  </div>
</div>"""
  },
  "unthread-resolved-sweep": {
    "prompt": "Varrer tickets resolvidos no Unthread e mover para o status correto",
    "input": "Sem input. O Claude acessa o Unthread via API e processa todas as conversas com status needs_response, in_progress e Em Execução.",
    "output_label": "Relatório de tickets movidos + skipped",
    "output_type": "action",
    "output_preview": """
<div class="prev-action">
  <div class="prev-action-title">🧹 Sweep concluído — 34 conversas analisadas</div>
  <div class="prev-action-item">
    <div class="act-badge created">Movido</div>
    <div class="act-text">Ticket #4821 — "Como integrar com Zendesk?" → <strong>Resolvido</strong> · Produto: Integração · Subproduto: Zendesk</div>
  </div>
  <div class="prev-action-item">
    <div class="act-badge created">Movido</div>
    <div class="act-text">Ticket #4808 — "FlowPrompt não salva" → <strong>Resolvido</strong> · Produto: Hub · Subproduto: FlowPrompt</div>
  </div>
  <div class="prev-action-item">
    <div class="act-badge skipped">Skipped</div>
    <div class="act-text">Ticket #4819 — "Erro na IDS ao importar CSV" → Aguardando resposta do cliente</div>
  </div>
  <div class="prev-action-summary">34 analisados · 22 movidos · 8 skipped · 4 para revisão humana</div>
</div>"""
  },
  "daily-board-cleanup": {
    "prompt": "Fazer o cleanup do board — triagem diária de tickets tech",
    "input": "Sem input. O Claude acessa o Unthread e o Azure Boards automaticamente.",
    "output_label": "Tickets escalados + relatório no Slack",
    "output_type": "action",
    "output_preview": """
<div class="prev-action">
  <div class="prev-action-title">🗂️ Board Cleanup — 28 tickets analisados</div>
  <div class="prev-action-item">
    <div class="act-badge created">Escalado</div>
    <div class="act-text"><strong>#4830</strong> — "Bug: ClaudIA responde em inglês para clientes PT-BR" → Board #1204 criado · Cliente notificado via Slack</div>
  </div>
  <div class="prev-action-item">
    <div class="act-badge review">Validar</div>
    <div class="act-text"><strong>#4826</strong> — "IDS não atualiza após salvar" → Possivelmente duplicata do #1198. Verificar antes de escalar.</div>
  </div>
  <div class="prev-action-item">
    <div class="act-badge skipped">Ignorado</div>
    <div class="act-text"><strong>#4822</strong> — "Dúvida sobre relatórios" → Não é tech, redirecionar para CS</div>
  </div>
  <div class="prev-action-summary">28 analisados · 4 escalados (HIGH) · 3 para validação (MED) · 21 ignorados</div>
</div>"""
  },
  "board-unthread-sync": {
    "prompt": "Rodar a sync do board com Unthread — verificar pendências de suporte",
    "input": "Sem input. O Claude acessa o Unthread (tickets on_hold) e o Azure Boards automaticamente.",
    "output_label": "Tickets fechados/respondidos + relatório no Slack",
    "output_type": "slack",
    "output_preview": """
<div class="prev-slack">
  <div class="prev-slack-header"><span class="slack-hash">#</span>suporte-execucao-ia</div>
  <div class="prev-slack-msg">
    <div class="slack-avatar">🤖</div>
    <div class="slack-body">
      <span class="slack-name">ClaudIA</span><span class="slack-time">09:04</span>
      <div class="slack-text">🔗 <strong>Board Sync — 02/04</strong><br>
      ✅ <strong>#4801</strong> Board #1190 → <em>Done</em>. Ticket fechado e cliente notificado com explicação da correção.<br>
      💬 <strong>#4815</strong> Board #1198 → <em>In Review</em>. Perguntei ao cliente se o problema persiste após o deploy de ontem.<br>
      ⚠️ <strong>#4820</strong> Sem board vinculado — @suporte favor verificar manualmente.</div>
    </div>
  </div>
</div>"""
  },
  "cx-deep-analysis": {
    "prompt": "Analisar os tickets de suporte das últimas 4 semanas — onde o produto está gerando mais fricção?",
    "input": "Período de análise (padrão: últimas 4 semanas). O Claude acessa o Unthread automaticamente.",
    "output_label": "Relatório HTML interativo de fricção de produto",
    "output_type": "html-report",
    "output_preview": """
<div class="prev-report cx-report">
  <div class="prev-report-header">🔎 CX Deep Analysis — <strong>Últimas 4 semanas</strong></div>
  <div class="prev-report-stats">
    <span class="rst high">312 tickets analisados</span>
    <span class="rst med">8 padrões identificados</span>
    <span class="rst low">CSAT médio: 3.9</span>
  </div>
  <div class="cx-patterns">
    <div class="cx-pat">
      <div class="cx-pat-bar" style="width:78%"></div>
      <span class="cx-pat-name">Rastreio de pedido</span><span class="cx-pat-count">82 tickets (26%)</span>
    </div>
    <div class="cx-pat">
      <div class="cx-pat-bar" style="width:52%"></div>
      <span class="cx-pat-name">Troca e devolução</span><span class="cx-pat-count">54 tickets (17%)</span>
    </div>
    <div class="cx-pat">
      <div class="cx-pat-bar" style="width:38%"></div>
      <span class="cx-pat-name">Cancelamento de pedido</span><span class="cx-pat-count">40 tickets (13%)</span>
    </div>
  </div>
</div>"""
  },
  "sunne-reply-suggester": {
    "prompt": "Rodar sugestões de resposta para o #ch-sunne",
    "input": "Sem input. O Claude lê as mensagens sem resposta no canal #ch-sunne do Slack automaticamente.",
    "output_label": "Sugestões postadas em thread no Slack",
    "output_type": "slack",
    "output_preview": """
<div class="prev-slack">
  <div class="prev-slack-header"><span class="slack-hash">#</span>ch-sunne</div>
  <div class="prev-slack-msg">
    <div class="slack-avatar">🧑</div>
    <div class="slack-body">
      <span class="slack-name">Ana (cliente)</span><span class="slack-time">14:32</span>
      <div class="slack-text">Como faço para ativar o FUP automático no CloudChat?</div>
    </div>
  </div>
  <div class="prev-slack-msg reply">
    <div class="slack-avatar">🤖</div>
    <div class="slack-body">
      <span class="slack-name">ClaudIA</span><span class="slack-time">14:33</span>
      <div class="slack-text">💡 <em>Sugestão (aguardando ✅ do owner):</em><br>
      O FUP automático é ativado em <strong>Hub → Configurações → Comportamento → Follow-up</strong>. Você pode definir o tempo de inatividade e a mensagem padrão. Quer que eu envie o passo a passo completo?</div>
    </div>
  </div>
</div>"""
  },
  "financeiro-task-sync": {
    "prompt": "Validar o financeiro — sincronizar conversas do Unthread com tasks no Airtable",
    "input": "Sem input. O Claude acessa o projeto Financeiro do Unthread e o Airtable automaticamente.",
    "output_label": "Tasks criadas/atualizadas no Airtable",
    "output_type": "action",
    "output_preview": """
<div class="prev-action">
  <div class="prev-action-title">💰 Financeiro Task Sync</div>
  <div class="prev-action-item">
    <div class="act-badge created">Criada</div>
    <div class="act-text"><strong>Acme Corp</strong> — NF de março não recebida pelo cliente · CS Owner: Marina · Prioridade: Alta</div>
  </div>
  <div class="prev-action-item">
    <div class="act-badge review">Atualizada</div>
    <div class="act-text"><strong>Beta Ltda</strong> — Task #4102 atualizada: cobrança de fevereiro confirmada como paga</div>
  </div>
  <div class="prev-action-item">
    <div class="act-badge skipped">Já existe</div>
    <div class="act-text"><strong>Gama SA</strong> — Task #3987 já registrada e em andamento</div>
  </div>
  <div class="prev-action-summary">11 conversas analisadas · 3 tasks criadas · 2 atualizadas · 6 já existiam</div>
</div>"""
  },
}

# ── Ler skills ───────────────────────────────────────────────────────────────
def read_skill_md(skill_dir):
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return None
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

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

    if not name:
        name = os.path.basename(skill_dir)

    triggers = re.findall(r'"([^"]{5,60})"', description)[:3]

    clean_desc = re.sub(r'Use (?:esta skill |this skill )?(?:SEMPRE|sempre|whenever)[^\.]+\.', '', description)
    clean_desc = re.sub(r'(?:Trigger|Gatilho)[s]?[:\s][^\.]+\.', '', clean_desc, flags=re.IGNORECASE)
    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
    if len(clean_desc) > 200:
        cut = clean_desc[:200].rsplit(' ', 1)[0]
        clean_desc = cut + "…"

    return {"name": name, "description": clean_desc or description[:200], "triggers": triggers}


def collect_skills():
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
        areas  = SKILL_AREAS.get(skill_key, ["gen"])
        meta   = SKILL_META.get(skill_key, {"icon": "⚡", "type": "Skill", "auto": False})
        detail = SKILL_DETAILS.get(skill_key, {})
        skills.append({
            "key":          skill_key,
            "name":         skill_data["name"],
            "description":  skill_data["description"],
            "triggers":     skill_data["triggers"],
            "areas":        areas,
            "icon":         meta.get("icon", "⚡"),
            "type":         meta.get("type", "Skill"),
            "auto":         meta.get("auto", False),
            "prompt":       detail.get("prompt", ""),
            "input":        detail.get("input", ""),
            "output_label": detail.get("output_label", ""),
            "output_type":  detail.get("output_type", "none"),
            "output_preview": detail.get("output_preview", ""),
        })
    return skills


def area_counts(skills):
    counts = {k: 0 for k in AREA_LABELS}
    for s in skills:
        for a in s["areas"]:
            if a in counts:
                counts[a] += 1
    return counts


AREA_COLORS = {
    "am":  ("#eef2ff", "#6366f1"),
    "ob":  ("#f0fdf4", "#22c55e"),
    "sup": ("#fffbeb", "#f59e0b"),
    "com": ("#fdf2f8", "#ec4899"),
    "gen": ("#f8fafc", "#64748b"),
}
AREA_TAG_CLASS = {"am":"tag-am","ob":"tag-ob","sup":"tag-sup","com":"tag-com","gen":"tag-gen"}

OUTPUT_TYPE_LABELS = {
    "plan":        "📋 Plano estruturado",
    "html-report": "🌐 Relatório HTML",
    "docx":        "📝 Documento Word",
    "pptx":        "🎨 Apresentação PPTX",
    "slack":       "💬 Mensagem no Slack",
    "action":      "⚡ Ações automáticas",
    "none":        "",
}

def render_card(skill):
    areas_str = " ".join(skill["areas"])
    primary_area = skill["areas"][0] if skill["areas"] else "gen"
    icon_bg, _ = AREA_COLORS.get(primary_area, ("#f1f5f9", "#64748b"))

    if skill["triggers"]:
        joined = " · ".join(f'"{t}"' for t in skill["triggers"])
        trigger_html = f'<div class="card-trigger">{joined}</div>'
    else:
        trigger_html = ""

    tags_html = "".join(
        f'<span class="tag {AREA_TAG_CLASS.get(a,"tag-gen")}">{AREA_LABELS.get(a,a)}</span>'
        for a in skill["areas"]
    )
    auto_badge = '<span class="card-auto-badge">Automatizável</span>' if skill["auto"] else ""
    has_detail = bool(skill["prompt"] or skill["input"] or skill["output_label"])
    detail_hint = '<div class="card-detail-hint">Ver detalhes →</div>' if has_detail else ""

    safe_key = html_module.escape(skill["key"])
    return f"""
    <div class="skill-card" data-areas="{areas_str}" data-key="{safe_key}" onclick="openModal('{safe_key}')" role="button" tabindex="0">
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
        {detail_hint}
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


def render_modals(skills):
    modals = []
    for s in skills:
        if not (s["prompt"] or s["input"] or s["output_label"]):
            continue
        safe_key = html_module.escape(s["key"])
        primary_area = s["areas"][0] if s["areas"] else "gen"
        _, accent = AREA_COLORS.get(primary_area, ("#f1f5f9","#64748b"))
        icon_bg, _ = AREA_COLORS.get(primary_area, ("#f1f5f9","#64748b"))

        tags_html = "".join(
            f'<span class="tag {AREA_TAG_CLASS.get(a,"tag-gen")}">{AREA_LABELS.get(a,a)}</span>'
            for a in s["areas"]
        )
        auto_badge = '<span class="card-auto-badge">Automatizável</span>' if s["auto"] else ""
        output_label_badge = ""
        if s["output_type"] and s["output_type"] != "none":
            lbl = OUTPUT_TYPE_LABELS.get(s["output_type"], "")
            if lbl:
                output_label_badge = f'<span class="modal-output-badge">{lbl}</span>'

        input_block = ""
        if s["input"]:
            safe_input = html_module.escape(s["input"])
            input_block = f"""
            <div class="modal-info-block">
              <div class="modal-info-label">📥 O que você precisa fornecer</div>
              <div class="modal-info-text">{safe_input}</div>
            </div>"""

        output_block = ""
        if s["output_label"]:
            safe_output_label = html_module.escape(s["output_label"])
            output_block = f"""
            <div class="modal-info-block">
              <div class="modal-info-label">📤 O que você recebe</div>
              <div class="modal-info-text">{safe_output_label} {output_label_badge}</div>
            </div>"""

        preview_block = ""
        if s["output_preview"]:
            preview_block = f"""
            <div class="modal-preview-section">
              <div class="modal-preview-label">Exemplo de output</div>
              <div class="modal-preview-box">{s["output_preview"]}</div>
            </div>"""

        prompt_block = ""
        if s["prompt"]:
            safe_prompt = html_module.escape(s["prompt"])
            prompt_block = f"""
            <div class="modal-prompt-section">
              <div class="modal-prompt-label">Como acionar no Cowork</div>
              <div class="modal-prompt-box">
                <div class="modal-prompt-text" id="prompt-{safe_key}">{safe_prompt}</div>
                <button class="modal-copy-btn" onclick="copyPrompt('{safe_key}', event)">Copiar prompt</button>
              </div>
            </div>"""

        modals.append(f"""
  <div class="modal-overlay" id="modal-{safe_key}" onclick="closeModalOnOverlay(event, '{safe_key}')">
    <div class="modal-panel" role="dialog">
      <div class="modal-header" style="border-top:4px solid {accent}">
        <div class="modal-header-left">
          <div class="modal-icon" style="background:{icon_bg}">{s["icon"]}</div>
          <div>
            <div class="modal-title">{s["name"]}</div>
            <div class="modal-tags">{tags_html} {auto_badge}</div>
          </div>
        </div>
        <button class="modal-close" onclick="closeModal('{safe_key}')" aria-label="Fechar">✕</button>
      </div>
      <div class="modal-body">
        <div class="modal-left">
          <div class="modal-info-block">
            <div class="modal-info-label">📌 O que faz</div>
            <div class="modal-info-text">{s["description"]}</div>
          </div>
          {input_block}
          {output_block}
          {prompt_block}
        </div>
        <div class="modal-right">
          {preview_block}
        </div>
      </div>
    </div>
  </div>""")
    return "\n".join(modals)


def generate_html(skills):
    counts = area_counts(skills)
    total  = len(skills)
    auto_count = sum(1 for s in skills if s["auto"])
    now    = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%Mh UTC")

    sections_html = "\n".join(render_section(a, skills) for a in AREA_LABELS)
    modals_html   = render_modals(skills)

    # Build JS skills data for modal lookup
    skills_json_parts = []
    for s in skills:
        skills_json_parts.append(
            f'"{s["key"]}": {json.dumps({"name": s["name"], "prompt": s.get("prompt","")}, ensure_ascii=False)}'
        )
    skills_js = "{" + ",".join(skills_json_parts) + "}"

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

    /* ── Header ── */
    .header {{ background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%); padding:40px 48px 36px; color:white; }}
    .header-inner {{ max-width:1280px; margin:0 auto; }}
    .header-logo {{ font-size:13px; font-weight:600; letter-spacing:.12em; text-transform:uppercase; color:#94a3b8; margin-bottom:10px; }}
    .header h1 {{ font-size:32px; font-weight:700; letter-spacing:-.5px; margin-bottom:8px; }}
    .header p {{ font-size:15px; color:#94a3b8; max-width:560px; line-height:1.6; }}
    .header-stats {{ display:flex; gap:32px; margin-top:28px; flex-wrap:wrap; }}
    .stat {{ display:flex; flex-direction:column; }}
    .stat-num {{ font-size:28px; font-weight:700; color:white; line-height:1; }}
    .stat-label {{ font-size:12px; color:#94a3b8; margin-top:4px; }}
    .updated {{ font-size:11px; color:#475569; margin-top:20px; }}

    /* ── Filters ── */
    .filters-bar {{ background:white; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:100; }}
    .filters-inner {{ max-width:1280px; margin:0 auto; padding:0 48px; display:flex; gap:4px; overflow-x:auto; scrollbar-width:none; }}
    .filters-inner::-webkit-scrollbar {{ display:none; }}
    .filter-btn {{ display:flex; align-items:center; gap:8px; padding:14px 20px; border:none; background:transparent; font-size:14px; font-weight:500; color:var(--muted); cursor:pointer; white-space:nowrap; border-bottom:3px solid transparent; transition:all .18s; }}
    .filter-btn:hover {{ color:var(--text); }}
    .filter-btn.active.all {{ border-bottom-color:#0f172a; color:#0f172a; }}
    .filter-btn.active.am  {{ border-bottom-color:var(--am); color:var(--am); }}
    .filter-btn.active.ob  {{ border-bottom-color:var(--ob); color:var(--ob); }}
    .filter-btn.active.sup {{ border-bottom-color:var(--sup); color:var(--sup); }}
    .filter-btn.active.com {{ border-bottom-color:var(--com); color:var(--com); }}
    .filter-btn.active.gen {{ border-bottom-color:var(--gen); color:var(--gen); }}
    .filter-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
    .filter-count {{ background:#f1f5f9; color:#64748b; font-size:12px; font-weight:600; padding:1px 7px; border-radius:99px; }}

    /* ── Main ── */
    .main {{ max-width:1280px; margin:0 auto; padding:36px 48px; }}
    .section-title {{ font-size:12px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:20px; margin-top:40px; display:flex; align-items:center; gap:10px; }}
    .section-title:first-of-type {{ margin-top:0; }}
    .section-title::after {{ content:''; flex:1; height:1px; background:var(--border); }}
    .skills-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:20px; }}

    /* ── Cards ── */
    .skill-card {{ background:var(--card-bg); border:1px solid var(--border); border-radius:var(--radius); padding:24px; display:flex; flex-direction:column; gap:14px; transition:box-shadow .2s,transform .2s,border-color .2s; cursor:pointer; position:relative; }}
    .skill-card:hover {{ box-shadow:0 8px 24px rgba(0,0,0,.09); transform:translateY(-2px); border-color:#cbd5e1; }}
    .skill-card:focus {{ outline:2px solid var(--am); outline-offset:2px; }}
    .skill-card.hidden {{ display:none; }}
    .card-header {{ display:flex; align-items:flex-start; gap:14px; }}
    .card-icon {{ width:44px; height:44px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:22px; flex-shrink:0; }}
    .card-meta {{ flex:1; min-width:0; }}
    .card-name {{ font-size:15px; font-weight:700; color:var(--text); line-height:1.3; }}
    .card-trigger {{ font-size:12px; color:var(--muted); margin-top:3px; font-style:italic; }}
    .card-desc {{ font-size:13.5px; color:#475569; line-height:1.6; }}
    .card-tags {{ display:flex; flex-wrap:wrap; gap:6px; }}
    .tag {{ font-size:11px; font-weight:600; padding:3px 10px; border-radius:99px; letter-spacing:.04em; }}
    .tag-am  {{ background:var(--am-light); color:var(--am); }}
    .tag-ob  {{ background:var(--ob-light); color:#15803d; }}
    .tag-sup {{ background:var(--sup-light); color:#b45309; }}
    .tag-com {{ background:var(--com-light); color:#be185d; }}
    .tag-gen {{ background:var(--gen-light); color:var(--gen); border:1px solid var(--border); }}
    .card-footer {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
    .card-type {{ font-size:11px; font-weight:600; padding:3px 10px; border-radius:6px; background:#f8fafc; color:#64748b; border:1px solid #e2e8f0; }}
    .card-auto-badge {{ font-size:11px; font-weight:600; padding:3px 10px; border-radius:6px; background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; }}
    .card-detail-hint {{ margin-left:auto; font-size:12px; font-weight:500; color:#94a3b8; transition:color .15s; }}
    .skill-card:hover .card-detail-hint {{ color:var(--am); }}

    /* ── Legend ── */
    .legend {{ background:white; border:1px solid var(--border); border-radius:var(--radius); padding:20px 24px; margin-bottom:32px; display:flex; flex-wrap:wrap; gap:16px; align-items:center; }}
    .legend-label {{ font-size:12px; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; flex-shrink:0; }}
    .legend-items {{ display:flex; flex-wrap:wrap; gap:10px; }}
    .legend-item {{ display:flex; align-items:center; gap:7px; font-size:13px; color:var(--text); }}
    .legend-dot {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}
    .empty-state {{ text-align:center; padding:60px 20px; color:var(--muted); display:none; }}
    .empty-state.visible {{ display:block; }}

    /* ── Modal overlay ── */
    .modal-overlay {{ display:none; position:fixed; inset:0; background:rgba(15,23,42,.55); backdrop-filter:blur(4px); z-index:1000; align-items:center; justify-content:center; padding:24px; }}
    .modal-overlay.open {{ display:flex; }}

    .modal-panel {{
      background:white; border-radius:20px; max-width:900px; width:100%;
      max-height:90vh; overflow:hidden; display:flex; flex-direction:column;
      box-shadow:0 24px 64px rgba(0,0,0,.2);
      animation: modalIn .22s cubic-bezier(.34,1.3,.64,1);
    }}
    @keyframes modalIn {{ from {{ opacity:0; transform:scale(.95) translateY(8px); }} to {{ opacity:1; transform:none; }} }}

    .modal-header {{
      display:flex; align-items:center; justify-content:space-between;
      padding:22px 28px 20px; border-bottom:1px solid var(--border);
      flex-shrink:0;
    }}
    .modal-header-left {{ display:flex; align-items:center; gap:16px; }}
    .modal-icon {{ width:52px; height:52px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:26px; flex-shrink:0; }}
    .modal-title {{ font-size:20px; font-weight:700; color:var(--text); }}
    .modal-tags {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; }}
    .modal-output-badge {{ font-size:11px; font-weight:600; padding:3px 10px; border-radius:6px; background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }}
    .modal-close {{ width:36px; height:36px; border-radius:50%; border:none; background:#f1f5f9; cursor:pointer; font-size:16px; color:#64748b; display:flex; align-items:center; justify-content:center; transition:background .15s; flex-shrink:0; }}
    .modal-close:hover {{ background:#e2e8f0; color:var(--text); }}

    .modal-body {{
      display:grid; grid-template-columns:1fr 1fr; gap:0;
      overflow-y:auto; flex:1;
    }}
    .modal-left {{ padding:24px 28px; border-right:1px solid var(--border); display:flex; flex-direction:column; gap:20px; }}
    .modal-right {{ padding:24px 28px; background:#fafafa; display:flex; flex-direction:column; gap:16px; overflow-y:auto; }}

    .modal-info-block {{ display:flex; flex-direction:column; gap:8px; }}
    .modal-info-label {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
    .modal-info-text {{ font-size:14px; color:#334155; line-height:1.65; }}

    /* Prompt section */
    .modal-prompt-section {{ margin-top:auto; padding-top:16px; border-top:1px solid var(--border); }}
    .modal-prompt-label {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin-bottom:10px; }}
    .modal-prompt-box {{ background:#f8fafc; border:1px solid var(--border); border-radius:10px; padding:14px 16px; display:flex; align-items:flex-start; gap:12px; }}
    .modal-prompt-text {{ font-size:13px; color:#334155; flex:1; line-height:1.5; font-family:'SF Mono','Fira Code',monospace; }}
    .modal-copy-btn {{
      flex-shrink:0; padding:7px 14px; background:#0f172a; color:white;
      border:none; border-radius:8px; font-size:12px; font-weight:600; cursor:pointer;
      transition:background .15s, transform .1s;
      white-space:nowrap;
    }}
    .modal-copy-btn:hover {{ background:#1e293b; }}
    .modal-copy-btn:active {{ transform:scale(.96); }}
    .modal-copy-btn.copied {{ background:#16a34a; }}

    /* Preview section */
    .modal-preview-section {{ display:flex; flex-direction:column; gap:10px; }}
    .modal-preview-label {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); }}
    .modal-preview-box {{ background:white; border:1px solid var(--border); border-radius:12px; padding:16px; overflow:hidden; font-size:13px; }}

    /* ── Preview styles: Plan ── */
    .prev-plan-header {{ font-size:13px; font-weight:600; color:var(--text); margin-bottom:12px; display:flex; align-items:center; justify-content:space-between; }}
    .prev-date {{ font-size:11px; color:var(--muted); font-weight:400; }}
    .prev-plan-item {{ display:flex; gap:10px; margin-bottom:10px; }}
    .prev-priority {{ width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:800; flex-shrink:0; }}
    .prev-plan-item.p0 .prev-priority {{ background:#fef2f2; color:#dc2626; }}
    .prev-plan-item.p1 .prev-priority {{ background:#fffbeb; color:#d97706; }}
    .prev-plan-item.p2 .prev-priority {{ background:#f0fdf4; color:#16a34a; }}
    .prev-content strong {{ font-size:13px; color:var(--text); display:block; margin-bottom:3px; }}
    .prev-content p {{ font-size:12px; color:#64748b; line-height:1.5; }}

    /* ── Preview styles: Report ── */
    .prev-report-header {{ font-size:13px; font-weight:600; color:var(--text); margin-bottom:10px; }}
    .prev-report-stats {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px; }}
    .rst {{ font-size:11px; font-weight:600; padding:3px 10px; border-radius:99px; }}
    .rst.high {{ background:#fef2f2; color:#dc2626; }}
    .rst.med  {{ background:#fffbeb; color:#d97706; }}
    .rst.low  {{ background:#f0fdf4; color:#16a34a; }}
    .prev-table {{ width:100%; border-collapse:collapse; font-size:12px; }}
    .prev-table th {{ text-align:left; padding:6px 8px; background:#f8fafc; color:#64748b; font-weight:600; border-bottom:1px solid var(--border); }}
    .prev-table td {{ padding:6px 8px; border-bottom:1px solid #f1f5f9; color:#334155; }}
    .score {{ font-weight:700; padding:2px 6px; border-radius:4px; }}
    .score.high {{ background:#fef2f2; color:#dc2626; }}
    .score.med  {{ background:#fffbeb; color:#d97706; }}
    .act {{ font-size:11px; font-weight:600; padding:2px 8px; border-radius:99px; }}
    .act.merge  {{ background:#fef2f2; color:#dc2626; }}
    .act.review {{ background:#fffbeb; color:#d97706; }}
    .act.ok     {{ background:#f0fdf4; color:#16a34a; }}

    /* ── Preview styles: CX patterns ── */
    .cx-report .prev-report-stats .rst {{ background:#f1f5f9; color:#334155; }}
    .cx-patterns {{ display:flex; flex-direction:column; gap:8px; }}
    .cx-pat {{ position:relative; padding:6px 8px; background:#f8fafc; border-radius:6px; }}
    .cx-pat-bar {{ position:absolute; left:0; top:0; bottom:0; background:rgba(99,102,241,.1); border-radius:6px; }}
    .cx-pat-name {{ font-size:12px; font-weight:600; color:var(--text); position:relative; }}
    .cx-pat-count {{ font-size:11px; color:var(--muted); position:relative; float:right; }}

    /* ── Preview styles: Docx ── */
    .prev-docx {{ font-size:12px; }}
    .prev-docx-header {{ display:flex; align-items:center; gap:12px; padding-bottom:12px; border-bottom:2px solid #0f172a; margin-bottom:12px; }}
    .docx-logo {{ width:36px; height:36px; background:#0f172a; color:white; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:800; flex-shrink:0; }}
    .docx-title {{ font-size:14px; font-weight:800; color:#0f172a; letter-spacing:.04em; }}
    .docx-subtitle {{ font-size:11px; color:#64748b; }}
    .prev-docx-body p {{ color:#334155; margin-bottom:6px; }}
    .docx-clause {{ color:#334155; margin-bottom:6px; padding:6px 10px; background:#f8fafc; border-left:3px solid #e2e8f0; border-radius:0 4px 4px 0; }}
    .docx-clause-faded {{ color:#94a3b8; font-style:italic; font-size:11px; }}

    /* ── Preview styles: PPTX ── */
    .prev-slides {{ display:flex; flex-direction:column; gap:10px; }}
    .prev-slide {{ background:linear-gradient(135deg,#1e293b,#334155); border-radius:10px; padding:20px; color:white; }}
    .prev-slide-label {{ font-size:10px; text-transform:uppercase; letter-spacing:.1em; color:#94a3b8; margin-bottom:6px; }}
    .prev-slide-title {{ font-size:16px; font-weight:700; margin-bottom:14px; }}
    .prev-slide-metrics {{ display:flex; gap:16px; }}
    .prev-metric {{ display:flex; flex-direction:column; align-items:center; }}
    .metric-val {{ font-size:22px; font-weight:800; }}
    .metric-val.green {{ color:#4ade80; }}
    .metric-lbl {{ font-size:10px; color:#94a3b8; margin-top:2px; }}
    .prev-slide-strip {{ display:flex; gap:6px; }}
    .strip-slide {{ flex:1; height:8px; border-radius:3px; background:#e2e8f0; }}
    .strip-slide.sel {{ background:var(--am); }}

    /* ── Preview styles: Slack ── */
    .prev-slack {{ font-size:13px; }}
    .prev-slack-header {{ font-size:12px; font-weight:700; color:#1d1c1d; padding-bottom:10px; border-bottom:1px solid var(--border); margin-bottom:10px; }}
    .slack-hash {{ color:#64748b; margin-right:2px; }}
    .prev-slack-msg {{ display:flex; gap:10px; margin-bottom:8px; }}
    .prev-slack-msg.reply {{ margin-left:20px; border-left:2px solid var(--border); padding-left:10px; }}
    .slack-avatar {{ width:32px; height:32px; border-radius:6px; background:#e2e8f0; display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
    .slack-body {{ flex:1; }}
    .slack-name {{ font-weight:700; font-size:13px; color:#1d1c1d; }}
    .slack-time {{ font-size:11px; color:#64748b; margin-left:6px; }}
    .slack-text {{ font-size:13px; color:#1d1c1d; margin-top:2px; line-height:1.5; }}

    /* ── Preview styles: Action ── */
    .prev-action {{ font-size:13px; }}
    .prev-action-title {{ font-size:13px; font-weight:700; color:var(--text); margin-bottom:10px; }}
    .prev-action-item {{ display:flex; gap:10px; margin-bottom:8px; align-items:flex-start; }}
    .act-badge {{ font-size:10px; font-weight:700; padding:3px 8px; border-radius:99px; white-space:nowrap; flex-shrink:0; margin-top:1px; }}
    .act-badge.created {{ background:#f0fdf4; color:#16a34a; }}
    .act-badge.skipped {{ background:#f8fafc; color:#64748b; border:1px solid var(--border); }}
    .act-badge.review  {{ background:#fffbeb; color:#d97706; }}
    .act-text {{ font-size:12px; color:#334155; line-height:1.5; }}
    .prev-action-summary {{ font-size:11px; color:var(--muted); margin-top:10px; padding-top:8px; border-top:1px solid var(--border); }}

    /* ── Responsive ── */
    @media (max-width:768px) {{
      .header {{ padding:28px 24px; }}
      .filters-inner {{ padding:0 24px; }}
      .main {{ padding:24px; }}
      .skills-grid {{ grid-template-columns:1fr; }}
      .modal-body {{ grid-template-columns:1fr; }}
      .modal-left {{ border-right:none; border-bottom:1px solid var(--border); }}
      .modal-panel {{ max-height:95vh; }}
    }}
  </style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div class="header-logo">Cloud Humans · ClaudIA Cowork</div>
    <h1>🗺️ Mapa de Skills</h1>
    <p>Tudo que o time pode automatizar ou delegar para o Claude Cowork. Clique em qualquer skill para ver detalhes e copiar o prompt de ativação.</p>
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
    <button class="filter-btn active all" onclick="filterSkills('all',this)">
      <span class="filter-dot" style="background:#0f172a"></span> Todas as Áreas
      <span class="filter-count">{total}</span>
    </button>
    <button class="filter-btn am" onclick="filterSkills('am',this)">
      <span class="filter-dot" style="background:var(--am)"></span> Account Management
      <span class="filter-count">{counts['am']}</span>
    </button>
    <button class="filter-btn ob" onclick="filterSkills('ob',this)">
      <span class="filter-dot" style="background:var(--ob)"></span> Onboarding
      <span class="filter-count">{counts['ob']}</span>
    </button>
    <button class="filter-btn sup" onclick="filterSkills('sup',this)">
      <span class="filter-dot" style="background:var(--sup)"></span> Suporte
      <span class="filter-count">{counts['sup']}</span>
    </button>
    <button class="filter-btn com" onclick="filterSkills('com',this)">
      <span class="filter-dot" style="background:var(--com)"></span> Comercial
      <span class="filter-count">{counts['com']}</span>
    </button>
    <button class="filter-btn gen" onclick="filterSkills('gen',this)">
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
      <div class="legend-item"><span class="legend-dot" style="background:var(--gen)"></span> Geral</div>
    </div>
    <div class="legend-items" style="margin-left:auto">
      <div class="legend-item"><span style="background:#eff6ff;color:#2563eb;font-size:11px;font-weight:600;padding:3px 10px;border-radius:6px;border:1px solid #bfdbfe;">Automatizável</span> pode ser agendada</div>
    </div>
  </div>

  <div class="empty-state" id="empty-state">
    <div style="font-size:40px;margin-bottom:12px">🔍</div>
    <div style="font-size:15px">Nenhuma skill encontrada.</div>
  </div>

  {sections_html}
</div>

{modals_html}

<script>
  const SKILLS = {skills_js};

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

  function openModal(key) {{
    const el = document.getElementById('modal-' + key);
    if (!el) return;
    el.classList.add('open');
    document.body.style.overflow = 'hidden';
  }}

  function closeModal(key) {{
    const el = document.getElementById('modal-' + key);
    if (!el) return;
    el.classList.remove('open');
    document.body.style.overflow = '';
  }}

  function closeModalOnOverlay(e, key) {{
    if (e.target === e.currentTarget) closeModal(key);
  }}

  document.addEventListener('keydown', e => {{
    if (e.key === 'Escape') {{
      document.querySelectorAll('.modal-overlay.open').forEach(m => {{
        m.classList.remove('open');
        document.body.style.overflow = '';
      }});
    }}
  }});

  function copyPrompt(key, event) {{
    event.stopPropagation();
    const el = document.getElementById('prompt-' + key);
    if (!el) return;
    const text = el.textContent;
    navigator.clipboard.writeText(text).then(() => {{
      const btn = event.currentTarget;
      btn.textContent = '✓ Copiado!';
      btn.classList.add('copied');
      setTimeout(() => {{
        btn.textContent = 'Copiar prompt';
        btn.classList.remove('copied');
      }}, 2000);
    }});
  }}
</script>
</body>
</html>"""


if __name__ == "__main__":
    skills = collect_skills()
    html   = generate_html(skills)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ index.html gerado com {len(skills)} skills em {OUTPUT_PATH}")
