# Datenbank-Status Anzeige Fix

## Problem
Die Datenbank-Status Anzeige (grün ✅ / rot ❌) wurde nicht korrekt angezeigt.

## Ursache
Die Konstanten `DATABASE_PRIVATE` und `DATABASE_SHARED` hatten keine Platzhalter für die Status-Emojis. Der Code versuchte `.format(status=...)` aufzurufen, aber die Strings hatten keine `{status}` Platzhalter.

## Lösung
1. **Status-Anzeige korrigiert**: Die Status-Emojis werden jetzt direkt nach dem Datenbank-Namen mit einem Doppelpunkt angezeigt:
   - Vorher: `DATABASE_PRIVATE.format(status=private_status)` (funktionierte nicht)
   - Nachher: `DATABASE_PRIVATE}: {private_status}` (funktioniert)

2. **Memo-Datenbank hinzugefügt**: Die Status-Anzeige zeigt jetzt auch den Status der Memo-Datenbank an:
   - 📝 Memo Datenbank: ✅ (wenn verbunden)
   - 📝 Memo Datenbank: ❌ (wenn Fehler)
   - 📝 Memo Datenbank: ❌ Nicht konfiguriert (wenn nicht eingerichtet)

## Geänderte Dateien
- `src/handlers/enhanced_appointment_handler.py`: 
  - Zeilen 70-102: Status-Anzeige korrigiert und Memo-Datenbank-Status hinzugefügt

## Resultat
Die Willkommensnachricht zeigt jetzt korrekt den Status aller drei Datenbanken an:
- 🔒 Private Datenbank: ✅/❌
- 👥 Geteilte Datenbank: ✅/❌/Nicht konfiguriert
- 📝 Memo Datenbank: ✅/❌/Nicht konfiguriert