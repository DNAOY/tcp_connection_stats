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
- **Histogram Tracking**: Categorizes connection times into buckets:
  - (0, 100] ms
  - (100, 500] ms
  - (500, 1000] ms
  - (1000, 2000] ms
  - > 2000 ms
- **Daily Log Files**: Writes statistics to daily log files named `tcp_stats_YYYYMMDD.log`
- **Statistics Reporting**: Logs detailed statistics every 5 minutes in tabular format
- **Error Handling**: Tracks failed connections separately
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
The daily log files contain tabular data with the following columns:
```
Timestamp           | Service              | 0-100ms  | 100-500ms | 500-1000ms | 1000-2000ms | >2000ms  | Failed | Total
2025-10-08 14:30:00 | promotion-api        |      125 |        15 |          2 |           0 |        0 |      1 |   143
2025-10-08 14:30:00 | total-commander-api  |       98 |        45 |          0 |           0 |        0 |      0 |   143
2025-10-08 14:30:00 | profile-api          |      140 |         3 |          0 |           0 |        0 |      0 |   143
```

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
- profile-api (profile-api.einstein.dna.fi:443)