# 🔧 Memo-Funktion Fehlerbehebung

## ✅ Problem behoben

Das Memo-Modell war veraltet und verwendete die falschen Feldnamen. Es wurde jetzt korrigiert.

## 📋 Notion-Datenbank Anforderungen

Damit die Memo-Funktion funktioniert, muss Ihre Notion-Datenbank folgende Felder haben:

### Pflichtfelder:
1. **Aufgabe** (Title) - Das Hauptfeld für den Aufgabentitel
2. **Status** (Select) mit folgenden Optionen:
   - "Nicht begonnen"
   - "In Arbeit"
   - "Erledigt"

### Optionale Felder:
3. **Fälligkeitsdatum** (Date) - Für Termine/Deadlines
4. **Bereich** (Multi-select) - Für Kategorien (z.B. "Arbeit", "Privat")
5. **Projekt** (Multi-select) - Für Projektzuordnung
6. **Notizen** (Text/Rich text) - Für zusätzliche Details

## 🛠️ Einrichtung in Notion

### Schritt 1: Neue Datenbank erstellen
1. Öffnen Sie Notion
2. Erstellen Sie eine neue Seite
3. Wählen Sie "Table" als Datenbanktyp
4. Benennen Sie die Datenbank (z.B. "Memos" oder "Aufgaben")

### Schritt 2: Felder hinzufügen
Klicken Sie auf "+ New property" und fügen Sie folgende Felder hinzu:

| Feldname | Typ | Pflicht | Optionen |
|----------|-----|---------|----------|
| Aufgabe | Title | ✅ | (Standard) |
| Status | Select | ✅ | "Nicht begonnen", "In Arbeit", "Erledigt" |
| Fälligkeitsdatum | Date | ❌ | - |
| Bereich | Multi-select | ❌ | z.B. "Arbeit", "Privat", "Einkauf" |
| Projekt | Multi-select | ❌ | Ihre Projekte |
| Notizen | Text | ❌ | - |

### Schritt 3: Datenbank-ID kopieren
1. Öffnen Sie die Datenbank in Notion
2. Kopieren Sie die URL (z.B. `https://www.notion.so/Your-Database-abc123...`)
3. Die ID ist der Teil nach dem letzten `/` und vor dem `?` (falls vorhanden)
4. Beispiel: Bei `https://www.notion.so/Memos-abc123def456?v=...` ist die ID `abc123def456`

### Schritt 4: Bot konfigurieren
Fügen Sie die Datenbank-ID in Ihre `users_config.json` ein:

```json
{
  "users": {
    "YOUR_TELEGRAM_ID": {
      "telegram_id": 123456789,
      "notion_api_key": "secret_...",
      "notion_database_id": "your-appointments-db-id",
      "memo_database_id": "abc123def456",  // ← Hier einfügen!
      "timezone": "Europe/Berlin"
    }
  }
}
```

## 🚀 Verwendung

### Memo erstellen:
1. Öffnen Sie das Bot-Menü mit `/menu`
2. Klicken Sie auf "➕ Neues Memo"
3. Geben Sie Ihre Aufgabe ein:
   - Einfach: "Einkaufen gehen"
   - Mit Datum: "Präsentation vorbereiten bis Freitag"
   - Mit Details: "Projekt-Bericht schreiben - Deadline 15.8., Fokus auf Q3 Zahlen"

### AI-Extraktion:
Der Bot erkennt automatisch:
- **Aufgabe**: Der Haupttext wird zur Aufgabe
- **Fälligkeitsdatum**: "bis Freitag", "bis morgen", "am 25.12."
- **Bereich/Projekt**: Basierend auf Keywords im Text
- **Notizen**: Zusätzliche Details nach Bindestrichen oder in Klammern

## ❌ Häufige Fehler

### "Memo-Datenbank nicht konfiguriert"
- Lösung: `memo_database_id` in `users_config.json` hinzufügen

### "Failed to create memo in Notion"
Mögliche Ursachen:
1. Falscher Notion API Key
2. Keine Berechtigung für die Datenbank
3. Fehlende oder falsch benannte Felder in Notion
4. Falsche Datenbank-ID

### Überprüfung:
1. Testen Sie die Notion-Verbindung mit einem Termin
2. Prüfen Sie, ob alle Feldnamen EXAKT übereinstimmen (Groß-/Kleinschreibung!)
3. Stellen Sie sicher, dass der API-Key Zugriff auf die Memo-Datenbank hat

## 💡 Tipps

- Die Memo-Datenbank kann dieselbe sein wie die Termin-Datenbank (wenn die Felder vorhanden sind)
- Oder verwenden Sie separate Datenbanken für bessere Organisation
- Die Status-Optionen müssen EXAKT "Nicht begonnen", "In Arbeit", "Erledigt" heißen