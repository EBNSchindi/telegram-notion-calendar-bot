"""Debug handler for testing time formats and troubleshooting."""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.utils.robust_time_parser import RobustTimeParser
from src.services.combined_appointment_service import CombinedAppointmentService
from config.user_config import UserConfigManager
from config.settings import Settings

logger = logging.getLogger(__name__)


class DebugHandler:
    """Handler for debugging and testing time formats."""
    
    def __init__(self, user_config_manager: UserConfigManager = None):
        self.user_config_manager = user_config_manager
        self.settings = Settings()
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is authorized to use debug commands."""
        return user_id in self.settings.admin_users or (
            self.settings.environment == 'development' and user_id in self.settings.authorized_users
        )
    
    async def test_time_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Test a time format input."""
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ Zugriff verweigert. Debug-Befehle sind nur für Administratoren verfügbar.")
            return
            
        if not context.args:
            help_text = (
                "🧪 *Zeit-Format Tester*\n\n"
                "*Verwendung:*\n"
                "`/test_time <Zeitformat>`\n\n"
                "*Beispiele:*\n"
                "• `/test_time 16 Uhr`\n"
                "• `/test_time 4 PM`\n"
                "• `/test_time halb 3`\n"
                "• `/test_time quarter past 2`\n\n"
                "*Zweck:*\n"
                "Teste verschiedene Zeitformate, um zu sehen, "
                "wie sie interpretiert werden."
            )
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        time_input = " ".join(context.args)
        
        try:
            parsed_time = RobustTimeParser.parse_time(time_input)
            
            # Format in different ways
            standard_format = parsed_time.strftime("%H:%M")
            natural_de = RobustTimeParser.format_time(parsed_time, use_natural=True, language='de')
            natural_en = RobustTimeParser.format_time(parsed_time, use_natural=True, language='en')
            
            result_text = (
                f"✅ *Zeitformat erfolgreich geparst!*\n\n"
                f"*Eingabe:* `{time_input}`\n"
                f"*Ergebnis:* `{standard_format}`\n\n"
                f"*Formatierungen:*\n"
                f"• Standard: {standard_format}\n"
                f"• Deutsch: {natural_de}\n"
                f"• English: {natural_en}\n\n"
                f"💡 *Tipp:* Dieses Format funktioniert für `/add` Befehle!"
            )
            
            await update.message.reply_text(result_text, parse_mode='Markdown')
            
        except ValueError as e:
            error_text = (
                f"❌ *Zeitformat nicht erkannt*\n\n"
                f"*Eingabe:* `{time_input}`\n"
                f"*Fehler:* {str(e)}\n\n"
                f"💡 *Tipp:* Versuche eines der unterstützten Formate!"
            )
            
            await update.message.reply_text(error_text, parse_mode='Markdown')
        
        except Exception as e:
            logger.error(f"Unexpected error in test_time_format: {e}")
            await update.message.reply_text(
                f"❌ Ein unerwarteter Fehler ist aufgetreten: {str(e)}"
            )
    
    async def show_time_formats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show all supported time formats with examples."""
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ Zugriff verweigert. Debug-Befehle sind nur für Administratoren verfügbar.")
            return
        formats_text = """
📚 *Unterstützte Zeitformate*

*🕐 Standard-Formate:*
• `14:30` - 24-Stunden mit Doppelpunkt
• `14.30` - 24-Stunden mit Punkt  
• `1430` - Kompakt ohne Trenner
• `930` - Kompakt für einstellige Stunden

*🇩🇪 Deutsche Formate:*
• `16 Uhr` - Volle Stunde
• `16 Uhr 30` - Mit Minuten
• `16:30 Uhr` - Standard mit "Uhr"
• `halb 3` - Halbe Stunden (2:30)
• `viertel vor 5` - Viertel vor (4:45)
• `viertel nach 3` - Viertel nach (3:15)

*🇺🇸 English Formats:*
• `4 PM` - Afternoon/Evening
• `8 AM` - Morning
• `4:30 PM` - With minutes
• `4.30 PM` - Alternative separator
• `12 AM` - Midnight (00:00)
• `12 PM` - Noon (12:00)
• `quarter past 2` - Quarter past (2:15)
• `half past 3` - Half past (3:30)
• `quarter to 5` - Quarter to (4:45)

*💡 Tipps:*
• Groß-/Kleinschreibung spielt keine Rolle
• Leerzeichen sind flexibel
• Teste mit `/test_time <format>` bevor du einen Termin erstellst
        """
        
        await update.message.reply_text(formats_text, parse_mode='Markdown')
    
    async def validate_appointment_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Validate a complete appointment input."""
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ Zugriff verweigert. Debug-Befehle sind nur für Administratoren verfügbar.")
            return
            
        if len(context.args) < 3:
            help_text = (
                "🔍 *Termin-Eingabe Validator*\n\n"
                "*Verwendung:*\n"
                "`/validate_appointment <Datum> <Zeit> <Titel>`\n\n"
                "*Beispiel:*\n"
                "`/validate_appointment morgen 16 Uhr Meeting`\n\n"
                "*Zweck:*\n"
                "Überprüfe deine Termin-Eingabe bevor du sie mit `/add` erstellst."
            )
            await update.message.reply_text(help_text, parse_mode='Markdown')
            return
        
        date_str = context.args[0]
        time_str = context.args[1]
        title = " ".join(context.args[2:])
        
        # Validate date
        date_valid = True
        date_feedback = ""
        
        if date_str.lower() in ['heute', 'today']:
            date_feedback = "✅ Heute erkannt"
        elif date_str.lower() in ['morgen', 'tomorrow']:
            date_feedback = "✅ Morgen erkannt"
        else:
            try:
                from datetime import datetime
                for fmt in ['%d.%m.%Y', '%d.%m.%y', '%Y-%m-%d']:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt).date()
                        date_feedback = f"✅ Datum erkannt: {parsed_date.strftime('%d.%m.%Y')}"
                        break
                    except ValueError:
                        continue
                else:
                    date_valid = False
                    date_feedback = "❌ Datum nicht erkannt"
            except:
                date_valid = False
                date_feedback = "❌ Datum-Fehler"
        
        # Validate time
        time_valid = True
        time_feedback = ""
        
        try:
            parsed_time = RobustTimeParser.parse_time(time_str)
            time_feedback = f"✅ Zeit erkannt: {parsed_time.strftime('%H:%M')}"
        except ValueError as e:
            time_valid = False
            time_feedback = f"❌ Zeit nicht erkannt: {str(e).split('.')[0]}"
        except Exception as e:
            time_valid = False
            time_feedback = f"❌ Zeit-Fehler: {str(e)}"
        
        # Validate title
        title_valid = len(title.strip()) > 0
        title_feedback = "✅ Titel OK" if title_valid else "❌ Titel ist leer"
        
        # Overall status
        all_valid = date_valid and time_valid and title_valid
        status_icon = "✅" if all_valid else "❌"
        
        result_text = (
            f"{status_icon} *Termin-Validierung*\n\n"
            f"*Eingabe:*\n"
            f"• Datum: `{date_str}` → {date_feedback}\n"
            f"• Zeit: `{time_str}` → {time_feedback}\n"
            f"• Titel: `{title}` → {title_feedback}\n\n"
        )
        
        if all_valid:
            result_text += (
                f"🎯 *Bereit zum Erstellen!*\n"
                f"Verwende: `/add {date_str} {time_str} {title}`"
            )
        else:
            result_text += (
                f"🔧 *Korrekturen erforderlich:*\n"
                f"• Nutze `/formats` für unterstützte Zeitformate\n"
                f"• Nutze `/test_time {time_str}` zum Testen der Zeit"
            )
        
        await update.message.reply_text(result_text, parse_mode='Markdown')
    
    async def test_notion_connection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Test Notion database connections for the user."""
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ Zugriff verweigert. Debug-Befehle sind nur für Administratoren verfügbar.")
            return
            
        if not self.user_config_manager:
            await update.message.reply_text("❌ User Config Manager nicht verfügbar")
            return
        user_config = self.user_config_manager.get_user_config(user_id)
        
        if not user_config:
            await update.message.reply_text(
                "❌ Du bist noch nicht konfiguriert.\n"
                f"Deine User ID: `{user_id}`"
            )
            return
        
        await update.message.reply_text("🔍 Teste Notion-Verbindungen...")
        
        try:
            # Create combined service
            combined_service = CombinedAppointmentService(user_config)
            
            # Test connections
            private_ok, shared_ok = await combined_service.test_connections()
            
            # Build status message
            status_parts = ["📊 *Notion-Verbindungstest:*\n"]
            
            # Private database status
            private_icon = "✅" if private_ok else "❌"
            status_parts.append(f"👤 Private DB: {private_icon}")
            if not private_ok:
                status_parts.append("   • API Key oder Database ID prüfen")
            
            # Shared database status
            if shared_ok is None:
                status_parts.append("🌐 Gemeinsame DB: ⚠️ Nicht konfiguriert")
            else:
                shared_icon = "✅" if shared_ok else "❌"
                status_parts.append(f"🌐 Gemeinsame DB: {shared_icon}")
                if not shared_ok:
                    status_parts.append("   • Shared API Key oder Database ID prüfen")
            
            # Add configuration details
            status_parts.append(f"\n*Konfiguration:*")
            status_parts.append(f"• User ID: `{user_config.telegram_user_id}`")
            status_parts.append(f"• Username: `{user_config.telegram_username}`")
            status_parts.append(f"• Timezone: `{user_config.timezone}`")
            status_parts.append(f"• Private DB ID: `{user_config.notion_database_id[:8]}...`")
            
            if user_config.shared_notion_database_id:
                status_parts.append(f"• Shared DB ID: `{user_config.shared_notion_database_id[:8]}...`")
            else:
                status_parts.append("• Shared DB: Nicht konfiguriert")
            
            # Overall status
            if private_ok:
                if shared_ok or shared_ok is None:
                    status_parts.append("\n🎯 *Status: Einsatzbereit!*")
                else:
                    status_parts.append("\n⚠️ *Status: Private DB OK, Shared DB Problem*")
            else:
                status_parts.append("\n❌ *Status: Private DB Problem - Bot nicht einsatzbereit*")
            
            await update.message.reply_text("\n".join(status_parts), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error testing Notion connection: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Fehler beim Testen der Verbindung:\n\n"
                f"`{str(e)}`\n\n"
                "Überprüfe deine Notion-Konfiguration."
            )