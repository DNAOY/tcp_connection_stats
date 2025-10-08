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

        # Histogram buckets: (0, 100], (100, 500], (500, 1000], (1000, 2000], > 2000
        self.buckets = [
            (0, 100),
            (100, 500),
            (500, 1000),
            (1000, 2000),
            (2000, float('inf'))
        ]

        # Counters for each host and bucket
        self.counters = defaultdict(lambda: defaultdict(int))
        self.total_attempts = defaultdict(int)
        self.failed_connections = defaultdict(int)

        # Threading control
        self.running = True
        self.lock = threading.Lock()

    def measure_connection_time(self, hostname: str, port: int) -> float:
        """
        Measure the time to establish a TCP connection to the given host and port.

        Args:
            hostname: Target hostname
            port: Target port

        Returns:
            Connection time in milliseconds, or -1 if connection failed
        """
        start_time = time.time()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((hostname, port))
            sock.close()

            end_time = time.time()
            connection_time_ms = (end_time - start_time) * 1000
            return connection_time_ms

        except (socket.error, socket.timeout, OSError) as e:
            print(f"Connection failed to {hostname}:{port} - {e}")
            return -1

    def categorize_time(self, time_ms: float) -> str:
        """
        Categorize the connection time into appropriate bucket.

        Args:
            time_ms: Connection time in milliseconds

        Returns:
            String representation of the bucket
        """
        for min_val, max_val in self.buckets:
            if min_val < time_ms <= max_val:
                if max_val == float('inf'):
                    return f"> {min_val}ms"
                else:
                    return f"({min_val}, {max_val}]ms"
        return "Unknown"

    def update_counters(self, hostname: str, port: int, time_ms: float):
        """
        Update the histogram counters for the given connection time.

        Args:
            hostname: Target hostname
            port: Target port
            time_ms: Connection time in milliseconds
        """
        host_key = f"{hostname}:{port}"

        with self.lock:
            self.total_attempts[host_key] += 1

            if time_ms == -1:
                self.failed_connections[host_key] += 1
            else:
                bucket = self.categorize_time(time_ms)
                self.counters[host_key][bucket] += 1

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
                            log_file.write(f"{'Timestamp':<19} | {'Service':<20} | {'0-100ms':>8} | {'100-500ms':>9} | {'500-1000ms':>10} | {'1000-2000ms':>11} | {'>2000ms':>8} | {'Failed':>6} | {'Total':>5}\n")
                            log_file.write("-" * 100 + "\n")
                    except OSError:
                        # File position not available, skip header check
                        pass

                    for host_key in sorted(self.total_attempts.keys(), key=lambda k: self.service_names.get(k, k)):
                        # Get bucket counts
                        bucket_0_100 = self.counters[host_key].get("(0, 100]ms", 0)
                        bucket_100_500 = self.counters[host_key].get("(100, 500]ms", 0)
                        bucket_500_1000 = self.counters[host_key].get("(500, 1000]ms", 0)
                        bucket_1000_2000 = self.counters[host_key].get("(1000, 2000]ms", 0)
                        bucket_2000_plus = self.counters[host_key].get("> 2000ms", 0)

                        failed = self.failed_connections[host_key]
                        total = self.total_attempts[host_key]

                        # Get service name for display
                        service_name = self.service_names.get(host_key, host_key.split(':')[0].split('.')[0])

                        # Write data row to log file
                        log_file.write(f"{current_time:<19} | {service_name:<20} | {bucket_0_100:>8} | {bucket_100_500:>9} | {bucket_500_1000:>10} | {bucket_1000_2000:>11} | {bucket_2000_plus:>8} | {failed:>6} | {total:>5}\n")

                # Also print to console for immediate feedback
                print(f"Statistics logged to {log_filename} at {current_time}")

            # Reset counters
            self.counters.clear()
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
                connection_time = self.measure_connection_time(hostname, port)
                print(".", end="", flush=True)
                self.update_counters(hostname, port, connection_time)

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
            "service": "profile-api",
            "hostname": "profile-api.einstein.dna.fi",
            "port": 443
        }
    ]

    # You can modify these hosts as needed:
    # hosts = [
    #     {
    #         "service": "web-service",
    #         "hostname": "your-host1.com",
    #         "port": 8080
    #     },
    #     {
    #         "service": "database",
    #         "hostname": "your-host2.com",
    #         "port": 3306
    #     }
    # ]

    monitor = TCPConnectionMonitor(hosts, timeout=5.0)
    monitor.start()


if __name__ == "__main__":
    main()