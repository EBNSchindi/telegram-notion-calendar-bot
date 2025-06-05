# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-05

### Added
- Initial release of Telegram-Notion Calendar Bot
- Telegram bot with python-telegram-bot library
- Notion API integration for calendar management
- Command handlers for appointment management:
  - `/start` - Initialize bot and check connection status
  - `/help` - Display help and examples
  - `/add` - Create new appointments
  - `/list` - Show upcoming appointments
  - `/today` - Display today's appointments
- Natural language date parsing (German):
  - Relative dates: "heute", "morgen"
  - Absolute dates: DD.MM.YYYY format
- Support for appointment fields:
  - Name (Title)
  - Date and time
  - Description (optional)
  - Location (optional)
  - Tags (comma-separated)
- Timezone support (Europe/Berlin)
- Comprehensive test suite with pytest
- Docker support for deployment
- Detailed logging to file and console
- Configuration via environment variables
- Development tools:
  - Makefile for common tasks
  - Test script for Notion connection
  - Black/isort for code formatting
  - Type hints throughout codebase

### Technical Details
- Python 3.11 base
- Asynchronous architecture
- Pydantic for data validation
- TDD approach with >80% test coverage
- GitHub Actions ready structure

### Security
- No hardcoded credentials
- Environment variable configuration
- Docker non-root user execution
- Input validation on all user data

## [Unreleased]

### Planned Features
- Delete appointment command (`/delete`)
- Edit appointment command (`/edit`)
- Appointment reminders/notifications
- Recurring appointments support
- Multi-user/multi-database support
- English language support
- Calendar view/export features
- Google Calendar synchronization