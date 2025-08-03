import logging
import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
import re
from src.constants import (
    AI_MODEL,
    AI_TEMPERATURE,
    AI_MAX_TOKENS,
    AI_MAX_RETRIES,
    AI_RETRY_DELAY,
    AI_TIMEOUT,
    AI_FALLBACK_CONFIDENCE,
    AI_MIN_CONFIDENCE,
    MAX_APPOINTMENT_TITLE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_LOCATION_LENGTH,
    MAX_MEMO_TITLE_LENGTH,
    MAX_MEMO_NOTES_LENGTH,
    MEMO_STATUS_NOT_STARTED
)
from src.utils.error_handler import BotError, ErrorType, ErrorSeverity

logger = logging.getLogger(__name__)


class AIAssistantService:
    """Service for processing natural language appointment inputs using OpenAI."""
    
    def __init__(self):
        """Initialize the AI Assistant Service."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
            self.client = None
        else:
            try:
                self.client = AsyncOpenAI(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        
        self.max_retries = AI_MAX_RETRIES
        self.retry_delay = AI_RETRY_DELAY
        self.timeout = AI_TIMEOUT
        
        # German month names for parsing
        self.german_months = {
            'januar': 1, 'februar': 2, 'märz': 3, 'april': 4,
            'mai': 5, 'juni': 6, 'juli': 7, 'august': 8,
            'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12
        }
        
        # German weekday names
        self.german_weekdays = {
            'montag': 0, 'dienstag': 1, 'mittwoch': 2, 'donnerstag': 3,
            'freitag': 4, 'samstag': 5, 'sonntag': 6
        }

    async def extract_appointment_from_text(self, text: str, user_timezone: str = 'Europe/Berlin') -> Optional[Dict[str, Any]]:
        """
        Extract appointment information from natural language text.
        
        Uses OpenAI to parse natural language and extract structured appointment data.
        Now includes duration extraction from various formats.
        
        Args:
            text: The user's message containing appointment information
            user_timezone: The user's timezone for relative date calculations
            
        Returns:
            Dictionary with extracted appointment data or None if extraction failed
            
        Return format:
            {
                "title": str,           # Appointment title
                "date": "YYYY-MM-DD",   # Date in ISO format
                "time": "HH:MM",        # Time in 24-hour format (optional)
                "duration_minutes": int, # Duration in minutes (default: 60)
                "description": str,      # Additional details (optional)
                "location": str,         # Location (optional)
                "confidence": float      # AI confidence score (0.0-1.0)
            }
            
        Supported duration formats:
            - "30 min", "1h", "2 Stunden", "halbe Stunde"
            - "1.5h", "1,5h", "anderthalb Stunden"
            - "Viertelstunde" (15 min)
        """
        if not self.client:
            logger.warning("OpenAI client not initialized - AI extraction unavailable")
            return None
        
        # Get current date/time in user's timezone
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(user_timezone))
        current_date = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M')
        current_weekday = now.strftime('%A')
        
        prompt = f"""You are an appointment extraction assistant. Extract appointment information from the following German or English text.

Current date: {current_date} ({current_weekday})
Current time: {current_time}
User timezone: {user_timezone}

Text: "{text}"

Extract and return a JSON object with the following structure:
{{
    "title": "appointment title",
    "date": "YYYY-MM-DD",
    "time": "HH:MM" (24-hour format, null if no time mentioned),
    "duration_minutes": number (default 60 if not specified),
    "description": "additional details if any" (null if none),
    "location": "location if mentioned" (null if none),
    "confidence": 0.0 to 1.0 (how confident you are in the extraction)
}}

CRITICAL TITLE EXTRACTION RULES:
1. Create concise, meaningful titles that capture the essence of the appointment
2. ALWAYS include WHO the appointment is with in the title if mentioned:
   - "Feierabendbier mit Peter" → "Feierabendbier mit Peter" (keep "mit Peter"!)
   - "Mittagessen mit Anna" → "Mittagessen mit Anna"
   - "Meeting mit Team" → "Team Meeting"
   - "Kaffee mit Sarah" → "Kaffee mit Sarah"
3. Transform activities but PRESERVE person/context:
   - "Mama im Krankenhaus besuchen" → "Krankenhausbesuch Mama"
   - "zum Arzt gehen" → "Arzttermin"
   - "Einkaufen gehen" → "Einkauf"
   - "Oma besuchen" → "Besuch bei Oma"
4. Keep titles descriptive but concise (max 50 characters)
5. Use German noun compounds when appropriate
6. NEVER remove person names or "mit [Person]" from the title

DATE/TIME EXTRACTION RULES:
1. For relative dates like "morgen" (tomorrow), "übermorgen" (day after tomorrow), "nächste Woche" (next week), calculate the actual date
2. For weekday names, find the next occurrence of that weekday
3. If no year is mentioned, assume current year
4. If time is mentioned in 12-hour format (e.g., "3pm", "15 Uhr"), convert to 24-hour
5. "heute" = today, "morgen" = tomorrow, "übermorgen" = day after tomorrow

DURATION EXTRACTION RULES:
1. Default is 60 minutes if no duration is mentioned
2. Convert all durations to minutes:
   - "30 min" → 30
   - "1h" or "1 Stunde" → 60
   - "1.5h" or "1,5h" or "anderthalb Stunden" → 90
   - "2h" or "2 Stunden" → 120
   - "halbe Stunde" → 30
   - "Viertelstunde" → 15
3. Common patterns to recognize:
   - German: "[X] Minuten", "[X] min", "[X] Stunde(n)", "[X] h", "halbe Stunde", "anderthalb Stunden"
   - English: "[X] minutes", "[X] min", "[X] hour(s)", "[X] h", "half hour", "half an hour"
4. Duration can appear anywhere in the text

CONTEXT EXTRACTION:
1. Extract ALL relevant context from the input - NOTHING should be lost!
2. If location is mentioned, include it in the location field
3. If a person is mentioned:
   - Include them in the title (e.g., "Lunch mit Peter", "Meeting mit Sarah")
   - Also add details to description if needed
4. If reason/purpose is mentioned, include it in description
5. Put any additional context that doesn't fit elsewhere into the description
6. IMPORTANT: The description field should capture ALL context not in the title/location

CONFIDENCE RULES:
1. High confidence (0.8-1.0): Clear time/date + activity
2. Medium confidence (0.5-0.7): Partial information or vague timing
3. Low confidence (0.1-0.4): Unclear or conversational text
4. If confidence < 0.5, the appointment will be rejected

Examples:
- "Morgen um 15 Uhr Zahnarzttermin" → title: "Zahnarzttermin", date: tomorrow's date, time: "15:00", duration_minutes: 60
- "heute 16 Uhr Mama im Krankenhaus besuchen für 30 min" → title: "Krankenhausbesuch Mama", location: "Krankenhaus", date: today, duration_minutes: 30
- "Nächsten Montag Meeting mit dem Team im Büro für 2 Stunden" → title: "Team Meeting", location: "Büro", date: next Monday, duration_minutes: 120
- "Arzttermin am 25.3. um 10:30 wegen Vorsorge (halbe Stunde)" → title: "Arzttermin", description: "Vorsorgeuntersuchung", date: "2025-03-25", time: "10:30", duration_minutes: 30
- "Feierabendbier mit Peter" → title: "Feierabendbier mit Peter", description: "Treffen mit Peter", confidence: 0.85, duration_minutes: 60
- "Kaffee trinken mit Sarah im Café Central für 1.5h" → title: "Kaffee mit Sarah", location: "Café Central", confidence: 0.9, duration_minutes: 90
- "Abendessen mit den Eltern bei Mama (2h)" → title: "Abendessen mit Eltern", location: "bei Mama", confidence: 0.9, duration_minutes: 120

IMPORTANT: Return ONLY valid JSON, no additional text, no markdown code blocks, no explanations."""

        try:
            for attempt in range(self.max_retries):
                try:
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model=AI_MODEL,
                            messages=[
                                {"role": "system", "content": "You are a precise appointment extraction assistant. You MUST respond with ONLY valid JSON, no additional text, no markdown formatting, no code blocks."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=AI_TEMPERATURE,
                            max_tokens=AI_MAX_TOKENS
                        ),
                        timeout=self.timeout
                    )
                    
                    content = response.choices[0].message.content.strip()
                    
                    # Try to extract JSON from the response with improved pattern
                    # This handles the "Extra data: line X column Y" error by:
                    # 1. First trying to find JSON in a code block
                    # 2. Using non-greedy regex to match nested JSON objects
                    # 3. Cleaning up any trailing content after the last closing brace
                    
                    # First try to find JSON in code block
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if not json_match:
                        # Try without code block - use non-greedy matching for nested objects
                        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', content, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(1) if '```' in content else json_match.group(0)
                        # Clean up any trailing content that causes "Extra data" errors
                        json_str = json_str.strip()
                        # Remove any content after the last closing brace
                        last_brace = json_str.rfind('}')
                        if last_brace != -1:
                            json_str = json_str[:last_brace + 1]
                        
                        result = json.loads(json_str)
                    else:
                        raise json.JSONDecodeError("No valid JSON found in response", content, 0)
                    
                    # Validate required fields
                    if not result.get('title') or not result.get('date'):
                        logger.warning("Missing required fields in AI response")
                        return None
                    
                    # Validate confidence
                    if result.get('confidence', 0) < AI_MIN_CONFIDENCE:
                        logger.info(f"Low confidence extraction: {result.get('confidence')}")
                        return None
                    
                    # Set default duration if not provided
                    # This ensures backward compatibility and handles missing duration
                    if 'duration_minutes' not in result or result['duration_minutes'] is None:
                        result['duration_minutes'] = 60
                    
                    # Ensure duration is an integer (AI might return float or string)
                    try:
                        result['duration_minutes'] = int(result['duration_minutes'])
                    except (ValueError, TypeError):
                        result['duration_minutes'] = 60
                    
                    return result
                    
                except asyncio.TimeoutError:
                    logger.warning(f"OpenAI API timeout (attempt {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI response as JSON: {e}")
                    logger.debug(f"Response content: {content}")
                    raise BotError(
                        f"Failed to parse AI response: {str(e)}",
                        ErrorType.AI_SERVICE,
                        ErrorSeverity.MEDIUM,
                        user_message="🤖 KI-Antwort konnte nicht verarbeitet werden. Bitte versuche es erneut."
                    )
                    
                except Exception as e:
                    logger.error(f"OpenAI API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
            
            logger.error("All retry attempts failed")
            return None
            
        except BotError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in extract_appointment_from_text: {e}")
            raise BotError(
                f"Unexpected error during appointment extraction: {str(e)}",
                ErrorType.AI_SERVICE,
                ErrorSeverity.MEDIUM,
                user_message="🤖 Unerwarteter Fehler bei der Terminextraktion. Bitte versuche es erneut."
            )

    async def improve_appointment_title(self, title: str) -> str:
        """
        Improve appointment title using AI to make it more descriptive and clear.
        
        Args:
            title: Original appointment title
            
        Returns:
            Improved title or original if improvement fails
        """
        if not self.client:
            return title
        
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=AI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that improves appointment titles to be clear and descriptive in German. Keep titles concise (max 50 characters)."},
                        {"role": "user", "content": f"Improve this appointment title to be more descriptive but keep it short: '{title}'. Return only the improved title, nothing else."}
                    ],
                    temperature=AI_TEMPERATURE,
                    max_tokens=100
                ),
                timeout=AI_TIMEOUT
            )
            
            improved = response.choices[0].message.content.strip()
            # Remove quotes if present
            improved = improved.strip('"\'')
            
            # Ensure it's not too long
            if len(improved) > 50:
                return title
                
            return improved
            
        except Exception as e:
            logger.warning(f"Failed to improve title: {e}")
            return title

    async def validate_appointment_data(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean appointment data extracted by AI.
        
        Args:
            appointment_data: Raw appointment data from AI
            
        Returns:
            Validated and cleaned appointment data
        """
        # Ensure required fields
        if not appointment_data.get('title'):
            appointment_data['title'] = 'Neuer Termin'
        
        # Validate date format
        try:
            date_obj = datetime.strptime(appointment_data['date'], '%Y-%m-%d')
            appointment_data['date'] = date_obj.strftime('%Y-%m-%d')
        except (ValueError, KeyError):
            logger.error(f"Invalid date format: {appointment_data.get('date')}")
            raise BotError(
                f"Invalid date format: {appointment_data.get('date')}",
                ErrorType.VALIDATION,
                ErrorSeverity.LOW,
                user_message="❌ Ungültiges Datumsformat. Bitte versuche es erneut."
            )
        
        # Validate time format if present
        if appointment_data.get('time'):
            try:
                time_parts = appointment_data['time'].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    appointment_data['time'] = f"{hour:02d}:{minute:02d}"
                else:
                    appointment_data['time'] = None
            except (ValueError, IndexError):
                appointment_data['time'] = None
        
        # Clean description and location
        if appointment_data.get('description'):
            appointment_data['description'] = appointment_data['description'].strip()
            if len(appointment_data['description']) > 500:
                appointment_data['description'] = appointment_data['description'][:497] + '...'
        else:
            # If no description but title is long, consider adding context to description
            if len(appointment_data.get('title', '')) > 30 and ' mit ' in appointment_data.get('title', ''):
                # Extract context after "mit" for description if not already there
                title_parts = appointment_data['title'].split(' mit ', 1)
                if len(title_parts) > 1 and not appointment_data.get('description'):
                    appointment_data['description'] = f"Treffen mit {title_parts[1]}"
        
        if appointment_data.get('location'):
            appointment_data['location'] = appointment_data['location'].strip()
            if len(appointment_data['location']) > 200:
                appointment_data['location'] = appointment_data['location'][:197] + '...'
        
        # Validate and clean duration_minutes
        # Ensures duration is within reasonable bounds and properly formatted
        if appointment_data.get('duration_minutes') is not None:
            try:
                duration = int(appointment_data['duration_minutes'])
                # Ensure duration is reasonable (between 5 minutes and 24 hours)
                if duration < 5:
                    duration = 60  # Default to 1 hour if too small
                elif duration > 1440:  # More than 24 hours
                    duration = 1440  # Cap at 24 hours
                appointment_data['duration_minutes'] = duration
            except (ValueError, TypeError):
                # If conversion fails, default to 60 minutes
                appointment_data['duration_minutes'] = 60
        else:
            # No duration specified, use default
            appointment_data['duration_minutes'] = 60
        
        return appointment_data

    async def extract_memo_from_text(self, text: str, user_timezone: str = 'Europe/Berlin') -> Optional[Dict[str, Any]]:
        """
        Extract memo information from natural language text.
        
        Uses OpenAI to parse natural language and extract structured memo/task data.
        Falls back to basic extraction if AI service is unavailable.
        
        Args:
            text: The user's message containing memo/task information
            user_timezone: The user's timezone for relative date calculations
            
        Returns:
            Dictionary with extracted memo data or None if extraction failed
            
        Return format:
            {
                "aufgabe": str,           # Task/memo title (required)
                "notizen": str,           # Additional notes (optional)
                "faelligkeitsdatum": str, # Due date in YYYY-MM-DD format (optional)
                "bereich": str,           # Category/area (optional)
                "projekt": str,           # Project name (optional)
                "confidence": float       # AI confidence score (0.0-1.0)
            }
        """
        if not self.client:
            logger.warning("OpenAI client not initialized - falling back to basic extraction")
            return self._basic_memo_extraction(text)
        
        # Get current date/time in user's timezone
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(user_timezone))
        current_date = now.strftime('%Y-%m-%d')
        current_weekday = now.strftime('%A')
        
        prompt = f"""You are a memo/task extraction assistant. Extract memo information from the following German or English text.

Current date: {current_date} ({current_weekday})
User timezone: {user_timezone}

Text: "{text}"

Extract and return a JSON object with the following structure:
{{
    "aufgabe": "task/memo title (REQUIRED)",
    "notizen": "additional notes/details" (null if none),
    "faelligkeitsdatum": "YYYY-MM-DD" (null if no due date mentioned),
    "bereich": "category/area" (null if none),
    "projekt": "project name" (null if none),
    "confidence": 0.0 to 1.0 (how confident you are in the extraction)
}}

CRITICAL TASK EXTRACTION RULES:
1. The "aufgabe" field is REQUIRED and must capture the main task/memo
2. Transform activities into proper task titles:
   - "Präsentation vorbereiten bis Freitag" → aufgabe: "Präsentation vorbereiten", faelligkeitsdatum: Friday's date
   - "Einkaufsliste erstellen - Milch, Brot, Butter" → aufgabe: "Einkaufsliste erstellen", notizen: "Milch, Brot, Butter"
   - "Call back John about the project" → aufgabe: "John zurückrufen", projekt: "project"
   - "Remember to book dentist appointment" → aufgabe: "Zahnarzttermin buchen"
3. Keep task titles concise but descriptive (max 50 characters)
4. Use German when possible, but keep English if more natural

DATE EXTRACTION RULES:
1. Only extract dates that are clearly due dates or deadlines
2. For relative dates like "bis morgen", "bis Freitag", calculate the actual date
3. For weekday names, find the next occurrence of that weekday
4. If no year mentioned, assume current year
5. "heute" = today, "morgen" = tomorrow, "übermorgen" = day after tomorrow

CONTEXT EXTRACTION:
1. Extract additional details into "notizen" field
2. If a project is mentioned, extract to "projekt" field
3. If a category/area is mentioned (work, personal, shopping, etc.), extract to "bereich" field
4. Don't duplicate information between fields

CONFIDENCE RULES:
1. High confidence (0.8-1.0): Clear task with actionable content
2. Medium confidence (0.5-0.7): Somewhat clear task but vague details
3. Low confidence (0.1-0.4): Unclear or conversational text
4. If confidence < 0.5, the memo will be rejected

Examples:
- "Präsentation vorbereiten bis Freitag" → aufgabe: "Präsentation vorbereiten", faelligkeitsdatum: next Friday
- "Einkaufsliste: Milch, Brot, Butter nicht vergessen" → aufgabe: "Einkaufsliste erstellen", notizen: "Milch, Brot, Butter"
- "Website Projekt: Feedback von Client einholen" → aufgabe: "Client Feedback einholen", projekt: "Website"
- "Arbeitsbereich: Meeting notes zusammenfassen" → aufgabe: "Meeting Notes zusammenfassen", bereich: "Arbeit"

Return ONLY the JSON object, no additional text."""

        try:
            for attempt in range(self.max_retries):
                try:
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a precise memo/task extraction assistant. Always respond with valid JSON only."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=AI_TEMPERATURE,
                            max_tokens=AI_MAX_TOKENS
                        ),
                        timeout=self.timeout
                    )
                    
                    content = response.choices[0].message.content.strip()
                    
                    # Try to extract JSON from the response with improved pattern
                    # This handles the "Extra data: line X column Y" error by:
                    # 1. First trying to find JSON in a code block
                    # 2. Using non-greedy regex to match nested JSON objects
                    # 3. Cleaning up any trailing content after the last closing brace
                    
                    # First try to find JSON in code block
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if not json_match:
                        # Try without code block - use non-greedy matching for nested objects
                        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', content, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(1) if '```' in content else json_match.group(0)
                        # Clean up any trailing content that causes "Extra data" errors
                        json_str = json_str.strip()
                        # Remove any content after the last closing brace
                        last_brace = json_str.rfind('}')
                        if last_brace != -1:
                            json_str = json_str[:last_brace + 1]
                        
                        result = json.loads(json_str)
                    else:
                        raise json.JSONDecodeError("No valid JSON found in response", content, 0)
                    
                    # Validate required fields
                    if not result.get('aufgabe'):
                        logger.warning("Missing required 'aufgabe' field in AI response")
                        return None
                    
                    # Validate confidence
                    if result.get('confidence', 0) < 0.5:
                        logger.info(f"Low confidence memo extraction: {result.get('confidence')}")
                        return None
                    
                    return result
                    
                except asyncio.TimeoutError:
                    logger.warning(f"OpenAI API timeout (attempt {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI memo response as JSON: {e}")
                    logger.debug(f"Response content: {content}")
                    return None
                    
                except Exception as e:
                    logger.error(f"OpenAI API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
            
            logger.error("All retry attempts failed for memo extraction")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error in extract_memo_from_text: {e}")
            return None

    async def validate_memo_data(self, memo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean memo data extracted by AI.
        
        Args:
            memo_data: Raw memo data from AI
            
        Returns:
            Validated and cleaned memo data
        """
        # Ensure required field
        if not memo_data.get('aufgabe'):
            raise BotError(
                "Missing required 'aufgabe' field in memo data",
                ErrorType.VALIDATION,
                ErrorSeverity.LOW,
                user_message="❌ Aufgabe konnte nicht erkannt werden. Bitte formuliere deine Aufgabe klarer."
            )
        
        # Clean and validate aufgabe
        memo_data['aufgabe'] = memo_data['aufgabe'].strip()
        if len(memo_data['aufgabe']) > 200:
            memo_data['aufgabe'] = memo_data['aufgabe'][:197] + '...'
        
        # Validate due date format if present
        if memo_data.get('faelligkeitsdatum'):
            try:
                date_obj = datetime.strptime(memo_data['faelligkeitsdatum'], '%Y-%m-%d')
                memo_data['faelligkeitsdatum'] = date_obj.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                logger.warning(f"Invalid due date format: {memo_data.get('faelligkeitsdatum')}")
                memo_data['faelligkeitsdatum'] = None
        
        # Clean optional fields
        for field in ['notizen', 'bereich', 'projekt']:
            if memo_data.get(field):
                memo_data[field] = memo_data[field].strip()
                max_lengths = {'notizen': 2000, 'bereich': 100, 'projekt': 100}
                max_len = max_lengths.get(field, 100)
                if len(memo_data[field]) > max_len:
                    memo_data[field] = memo_data[field][:max_len-3] + '...'
            else:
                memo_data[field] = None
        
        return memo_data

    def is_available(self) -> bool:
        """Check if the AI service is available."""
        return self.client is not None
    
    def _basic_memo_extraction(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Basic memo extraction without AI for fallback.
        
        Args:
            text: The user's message
            
        Returns:
            Dictionary with basic memo data or None if extraction failed
        """
        try:
            # Clean up the text
            text = text.strip()
            if not text:
                return None
            
            # Basic extraction - use the entire text as task
            memo_data = {
                "aufgabe": text[:200],  # Limit to 200 chars
                "notizen": None,
                "faelligkeitsdatum": None,
                "bereich": None,
                "projekt": None,
                "confidence": AI_FALLBACK_CONFIDENCE  # Medium confidence for basic extraction
            }
            
            # Try to detect due dates (basic patterns)
            date_patterns = [
                (r'\bbis\s+(morgen|heute|übermorgen)\b', 'relative'),
                (r'\bbis\s+(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}|\d{2}))?\b', 'date'),
                (r'\bfällig\s+am\s+(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}|\d{2}))?\b', 'date')
            ]
            
            import re
            from datetime import datetime, timedelta
            
            for pattern, pattern_type in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if pattern_type == 'relative':
                        relative_date = match.group(1).lower()
                        today = datetime.now().date()
                        if relative_date == 'heute':
                            memo_data['faelligkeitsdatum'] = today.strftime('%Y-%m-%d')
                        elif relative_date == 'morgen':
                            memo_data['faelligkeitsdatum'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                        elif relative_date == 'übermorgen':
                            memo_data['faelligkeitsdatum'] = (today + timedelta(days=2)).strftime('%Y-%m-%d')
                    elif pattern_type == 'date':
                        day = int(match.group(1))
                        month = int(match.group(2))
                        year_match = match.group(3)
                        
                        if year_match:
                            year = int(year_match) if len(year_match) == 4 else 2000 + int(year_match)
                        else:
                            year = datetime.now().year
                        
                        try:
                            date_obj = datetime(year, month, day)
                            # If date is in the past, assume next year
                            if date_obj.date() < datetime.now().date():
                                date_obj = date_obj.replace(year=year + 1)
                            memo_data['faelligkeitsdatum'] = date_obj.strftime('%Y-%m-%d')
                        except ValueError:
                            pass
                    break
            
            # Try to detect project or area keywords
            project_keywords = ['projekt', 'project', 'arbeit', 'work', 'privat', 'personal']
            for keyword in project_keywords:
                if keyword in text.lower():
                    memo_data['bereich'] = keyword.capitalize()
                    break
            
            logger.info(f"Basic memo extraction result: {memo_data}")
            return memo_data
            
        except Exception as e:
            logger.error(f"Error in basic memo extraction: {e}")
            return None