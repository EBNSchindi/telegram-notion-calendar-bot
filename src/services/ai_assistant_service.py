import logging
import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
import re

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
        
        self.max_retries = 3
        self.retry_delay = 1
        self.timeout = 30
        
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
        
        Args:
            text: The user's message containing appointment information
            user_timezone: The user's timezone
            
        Returns:
            Dictionary with extracted appointment data or None if extraction failed
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
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
    "description": "additional details if any" (null if none),
    "location": "location if mentioned" (null if none),
    "confidence": 0.0 to 1.0 (how confident you are in the extraction)
}}

CRITICAL TITLE EXTRACTION RULES:
1. Create concise, meaningful titles that capture the essence of the appointment
2. Transform activities into proper appointment titles:
   - "Mama im Krankenhaus besuchen" → "Krankenhausbesuch Mama"
   - "zum Arzt gehen" → "Arzttermin"
   - "Meeting mit Team" → "Team Meeting"
   - "Einkaufen gehen" → "Einkauf"
   - "Oma besuchen" → "Besuch bei Oma"
3. Keep titles short but descriptive (max 30 characters)
4. Use German noun compounds when appropriate
5. Include the main person/place/activity in the title

DATE/TIME EXTRACTION RULES:
1. For relative dates like "morgen" (tomorrow), "übermorgen" (day after tomorrow), "nächste Woche" (next week), calculate the actual date
2. For weekday names, find the next occurrence of that weekday
3. If no year is mentioned, assume current year
4. If time is mentioned in 12-hour format (e.g., "3pm", "15 Uhr"), convert to 24-hour
5. "heute" = today, "morgen" = tomorrow, "übermorgen" = day after tomorrow

CONTEXT EXTRACTION:
1. Extract ALL relevant context from the input
2. If location is mentioned, include it (hospital, office, restaurant, etc.)
3. If reason/purpose is mentioned, include it in description
4. If person is mentioned, include in title or description appropriately

CONFIDENCE RULES:
1. High confidence (0.8-1.0): Clear time/date + activity
2. Medium confidence (0.5-0.7): Partial information or vague timing
3. Low confidence (0.1-0.4): Unclear or conversational text
4. If confidence < 0.5, the appointment will be rejected

Examples:
- "Morgen um 15 Uhr Zahnarzttermin" → title: "Zahnarzttermin", date: tomorrow's date, time: "15:00"
- "heute 16 Uhr Mama im Krankenhaus besuchen" → title: "Krankenhausbesuch Mama", location: "Krankenhaus", date: today
- "Nächsten Montag Meeting mit dem Team im Büro" → title: "Team Meeting", location: "Büro", date: next Monday
- "Arzttermin am 25.3. um 10:30 wegen Vorsorge" → title: "Arzttermin", description: "Vorsorgeuntersuchung", date: "2025-03-25", time: "10:30"

Return ONLY the JSON object, no additional text."""

        try:
            for attempt in range(self.max_retries):
                try:
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a precise appointment extraction assistant. Always respond with valid JSON only."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.2,
                            max_tokens=500
                        ),
                        timeout=self.timeout
                    )
                    
                    content = response.choices[0].message.content.strip()
                    
                    # Try to extract JSON from the response
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        content = json_match.group()
                    
                    result = json.loads(content)
                    
                    # Validate required fields
                    if not result.get('title') or not result.get('date'):
                        logger.warning("Missing required fields in AI response")
                        return None
                    
                    # Validate confidence
                    if result.get('confidence', 0) < 0.5:
                        logger.info(f"Low confidence extraction: {result.get('confidence')}")
                        return None
                    
                    return result
                    
                except asyncio.TimeoutError:
                    logger.warning(f"OpenAI API timeout (attempt {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI response as JSON: {e}")
                    logger.debug(f"Response content: {content}")
                    return None
                    
                except Exception as e:
                    logger.error(f"OpenAI API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
            
            logger.error("All retry attempts failed")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error in extract_appointment_from_text: {e}")
            return None

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
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that improves appointment titles to be clear and descriptive in German. Keep titles concise (max 50 characters)."},
                        {"role": "user", "content": f"Improve this appointment title to be more descriptive but keep it short: '{title}'. Return only the improved title, nothing else."}
                    ],
                    temperature=0.3,
                    max_tokens=100
                ),
                timeout=10
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
            raise ValueError("Invalid date format")
        
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
        
        if appointment_data.get('location'):
            appointment_data['location'] = appointment_data['location'].strip()
            if len(appointment_data['location']) > 200:
                appointment_data['location'] = appointment_data['location'][:197] + '...'
        
        return appointment_data

    async def extract_memo_from_text(self, text: str, user_timezone: str = 'Europe/Berlin') -> Optional[Dict[str, Any]]:
        """
        Extract memo information from natural language text.
        
        Args:
            text: The user's message containing memo/task information
            user_timezone: The user's timezone
            
        Returns:
            Dictionary with extracted memo data or None if extraction failed
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return None
        
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
                            temperature=0.2,
                            max_tokens=500
                        ),
                        timeout=self.timeout
                    )
                    
                    content = response.choices[0].message.content.strip()
                    
                    # Try to extract JSON from the response
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        content = json_match.group()
                    
                    result = json.loads(content)
                    
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
            raise ValueError("Missing required 'aufgabe' field")
        
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