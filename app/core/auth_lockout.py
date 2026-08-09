"""
Authentication lockout mechanism for brute force protection
"""
import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LockoutConfig:
    """Configuration for account lockout"""
    max_attempts: int = 5  # Max failed attempts before lockout
    window_seconds: int = 300  # Time window for counting attempts (5 minutes)
    lockout_duration: int = 900  # Lockout duration in seconds (15 minutes)
    exponential_backoff: bool = True  # Enable exponential backoff


class AuthLockoutManager:
    """
    Manages authentication lockouts to prevent brute force attacks
    
    Features:
    - Track failed login attempts per user/IP
    - Automatic account lockout after threshold
    - Exponential backoff for repeated failures
    - Configurable lockout duration
    """
    
    def __init__(self, config: Optional[LockoutConfig] = None):
        self.config = config or LockoutConfig()
        
        # Track failed attempts: {identifier: deque of timestamps}
        self.failed_attempts: Dict[str, deque] = defaultdict(deque)
        
        # Track locked accounts: {identifier: lock_until_timestamp}
        self.locked_until: Dict[str, float] = {}
        
        # Track lockout count for exponential backoff
        self.lockout_count: Dict[str, int] = defaultdict(int)
        
        self.last_cleanup = time.time()
    
    def is_locked(self, identifier: str) -> tuple[bool, Optional[float]]:
        """
        Check if an account/IP is currently locked
        
        Returns:
            (is_locked, unlock_time) - unlock_time is None if not locked
        """
        now = time.time()
        
        if identifier in self.locked_until:
            unlock_time = self.locked_until[identifier]
            
            if now < unlock_time:
                # Still locked
                remaining = unlock_time - now
                logger.warning(
                    f"Login attempt for locked identifier: {identifier}. "
                    f"Unlocks in {int(remaining)}s"
                )
                return True, unlock_time
            else:
                # Lock expired, clean up
                del self.locked_until[identifier]
                # Keep lockout count for exponential backoff
        
        return False, None
    
    def record_failed_attempt(self, identifier: str) -> dict:
        """
        Record a failed login attempt
        
        Returns:
            dict with lockout info if locked, empty dict otherwise
        """
        now = time.time()
        
        # Clean up old attempts outside the window
        attempts = self.failed_attempts[identifier]
        while attempts and attempts[0] <= now - self.config.window_seconds:
            attempts.popleft()
        
        # Add new failed attempt
        attempts.append(now)
        
        # Check if threshold exceeded
        if len(attempts) >= self.config.max_attempts:
            return self._lock_account(identifier)
        
        # Return remaining attempts
        remaining = self.config.max_attempts - len(attempts)
        logger.info(f"Failed login for {identifier}. {remaining} attempts remaining.")
        
        return {
            "locked": False,
            "attempts_remaining": remaining,
            "window_seconds": self.config.window_seconds
        }
    
    def _lock_account(self, identifier: str) -> dict:
        """Lock an account due to too many failed attempts"""
        now = time.time()
        
        # Calculate lockout duration (exponential backoff if enabled)
        lockout_duration = self.config.lockout_duration
        if self.config.exponential_backoff:
            # Double duration for each repeated lockout (capped at 24 hours)
            multiplier = min(2 ** self.lockout_count[identifier], 96)  # Max 96x (24h)
            lockout_duration = min(lockout_duration * multiplier, 86400)
            self.lockout_count[identifier] += 1
        
        unlock_time = now + lockout_duration
        self.locked_until[identifier] = unlock_time
        
        # Clear failed attempts (they've already triggered the lock)
        self.failed_attempts[identifier].clear()
        
        logger.warning(
            f"Account/IP locked: {identifier}. Duration: {int(lockout_duration)}s. "
            f"Lockout count: {self.lockout_count[identifier]}"
        )
        
        return {
            "locked": True,
            "unlock_time": unlock_time,
            "lockout_duration": lockout_duration,
            "message": f"Too many failed attempts. Account locked for {int(lockout_duration / 60)} minutes."
        }
    
    def record_successful_login(self, identifier: str):
        """
        Record a successful login and reset counters
        """
        # Clear failed attempts
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
        
        # Clear lockout
        if identifier in self.locked_until:
            del self.locked_until[identifier]
        
        # Reset lockout count
        if identifier in self.lockout_count:
            del self.lockout_count[identifier]
        
        logger.info(f"Successful login: {identifier}. Counters reset.")
    
    def unlock_account(self, identifier: str):
        """Manually unlock an account (admin action)"""
        if identifier in self.locked_until:
            del self.locked_until[identifier]
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
        if identifier in self.lockout_count:
            del self.lockout_count[identifier]
        
        logger.info(f"Account manually unlocked: {identifier}")
    
    def get_lockout_info(self, identifier: str) -> dict:
        """Get lockout information for an identifier"""
        is_locked, unlock_time = self.is_locked(identifier)
        
        if is_locked:
            remaining = int(unlock_time - time.time())
            return {
                "locked": True,
                "unlock_time": datetime.fromtimestamp(unlock_time).isoformat(),
                "remaining_seconds": remaining,
                "lockout_count": self.lockout_count.get(identifier, 0)
            }
        
        attempts = self.failed_attempts.get(identifier, deque())
        return {
            "locked": False,
            "failed_attempts": len(attempts),
            "attempts_remaining": self.config.max_attempts - len(attempts),
            "lockout_count": self.lockout_count.get(identifier, 0)
        }
    
    def cleanup_old_entries(self):
        """Remove old entries to prevent memory leaks"""
        now = time.time()
        
        # Clean up expired locks
        expired_locks = [
            identifier for identifier, unlock_time in self.locked_until.items()
            if now >= unlock_time + 3600  # 1 hour grace period
        ]
        for identifier in expired_locks:
            del self.locked_until[identifier]
        
        # Clean up old failed attempts
        for identifier in list(self.failed_attempts.keys()):
            attempts = self.failed_attempts[identifier]
            while attempts and attempts[0] <= now - 3600:  # 1 hour
                attempts.popleft()
            if not attempts:
                del self.failed_attempts[identifier]
        
        # Clean up old lockout counts (after 24 hours of no activity)
        inactive_identifiers = [
            identifier for identifier in self.lockout_count
            if identifier not in self.locked_until 
            and identifier not in self.failed_attempts
        ]
        for identifier in inactive_identifiers:
            del self.lockout_count[identifier]
        
        self.last_cleanup = now
        logger.info(f"Lockout cleanup complete. Removed {len(expired_locks)} expired locks.")
    
    def get_stats(self) -> dict:
        """Get statistics about lockout system"""
        # Periodic cleanup
        if time.time() - self.last_cleanup > 300:  # Every 5 minutes
            self.cleanup_old_entries()
        
        return {
            "currently_locked": len(self.locked_until),
            "accounts_with_failures": len(self.failed_attempts),
            "total_failed_attempts": sum(len(a) for a in self.failed_attempts.values()),
            "accounts_with_multiple_lockouts": sum(1 for c in self.lockout_count.values() if c > 1),
            "config": {
                "max_attempts": self.config.max_attempts,
                "window_seconds": self.config.window_seconds,
                "lockout_duration": self.config.lockout_duration,
                "exponential_backoff": self.config.exponential_backoff
            }
        }


# Global lockout manager instance
auth_lockout_manager = AuthLockoutManager()


