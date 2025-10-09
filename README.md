# TCP Connection Monitor

This directory contains a Python script for monitoring TCP connection delays to multiple hosts and logging statistics to daily log files.

## Usage

1. Edit the `hosts` list in `tcp_connection_monitor.py` to specify your target hosts:

```python
hosts = [
    {
        "service": "web-service",
        "hostname": "your-host1.example.com",
        "port": 443
    },
    {
        "service": "database",
        "hostname": "your-host2.example.com",
        "port": 3306
    }
]
```

2. Run the script:

```bash
python3 tcp_connection_monitor.py
```

## Features

- **Connection Testing**: Tests TCP connections to specified hosts every 2 seconds
- **Separate Timing**: Measures DNS resolution and TCP connection times independently
- **Histogram Tracking**: Categorizes both connection and DNS resolution times into performance buckets
- **Daily Log Files**: Writes statistics to daily log files named `tcp_stats_YYYYMMDD.log`
- **Statistics Reporting**: Logs detailed statistics every 5 minutes in tabular format
- **Error Handling**: Tracks connection failures, DNS failures, and timeouts separately
- **Multithreaded**: Uses separate threads for monitoring and statistics reporting
- **Service Names**: Uses configurable service names for easier identification in logs

## Sample Output

### Console Output
```
Starting TCP Connection Monitor...
Monitoring hosts: promotion-api (promotion-api.raprod.acs.dnacloud.fi:443), total-commander-api (x754686ncl-vpce-0e6f57fcc39b0622c.execute-api.eu-west-1.amazonaws.com:443), profile-api (profile-api.einstein.dna.fi:443)
Press Ctrl+C to stop

..........................................
Statistics logged to tcp_stats_20251008.log at 2025-10-08 14:30:00
```

### Log File Format
The daily log files contain tabular data with separate metrics for connection and DNS performance:
```
Timestamp           | Service              | Conn<1s | Conn1-5s | DNS<1s | DNS1-5s | DNSFail | ConnFailed | Total
2025-10-09 14:30:00 | promotion-api        |     120 |       15 |    135 |        0 |       0 |          8 |   143
2025-10-09 14:30:00 | total-commander-api  |      98 |       45 |    140 |        3 |       0 |          0 |   143
2025-10-09 14:30:00 | monokkeli            |     140 |        3 |    143 |        0 |       0 |          0 |   143
```

**Column Descriptions:**
- **Conn<1s/Conn1-5s**: TCP connection time performance buckets
- **DNS<1s/DNS1-5s**: DNS resolution time performance buckets
- **DNSFail**: DNS failures (failed resolutions + slow resolutions ≥5s)
- **ConnFailed**: Connection failures and timeouts (≥5 seconds)
- **Total**: Total connection attempts

## Configuration

- **Timeout**: Default socket timeout is 5 seconds (configurable in main function)
- **Sleep Interval**: 2 seconds between connection test cycles
- **Report Interval**: 5 minutes between statistics reports
- **Log Files**: Daily log files with format `tcp_stats_YYYYMMDD.log`
- **Host Configuration**: Each host requires hostname, port, and service
- **Threading**: Uses daemon threads for monitoring and statistics collection

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

## Current Configuration

The script is currently configured to monitor:
- promotion-api (promotion-api.raprod.acs.dnacloud.fi:443)
- total-commander-api (x754686ncl-vpce-0e6f57fcc39b0622c.execute-api.eu-west-1.amazonaws.com:443)
- monokkeli (monokkeli.dna.fi:443)
- monokkeli (monokkeli.dna.fi:443)