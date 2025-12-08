#!/usr/bin/env python3
"""
Generiert Einzel- und Sammelspendenbescheinigungen aus CSV.
CSV-Format: Nachname;Vorname;Straße;Adresszusatz;PLZ Ort;Betrag;Spendendatum
- Für Personen mit mehreren Einträgen wird das collective-template verwendet.
- collective-template muss den Token DONATION_ROWS enthalten.
"""
from pathlib import Path
import csv
import argparse
import subprocess
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

try:
    from num2words import num2words
except Exception:
    print("Bitte installieren: pip install num2words")
    raise SystemExit(1)

HERE = Path(__file__).parent
OUTDIR = HERE / "spendenbescheinigungen"

def amount_to_words(amount: str) -> str:
    s = amount.strip().replace('.', ',')
    if ',' in s:
        euro, cent = s.split(',')
        cent = (cent + "00")[:2]
    else:
        euro, cent = s, "00"
    try:
        euro_i = int(euro)
    except ValueError:
        raise
    words = num2words(euro_i, lang='de').capitalize()
    return f"{words} Euro und {cent}/100" if cent and cent != "00" else f"{words} Euro"

# neu: Wandelt einen Decimal-Betrag in Worte um (inkl. Cent)
def amount_decimal_to_words(dec: Decimal) -> str:
    # dec erwartet z.B. Decimal('1234.56')
    total_cents = (dec * 100).quantize(Decimal('1'))
    euro = int(total_cents // 100)
    cent = int(total_cents % 100)
    words = num2words(euro, lang='de').capitalize()
    if cent != 0:
        return f"{words} Euro und {cent:02d}/100"
    return f"{words} Euro"

def safe(s: str) -> str:
    return "".join(c if (c.isalnum() or c in "_-") else "_" for c in s).strip("_")

def parse_date(s: str):
    for fmt in ("%d.%m.%Y","%d.%m.%y","%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except Exception:
            pass
    return None

def compile_latex(texpath: Path):
    subprocess.run(["pdflatex","-interaction=nonstopmode","-halt-on-error","-output-directory",str(texpath.parent),str(texpath)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csvfile", type=Path)
    ap.add_argument("--template", type=Path, default=HERE/"00-spendenbescheinigung.tex")
    ap.add_argument("--collective-template", type=Path, default=HERE/"00-sammelbescheinigung.tex")
    ap.add_argument("--keep-tex", action="store_true")
    ap.add_argument("--ausstellungsdatum", "-d", type=str,
                    help="Ausstellungsdatum (z.B. 05.12.2025 oder 2025-12-05). Wenn nicht gesetzt: heute.")
    args = ap.parse_args()

    if not args.csvfile.exists():
        print("CSV nicht gefunden"); return
    if not args.template.exists():
        print("Einzel-Template nicht gefunden"); return
    if not args.collective_template.exists():
        print("Sammel-Template nicht gefunden"); return

    OUTDIR.mkdir(exist_ok=True)
    rows = []
    with args.csvfile.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=';')
        for r in reader:
            if not r or r[0].strip().startswith("#"): continue
            # pad to 7 cols (neu: zusätzliche Adresszeile / Adresszusatz)
            r = (r + [""]*7)[:7]
            nachname, vorname, strasse, strasse2, ort, betrag, spendendatum = [c.strip() for c in r]
            rows.append({
                "nachname": nachname,
                "vorname": vorname,
                "strasse": strasse,
                "strasse2": strasse2,
                "ort": ort,
                "betrag": betrag,
                "spendendatum": spendendatum,
                "dateobj": parse_date(spendendatum)
            })

    # group by lowercased name tuple
    groups = defaultdict(list)
    for r in rows:
        key = (r["nachname"].lower(), r["vorname"].lower())
        groups[key].append(r)

    # Ausstellungsdatum: entweder vom Argument oder heute
    if args.ausstellungsdatum:
        dt = parse_date(args.ausstellungsdatum)
        if not dt:
            print("Ungültiges Ausstellungsdatum. Erwartetes Format: DD.MM.YYYY oder YYYY-MM-DD"); return
        ausstellungsdatum = dt.strftime("%d.%m.%Y")
    else:
        ausstellungsdatum = datetime.now().strftime("%d.%m.%Y")

    tmpl_single = args.template.read_text(encoding="utf-8")
    tmpl_collective = args.collective_template.read_text(encoding="utf-8")

    for key, items in groups.items():
        nachname = items[0]["nachname"]
        vorname = items[0]["vorname"]
        display_name = f"{vorname} {nachname}".strip()
        if len(items) == 1:
            it = items[0]
            betrag_z = it["betrag"].replace('.',',')
            try:
                betrag_w = amount_to_words(it["betrag"])
            except Exception:
                betrag_w = it["betrag"]
            ctx = {
                "SPENDERNACHNAME": nachname,
                "SPENDERVORNAME": vorname,
                "SPENDERNAME": display_name,
                "SPENDERSTRASSE": it["strasse"],
                "SPENDERZUSATZ": it.get("strasse2",""),
                "SPENDERORT": it["ort"],
                "BETRAGZIFFERN": betrag_z,
                "BETRAGBUCHSTABEN": betrag_w,
                "SPENDENDATUM": it["spendendatum"],
                "AUSSTELLUNGSDATUM": ausstellungsdatum
            }
            tex = tmpl_single
            for k,v in ctx.items(): tex = tex.replace(k, v)
            fname = f"{safe(nachname)}_{safe(vorname)}_{it['spendendatum'].replace('.','-')}.tex"
            texpath = OUTDIR / fname
            texpath.write_text(tex, encoding="utf-8")
            compile_latex(texpath)
            if not args.keep_tex:
                for ext in (".tex",".aux",".log"):
                    p = texpath.with_suffix(ext)
                    if p.exists(): p.unlink()
            print("Einzel:", display_name)
        else:
            # Sammelbescheinigung: sort by date (fallback original order)
            items_sorted = sorted(items, key=lambda x: (x["dateobj"] if x["dateobj"] else datetime.min))
            # Erzeuge Zeilen: Datum & Betrag \\ \hline
            rows_tex = []
            total = Decimal('0.00')
            for it in items_sorted:
                betrag_raw = it["betrag"].strip()
                # Normalisiere Betrag: "1.234,56" -> "1234.56"
                norm = betrag_raw.replace('.', '').replace(',', '.')
                try:
                    dec = Decimal(norm)
                except (InvalidOperation, ValueError):
                    dec = Decimal('0.00')
                total += dec
                # Darstellung mit Komma als Dezimaltrennzeichen
                betrag_z = f"{dec:.2f}".replace('.',',')
                # Ausgabe-Zeile für LaTeX: "DD.MM.YYYY & 123,45 \\ \hline"
                rows_tex.append(f"{it['spendendatum']} & Spende & Nein & --{betrag_z} Euro -- \\\\ \\hline")
            # Spendenjahr aus letzten Eintrag
            year = datetime.strptime(it['spendendatum'],"%d.%m.%Y")
            # Gesamtbetrag als letzte Tabellenzeile (fett)
            total_str = f"{total:.2f}".replace('.',',')
            donation_rows = "\n".join(rows_tex)
            # Gesamtbetrag in Worten
            try:
                total_words = amount_decimal_to_words(total)
            except Exception:
                total_words = ""
            ctx = {
                "SPENDERNACHNAME": nachname,
                "SPENDERVORNAME": vorname,
                "BETRAGZIFFERN": total_str,
                "SPENDERNAME": display_name,
                "SPENDERSTRASSE": items_sorted[0]["strasse"],
                "SPENDERZUSATZ": items_sorted[0].get("strasse2",""),
                "SPENDERORT": items_sorted[0]["ort"],
                "DONATION_ROWS": donation_rows,
                "GESAMTBETRAGSWORTE": total_words,
                "AUSSTELLUNGSDATUM": ausstellungsdatum,
                "SPENDENJAHR": str(year.year)
            }
            tex = tmpl_collective
            for k,v in ctx.items(): tex = tex.replace(k, v)
            fname = f"{safe(nachname)}_{safe(vorname)}_sammel.tex"
            texpath = OUTDIR / fname
            texpath.write_text(tex, encoding="utf-8")
            compile_latex(texpath)
            if not args.keep_tex:
                for ext in (".tex",".aux",".log"):
                    p = texpath.with_suffix(ext)
                    if p.exists(): p.unlink()
            print("Sammel:", display_name, f"({len(items)} Spenden)")

if __name__ == "__main__":
    main()