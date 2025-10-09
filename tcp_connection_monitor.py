#!/usr/bin/env python3

import socket
import time
import threading
from datetime import datetime
from typing import List, Tuple, Dict
from collections import defaultdict


class TCPConnectionMonitor:
    def __init__(self, hosts: List[Dict[str, any]], timeout: float = 5.0):
        """
        Initialize the TCP connection monitor.

        Args:
            hosts: List of dictionaries with 'hostname', 'port', and 'service' keys
            timeout: Socket connection timeout in seconds
        """
        self.hosts = hosts
        self.timeout = timeout

        # Create mapping from host_key to service name for display
        self.service_names = {}
        for host in hosts:
            host_key = f"{host['hostname']}:{host['port']}"
            self.service_names[host_key] = host['service']

        # Histogram buckets: <1s, 1-5s (times in milliseconds)
        self.buckets = [
            (0, 1000),      # <1s
            (1000, 5000),   # 1-5s
        ]

        # Counters for each host and bucket
        self.counters = defaultdict(lambda: defaultdict(int))
        self.dns_counters = defaultdict(lambda: defaultdict(int))
        self.total_attempts = defaultdict(int)
        self.failed_connections = defaultdict(int)
        self.dns_failures = defaultdict(int)

        # Threading control
        self.running = True
        self.lock = threading.Lock()

    def measure_connection_time(self, hostname: str, port: int) -> tuple[float, float]:
        """
        Measure the time to establish a TCP connection to the given host and port.
        DNS resolution is timed separately from connection timing.

        Args:
            hostname: Target hostname
            port: Target port

        Returns:
            Tuple of (connection_time_ms, dns_resolution_time_ms), or (-1, -1) if failed
        """
        try:
            # default is timeout/failure
            connection_time_ms, dns_resolution_time_ms = -1, -1
            # Measure DNS resolution time
            dns_start_time = time.time()
            ip_address = socket.gethostbyname(hostname)
            dns_end_time = time.time()
            dns_resolution_time_ms = (dns_end_time - dns_start_time) * 1000

            # Now measure only the TCP connection time
            start_time = time.time()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((ip_address, port))
            sock.close()

            end_time = time.time()
            connection_time_ms = (end_time - start_time) * 1000
            return connection_time_ms, dns_resolution_time_ms

        except (socket.error, socket.timeout, OSError, socket.gaierror) as e:
            print(f"Connection failed to {hostname}:{port} - {e}")
            return connection_time_ms, dns_resolution_time_ms

    def categorize_time(self, time_ms: float) -> str:
        """
        Categorize the connection time into appropriate bucket.

        Args:
            time_ms: Connection time in milliseconds

        Returns:
            String representation of the bucket
        """
        for min_val, max_val in self.buckets:
            if min_val <= time_ms < max_val:
                if min_val == 0:
                    return "<1s"
                elif min_val == 1000:
                    return "1-5s"

        # If time_ms >= 5000, it's considered a timeout/failure
        return "timeout"

    def update_counters(self, hostname: str, port: int, connection_time_ms: float, dns_time_ms: float):
        """
        Update the histogram counters for the given connection and DNS resolution times.

        Args:
            hostname: Target hostname
            port: Target port
            connection_time_ms: Connection time in milliseconds
            dns_time_ms: DNS resolution time in milliseconds
        """
        host_key = f"{hostname}:{port}"

        with self.lock:
            self.total_attempts[host_key] += 1

            if connection_time_ms == -1:
                self.failed_connections[host_key] += 1
            elif connection_time_ms >= 5000:
                # Treat connections >= 5s as failures
                self.failed_connections[host_key] += 1
            else:
                bucket = self.categorize_time(connection_time_ms)
                if bucket != "timeout":
                    self.counters[host_key][bucket] += 1

            # Track DNS resolution time
            if dns_time_ms == -1:
                # DNS resolution failed
                self.dns_failures[host_key] += 1
            elif dns_time_ms >= 5000:
                # DNS resolution too slow (>=5s), treat as DNS failure
                self.dns_failures[host_key] += 1
            else:
                # DNS resolution succeeded and was within acceptable time
                dns_bucket = self.categorize_time(dns_time_ms)
                if dns_bucket != "timeout":
                    self.dns_counters[host_key][dns_bucket] += 1

    def print_statistics(self):
        """Print current statistics to log file and reset counters."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_filename = f"tcp_stats_{datetime.now().strftime('%Y%m%d')}.log"

        with self.lock:
            if self.total_attempts:
                # Write to log file
                with open(log_filename, 'a') as log_file:
                    # Write header if file is new/empty
                    try:
                        if log_file.tell() == 0:
                            log_file.write(f"{'Timestamp':<19} | {'Service':<20} | {'Conn<1s':>8} | {'Conn1-5s':>9} | {'DNS<1s':>7} | {'DNS1-5s':>8} | {'DNSFail':>7} | {'ConnFailed':>10} | {'Total':>5}\n")
                            log_file.write("-" * 107 + "\n")
                    except OSError:
                        # File position not available, skip header check
                        pass

                    for host_key in sorted(self.total_attempts.keys(), key=lambda k: self.service_names.get(k, k)):
                        # Get connection bucket counts
                        conn_under_1s = self.counters[host_key].get("<1s", 0)
                        conn_1_to_5s = self.counters[host_key].get("1-5s", 0)

                        # Get DNS bucket counts
                        dns_under_1s = self.dns_counters[host_key].get("<1s", 0)
                        dns_1_to_5s = self.dns_counters[host_key].get("1-5s", 0)
                        dns_failed = self.dns_failures[host_key]

                        failed = self.failed_connections[host_key]
                        total = self.total_attempts[host_key]

                        # Get service name for display
                        service_name = self.service_names.get(host_key, host_key.split(':')[0].split('.')[0])

                        # Write data row to log file
                        log_file.write(f"{current_time:<19} | {service_name:<20} | {conn_under_1s:>8} | {conn_1_to_5s:>9} | {dns_under_1s:>7} | {dns_1_to_5s:>8} | {dns_failed:>7} | {failed:>10} | {total:>5}\n")

                # Also print to console for immediate feedback
                print(f"Statistics logged to {log_filename} at {current_time}")

            # Reset counters
            self.counters.clear()
            self.dns_counters.clear()
            self.dns_failures.clear()
            self.total_attempts.clear()
            self.failed_connections.clear()

    def monitoring_loop(self):
        """Main monitoring loop that tests connections every 2 seconds."""
        while self.running:
            for host in self.hosts:
                if not self.running:
                    break

                hostname = host['hostname']
                port = host['port']
                connection_time, dns_time = self.measure_connection_time(hostname, port)
                print(".", end="", flush=True)
                self.update_counters(hostname, port, connection_time, dns_time)

            if self.running:
                time.sleep(2)

    def statistics_loop(self):
        """Loop that prints statistics every 5 minutes."""
        while self.running:
            time.sleep(300)  # 5 minutes
            if self.running:
                self.print_statistics()

    def start(self):
        """Start the monitoring and statistics threads."""
        print("Starting TCP Connection Monitor...")
        host_list = ', '.join([f'{h["service"]} ({h["hostname"]}:{h["port"]})' for h in self.hosts])
        print(f"Monitoring hosts: {host_list}")
        print("Press Ctrl+C to stop\n")

        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        monitor_thread.start()

        # Start statistics thread
        stats_thread = threading.Thread(target=self.statistics_loop, daemon=True)
        stats_thread.start()

        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping monitor...")
            self.running = False

            # Print final statistics
            print("\nFinal Statistics:")
            self.print_statistics()


def main():
    """Main function to configure and start the monitor."""

    # Configure the hosts to monitor with hostname, port, and service name
    hosts = [
        {
            "service": "promotion-api",
            "hostname": "promotion-api.raprod.acs.dnacloud.fi",
            "port": 443
        },
        {
            "service": "total-commander-api",
            "hostname": "x754686ncl-vpce-0e6f57fcc39b0622c.execute-api.eu-west-1.amazonaws.com",
            "port": 443
        },
        {
            "service": "monokkeli",
            "hostname": "monokkeli.dna.fi",
            "port": 443
        }
    ]

    monitor = TCPConnectionMonitor(hosts, timeout=5.0)
    monitor.start()


if __name__ == "__main__":
    main()