#!/usr/bin/env python3
"""
Unified cleanup utility for duplicate appointments.

This module provides configurable duplicate cleanup functionality with:
- Smart duplicate detection using DuplicateChecker
- Configurable retention strategies (keep oldest/newest)
- Dry-run mode for safe testing
- Comprehensive logging and error handling
- Verification and prevention testing
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Literal, Tuple
from enum import Enum

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from config.user_config import UserConfigManager
from src.services.notion_service import NotionService
from src.models.appointment import Appointment
from src.utils.duplicate_checker import DuplicateChecker
from notion_client import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RetentionStrategy(Enum):
    """Strategy for which duplicate to keep."""
    OLDEST = "oldest"  # Keep the oldest (first created)
    NEWEST = "newest"  # Keep the newest (last created)
    MOST_COMPLETE = "most_complete"  # Keep the one with most fields filled


class DuplicateCleanupConfig:
    """Configuration for duplicate cleanup operations."""
    
    def __init__(
        self,
        dry_run: bool = True,
        retention_strategy: RetentionStrategy = RetentionStrategy.OLDEST,
        batch_size: int = 50,
        auto_confirm: bool = False,
        verbose: bool = True,
        max_appointments: int = 1000
    ):
        """
        Initialize cleanup configuration.
        
        Args:
            dry_run: If True, only simulate cleanup without archiving
            retention_strategy: Which duplicate to keep
            batch_size: Number of appointments to process at once
            auto_confirm: If True, skip confirmation prompts
            verbose: If True, print detailed progress
            max_appointments: Maximum appointments to fetch
        """
        self.dry_run = dry_run
        self.retention_strategy = retention_strategy
        self.batch_size = batch_size
        self.auto_confirm = auto_confirm
        self.verbose = verbose
        self.max_appointments = max_appointments


class DuplicateCleanupUtility:
    """Main utility class for cleaning up duplicate appointments."""
    
    def __init__(self, config: DuplicateCleanupConfig):
        """
        Initialize the cleanup utility.
        
        Args:
            config: Configuration for cleanup operations
        """
        self.config = config
        self.config_manager = UserConfigManager()
        self._stats = {
            'total_appointments': 0,
            'duplicate_groups': 0,
            'duplicates_found': 0,
            'duplicates_archived': 0,
            'errors': 0
        }
    
    async def analyze_duplicates(
        self, 
        notion_service: NotionService
    ) -> Dict[str, List[Appointment]]:
        """
        Analyze database for duplicate appointments.
        
        Args:
            notion_service: Notion service instance
            
        Returns:
            Dictionary mapping appointment keys to lists of duplicate appointments
        """
        if self.config.verbose:
            print("\n📊 Loading appointments from database...")
        
        all_appointments = await notion_service.get_appointments(
            limit=self.config.max_appointments
        )
        self._stats['total_appointments'] = len(all_appointments)
        
        if self.config.verbose:
            print(f"Total appointments found: {len(all_appointments)}")
        
        # Use DuplicateChecker to find duplicates
        duplicates = DuplicateChecker.check_for_duplicates(all_appointments)
        self._stats['duplicate_groups'] = len(duplicates)
        self._stats['duplicates_found'] = sum(len(group) for group in duplicates.values())
        
        return duplicates
    
    def _select_appointment_to_keep(
        self, 
        duplicates: List[Appointment]
    ) -> Tuple[Appointment, List[Appointment]]:
        """
        Select which appointment to keep based on retention strategy.
        
        Args:
            duplicates: List of duplicate appointments
            
        Returns:
            Tuple of (appointment to keep, appointments to archive)
        """
        if self.config.retention_strategy == RetentionStrategy.OLDEST:
            sorted_appointments = sorted(duplicates, key=lambda x: x.created_at)
            return sorted_appointments[0], sorted_appointments[1:]
            
        elif self.config.retention_strategy == RetentionStrategy.NEWEST:
            sorted_appointments = sorted(duplicates, key=lambda x: x.created_at, reverse=True)
            return sorted_appointments[0], sorted_appointments[1:]
            
        elif self.config.retention_strategy == RetentionStrategy.MOST_COMPLETE:
            # Score appointments by completeness
            def completeness_score(apt: Appointment) -> int:
                score = 0
                if apt.title: score += 1
                if apt.location: score += 1
                if apt.description: score += 1
                if apt.partner_id: score += 1
                if apt.reminder_time_minutes: score += 1
                if apt.ai_memo: score += 1
                return score
            
            sorted_appointments = sorted(
                duplicates, 
                key=lambda x: (completeness_score(x), x.created_at),
                reverse=True
            )
            return sorted_appointments[0], sorted_appointments[1:]
        
        # Default fallback
        return duplicates[0], duplicates[1:]
    
    async def cleanup_shared_database(
        self,
        user_id: int = 6091255402  # Default to owner
    ) -> Dict[str, any]:
        """
        Clean up duplicate appointments in shared database.
        
        Args:
            user_id: User ID to use for database access
            
        Returns:
            Dictionary with cleanup results
        """
        logger.info(f"Starting duplicate cleanup (dry_run={self.config.dry_run})")
        
        if self.config.verbose:
            print(f"\n🧹 {'[DRY RUN] ' if self.config.dry_run else ''}Cleaning Up Shared Database Duplicates")
            print("=" * 60)
            print(f"Configuration:")
            print(f"  - Retention Strategy: {self.config.retention_strategy.value}")
            print(f"  - Dry Run: {self.config.dry_run}")
            print(f"  - Auto Confirm: {self.config.auto_confirm}")
            print(f"  - Max Appointments: {self.config.max_appointments}")
            print("=" * 60)
        
        # Load user configuration
        user_config = self.config_manager.get_user_config(user_id)
        
        if not user_config or not user_config.shared_notion_database_id:
            error_msg = "Cannot access shared database"
            logger.error(error_msg)
            if self.config.verbose:
                print(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg, 'stats': self._stats}
        
        # Initialize Notion services
        client = Client(auth=user_config.notion_api_key)
        shared_service = NotionService(
            notion_api_key=user_config.notion_api_key,
            database_id=user_config.shared_notion_database_id
        )
        
        # Analyze duplicates
        duplicates = await self.analyze_duplicates(shared_service)
        
        if self.config.verbose:
            print(f"\n🔍 Analysis Results:")
            print(f"  - Total appointments: {self._stats['total_appointments']}")
            print(f"  - Duplicate groups: {self._stats['duplicate_groups']}")
            print(f"  - Total duplicates: {self._stats['duplicates_found']}")
        
        if not duplicates:
            if self.config.verbose:
                print("\n✅ No duplicates found!")
            return {'success': True, 'stats': self._stats}
        
        # Process duplicates
        to_archive = []
        
        for key, duplicate_list in duplicates.items():
            keeper, archives = self._select_appointment_to_keep(duplicate_list)
            
            if self.config.verbose:
                print(f"\n📌 Duplicate group: {keeper.title} ({keeper.date.strftime('%d.%m.%Y %H:%M')})")
                print(f"   Found {len(duplicate_list)} copies")
                print(f"   ✅ Keeping: ID {keeper.notion_page_id} (Created: {keeper.created_at})")
                
                for apt in archives:
                    print(f"   🗑️  Will archive: ID {apt.notion_page_id} (Created: {apt.created_at})")
            
            to_archive.extend(archives)
        
        if self.config.verbose:
            print(f"\n📊 Summary:")
            print(f"  - Unique appointments to keep: {self._stats['duplicate_groups']}")
            print(f"  - Duplicates to archive: {len(to_archive)}")
        
        # Confirm and execute cleanup
        if to_archive and not self.config.dry_run:
            if not self.config.auto_confirm:
                print("\n" + "="*60)
                confirm = input("Proceed with archiving duplicates? (yes/no): ")
                if confirm.lower() != 'yes':
                    if self.config.verbose:
                        print("\n❌ Cleanup cancelled")
                    return {'success': False, 'cancelled': True, 'stats': self._stats}
            
            if self.config.verbose:
                print("\n🗑️  Archiving duplicates...")
            
            # Process in batches
            for i in range(0, len(to_archive), self.config.batch_size):
                batch = to_archive[i:i + self.config.batch_size]
                
                for apt in batch:
                    try:
                        # Archive the page (safer than deletion)
                        client.pages.update(
                            page_id=apt.notion_page_id,
                            archived=True
                        )
                        self._stats['duplicates_archived'] += 1
                        
                        if self.config.verbose:
                            print(f"   ✅ Archived: {apt.title}")
                        
                        logger.info(f"Archived duplicate: {apt.notion_page_id}")
                        
                    except Exception as e:
                        self._stats['errors'] += 1
                        error_msg = f"Error archiving {apt.title}: {e}"
                        logger.error(error_msg)
                        if self.config.verbose:
                            print(f"   ❌ {error_msg}")
            
            if self.config.verbose:
                print(f"\n✅ Archived {self._stats['duplicates_archived']} duplicate appointments")
                if self._stats['errors'] > 0:
                    print(f"⚠️  Encountered {self._stats['errors']} errors")
        
        elif self.config.dry_run and self.config.verbose:
            print("\n✅ [DRY RUN] No appointments were archived")
        
        return {'success': True, 'stats': self._stats}
    
    async def verify_cleanup(self, user_id: int = 6091255402) -> Dict[str, any]:
        """
        Verify that no duplicates remain in the database.
        
        Args:
            user_id: User ID to use for database access
            
        Returns:
            Dictionary with verification results
        """
        if self.config.verbose:
            print("\n\n🔍 Verifying Database Integrity")
            print("=" * 60)
        
        user_config = self.config_manager.get_user_config(user_id)
        
        if not user_config or not user_config.shared_notion_database_id:
            return {'success': False, 'error': 'Cannot access shared database'}
        
        shared_service = NotionService(
            notion_api_key=user_config.notion_api_key,
            database_id=user_config.shared_notion_database_id
        )
        
        # Check for duplicates
        duplicates = await self.analyze_duplicates(shared_service)
        
        verification_stats = {
            'total_appointments': self._stats['total_appointments'],
            'remaining_duplicates': len(duplicates),
            'is_clean': len(duplicates) == 0
        }
        
        if duplicates and self.config.verbose:
            print(f"\n⚠️  Still found {len(duplicates)} duplicate groups!")
            for key, dup_list in list(duplicates.items())[:5]:  # Show first 5
                print(f"   - {key}: {len(dup_list)} copies")
            if len(duplicates) > 5:
                print(f"   ... and {len(duplicates) - 5} more groups")
        elif self.config.verbose:
            print("✅ No duplicates found - database is clean!")
            print(f"Total appointments in database: {verification_stats['total_appointments']}")
        
        return {'success': True, 'stats': verification_stats}
    
    async def test_duplicate_prevention(self) -> Dict[str, any]:
        """
        Test duplicate prevention in partner sync service.
        
        Returns:
            Dictionary with test results
        """
        if self.config.verbose:
            print("\n\n🔄 Testing Duplicate Prevention in Partner Sync")
            print("=" * 60)
        
        # Import here to test the updated service
        from src.services.partner_sync_service import PartnerSyncService
        
        sync_service = PartnerSyncService(self.config_manager)
        test_results = []
        
        # Test sync for both users
        for user_id in [906939299, 6091255402]:
            user_config = self.config_manager.get_user_config(user_id)
            if user_config and user_config.shared_notion_database_id:
                if self.config.verbose:
                    print(f"\n👤 Testing sync for user: {user_config.telegram_username}")
                
                result = await sync_service.sync_partner_relevant_appointments(user_config)
                test_results.append({
                    'user_id': user_id,
                    'username': user_config.telegram_username,
                    'result': result
                })
                
                if result["success"] and self.config.verbose:
                    stats = result["stats"]
                    print(f"   ✅ Sync successful:")
                    print(f"      - Created: {stats['created']}")
                    print(f"      - Updated: {stats['updated']}")
                    print(f"      - Errors: {stats['errors']}")
                    print(f"      - Removed: {stats['removed']}")
                elif not result["success"] and self.config.verbose:
                    print(f"   ❌ Sync failed: {result.get('error')}")
        
        return {'success': True, 'test_results': test_results}


async def main():
    """Main entry point for the cleanup utility."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clean up duplicate appointments in shared Notion database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Simulate cleanup without making changes (default: True)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the cleanup (disables dry-run)'
    )
    parser.add_argument(
        '--strategy',
        choices=['oldest', 'newest', 'most_complete'],
        default='oldest',
        help='Strategy for which duplicate to keep (default: oldest)'
    )
    parser.add_argument(
        '--auto-confirm',
        action='store_true',
        help='Skip confirmation prompts'
    )
    parser.add_argument(
        '--max-appointments',
        type=int,
        default=1000,
        help='Maximum appointments to fetch (default: 1000)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Batch size for archiving operations (default: 50)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify database integrity'
    )
    parser.add_argument(
        '--test-prevention',
        action='store_true',
        help='Test duplicate prevention in partner sync'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = DuplicateCleanupConfig(
        dry_run=not args.execute,
        retention_strategy=RetentionStrategy(args.strategy),
        batch_size=args.batch_size,
        auto_confirm=args.auto_confirm,
        verbose=not args.quiet,
        max_appointments=args.max_appointments
    )
    
    # Create utility
    utility = DuplicateCleanupUtility(config)
    
    try:
        if args.verify_only:
            # Only run verification
            result = await utility.verify_cleanup()
            if not args.quiet:
                print(f"\n{'✅' if result['success'] else '❌'} Verification complete")
        
        elif args.test_prevention:
            # Only test prevention
            result = await utility.test_duplicate_prevention()
            if not args.quiet:
                print(f"\n{'✅' if result['success'] else '❌'} Prevention test complete")
        
        else:
            # Run full cleanup workflow
            # Step 1: Cleanup
            cleanup_result = await utility.cleanup_shared_database()
            
            if cleanup_result['success'] and not cleanup_result.get('cancelled'):
                # Step 2: Verify
                verify_result = await utility.verify_cleanup()
                
                # Step 3: Test prevention (optional)
                if not args.dry_run and not args.quiet:
                    test_result = await utility.test_duplicate_prevention()
            
            # Print final summary
            if not args.quiet:
                print("\n" + "="*60)
                print("📊 Final Statistics:")
                stats = cleanup_result['stats']
                print(f"  - Total appointments processed: {stats['total_appointments']}")
                print(f"  - Duplicate groups found: {stats['duplicate_groups']}")
                print(f"  - Duplicates identified: {stats['duplicates_found']}")
                print(f"  - Duplicates archived: {stats['duplicates_archived']}")
                print(f"  - Errors encountered: {stats['errors']}")
                print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Cleanup interrupted by user")
        return 1
    except Exception as e:
        logger.exception("Unexpected error during cleanup")
        print(f"\n❌ Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))