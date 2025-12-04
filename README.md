# Spendenbescheinigungen automatisch generieren

Dieses Repository erzeugt PDF-Spendenbescheinigungen aus einer semikolon-getrennten CSV-Datei.

Kurzfassung
- Eingabe: CSV (Semikolon) mit Spenderdaten
- Ausgabe: PDFs im Ordner `spendenbescheinigungen/`
- Templates: LaTeX-Dateien im Projekt (Einzel- und Sammel-Templates)
- Hauptscript: `generate-spendenbescheinigung.py`

Voraussetzungen
- Python 3 (>=3.7)
- pdflatex (Teil einer LaTeX-Distribution, z. B. TeX Live)
- Python-Paket: num2words

Installation (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install -y texlive-latex-base texlive-lang-german
python3 -m pip install --user num2words
```

Installation (Fedora)
```bash
sudo dnf install -y texlive-scheme-medium texlive-babel-german
python3 -m pip install --user num2words
```

CSV-Format
Die Datei muss UTF-8-kodiert sein und das Format (Semikolon) haben:
```
Nachname;Vorname;Straße;PLZ Ort;Betrag;Spendendatum
```
Beispiel:
```
Mustermensch;Muster;Musterstr. 1;10000 Musterstadt;50,00;01.01.2025
Menschmuster;Mona;Musterallee 1;12345 Musterdorf;100.00;15.07.2025
```
- Beträge können Komma oder Punkt als Dezimaltrennzeichen verwenden.
- Kommentarzeilen mit `#` werden ignoriert.

Verwendung
```bash
# ausführbar machen (optional)
chmod +x generate-spendenbescheinigung.py

# Einzel- und Sammelbescheinigungen generieren
python3 generate-spendenbescheinigung.py spenden.csv

# .tex-Dateien behalten (für Debug)
python3 generate-spendenbescheinigung.py spenden.csv --keep-tex
```

Wichtige Hinweise
- Das Script erwartet die Template-Dateien `00-spendenbescheinigung.tex` und `00-sammelbescheinigung.tex` im Projektverzeichnis.
- Das Datum der Ausstellung wird automatisch gesetzt.
- Bitte prüfe die erzeugten PDFs rechtlich (Steuernummern, Freistellungsbescheide etc.) vor dem Versand.

Fehlerbehebung
- "pdflatex: command not found": LaTeX nicht installiert oder nicht im PATH.
- Umlaute falsch? Stelle sicher, dass CSV UTF-8-kodiert ist.
- num2words fehlt? Installieren mit `python3 -m pip install --user num2words`.

Lizenz & Haftung
Dieses Script ist ein Hilfsmittel. Die Verantwortung für inhaltliche und rechtliche Richtigkeit der Bescheinigungen liegt beim Aussteller.