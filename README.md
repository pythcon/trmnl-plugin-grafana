# TRMNL Grafana Plugin

Display Grafana panels on TRMNL e-ink displays. This plugin is built as a TRMNL Recipe, compatible with the TRMNL marketplace and works with both TRMNL Core (cloud) and BYOS Laravel (self-hosted).

## How It Works

This plugin has two parts:

1. **Liquid Templates** (`src/`) - Define how data is displayed on your TRMNL device
2. **Data Service** (`service/`) - Fetches data from Grafana and makes it available to TRMNL

TRMNL supports two strategies for getting data:

| Strategy | How it works | Best for |
|----------|--------------|----------|
| **Polling** | TRMNL fetches from your API | Public endpoints, serverless |
| **Webhook** | You push data to TRMNL | 🚧 Work in progress |

## Getting Started Options

| Option | Setup | Best For |
|--------|-------|----------|
| **Public Instance** | None - ready to use | Quick setup, most users |
| **Self-Hosted** | Deploy Docker container | Privacy, customization, firewalled Grafana |

The plugin is pre-configured to use our public API at `https://grafana.trmnlplugins.com/api/data`. Just install the plugin and enter your Grafana credentials - no server setup required.

**Note:** To use the public instance, your Grafana must be accessible from the internet. If your Grafana is behind a firewall or on a private network, you'll need to self-host the data service.

## Quick Start

### Using the Public Instance (Recommended)

1. Install the **Grafana Panel** plugin from the TRMNL marketplace
2. Configure with your Grafana details:
   - Grafana URL
   - API Key (service account token)
   - Dashboard UID
   - Panel ID
3. Done! The plugin uses the public API automatically.

### Self-Hosting (Optional)

If you need to self-host (e.g., Grafana behind a firewall):

```bash
# Configure environment
cp .env.example .env
# Edit .env with your Grafana credentials

# Run with Docker
docker-compose up grafana-trmnl-api -d

# Or run directly
pip install -r requirements.txt
python -m service.api
```

Then update your TRMNL plugin's Polling URL to point to your API (e.g., `http(s)://your-server.com/api/data`).

## Supported Panel Types

| Panel Type | Status | Description |
|------------|--------|-------------|
| Stat | ✅ | Single value with optional sparkline |
| Time Series | ✅ | Line charts with multiple series |
| Graph | ✅ | Legacy graph panels |
| Gauge | ✅ | Radial gauge with thresholds |
| Bar Gauge | ✅ | Horizontal bar gauge |
| Bar Chart | ✅ | Vertical bar charts |
| Table | ✅ | Tabular data |
| Polystat | ✅ | Honeycomb status display with ok/warning/critical states |

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GRAFANA_URL` | Yes | - | Base URL of Grafana instance |
| `GRAFANA_API_KEY` | Yes | - | Grafana API key or service account token |
| `DASHBOARD_UID` | Yes | - | UID of the dashboard |
| `PANEL_ID` | Yes | - | ID of the panel to display |
| `TIME_FROM` | No | `now-1h` | Start of time range |
| `TIME_TO` | No | `now` | End of time range |
| `TIMEZONE` | No | `UTC` | Timezone for timestamp display |
| `RATE_LIMIT` | No | - | Max requests per minute per Grafana URL |
| `TRMNL_WEBHOOK_URL` | Webhook only | - | TRMNL webhook URL |
| `INTERVAL` | Webhook only | `300` | Seconds between pushes |
| `API_PORT` | API only | `8080` | Port for API server |

### Getting Grafana API Key

1. Go to Grafana → Administration → Service accounts
2. Create a new service account
3. Create a token with "Viewer" role
4. Copy the token to `GRAFANA_API_KEY`

### Finding Dashboard UID and Panel ID

1. Open your Grafana dashboard
2. The UID is in the URL: `grafana.example.com/d/DASHBOARD_UID/...`
3. Click panel title → "Inspect" → "Panel JSON" to find the panel `id`

## Advanced Configuration

### Label Parameter

For polystat and stat panels that use Prometheus data, the `label` field specifies which Prometheus label to use for display names.

**Example**: If your Prometheus query returns:
```
{service_name="auth-service", instance="host:9090"} 1
```

Set `label` to `service_name` to display "auth-service" instead of the default metric name.

**Common label keys**:
- `name` (default) - Generic name label
- `service_name` - Service identifier
- `job` - Prometheus job name
- `instance` - Target instance

### Variables Parameter

For dashboards using Grafana template variables (like `${datasource}`), provide a JSON object with variable substitutions.

**Finding your datasource UID**:
1. Go to Grafana → Connections → Data sources
2. Click on your datasource
3. The UID is in the URL: `grafana.example.com/connections/datasources/edit/DATASOURCE_UID`

**Example**: If your panel uses `${datasource}` for the datasource:
```json
{"datasource": "your-datasource-uid"}
```

**Common patterns**:
- `{"datasource": "prometheus-uid"}` - Substitute datasource variable
- `{"instance": "server:9090"}` - Substitute instance variable
- `{"datasource": "abc123", "job": "my-job"}` - Multiple variables

**Note**: The plugin will substitute both `${varname}` and `$varname` patterns.

### Timezone Parameter

The `timezone` parameter controls how timestamps are displayed on your TRMNL device. Use standard Linux/IANA timezone names.

**Examples**:
- `America/New_York` - Eastern Time
- `America/Los_Angeles` - Pacific Time
- `Europe/London` - UK Time
- `Asia/Tokyo` - Japan Standard Time
- `UTC` (default) - Coordinated Universal Time

**Finding your timezone**: Run `timedatectl list-timezones` on Linux or see the [IANA timezone list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

### Rate Limiting

Set `RATE_LIMIT` to limit requests per minute per unique Grafana URL. This protects your Grafana instance from excessive API calls.

- If `RATE_LIMIT` is unset or empty, rate limiting is disabled
- The limit applies per Grafana URL, so multiple Grafana instances are tracked separately
- Returns HTTP 429 with `Retry-After` header when limit exceeded

**Example**: `RATE_LIMIT=60` allows 60 requests per minute to each Grafana instance.

## Template Development

Use `trmnlp serve` for local development with live preview:

```bash
trmnlp serve
# Open http://localhost:4567
```

Edit `.trmnlp.yml` to customize test data for previewing templates.

### Template Structure

```
src/
├── full.liquid           # Full screen (800x480)
├── half_horizontal.liquid # Half horizontal (800x240)
├── half_vertical.liquid  # Half vertical (400x480)
├── quadrant.liquid       # Quarter screen (400x240)
├── shared.liquid         # Reusable components
└── settings.yml          # Plugin configuration
```

## Project Structure

```
trmnl-plugin-grafana/
├── src/                    # Liquid templates
├── service/                # Python data service
│   ├── grafana/           # Grafana API client
│   ├── transformers/      # Data transformers
│   ├── api.py             # Flask API (Polling mode)
│   ├── main.py            # Webhook mode entry point
│   ├── config.py          # Configuration
│   └── trmnl.py           # TRMNL webhook client
├── .trmnlp.yml            # Local development config
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Docker Commands

```bash
# API mode (TRMNL polls your endpoint)
docker-compose up grafana-trmnl-api -d

# Webhook mode (push to TRMNL)
docker-compose up grafana-trmnl-webhook -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run API mode locally
python -m service.api

# Run webhook mode once
python -m service.main --once

# Run tests
pip install pytest pytest-cov respx
pytest
```

## Test Routes

The API includes test routes that return demonstration data for each panel type. Useful for testing your TRMNL templates without connecting to Grafana.

```bash
# Get test data for each panel type
curl http://localhost:8080/api/test/stat
curl http://localhost:8080/api/test/gauge
curl http://localhost:8080/api/test/bargauge
curl http://localhost:8080/api/test/polystat
curl http://localhost:8080/api/test/table
curl http://localhost:8080/api/test/timeseries
```

| Route | Description |
|-------|-------------|
| `/api/test/stat` | Single value with color |
| `/api/test/gauge` | Radial gauge with percentage |
| `/api/test/bargauge` | Multiple horizontal bars |
| `/api/test/polystat` | Honeycomb status grid |
| `/api/test/table` | Tabular data with rows/columns |
| `/api/test/timeseries` | Time series chart data |

Aliases also work: `graph` and `barchart` → `timeseries`, `grafana-polystat-panel` → `polystat`

## License

MIT License
