"""
Test factories for creating test data using factory-boy.
"""
import factory
from factory import fuzzy
from datetime import datetime, timedelta
import pytz
from src.models.appointment import Appointment
from src.models.memo import Memo
from src.models.shared_appointment import SharedAppointment
from unittest.mock import Mock, AsyncMock


class AppointmentFactory(factory.Factory):
    """Factory for creating Appointment objects."""
    
    class Meta:
        model = Appointment
    
    id = factory.Sequence(lambda n: f"appointment_{n}")
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=200)
    date = fuzzy.FuzzyDateTime(
        datetime.now(pytz.UTC),
        datetime.now(pytz.UTC) + timedelta(days=30)
    )
    location = factory.Faker('address')
    participants = factory.List([
        factory.Faker('name') for _ in range(3)
    ])
    reminder_sent = False
    created_by_user_id = factory.Faker('random_int', min=100000, max=999999)
    is_partner_relevant = factory.Faker('boolean')
    
    @factory.post_generation
    def add_tags(obj, create, extracted, **kwargs):
        if extracted:
            obj.tags = extracted
        else:
            obj.tags = ['work', 'meeting', 'important']


class MemoFactory(factory.Factory):
    """Factory for creating Memo objects."""
    
    class Meta:
        model = Memo
    
    id = factory.Sequence(lambda n: f"memo_{n}")
    title = factory.Faker('sentence', nb_words=3)
    content = factory.Faker('text', max_nb_chars=500)
    tags = factory.List([
        factory.Faker('word') for _ in range(3)
    ])
    created_at = factory.Faker('date_time_this_month', tzinfo=pytz.UTC)
    updated_at = factory.Faker('date_time_this_month', tzinfo=pytz.UTC)
    user_id = factory.Faker('random_int', min=100000, max=999999)
    is_archived = False
    priority = factory.Faker('random_element', elements=['low', 'medium', 'high'])
    
    @factory.post_generation
    def attachments(obj, create, extracted, **kwargs):
        if extracted:
            obj.attachments = extracted


class SharedAppointmentFactory(factory.Factory):
    """Factory for creating SharedAppointment objects."""
    
    class Meta:
        model = SharedAppointment
    
    appointment_id = factory.Sequence(lambda n: f"shared_appointment_{n}")
    shared_by_user_id = factory.Faker('random_int', min=100000, max=999999)
    shared_with_user_id = factory.Faker('random_int', min=100000, max=999999)
    shared_at = factory.Faker('date_time_this_week', tzinfo=pytz.UTC)
    access_level = factory.Faker('random_element', elements=['read', 'write', 'admin'])
    is_accepted = False
    notes = factory.Faker('sentence')


class TelegramUpdateFactory(factory.Factory):
    """Factory for creating mock Telegram Update objects."""
    
    class Meta:
        model = Mock
    
    @factory.lazy_attribute
    def message(self):
        message = Mock()
        message.text = factory.Faker('sentence').generate()
        message.reply_text = AsyncMock()
        message.reply_html = AsyncMock()
        message.edit_text = AsyncMock()
        message.delete = AsyncMock()
        message.message_id = factory.Faker('random_int', min=1, max=99999).generate()
        message.date = datetime.now(pytz.UTC)
        message.chat = Mock()
        message.chat.id = factory.Faker('random_int', min=100000, max=999999).generate()
        message.chat.type = 'private'
        return message
    
    @factory.lazy_attribute
    def effective_user(self):
        user = Mock()
        user.id = factory.Faker('random_int', min=100000, max=999999).generate()
        user.first_name = factory.Faker('first_name').generate()
        user.last_name = factory.Faker('last_name').generate()
        user.username = factory.Faker('user_name').generate()
        user.is_bot = False
        user.language_code = 'en'
        user.mention_html = Mock(return_value=f"<a href='tg://user?id={user.id}'>{user.first_name}</a>")
        return user
    
    @factory.lazy_attribute
    def callback_query(self):
        query = Mock()
        query.data = factory.Faker('word').generate()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_reply_markup = AsyncMock()
        query.message = self.message
        query.from_user = self.effective_user
        return query
    
    update_id = factory.Faker('random_int', min=1, max=999999)


class TelegramContextFactory(factory.Factory):
    """Factory for creating mock Telegram Context objects."""
    
    class Meta:
        model = Mock
    
    @factory.lazy_attribute
    def bot(self):
        bot = Mock()
        bot.send_message = AsyncMock()
        bot.edit_message_text = AsyncMock()
        bot.delete_message = AsyncMock()
        bot.answer_callback_query = AsyncMock()
        bot.get_me = AsyncMock(return_value=Mock(username='test_bot'))
        return bot
    
    @factory.lazy_attribute
    def user_data(self):
        return {}
    
    @factory.lazy_attribute
    def chat_data(self):
        return {}
    
    args = []
    
    @factory.lazy_attribute
    def job_queue(self):
        job_queue = Mock()
        job_queue.run_once = Mock()
        job_queue.run_repeating = Mock()
        job_queue.run_daily = Mock()
        return job_queue


class NotionPageFactory(factory.Factory):
    """Factory for creating mock Notion page objects."""
    
    class Meta:
        model = dict
    
    id = factory.Faker('uuid4')
    created_time = factory.Faker('iso8601')
    last_edited_time = factory.Faker('iso8601')
    archived = False
    
    @factory.lazy_attribute
    def properties(self):
        return {
            'Title': {
                'title': [{
                    'text': {
                        'content': factory.Faker('sentence').generate()
                    }
                }]
            },
            'Date': {
                'date': {
                    'start': factory.Faker('iso8601').generate()
                }
            },
            'Description': {
                'rich_text': [{
                    'text': {
                        'content': factory.Faker('text', max_nb_chars=200).generate()
                    }
                }]
            },
            'Location': {
                'rich_text': [{
                    'text': {
                        'content': factory.Faker('address').generate()
                    }
                }]
            }
        }


class UserConfigFactory(factory.Factory):
    """Factory for creating user configuration objects."""
    
    class Meta:
        model = dict
    
    user_id = factory.Faker('random_int', min=100000, max=999999)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    language = factory.Faker('random_element', elements=['en', 'de', 'fr', 'es'])
    timezone = factory.Faker('timezone')
    notion_database_id = factory.Faker('uuid4')
    reminder_settings = factory.Dict({
        'enabled': True,
        'advance_minutes': factory.Faker('random_element', elements=[15, 30, 60]),
        'daily_summary': True,
        'summary_time': '08:00'
    })
    permissions = factory.List(['create', 'read', 'update', 'delete'])
    is_active = True
    partner_user_id = factory.Faker('random_int', min=100000, max=999999)
    shared_database_id = factory.Faker('uuid4')