#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Central do Cliente
==============================
Monta o portal (index.html) e o guia de acesso (PDF) a partir de um config.json.

Uso:
    python3 gerar_central.py config.json

Saída (pasta ./saida/):
    index.html                       -> portal pronto para deploy
    vercel.json                      -> config de deploy
    README.md                        -> documentação do projeto
    <Cliente>_guia_de_acesso.pdf     -> guia para enviar ao cliente

Requisitos:
    pip install pillow numpy --break-system-packages
    pip install playwright --break-system-packages && python3 -m playwright install chromium
    (playwright só é necessário para gerar o PDF do guia)
"""

import base64
import json
import os
import re
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).parent
TEMPLATE_PORTAL = BASE / "template_portal.html"
TEMPLATE_GUIA = BASE / "template_guia.html"
OUT = BASE / "saida"

WA_NUMERO_PADRAO = "+55 11 99555-0735"

# CSS de impressão injetado em todo documento embutido (garante PDF com cores)
PRINT_CSS = """
    /* ===== PRINT / PDF ===== */
    @media print {
      * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
      html, body { background:#fff !important; }
      header { min-height:auto !important; padding:40px 24px !important; page-break-after: always; break-after: page; }
      nav { display:none !important; }
      section, .band, footer { page-break-inside: avoid; break-inside: avoid; }
      .card, .stat, .cmp, .panel, .crea, .tp, .item, .col, .ceo-box, .hero-card,
      .table-wrap, .accordion, .info-box, .chart-card, .amber-box, .highlight-grid {
        page-break-inside: avoid; break-inside: avoid;
      }
    }
    @page { margin: 12mm; }
"""


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------

def erro(msg):
    print(f"\n  ERRO: {msg}\n")
    sys.exit(1)


def preparar_logo(caminho, altura_export=72):
    """Carrega um logo, remove fundo branco se necessário e devolve data URI PNG.

    - PNG com transparência: usado como está (só recorta e redimensiona)
    - JPG/PNG com fundo branco: fundo removido por luminância
    - Exporta em 2x a altura de exibição para ficar nítido em telas retina
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        erro("Instale as dependências: pip install pillow numpy --break-system-packages")

    p = Path(caminho)
    if not p.exists():
        erro(f"Logo não encontrado: {caminho}")

    im = Image.open(p)
    tem_alpha = im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 255

    if tem_alpha:
        im = im.convert("RGBA")
    else:
        # remove fundo branco por luminância
        im = im.convert("RGB")
        a = np.array(im).astype(int)
        lum = a.mean(axis=2)
        alpha = np.clip((245 - lum) * 255 / 60, 0, 255).astype(np.uint8)
        im = Image.fromarray(np.dstack([a.astype(np.uint8), alpha]), "RGBA")

    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)

    w = max(1, int(im.width * altura_export / im.height))
    im = im.resize((w, altura_export), Image.LANCZOS)

    tmp = BASE / "_tmp_logo.png"
    im.save(tmp, optimize=True)
    b64 = base64.b64encode(tmp.read_bytes()).decode()
    tmp.unlink()
    return "data:image/png;base64," + b64


def embutir_documento(caminho):
    """Lê um HTML, garante o CSS de impressão e devolve o base64."""
    p = Path(caminho)
    if not p.exists():
        erro(f"Documento não encontrado: {caminho}")
    html = p.read_text(encoding="utf-8")
    if "@media print" not in html:
        if "</head>" in html:
            html = html.replace("</head>", f"<style>{PRINT_CSS}</style>\n</head>", 1)
        else:
            html = f"<style>{PRINT_CSS}</style>\n" + html
    return base64.b64encode(html.encode("utf-8")).decode()


def _rgba(hexcor, alpha):
    h = hexcor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def slug(texto):
    t = re.sub(r"[^a-zA-Z0-9]+", "_", texto.lower()).strip("_")
    return t or "doc"


def wa_link(numero, cliente):
    digitos = "".join(ch for ch in numero if ch.isdigit())
    from urllib.parse import quote
    msg = quote(f"Olá, preciso de ajuda com a Central do Cliente {cliente}")
    return f"https://wa.me/{digitos}?text={msg}"


# ----------------------------------------------------------------------------
# Montagem do portal
# ----------------------------------------------------------------------------

def montar_blocos(categorias, docs_b64):
    """Gera o HTML das seções de categoria + cards."""
    # tons rotativos para as tarjas dos cards (mesma família de cor)
    tons = [
        ("var(--brand-mid)",  "var(--brand-pale)", "var(--brand-deep)"),
        ("var(--accent)",     "var(--brand-pale)", "var(--brand-deep)"),
        ("var(--brand-deep)", "var(--brand-pale)", "var(--brand-dark)"),
        ("var(--brand)",      "var(--brand-pale)", "var(--brand-deep)"),
    ]
    partes = []
    i_tom = 0
    for cat in categorias:
        docs = cat.get("documentos", [])
        n = len(docs)
        plural = "material" if n == 1 else "materiais"
        cards = []
        for d in docs:
            chave = d["chave"]
            acc, bg, ink = tons[i_tom % len(tons)]
            i_tom += 1
            estilo = f'style="--accent:{acc};--accent-bg:{bg};--accent-ink:{ink};"'
            comum = f"""          <span class="block-tag">{d.get('tag', 'Documento')}</span>
          <h3>{d['titulo']}</h3>
          <p class="desc">{d.get('descricao', '')}</p>
          <div class="block-meta">{d.get('meta', '')}</div>"""

            if d.get("url_externa"):
                cards.append(f"""        <a class="block-card block-ext" href="{d['url_externa']}"
             target="_blank" rel="noopener" {estilo}>
{comum}
          <div class="block-foot">
            <span class="block-ext-badge">Link externo</span>
            <span class="block-open">{d.get('cta', 'Abrir')} ↗</span>
          </div>
        </a>""")
            else:
                cards.append(f"""        <div class="block-card" data-doc="{chave}" {estilo}>
{comum}
          <div class="block-foot">
            <button class="block-pdf" data-pdf="{chave}">⬇ PDF</button>
            <span class="block-open">{d.get('cta', 'Abrir')} →</span>
          </div>
        </div>""")

        partes.append(f"""    <!-- {cat['nome'].upper()} -->
    <section class="cat-block" id="{cat['id']}">
      <div class="cat-head">
        <h2>{cat.get('icone', '📁')} {cat['nome']} <span class="cnt">{n} {plural}</span></h2>
        <p>{cat.get('descricao', '')}</p>
      </div>
      <div class="grid">
{chr(10).join(cards)}
      </div>
    </section>
""")
    return "\n".join(partes)


def montar_docs_dict(categorias, docs_b64):
    """Gera as variáveis JS de base64 + o dicionário DOCS."""
    linhas_var, linhas_dict = [], []
    for cat in categorias:
        for d in cat.get("documentos", []):
            if d.get("url_externa"):
                continue
            chave = d["chave"]
            var = f"DOC_{slug(chave).upper()}_B64"
            linhas_var.append(f'  var {var} = "{docs_b64[chave]}";')
            titulo = d.get("titulo_viewer", d["titulo"]).replace('"', "'")
            linhas_dict.append(f'    {chave}: {{ title: "{titulo}", b64: {var} }},')
    if not linhas_dict:
        return "  var DOCS = {};"
    linhas_dict[-1] = linhas_dict[-1].rstrip(",")
    return "\n".join(linhas_var) + "\n\n  var DOCS = {\n" + "\n".join(linhas_dict) + "\n  };"


def montar_nav(categorias):
    links = ['<a href="#inicio">Início</a>', '<a href="#como-usar">Como usar</a>']
    for cat in categorias:
        links.append(f'<a href="#{cat["id"]}">{cat["nome"]}</a>')
    links.append('<a href="#duvidas">Dúvidas</a>')
    return "\n        " + "\n        ".join(links) + "\n      "


def gerar_portal(cfg, docs_b64, logo_cliente, logo_agencia):
    t = TEMPLATE_PORTAL.read_text(encoding="utf-8")
    cores = cfg["cores"]
    wa_display = cfg.get("whatsapp", WA_NUMERO_PADRAO)

    mapa = {
        "{{CLIENTE}}": cfg["cliente"],
        "{{AGENCIA}}": cfg.get("agencia", ""),
        "{{ANO}}": str(cfg.get("ano", 2026)),
        "{{SENHA}}": cfg["senha"],
        "{{LOGO_CLIENTE}}": logo_cliente,
        "{{LOGO_AGENCIA}}": logo_agencia,
        "{{WA_LINK}}": wa_link(wa_display, cfg["cliente"]),
        "{{WA_DISPLAY}}": wa_display,
        "{{C_DARK}}": cores["dark"],
        "{{C_DEEP}}": cores["deep"],
        "{{C_BRAND}}": cores["brand"],
        "{{C_MID}}": cores["mid"],
        "{{C_LIGHT}}": cores["light"],
        "{{C_PALE}}": cores["pale"],
        "{{C_ACCENT}}": cores["accent"],
        "{{C_TEXT}}": cores.get("text", "#1B2D1D"),
        "{{C_MUTED}}": cores.get("muted", "#5B7360"),
        "{{C_LINE}}": cores.get("line", "#E1EDE3"),
        "{{C_BG}}": cores.get("bg", cores["pale"]),
        "{{C_GLOW1}}": _rgba(cores["brand"], .14),
        "{{C_GLOW2}}": _rgba(cores["accent"], .18),
        "{{NAV_LINKS}}": montar_nav(cfg["categorias"]),
        "{{HERO_TEXTO}}": cfg.get(
            "hero_texto",
            f"Centralização dos materiais e relatórios de {cfg['cliente']}. "
            "Selecione um documento abaixo para visualizar ou baixar em PDF."
        ),
        "{{BLOCOS_CATEGORIAS}}": montar_blocos(cfg["categorias"], docs_b64),
        "{{DOCS_DICT}}": montar_docs_dict(cfg["categorias"], docs_b64),
    }
    for k, v in mapa.items():
        t = t.replace(k, v)

    restantes = re.findall(r"\{\{[A-Z_]+\}\}", t)
    if restantes:
        erro(f"Placeholders não substituídos: {set(restantes)}")
    return t


def gerar_guia_html(cfg, logo_cliente, logo_agencia):
    t = TEMPLATE_GUIA.read_text(encoding="utf-8")
    cores = cfg["cores"]
    wa_display = cfg.get("whatsapp", WA_NUMERO_PADRAO)
    mapa = {
        "{{CLIENTE}}": cfg["cliente"],
        "{{AGENCIA}}": cfg.get("agencia", ""),
        "{{SENHA}}": cfg["senha"],
        "{{URL}}": cfg.get("url_portal", ""),
        "{{RESUMO}}": cfg.get("resumo_guia", "O portal reúne os materiais e relatórios do projeto em um só lugar."),
        "{{LOGO_CLIENTE}}": logo_cliente,
        "{{LOGO_AGENCIA}}": logo_agencia,
        "{{WA_LINK}}": wa_link(wa_display, cfg["cliente"]),
        "{{WA_DISPLAY}}": wa_display,
        "{{C_DARK}}": cores["dark"],
        "{{C_DARK2}}": cores.get("dark2", cores["deep"]),
        "{{C_DEEP}}": cores["deep"],
        "{{C_BRAND}}": cores["brand"],
        "{{C_ACCENT}}": cores["accent"],
        "{{C_LIGHT}}": cores["light"],
        "{{C_GLOW1}}": _rgba(cores["accent"], .28),
        "{{C_GLOW2}}": _rgba(cores["light"], .35),
    }
    for k, v in mapa.items():
        t = t.replace(k, v)
    return t


def gerar_guia_pdf(html, destino):
    """Converte o guia para PDF de página única via Chromium headless."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ! playwright não instalado — guia salvo apenas em HTML")
        return False

    tmp = BASE / "_tmp_guia.html"
    tmp.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(f"file://{tmp.resolve()}")
        pg.wait_for_timeout(600)
        altura = pg.evaluate("document.body.scrollHeight")
        pg.pdf(path=str(destino), width="840px", height=f"{max(altura, 1200)}px",
               print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        b.close()
    tmp.unlink()
    return True


# ----------------------------------------------------------------------------
# Validação
# ----------------------------------------------------------------------------

def validar(cfg):
    obrig = ["cliente", "senha", "logo_cliente", "cores", "categorias"]
    for campo in obrig:
        if campo not in cfg:
            erro(f"Campo obrigatório ausente no config: '{campo}'")

    for c in ["dark", "deep", "brand", "mid", "light", "pale", "accent"]:
        if c not in cfg["cores"]:
            erro(f"Cor obrigatória ausente: cores.{c}")

    cats = cfg["categorias"]
    if not (1 <= len(cats) <= 4):
        erro("Use de 1 a 4 categorias (recomendado: 2 a 3).")
    if len(cats) > 3:
        print("  ! Aviso: mais de 3 categorias na entrada dificulta a navegação.")

    chaves = []
    for cat in cats:
        for campo in ["id", "nome"]:
            if campo not in cat:
                erro(f"Categoria sem '{campo}': {cat}")
        for d in cat.get("documentos", []):
            for campo in ["chave", "titulo"]:
                if campo not in d:
                    erro(f"Documento sem '{campo}' na categoria '{cat['nome']}'")
            if not d.get("arquivo") and not d.get("url_externa"):
                erro(f"Documento '{d['chave']}' precisa de 'arquivo' ou 'url_externa'")
            if d.get("arquivo") and d.get("url_externa"):
                erro(f"Documento '{d['chave']}': use 'arquivo' OU 'url_externa', nao ambos")
            if d["chave"] in chaves:
                erro(f"Chave de documento duplicada: {d['chave']}")
            if not re.fullmatch(r"[a-z0-9_]+", d["chave"]):
                erro(f"Chave inválida '{d['chave']}': use apenas minúsculas, números e _")
            chaves.append(d["chave"])
    if not chaves:
        erro("Nenhum documento declarado.")


def validar_saida(html, cfg):
    """Confere a integridade do portal gerado."""
    dd = set(re.findall(r'data-doc="([^"]+)"', html))
    dp = set(re.findall(r'data-pdf="([^"]+)"', html))
    if dd != dp:
        erro(f"Divergência entre cards e botões PDF: {dd ^ dp}")

    for chave in dd:
        m = re.search(r"var DOC_" + slug(chave).upper() + r'_B64 = "([A-Za-z0-9+/=]+)"', html)
        if not m:
            erro(f"Base64 ausente para '{chave}'")
        dec = base64.b64decode(m.group(1)).decode("utf-8", errors="ignore")
        if not dec.lstrip().lower().startswith("<!doctype html"):
            erro(f"Documento '{chave}' não é HTML válido")
        if "@media print" not in dec:
            erro(f"Documento '{chave}' sem CSS de impressão")
    print(f"  ✓ {len(dd)} documento(s) validado(s)")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cfg_path = Path(sys.argv[1])
    if not cfg_path.exists():
        erro(f"Config não encontrado: {cfg_path}")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    print(f"\n  Gerando central: {cfg.get('cliente', '?')}")
    validar(cfg)

    print("  · preparando logos")
    logo_cliente = preparar_logo(cfg["logo_cliente"], altura_export=120)
    logo_agencia = (preparar_logo(cfg["logo_agencia"], altura_export=72)
                    if cfg.get("logo_agencia") else "")

    print("  · embutindo documentos")
    docs_b64 = {}
    for cat in cfg["categorias"]:
        for d in cat.get("documentos", []):
            if d.get("url_externa"):
                print(f"      {d['chave']}  (link externo)")
                continue
            docs_b64[d["chave"]] = embutir_documento(d["arquivo"])
            print(f"      {d['chave']}")

    print("  · montando portal")
    html = gerar_portal(cfg, docs_b64, logo_cliente, logo_agencia)
    validar_saida(html, cfg)

    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(html, encoding="utf-8")

    # vercel.json
    (OUT / "vercel.json").write_text(json.dumps({
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "cleanUrls": True,
        "trailingSlash": False,
        "headers": [{
            "source": "/(.*)",
            "headers": [
                {"key": "X-Content-Type-Options", "value": "nosniff"},
                {"key": "X-Frame-Options", "value": "SAMEORIGIN"},
                {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"},
            ],
        }],
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    # README
    (OUT / "README.md").write_text(f"""# Central do Cliente · {cfg['cliente']}

Portal estático de documentos. Arquivo único: todo o HTML, CSS, JS e os documentos
(embutidos em base64) estão dentro do `index.html`. Sem build, sem dependências.

## Deploy

GitHub → Vercel → Add New Project → Framework Preset **Other** →
Build Command e Output Directory em branco → Deploy.

## Acesso

Protegido por credencial de acesso solicitada na tela de login.

> **Aviso de segurança.** A credencial é validada no navegador e fica visível no
> código-fonte. A barreira serve para organizar e apresentar o material, **não**
> como proteção de conteúdo confidencial. Para material sensível, use autenticação
> de servidor (ex.: Vercel Password Protection).

## Atualizar documentos

Edite o `config.json` e rode novamente o gerador.

---
© {cfg.get('ano', 2026)} {cfg.get('agencia', '')}
""", encoding="utf-8")

    print("  · gerando guia de acesso")
    guia_html = gerar_guia_html(cfg, logo_cliente, logo_agencia)
    nome = slug(cfg["cliente"])
    (OUT / f"{nome}_guia_de_acesso.html").write_text(guia_html, encoding="utf-8")
    if gerar_guia_pdf(guia_html, OUT / f"{nome}_guia_de_acesso.pdf"):
        print("      PDF gerado")

    print(f"\n  Pronto. Arquivos em: {OUT}/\n")


if __name__ == "__main__":
    main()
