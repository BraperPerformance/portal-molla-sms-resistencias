#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta os documentos da Central do Cliente SMS a partir de:
  sms_design.css  -> identidade visual compartilhada
  corpo/*.html    -> apenas o conteúdo de cada documento (sem <head>, sem CSS)

Saída: clientes/sms-resistencias/documentos/*.html  (autossuficientes)
"""
import base64, re
from pathlib import Path

BASE = Path(__file__).parent
CSS = (BASE / "sms_design.css").read_text(encoding="utf-8")
CORPO = BASE / "corpo"
OUT = BASE / "clientes/sms-resistencias/documentos"
LOGO_CLIENTE = BASE / "clientes/sms-resistencias/logos/cliente.png"
LOGO_AGENCIA = BASE / "extr/img0.png"   # logo Molla em alta, extraído da referência

FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800"
         "&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap")


def b64(p):
    return "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()


SHELL = """<!DOCTYPE html>
<html lang="pt-br"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} — SMS Resistências | Agência Molla</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts}" rel="stylesheet">
<style>
{css}
</style>
</head><body>

<header class="hdr"><div class="hdr-in">
  <img class="hdr-logo" src="{logo}" alt="SMS Resistências Elétricas" />
  <span class="hdr-sep"></span>
  <span class="hdr-tag">Central do Cliente</span>
  <button class="hdr-pdf" onclick="window.print()">Baixar PDF</button>
</div></header>

{body}

<footer class="ft"><div class="ft-in">
  <img class="ft-logo" src="{molla}" alt="Agência Molla" />
  <div class="ft-txt">{footer}</div>
</div></footer>
</body></html>
"""


def build(slug, title, footer):
    body = (CORPO / f"{slug}.html").read_text(encoding="utf-8")
    html = SHELL.format(title=title, fonts=FONTS, css=CSS, body=body, footer=footer,
                        logo=b64(LOGO_CLIENTE), molla=b64(LOGO_AGENCIA))
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{slug}.html"
    dest.write_text(html, encoding="utf-8")
    print(f"  ✓ {dest.name}  ({len(html)//1024} KB)")
    return dest


DOCS = [
    ("report_20260720_performance-jan-jul", "Performance Google Ads · Jan–Jul 2026",
     "<b>Agência Molla</b> · Performance &amp; Growth<br>Dados de 1 de janeiro a 20 de julho de 2026, extraídos do Google Ads."),
    ("report_20260615_status-semanal", "Atualização da Conta · Junho 2026",
     "<b>Agência Molla</b> · Performance &amp; Growth<br>Atualização de junho de 2026."),
    ("report_20260701_status-semanal_definicoes-importantes", "Atualização da Conta · Julho 2026",
     "<b>Agência Molla</b> · Performance &amp; Growth<br>Atualização de 1º de julho de 2026."),
]

if __name__ == "__main__":
    print("\n  Montando documentos com a identidade da Central:")
    for slug, title, foot in DOCS:
        if (CORPO / f"{slug}.html").exists():
            build(slug, title, foot)
        else:
            print(f"  ! corpo ausente: {slug}.html")
    print()
