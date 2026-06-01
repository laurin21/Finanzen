# 📊 Finanzanalyse App

Persönliche Finanzanalyse mit Streamlit & Google Sheets — läuft auf [share.streamlit.io](https://share.streamlit.io).

## Features
- Einnahmen vs. Ausgaben über Zeit (monatlich)
- Ausgaben nach Kategorie
- Monatliche Sparquote
- Kumulierter Saldo-Verlauf
- Budgetvergleich (Ø Monat vs. Ziel)
- Filter: Jahr, Kategorie, Beschreibungssuche (z.B. "REWE")

## Spaltennamen (deine Tabelle)
| Datum | Beschreibung | Kategorie | Betrag |
|-------|-------------|-----------|--------|
| 21.05.2026 | REWE | Lebensmittel | -45.30 |
| 01.05.2026 | Gehalt Mai | Einkommen | 2500.00 |

Negatives Betrag = Ausgabe, positiv = Einnahme.

---

## Setup

### Schritt 1 — Google Service Account
1. [console.cloud.google.com](https://console.cloud.google.com) → Projekt auswählen/erstellen
2. **Google Sheets API** aktivieren: APIs & Dienste → Bibliothek → suche "Sheets"
3. Anmeldedaten → Dienstkonto erstellen → JSON-Schlüssel herunterladen

### Schritt 2 — Google Sheet freigeben
- Sheet öffnen → Teilen
- `client_email` aus der JSON-Datei einfügen (sieht aus wie `xxx@projekt.iam.gserviceaccount.com`)
- Berechtigung: **Betrachter**

### Schritt 3 — Spreadsheet ID
Aus der URL: `https://docs.google.com/spreadsheets/d/`**`DIESE_ID`**`/edit`

### Schritt 4 — Secrets befüllen

**Lokal** — Datei `.streamlit/secrets.toml` öffnen und ausfüllen:
```toml
spreadsheet_id = "deine-spreadsheet-id"
worksheet_name = "Tabelle1"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```
> Tipp: Alle Werte stehen 1:1 in der heruntergeladenen JSON-Datei!

**Streamlit Cloud** → App Settings → **Secrets** → denselben Inhalt einfügen.

### Schritt 5 — Lokal starten
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Schritt 6 — Auf Streamlit Cloud deployen
1. Repo auf GitHub pushen (`.streamlit/secrets.toml` ist in `.gitignore` — wird nicht hochgeladen!)
2. [share.streamlit.io](https://share.streamlit.io) → "New app" → GitHub-Repo wählen
3. App Settings → Secrets → Inhalt der `secrets.toml` einfügen
4. Deploy!

---

## Budgets anpassen
In `app.py` oben im `CONFIG`-Block:
```python
"budgets": {
    "Lebensmittel": 300,   # € pro Monat
    "Miete":        800,
    "Transport":    100,
    # Kategorienamen müssen exakt mit deiner Tabelle übereinstimmen
}
```
