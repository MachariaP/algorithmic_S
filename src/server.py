"""Server implementation"""

import os
import socket
import logging
import resource
import threading
from typing import Dict, List, Optional, Set, Tuple

from .config import ServerConfig
from .search import SearchEngine, SearchOptions, SearchResult
from .monitoring import (
    ServerPerformanceMonitor,
    ServerHealthCheck,
    ServerAlertManager,
    Alert,
    AlertLevel
)
from .security import SecurityManager
from .rate_limiter import RateLimiter
from .connection_pool import ConnectionPool


class ServerError(Exception):
    """Base class for server errors"""
    pass


class RateLimiter:
    """Rate limiter implementation"""
    def __init__(self, requests_per_second: int, burst_size: int):
        self.rate = requests_per_second
        self.burst = burst_size
        self.tokens = defaultdict(float)
        self.last_update = defaultdict(float)
        self._lock = threading.Lock()
        
    def is_allowed(self, client_ip: str) -> bool:
        with self._lock:
            now = time.time()
            time_passed = now - self.last_update[client_ip]
            new_tokens = time_passed * self.rate
            self.tokens[client_ip] = min(self.burst, self.tokens[client_ip] + new_tokens)
            self.last_update[client_ip] = now
            
            if self.tokens[client_ip] >= 1.0:
                self.tokens[client_ip] -= 1.0
                return True
            return False


class ConnectionPool:
    """Connection pool for client sockets"""
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.pool: Set[socket.socket] = set()
        self._lock = threading.Lock()
        
    def add(self, sock: socket.socket) -> bool:
        with self._lock:
            if len(self.pool) >= self.max_size:
                return False
            self.pool.add(sock)
            return True
            
    def remove(self, sock: socket.socket) -> None:
        with self._lock:
            self.pool.discard(sock)
            
    def cleanup(self) -> None:
        with self._lock:
            for sock in list(self.pool):
                try:
                    sock.close()
                except:
                    pass
            self.pool.clear()


class StringSearchServer:
    """TCP server for string search operations"""
    
    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()
        self.search_engine = SearchEngine()
        self.sock = None
        self._running = threading.Event()
        self._lock = threading.Lock()
        self._clients: List[socket.socket] = []
        self.start_time = time.time()
        self._thread_pool = ThreadPoolExecutor(
            max_workers=self.config.resources.worker_threads,
            thread_name_prefix="search_worker"
        )
        self._rate_limiter = RateLimiter(
            self.config.security.rate_limit,
            self.config.security.rate_limit_burst
        )
        self._connection_pool = ConnectionPool(self.config.resources.connection_pool_size)
        
        # Monitoring metrics
        self.request_count = 0
        self.error_count = 0
        self.cache_hits = 0
        self.total_response_time = 0.0
        self.clients = set()
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.config.log.level.upper()),
            format=self.config.log.format
        )
        self.logger = logging.getLogger(__name__)
        
        # Set resource limits
        self._set_resource_limits()
        
        # Initialize monitoring
        self.monitor = ServerPerformanceMonitor(self)
        self.health = ServerHealthCheck(self)
        self.alerts = ServerAlertManager(self)
        
    def _set_resource_limits(self) -> None:
        """Set system resource limits"""
        try:
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (self.config.resources.max_file_descriptors, self.config.resources.max_file_descriptors)
            )
        except Exception as e:
            self.logger.warning(f"Failed to set resource limits: {e}")
        
    def start(self) -> None:
        """Start the server"""
        if self.sock:
            self.stop()
            time.sleep(0.1)
            
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        try:
            self.sock.bind((self.config.host, self.config.port))
            self.sock.listen(self.config.resources.max_connections)
            self._running.set()
            self.start_time = time.time()
            
            # Reset metrics
            with self._lock:
                self.request_count = 0
                self.error_count = 0
                self.cache_hits = 0
                self.total_response_time = 0.0
                self.clients.clear()
            
            # Start monitoring thread
            threading.Thread(target=self._monitor_resources, daemon=True).start()
            
            # Log server start
            self.alerts.send_alert(
                Alert(
                    level=AlertLevel.INFO,
                    source="server",
                    message=f"Server started on {self.config.host}:{self.config.port}"
                )
            )
            
            while self._running.is_set():
                try:
                    client_sock, addr = self.sock.accept()
                    client_sock.settimeout(self.config.resources.connection_timeout)
                    
                    if not self._connection_pool.add(client_sock):
                        self.logger.warning(f"Connection pool full, rejecting {addr}")
                        self._send_error(client_sock, "Connection pool full")
                        client_sock.close()
                        continue
                        
                    with self._lock:
                        self._clients.append(client_sock)
                    self._thread_pool.submit(self._handle_client, client_sock, addr)
                except socket.error as e:
                    if self._running.is_set():
                        self.logger.error(f"Error accepting connection: {e}")
                        self.alerts.send_alert(
                            Alert(
                                level=AlertLevel.ERROR,
                                source="server",
                                message=f"Error accepting connection: {str(e)}"
                            )
                        )
                    break
        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            self.alerts.send_alert(
                Alert(
                    level=AlertLevel.ERROR,
                    source="server",
                    message=f"Server error: {str(e)}"
                )
            )
            raise ServerError(f"Failed to start server: {str(e)}")
        finally:
            self.stop()
                    
    def stop(self) -> None:
        """Stop the server and clean up resources"""
        self._running.clear()
        
        # Log server stop
        self.alerts.send_alert(
            Alert(
                level=AlertLevel.INFO,
                source="server",
                message="Server stopped"
            )
        )
        
        # Clean up connection pool
        self._connection_pool.cleanup()
        
        # Close all client connections
        with self._lock:
            for client in self._clients:
                try:
                    client.close()
                except:
                    pass
            self._clients.clear()
            self.clients.clear()
        
        # Close server socket
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
            
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
            
    def load_data(self, file_path: Optional[Path] = None) -> None:
        """Load search data from file"""
        if file_path is None:
            file_path = self.config.data_file
        if file_path:
            try:
                self.search_engine.load_data(file_path)
            except Exception as e:
                raise ServerError(f"Failed to load data: {e}")
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics"""
        return {
            'uptime': time.time() - self.start_time,
            'active_connections': len(self._clients),
            'search_metrics': self.search_engine.get_metrics()
        }

    def _send_response(self, sock: socket.socket, data: Dict[str, Any]) -> None:
        """Send JSON response to client"""
        try:
            response = json.dumps(data).encode() + b'\n'
            sock.sendall(response)
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
            raise

    def _send_error(self, sock: socket.socket, message: str) -> None:
        """Send error response to client"""
        try:
            response = json.dumps({
                'success': False,
                'error': message
            }).encode() + b'\n'
            sock.sendall(response)
        except Exception as e:
            self.logger.error(f"Error sending error response: {e}")
            raise
            
    def _handle_client(self, client_sock: socket.socket, addr: tuple) -> None:
        """Handle client connection"""
        client_ip = addr[0]
        buffer = b''
        
        try:
            # Track client connection
            with self._lock:
                self.clients.add(client_sock)
            
            while self._running.is_set():
                try:
                    # Read data into buffer
                    chunk = client_sock.recv(4096)
                    if not chunk:
                        break
                    
                    buffer += chunk
                    
                    # Try to handle as length-prefixed message first
                    if len(buffer) >= 4:
                        try:
                            length = struct.unpack('!I', buffer[:4])[0]
                            if length > self.config.max_query_length:
                                self._send_error(client_sock, "Query too long")
                                buffer = buffer[4:]  # Skip length bytes
                                continue
                                
                            if len(buffer) >= length + 4:
                                data = buffer[4:length+4]
                                buffer = buffer[length+4:]
                                self._handle_request(client_sock, data, client_ip)
                                continue
                        except struct.error:
                            pass  # Not a length-prefixed message
                    
                    # Handle as raw message if no length prefix
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if len(line) > self.config.max_query_length:
                            self._send_error(client_sock, "Query too long")
                            continue
                        self._handle_request(client_sock, line, client_ip)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error handling client {addr}: {e}")
                    break
                    
        finally:
            # Remove client connection
            with self._lock:
                self.clients.discard(client_sock)
            
            self._connection_pool.remove(client_sock)
            with self._lock:
                if client_sock in self._clients:
                    self._clients.remove(client_sock)
            try:
                client_sock.close()
            except:
                pass

    def _handle_request(self, client_sock: socket.socket, data: bytes, client_ip: str) -> None:
        """Handle a single request"""
        start_time = time.time()
        
        if not self._rate_limiter.is_allowed(client_ip):
            self._send_error(client_sock, "Rate limit exceeded")
            return
            
        # Parse request
        try:
            try:
                request = json.loads(data)
                command = request.get('command', 'search')
                
                if command == 'search':
                    query = request.get('query', '').strip()
                    options = SearchOptions(**request.get('options', {}))
                    
                    if not query:
                        self._send_error(client_sock, "Empty query")
                        return
                        
                    # Perform search
                    result = self.search_engine.search(query, options)
                    
                    # Update metrics
                    with self._lock:
                        self.request_count += 1
                        if result.from_cache:
                            self.cache_hits += 1
                        self.total_response_time += time.time() - start_time
                    
                    # Record search metrics
                    duration = time.time() - start_time
                    self.monitor.record_metric("search_latency", duration)
                    self.monitor.record_metric("search_result_count", result.count)
                    self.monitor.record_metric("search_pattern_length", len(query))
                    
                    # Record throughput (requests per second)
                    self.monitor.record_metric(
                        "search_throughput",
                        1.0 / duration if duration > 0 else 0
                    )
                    
                    self._send_response(client_sock, {
                        'success': True,
                        'matches': result.matches,
                        'count': result.count,
                        'duration': result.duration
                    })
                    
                elif command == 'metrics':
                    # Generate metrics report
                    metrics = self.monitor.get_metrics()
                    self._send_response(client_sock, {
                        'success': True,
                        'metrics': metrics
                    })
                    
                elif command == 'health':
                    # Generate health report
                    health = self.health.check_health()
                    self._send_response(client_sock, {
                        'success': True,
                        'health': health
                    })
                    
                elif command == 'alerts':
                    # Get recent alerts
                    alerts = self.alerts.get_alert_history()
                    self._send_response(client_sock, {
                        'success': True,
                        'alerts': alerts
                    })
                    
                else:
                    self._send_error(client_sock, f"Unknown command: {command}")
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Handle raw text search
                query = data.decode('utf-8', errors='ignore').strip()
                options = SearchOptions()
                
                if not query:
                    self._send_error(client_sock, "Empty query")
                    return
                    
                # Perform search
                result = self.search_engine.search(query, options)
                
                # Update metrics
                with self._lock:
                    self.request_count += 1
                    if result.from_cache:
                        self.cache_hits += 1
                    self.total_response_time += time.time() - start_time
                
                # Record search metrics
                duration = time.time() - start_time
                self.monitor.record_metric("search_latency", duration)
                self.monitor.record_metric("search_result_count", result.count)
                self.monitor.record_metric("search_pattern_length", len(query))
                
                # Record throughput (requests per second)
                self.monitor.record_metric(
                    "search_throughput",
                    1.0 / duration if duration > 0 else 0
                )
                
                self._send_response(client_sock, {
                    'success': True,
                    'matches': result.matches,
                    'count': result.count,
                    'duration': result.duration
                })
                
        except Exception as e:
            # Update error metrics
            with self._lock:
                self.error_count += 1
                self.total_response_time += time.time() - start_time
            
            # Record error metrics
            self.monitor.record_metric("search_errors", 1)
            self.alerts.send_alert(
                Alert(
                    "search_error",
                    f"Search error for query '{query[:100]}...': {str(e)}",
                    "error"
                )
            )
            self._send_error(client_sock, str(e))

    def _monitor_resources(self) -> None:
        """Monitor system resources"""
        while self._running.is_set():
            try:
                # Check health
                health = self.health.check_health()
                if not health.healthy:
                    for issue in health.details.get("system", {}).get("issues", []):
                        self.alerts.send_alert(
                            Alert(
                                level=AlertLevel.WARNING,
                                source="health_check",
                                message=f"Health check failed: {issue}"
                            )
                        )
                
                time.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                self.alerts.send_alert(
                    Alert(
                        level=AlertLevel.ERROR,
                        source="monitoring",
                        message=f"Error monitoring resources: {str(e)}"
                    )
                )
