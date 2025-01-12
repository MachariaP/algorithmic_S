#!/usr/bin/env python3

"""Rate limiting implementation"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

class RateLimiter:
    """Token bucket rate limiter
    
    Why this approach?
    - Efficient O(1) operations
    - Handles burst traffic well
    - Thread-safe implementation
    - Memory efficient
    """
    
    def __init__(self, requests: int, window: int = 60):
        """Initialize rate limiter
        
        Args:
            requests: Number of requests allowed per window
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        self.clients: Dict[str, List[float]] = defaultdict(list)
        self.lock = Lock()
        
    def allow_request(self, client_ip: str) -> bool:
        """Check if request is allowed
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if request is allowed, False otherwise
        """
        with self.lock:
            now = time.time()
            requests = self.clients[client_ip]
            
            # Remove old requests
            while requests and requests[0] < now - self.window:
                requests.pop(0)
                
            # Check rate limit
            if len(requests) >= self.requests:
                return False
                
            # Allow request
            requests.append(now)
            return True
