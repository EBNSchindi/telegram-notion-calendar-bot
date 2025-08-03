# 🔧 Fehlerbehebung - Telegram Notion Calendar Bot

## 🕐 Zeitformat-Probleme

### Problem: "Ungültiges Zeitformat" Fehler

**Symptom:** Der Bot akzeptiert deine Zeitangabe nicht.

**Schnelle Lösung:**
1. **Teste dein Zeitformat:** `/test_time 16 Uhr`
2. **Zeige alle Formate:** `/formats`
3. **Validiere kompletten Befehl:** `/validate morgen 16 Uhr Meeting`

### Häufige Zeitformat-Fehler

| ❌ Falsch | ✅ Richtig | Ergebnis |
|-----------|------------|----------|
| `16` | `16 Uhr` oder `16:00` | 16:00 |
| `4 pm` (Leerzeichen) | `4pm` oder `4 PM` | 16:00 |
| `2,30` | `2:30` oder `2.30` | 02:30 |
| `halb3` | `halb 3` | 02:30 |
| `viertelvor5` | `viertel vor 5` | 04:45 |

### Unterstützte Zeitformate

#### 🕐 Standard-Formate
```
14:30    → 14:30
14.30    → 14:30  
1430     → 14:30
930      → 09:30
```

#### 🇩🇪 Deutsche Formate
```
16 Uhr              → 16:00
16 Uhr 30           → 16:30
16:30 Uhr           → 16:30
halb 3              → 02:30
viertel vor 5       → 04:45
viertel nach 3      → 03:15
```

#### 🇺🇸 English Formate
```
4 PM                → 16:00
8 AM                → 08:00
4:30 PM             → 16:30
12 AM               → 00:00 (Mitternacht)
12 PM               → 12:00 (Mittag)
quarter past 2      → 02:15
half past 3         → 03:30
quarter to 5        → 04:45
```

## 🗂 Datenbank-Probleme

### Problem: "Du bist noch nicht konfiguriert"

**Ursache:** Deine Telegram User ID ist nicht in der `users_config.json` eingetragen.

**Lösung:**
1. Deine User ID findest du mit `/start` (wird angezeigt)
2. Administrator muss dich in `users_config.json` hinzufügen
3. Bot neu starten

### Problem: Termine aus gemeinsamer Datenbank werden nicht angezeigt

**Mögliche Ursachen:**
- `shared_notion_api_key` oder `shared_notion_database_id` fehlen
- Keine Berechtigung für gemeinsame Datenbank
- Gemeinsame Datenbank ist leer

**Debugging:**
1. Prüfe mit `/start` den Datenbankstatus
2. Teste Verbindung mit `/reminder test`

### Problem: Partner-Sync funktioniert nicht (Termine erscheinen nicht in geteilter Datenbank)

**Symptome:**
- Termine mit "Partner Relevant" bleiben nur in privater Datenbank
- Keine Fehlermeldungen in Telegram
- Geteilte Datenbank bleibt leer

**Häufige Ursachen:**
1. **Fehlende Konfiguration:** `shared_notion_database_id` nicht gesetzt
2. **Berechtigungen:** API-Key hat keinen Zugriff auf beide Datenbanken
3. **Datumsfeld-Migration:** Alte `Datum` vs neue `Startdatum`/`Endedatum` Felder
4. **Netzwerk-Probleme:** Besonders in Docker-Umgebungen

**Schnelle Lösung:**
1. **Konfiguration prüfen:** Stelle sicher, dass `shared_notion_database_id` in `users_config.json` vorhanden ist
2. **Schema prüfen:** Geteilte Datenbank muss `Startdatum`, `Endedatum`, `SourcePrivateId` und `SourceUserId` haben
3. **Test-Termin:** Erstelle `/add morgen 14:00 SYNC_TEST` und markiere als Partner Relevant
4. **Logs prüfen:** `docker logs -f calendar-telegram-bot | grep "Partner sync"`

**Hinweis:** Der Bot hat jetzt einen automatischen Retry-Mechanismus (3 Versuche mit exponentieller Verzögerung: 1s → 2s → 4s). Bei temporären Fehlern (Netzwerk, Rate Limits) wird automatisch wiederholt.

📖 **Ausführliche Anleitung:** Siehe [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) für detaillierte Partner-Sync Fehlerbehebung

## 📅 Termin-Erstellung Probleme

### Problem: "Termin muss in der Zukunft liegen"

**Ursache:** Du versuchst einen Termin in der Vergangenheit zu erstellen.

**Lösung:**
```bash
# Falsch (wenn es schon nach 14:30 ist)
/add heute 14:30 Meeting

# Richtig
/add morgen 14:30 Meeting
# oder
/add heute 16:00 Meeting  # wenn es noch vor 16:00 ist
```

### Problem: Termin wird nicht erstellt

**Debugging-Schritte:**
1. **Validiere Eingabe:** `/validate morgen 16 Uhr Meeting`
2. **Teste Zeitformat:** `/test_time 16 Uhr`
3. **Prüfe Datenbankstatus:** `/start`

## 📨 Erinnerungs-Probleme

### Problem: Keine Erinnerungen erhalten

**Checkliste:**
1. ✅ Erinnerungen aktiviert: `/reminder`
2. ✅ Richtige Zeit eingestellt: `/reminder time 08:00`
3. ✅ Bot läuft und ist online
4. ✅ Termine für heute/morgen vorhanden

**Test:** `/reminder test` - sollte sofort eine Erinnerung senden

### Problem: Erinnerung zeigt falsche Termine

**Mögliche Ursachen:**
- Zeitzone falsch konfiguriert
- Daten in falscher Datenbank

**Lösung:**
- Prüfe Zeitzone in `users_config.json`
- Teste mit `/reminder preview`

## 🎛 Menü-Probleme

### Problem: Inline-Buttons funktionieren nicht

**Ursache:** Alte Telegram-Version oder Bot-Update

**Lösung:**
1. Telegram App aktualisieren
2. Bot mit `/start` neu starten
3. Alternativ: Direkte Befehle verwenden (`/today`, `/list`, etc.)

## 🔍 Debug-Befehle nutzen

### Zeitformat testen
```bash
/test_time 16 Uhr
# Zeigt: ✅ Success: 16:00 (16:00)

/test_time 4 PM  
# Zeigt: ✅ Success: 16:00 (16:00)

/test_time halb 3
# Zeigt: ✅ Success: 02:30 (02:30)
```

### Alle Formate anzeigen
```bash
/formats
# Zeigt komplette Liste aller unterstützten Zeitformate
```

### Termin-Eingabe validieren
```bash
/validate morgen 16 Uhr Meeting
# Prüft Datum, Zeit und Titel vor der Erstellung
```

## 📞 Support

### Wenn nichts hilft:

1. **Logs prüfen:** Bot-Administrator kann `bot_enhanced.log` überprüfen
2. **Neu starten:** Bot und/oder Telegram App neu starten
3. **Test-Commands:** Nutze Debug-Befehle zur Diagnose
4. **Config prüfen:** `users_config.json` und `.env` validieren

### Häufige Lösungen:
- Bot neu starten
- Telegram App aktualisieren  
- Konfiguration neu laden
- User-Cache löschen (Bot neu starten)

---

💡 **Tipp:** Nutze die Debug-Befehle (`/test_time`, `/formats`, `/validate`) um Probleme schnell zu identifizieren!