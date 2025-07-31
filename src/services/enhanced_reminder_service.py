"""Enhanced reminder service with combined database support."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz
from telegram import Bot
from telegram.error import TelegramError

from src.services.combined_appointment_service import CombinedAppointmentService
from src.services.memo_service import MemoService
from config.user_config import UserConfig, UserConfigManager

logger = logging.getLogger(__name__)


class EnhancedReminderService:
    """Enhanced service for sending daily appointment reminders from both databases."""
    
    def __init__(self, bot: Bot, user_config_manager: UserConfigManager):
        self.bot = bot
        self.user_config_manager = user_config_manager
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the reminder service."""
        if self._running:
            logger.warning("Reminder service is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._reminder_loop())
        logger.info("Enhanced reminder service started")
    
    async def stop(self):
        """Stop the reminder service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Enhanced reminder service stopped")
    
    async def _reminder_loop(self):
        """Main reminder loop that checks for reminders to send."""
        while self._running:
            try:
                # Get current time
                now = datetime.now(pytz.timezone('Europe/Berlin'))
                current_time = now.strftime('%H:%M')
                
                # Check if we need to send reminders
                users = self.user_config_manager.get_users_for_reminders(current_time)
                
                for user in users:
                    try:
                        await self._send_enhanced_reminder(user)
                    except Exception as e:
                        logger.error(f"Error sending reminder to user {user.telegram_user_id}: {e}")
                
                # Wait until next minute
                next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
                wait_seconds = (next_minute - datetime.now(pytz.timezone('Europe/Berlin'))).total_seconds()
                
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                    
            except Exception as e:
                logger.error(f"Error in reminder loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _send_enhanced_reminder(self, user: UserConfig):
        """Send enhanced reminder to a specific user from both databases."""
        try:
            # Create combined appointment service for this user
            combined_service = CombinedAppointmentService(user)
            
            # Create memo service if available
            memo_service = None
            open_memos = []
            if user.memo_database_id:
                try:
                    memo_service = MemoService.from_user_config(user)
                    # Get only open memos (not completed)
                    open_memos = await memo_service.get_recent_memos(limit=5, only_open=True)
                except Exception as e:
                    logger.warning(f"Could not load memos for user {user.telegram_user_id}: {e}")
            
            # Get user's timezone
            tz = pytz.timezone(user.timezone)
            today = datetime.now(tz).date()
            tomorrow = (datetime.now(tz) + timedelta(days=1)).date()
            
            # Get appointments for today and tomorrow
            today_appointments = await combined_service.get_today_appointments()
            tomorrow_appointments = await combined_service.get_tomorrow_appointments()
            
            # Build message
            message_parts = []
            
            if today_appointments or tomorrow_appointments or open_memos:
                message_parts.append("📅 *Deine Termine:*\n")
                
                if today_appointments:
                    message_parts.append(f"\n*📅 Heute ({today.strftime('%d.%m.%Y')}):*")
                    for apt_src in sorted(today_appointments, key=lambda x: x.appointment.date):
                        apt = apt_src.appointment
                        time_str = apt.date.astimezone(tz).strftime('%H:%M')
                        source_icon = "🌐" if apt_src.is_shared else "👤"
                        
                        message_parts.append(f"{source_icon} {time_str} - *{apt.title}*")
                        if apt.description:
                            message_parts.append(f"   _{apt.description}_")
                
                if tomorrow_appointments:
                    message_parts.append(f"\n\n*🗓️ Morgen ({tomorrow.strftime('%d.%m.%Y')}):*")
                    for apt_src in sorted(tomorrow_appointments, key=lambda x: x.appointment.date):
                        apt = apt_src.appointment
                        time_str = apt.date.astimezone(tz).strftime('%H:%M')
                        source_icon = "🌐" if apt_src.is_shared else "👤"
                        
                        message_parts.append(f"{source_icon} {time_str} - *{apt.title}*")
                        if apt.description:
                            message_parts.append(f"   _{apt.description}_")
                
                # Add open memos if available
                if open_memos:
                    message_parts.append("\n\n*📝 Offene Memos:*")
                    for memo in open_memos[:5]:  # Max 5 memos in reminder
                        # Use new checkbox formatting for consistent display
                        memo_formatted = memo.format_for_telegram_with_checkbox(user.timezone)
                        # Extract just the first line (checkbox + emoji + title) for compact reminder
                        memo_lines = memo_formatted.split('\n')
                        memo_title_line = memo_lines[0] if memo_lines else f"☐ *{memo.aufgabe}*"
                        
                        # Add due date if available on the same line for compact display
                        if memo.faelligkeitsdatum:
                            memo_date = memo.faelligkeitsdatum.astimezone(tz) if memo.faelligkeitsdatum.tzinfo else tz.localize(memo.faelligkeitsdatum)
                            memo_title_line += f" (📅 {memo_date.strftime('%d.%m.%Y')})"
                        
                        message_parts.append(memo_title_line)
                
                # Add legend
                if today_appointments or tomorrow_appointments:
                    message_parts.append("\n\n_👤 Private Termine | 🌐 Gemeinsame Termine_")
                
                # Send message
                await self.bot.send_message(
                    chat_id=user.telegram_user_id,
                    text="\n".join(message_parts),
                    parse_mode='Markdown'
                )
                
                # Log statistics
                total_today = len(today_appointments)
                total_tomorrow = len(tomorrow_appointments)
                today_private = sum(1 for x in today_appointments if not x.is_shared)
                today_shared = sum(1 for x in today_appointments if x.is_shared)
                tomorrow_private = sum(1 for x in tomorrow_appointments if not x.is_shared)
                tomorrow_shared = sum(1 for x in tomorrow_appointments if x.is_shared)
                
                logger.info(
                    f"Sent reminder to user {user.telegram_user_id}: "
                    f"Today: {total_today} ({today_private} private, {today_shared} shared), "
                    f"Tomorrow: {total_tomorrow} ({tomorrow_private} private, {tomorrow_shared} shared), "
                    f"Open memos: {len(open_memos)}"
                )
            else:
                # No appointments or memos - send appropriate message
                message_parts.append("📅 *Deine Termine:*\n")
                message_parts.append("🎉 Keine Termine für heute oder morgen!")
                message_parts.append("\nGenieße deine freie Zeit! ☀️")
                
                await self.bot.send_message(
                    chat_id=user.telegram_user_id,
                    text="\n".join(message_parts),
                    parse_mode='Markdown'
                )
                
                logger.info(f"Sent 'no appointments' reminder to user {user.telegram_user_id}")
            
        except TelegramError as e:
            logger.error(f"Telegram error sending reminder to {user.telegram_user_id}: {e}")
        except Exception as e:
            logger.error(f"Error sending reminder to {user.telegram_user_id}: {e}")
    
    async def send_test_reminder(self, user_id: int):
        """Send a test reminder to a specific user (for testing purposes)."""
        user_config = self.user_config_manager.get_user_config(user_id)
        if user_config:
            await self._send_enhanced_reminder(user_config)
            return True
        return False
    
    async def get_reminder_preview(self, user_id: int) -> Optional[str]:
        """Get a preview of what the reminder would look like for a user."""
        user_config = self.user_config_manager.get_user_config(user_id)
        if not user_config:
            return None
        
        try:
            # Create combined appointment service for this user
            combined_service = CombinedAppointmentService(user_config)
            
            # Create memo service if available
            memo_service = None
            open_memos = []
            if user_config.memo_database_id:
                try:
                    memo_service = MemoService.from_user_config(user_config)
                    # Get only open memos (not completed)
                    open_memos = await memo_service.get_recent_memos(limit=5, only_open=True)
                except Exception as e:
                    logger.warning(f"Could not load memos for preview for user {user_config.telegram_user_id}: {e}")
            
            # Get user's timezone
            tz = pytz.timezone(user_config.timezone)
            today = datetime.now(tz).date()
            tomorrow = (datetime.now(tz) + timedelta(days=1)).date()
            
            # Get appointments for today and tomorrow
            today_appointments = await combined_service.get_today_appointments()
            tomorrow_appointments = await combined_service.get_tomorrow_appointments()
            
            # Build preview message
            message_parts = ["📋 *Reminder-Vorschau:*\n"]
            
            if today_appointments or tomorrow_appointments or open_memos:
                if today_appointments:
                    message_parts.append(f"\n*📅 Heute ({today.strftime('%d.%m.%Y')})* - {len(today_appointments)} Termine")
                    
                if tomorrow_appointments:
                    message_parts.append(f"*🗓️ Morgen ({tomorrow.strftime('%d.%m.%Y')})* - {len(tomorrow_appointments)} Termine")
                
                if open_memos:
                    message_parts.append(f"*📝 Offene Memos* - {len(open_memos)} unerledigte Aufgaben")
                
                # Statistics
                total_private = sum(1 for x in today_appointments + tomorrow_appointments if not x.is_shared)
                total_shared = sum(1 for x in today_appointments + tomorrow_appointments if x.is_shared)
                
                message_parts.append(f"\n📊 *Statistik:*")
                message_parts.append(f"👤 Private: {total_private}")
                message_parts.append(f"🌐 Gemeinsam: {total_shared}")
                message_parts.append(f"📝 Offene Memos: {len(open_memos)}")
            else:
                message_parts.append("🎉 Keine Termine oder offene Memos!")
            
            return "\n".join(message_parts)
            
        except Exception as e:
            logger.error(f"Error generating reminder preview for user {user_id}: {e}")
            return f"❌ Fehler beim Erstellen der Vorschau: {str(e)}"