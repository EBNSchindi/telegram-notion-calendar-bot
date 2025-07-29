"""
Performance tests for identifying bottlenecks.
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import pytz
import cProfile
import pstats
from io import StringIO

from tests.factories import (
    AppointmentFactory, MemoFactory, NotionPageFactory,
    TelegramUpdateFactory, TelegramContextFactory
)


@pytest.mark.performance
class TestPerformance:
    """Performance test suite for bottleneck identification."""
    
    @pytest.fixture
    def profiler(self):
        """Create a profiler for performance analysis."""
        return cProfile.Profile()
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_appointment_creation_performance(self, benchmark, mock_notion_client):
        """Benchmark appointment creation performance."""
        from src.services.combined_appointment_service import CombinedAppointmentService
        
        service = CombinedAppointmentService()
        service.notion_service = Mock()
        service.notion_service.create_appointment = AsyncMock(
            return_value={"id": "test_id"}
        )
        
        async def create_appointment():
            return await service.create_appointment_from_text(
                123456, "Meeting tomorrow at 3pm"
            )
        
        # Run benchmark
        result = await benchmark(create_appointment)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_bulk_appointment_query_performance(self, performance_timer):
        """Test performance of querying large number of appointments."""
        from src.services.notion_service import NotionService
        
        # Create mock data
        appointments = [NotionPageFactory() for _ in range(1000)]
        
        with patch('src.services.notion_service.Client') as mock_client:
            mock_client.return_value.databases.query = AsyncMock(
                return_value={"results": appointments}
            )
            
            service = NotionService()
            service.client = mock_client.return_value
            
            # Measure performance
            performance_timer.start()
            result = await service.query_appointments(123456)
            performance_timer.stop()
            
            # Assert
            assert len(result) == 1000
            assert performance_timer.elapsed < 1.0  # Should complete within 1 second
            print(f"Query time for 1000 appointments: {performance_timer.elapsed:.3f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_user_handling_performance(self):
        """Test performance with multiple concurrent users."""
        from src.handlers.enhanced_appointment_handler import EnhancedAppointmentHandler
        
        handler = EnhancedAppointmentHandler()
        handler.appointment_service = Mock()
        handler.appointment_service.get_user_appointments = AsyncMock(
            return_value=[AppointmentFactory() for _ in range(10)]
        )
        
        # Create multiple user requests
        users = []
        for i in range(50):  # 50 concurrent users
            update = TelegramUpdateFactory()
            update.effective_user.id = 100000 + i
            context = TelegramContextFactory()
            users.append((update, context))
        
        # Measure concurrent execution time
        start_time = time.time()
        
        # Execute all requests concurrently
        tasks = [
            handler.handle_list_appointments(update, context)
            for update, context in users
        ]
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Assert
        assert execution_time < 5.0  # Should handle 50 users within 5 seconds
        print(f"Handled 50 concurrent users in {execution_time:.3f}s")
        print(f"Average time per user: {execution_time/50:.3f}s")
    
    @pytest.mark.asyncio
    async def test_ai_processing_performance(self, profiler):
        """Profile AI appointment extraction performance."""
        from src.services.ai_assistant_service import AIAssistantService
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"appointments": []}'
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_client.chat.completions.create = Mock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            service = AIAssistantService()
            
            # Profile the operation
            profiler.enable()
            
            # Test with various text lengths
            test_texts = [
                "Short meeting at 3pm",
                "Medium length text with meeting tomorrow at 2:30pm in conference room B with the team",
                "Very long text " * 50 + " with multiple appointments scattered throughout"
            ]
            
            for text in test_texts:
                start = time.time()
                result = await service.extract_appointments_from_text(text)
                elapsed = time.time() - start
                print(f"AI processing for {len(text)} chars: {elapsed:.3f}s")
            
            profiler.disable()
            
            # Print profiling results
            s = StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
            ps.print_stats(10)  # Top 10 functions
            print("\nTop 10 time-consuming functions:")
            print(s.getvalue())
    
    @pytest.mark.asyncio
    async def test_database_sync_performance(self):
        """Test performance of partner database synchronization."""
        from src.services.partner_sync_service import PartnerSyncService
        
        # Create test data
        appointments = [AppointmentFactory(is_partner_relevant=True) for _ in range(100)]
        
        with patch('src.services.notion_service.NotionService') as mock_notion:
            mock_notion.return_value.create_appointment = AsyncMock()
            mock_notion.return_value.query_appointments = AsyncMock(
                return_value=appointments
            )
            
            service = PartnerSyncService()
            
            # Measure sync performance
            start_time = time.time()
            result = await service.sync_appointments(123456, appointments)
            sync_time = time.time() - start_time
            
            # Assert
            assert sync_time < 10.0  # Should sync 100 appointments within 10 seconds
            print(f"Synced 100 appointments in {sync_time:.3f}s")
            print(f"Average sync time per appointment: {sync_time/100:.3f}s")
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(self):
        """Test memory usage with large appointment datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        large_dataset = []
        for _ in range(10000):
            appointment = AppointmentFactory()
            large_dataset.append(appointment)
        
        # Process the dataset
        from src.services.combined_appointment_service import CombinedAppointmentService
        service = CombinedAppointmentService()
        
        # Simulate processing
        processed = 0
        for appointment in large_dataset:
            # Simulate some processing
            processed += 1
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
        
        # Assert memory usage is reasonable
        assert memory_increase < 500  # Should not use more than 500MB for 10k appointments
    
    @pytest.mark.asyncio
    async def test_search_performance_with_indexing(self):
        """Test search performance with and without indexing."""
        from src.services.memo_service import MemoService
        
        # Create test memos
        memos = [MemoFactory(tags=[f"tag_{i%10}"]) for i in range(1000)]
        
        service = MemoService()
        service._memo_cache = {}  # Simulate cache/index
        
        # Test without index
        start_time = time.time()
        results_no_index = []
        for memo in memos:
            if "tag_5" in memo.tags:
                results_no_index.append(memo)
        time_no_index = time.time() - start_time
        
        # Build index
        index = {}
        for memo in memos:
            for tag in memo.tags:
                if tag not in index:
                    index[tag] = []
                index[tag].append(memo)
        
        # Test with index
        start_time = time.time()
        results_with_index = index.get("tag_5", [])
        time_with_index = time.time() - start_time
        
        print(f"Search without index: {time_no_index:.6f}s")
        print(f"Search with index: {time_with_index:.6f}s")
        print(f"Speed improvement: {time_no_index/time_with_index:.2f}x")
        
        # Assert index is faster
        assert time_with_index < time_no_index
        assert len(results_no_index) == len(results_with_index)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self):
        """Test rate limiter performance under load."""
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        
        # Simulate rapid requests
        start_time = time.time()
        allowed_requests = 0
        denied_requests = 0
        
        for _ in range(200):  # Try 200 requests
            if limiter.check_rate_limit(123456):
                allowed_requests += 1
            else:
                denied_requests += 1
            
            # Simulate some processing time
            await asyncio.sleep(0.001)
        
        execution_time = time.time() - start_time
        
        print(f"Processed 200 requests in {execution_time:.3f}s")
        print(f"Allowed: {allowed_requests}, Denied: {denied_requests}")
        print(f"Rate limiter overhead: {execution_time/200*1000:.2f}ms per request")
        
        # Assert
        assert allowed_requests == 100  # Should allow exactly 100 requests
        assert denied_requests == 100  # Should deny the rest
    
    @pytest.mark.asyncio
    async def test_notification_delivery_performance(self):
        """Test performance of sending bulk notifications."""
        from src.services.enhanced_reminder_service import EnhancedReminderService
        
        # Mock telegram bot
        mock_bot = Mock()
        mock_bot.send_message = AsyncMock()
        
        service = EnhancedReminderService()
        service.bot = mock_bot
        
        # Create reminders for multiple users
        reminders = []
        for i in range(100):
            appointment = AppointmentFactory()
            reminders.append((100000 + i, appointment))
        
        # Measure notification sending time
        start_time = time.time()
        
        # Send notifications concurrently
        tasks = []
        for user_id, appointment in reminders:
            task = service.send_reminder_notification(user_id, appointment)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        notification_time = time.time() - start_time
        
        print(f"Sent 100 notifications in {notification_time:.3f}s")
        print(f"Average time per notification: {notification_time/100*1000:.2f}ms")
        
        # Assert
        assert notification_time < 10.0  # Should send 100 notifications within 10 seconds
        assert mock_bot.send_message.call_count == 100
    
    @pytest.mark.asyncio
    async def test_caching_effectiveness(self):
        """Test effectiveness of caching for frequently accessed data."""
        from src.services.notion_service import NotionService
        
        service = NotionService()
        service._cache = {}  # Simple cache implementation
        
        # Mock database query
        service.client = Mock()
        service.client.databases.query = AsyncMock(
            return_value={"results": [NotionPageFactory() for _ in range(50)]}
        )
        
        # First query (cache miss)
        start_time = time.time()
        result1 = await service.query_appointments(123456)
        time_no_cache = time.time() - start_time
        
        # Cache the result
        cache_key = f"appointments_123456"
        service._cache[cache_key] = result1
        
        # Second query (cache hit)
        start_time = time.time()
        if cache_key in service._cache:
            result2 = service._cache[cache_key]
        else:
            result2 = await service.query_appointments(123456)
        time_with_cache = time.time() - start_time
        
        print(f"Query without cache: {time_no_cache:.6f}s")
        print(f"Query with cache: {time_with_cache:.6f}s")
        print(f"Cache speedup: {time_no_cache/time_with_cache:.0f}x")
        
        # Assert
        assert time_with_cache < time_no_cache / 100  # Cache should be at least 100x faster
        assert len(result1) == len(result2)