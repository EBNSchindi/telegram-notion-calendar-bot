# 📝 Memo-Funktionen - Bedienungsanleitung

## So erstellen Sie ein neues Memo:

### Option 1: Über das Hauptmenü (Empfohlen)
1. Senden Sie `/start` an den Bot
2. Klicken Sie auf **"➕ Neues Memo"**
3. Der Bot antwortet mit Anweisungen und Beispielen
4. Schreiben Sie Ihre Aufgabe als normale Nachricht, z.B.:
   - "Einkaufsliste: Milch, Brot, Butter"
   - "Präsentation vorbereiten bis Freitag"
   - "Zahnarzttermin buchen"
5. Der Bot verarbeitet Ihre Nachricht und speichert das Memo

### Option 2: Direkte Eingabe
1. Öffnen Sie das Hauptmenü mit `/start`
2. Klicken Sie auf **"➕ Neues Memo"**
3. Folgen Sie den Anweisungen

## So zeigen Sie Ihre Memos an:

### Nur offene Memos anzeigen:
- Befehl: `/start` → **"📝 Letzte Memos"**
- Zeigt nur unerledigte Memos (Status_Check = false)

### Alle Memos anzeigen:
- Befehl: `/show_all`
- Zeigt alle Memos inklusive erledigte

## Wichtige Hinweise:

### ✅ Was funktioniert:
- Memo-Erstellung über das Menü
- Anzeige offener Memos
- Anzeige aller Memos mit `/show_all`
- KI-unterstützte Texterkennung

### ⚠️ Bekannte Einschränkungen:
- Eine korrupte Seite in der Datenbank wird übersprungen
- Memo-Abhaken über Telegram ist implementiert aber nicht empfohlen

### 🔧 Bei Problemen:
1. Stellen Sie sicher, dass Sie den Bot mit `/start` gestartet haben
2. Verwenden Sie die Menü-Buttons statt direkte Texteingabe
3. Warten Sie nach dem Klicken auf "➕ Neues Memo" auf die Antwort des Bots
4. Schreiben Sie erst dann Ihre Aufgabe

## Technische Details:
- Die Memos werden in der Notion-Datenbank "Aufgaben" gespeichert
- Neue Memos haben standardmäßig Status_Check = false
- Der Bot nutzt KI zur Texterkennung (falls verfügbar)