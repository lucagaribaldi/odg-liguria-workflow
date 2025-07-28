"""
Dashboard Generator for ODG Liguria Workflow Analytics.
Generates interactive HTML dashboards with metrics and visualizations.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import glob
from collections import Counter, defaultdict

from notion_integrator import NotionIntegrator


class DashboardGenerator:
    """Generator for HTML analytics dashboards."""

    def __init__(
        self,
        notion_token: Optional[str] = None,
        notion_database_id: Optional[str] = None,
        backup_dir: str = "data/backups",
    ):
        """
        Initialize dashboard generator.

        Args:
            notion_token: Optional Notion API token
            notion_database_id: Optional Notion database ID
            backup_dir: Directory containing backup JSON files
        """
        self.backup_dir = Path(backup_dir)
        self.notion_integrator = None

        # Setup Notion integration if credentials provided
        if notion_token and notion_database_id:
            try:
                self.notion_integrator = NotionIntegrator(notion_token, notion_database_id)
            except Exception as e:
                logging.warning(f"Failed to initialize Notion integration: {e}")

        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

        self.logger.info("DashboardGenerator initialized")

    def _load_health_metrics(self) -> List[Dict]:
        """Load health metrics from logs/health_metrics.json."""
        try:
            health_file = Path("logs/health_metrics.json")
            if not health_file.exists():
                self.logger.warning(f"Health metrics file not found: {health_file}")
                return []

            with open(health_file, "r", encoding="utf-8") as f:
                health_data = json.load(f)

            self.logger.info(f"Loaded {len(health_data)} health metrics entries")
            return health_data if isinstance(health_data, list) else []

        except Exception as e:
            self.logger.error(f"Error loading health metrics: {str(e)}")
            return []

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def generate_dashboard_html(
        self, output_path: str = "dashboard.html", data_source: str = "backup"
    ) -> str:
        """
        Generate complete HTML dashboard.

        Args:
            output_path: Path where to save the HTML file
            data_source: Data source ('backup' or 'notion')

        Returns:
            Path to generated HTML file
        """
        try:
            self.logger.info(f"Generating dashboard from {data_source} data")

            # Load data
            if data_source == "notion" and self.notion_integrator:
                data = self._load_data_from_notion()
            else:
                data = self._load_data_from_backup()

            # Load health metrics
            health_data = self._load_health_metrics()

            # Calculate metrics
            metrics = self._calculate_metrics(data)
            health_metrics = self._calculate_health_metrics(health_data)

            # Generate HTML
            html_content = self._generate_html_content(metrics, data, health_metrics)

            # Save to file
            output_path = Path(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            self.logger.info(f"Dashboard generated: {output_path}")
            return str(output_path)

        except Exception as e:
            self.logger.error(f"Error generating dashboard: {str(e)}")
            raise

    def _load_data_from_backup(self) -> List[Dict]:
        """Load data from JSON backup files."""
        try:
            deliberations = []

            # Find all backup JSON files
            backup_files = glob.glob(str(self.backup_dir / "odg_backup_*.json"))

            if not backup_files:
                self.logger.warning("No backup files found")
                return []

            # Load from most recent backup files
            backup_files.sort(key=os.path.getmtime, reverse=True)

            for backup_file in backup_files[:5]:  # Load last 5 backups
                try:
                    with open(backup_file, "r", encoding="utf-8") as f:
                        backup_data = json.load(f)

                    file_deliberations = backup_data.get("deliberations", [])
                    deliberations.extend(file_deliberations)

                    self.logger.debug(
                        f"Loaded {len(file_deliberations)} deliberations from " f"{backup_file}"
                    )

                except Exception as e:
                    self.logger.warning(f"Error loading backup {backup_file}: {e}")
                    continue

            self.logger.info(f"Loaded {len(deliberations)} total deliberations from backups")
            return deliberations

        except Exception as e:
            self.logger.error(f"Error loading data from backup: {str(e)}")
            return []

    def _load_data_from_notion(self) -> List[Dict]:
        """Load data directly from Notion database."""
        try:
            # This would implement direct querying from Notion
            # For now, return empty list as placeholder
            self.logger.info("Loading data from Notion (placeholder)")
            return []

        except Exception as e:
            self.logger.error(f"Error loading data from Notion: {str(e)}")
            return []

    def _calculate_metrics(self, deliberations: List[Dict]) -> Dict[str, Any]:
        """Calculate dashboard metrics from deliberations data."""
        metrics = {
            "total_deliberations": len(deliberations),
            "published_count": 0,
            "publication_rate": 0.0,
            "fs_count": 0,
            "fs_rate": 0.0,
            "categories": Counter(),
            "proponents": Counter(),
            "monthly_distribution": defaultdict(int),
            "recent_publications": [],
            "avg_publication_delay": 0.0,
            "top_categories": [],
            "top_proponents": [],
        }

        if not deliberations:
            return metrics

        publication_delays = []
        recent_cutoff = datetime.now() - timedelta(days=30)

        for delib in deliberations:
            # Publication metrics
            if delib.get("pubblicato", False):
                metrics["published_count"] += 1

                # Calculate publication delay
                data_seduta = delib.get("data_seduta")
                data_pubblicazione = delib.get("data_pubblicazione")

                if data_seduta and data_pubblicazione:
                    try:
                        seduta_date = datetime.strptime(data_seduta, "%Y-%m-%d")
                        pub_date = datetime.strptime(data_pubblicazione, "%Y-%m-%d")
                        delay = (pub_date - seduta_date).days
                        publication_delays.append(delay)

                        # Recent publications
                        if pub_date > recent_cutoff:
                            metrics["recent_publications"].append(
                                {
                                    "numero": delib.get("numero"),
                                    "oggetto": delib.get("oggetto", "")[:100] + "...",
                                    "data_pubblicazione": data_pubblicazione,
                                    "dgr_numero": delib.get("dgr_numero"),
                                    "dgr_anno": delib.get("dgr_anno"),
                                }
                            )
                    except Exception:
                        pass

            # FS metrics
            if delib.get("fs_flag", False):
                metrics["fs_count"] += 1

            # Categories
            if hasattr(delib.get("extracted_info"), "category"):
                category = delib["extracted_info"].category.value
                metrics["categories"][category] += 1
            else:
                # Fallback categorization
                oggetto = delib.get("oggetto", "").lower()
                category = self._categorize_by_keywords(oggetto)
                metrics["categories"][category] += 1

            # Proponents
            proponente = delib.get("proponente", "N/A")
            metrics["proponents"][proponente] += 1

            # Monthly distribution
            data_seduta = delib.get("data_seduta")
            if data_seduta:
                try:
                    month_key = data_seduta[:7]  # YYYY-MM
                    metrics["monthly_distribution"][month_key] += 1
                except Exception:
                    pass

        # Calculate rates
        if metrics["total_deliberations"] > 0:
            metrics["publication_rate"] = (
                metrics["published_count"] / metrics["total_deliberations"]
            ) * 100
            metrics["fs_rate"] = (metrics["fs_count"] / metrics["total_deliberations"]) * 100

        # Average publication delay
        if publication_delays:
            metrics["avg_publication_delay"] = sum(publication_delays) / len(publication_delays)

        # Top categories and proponents
        metrics["top_categories"] = metrics["categories"].most_common(5)
        metrics["top_proponents"] = metrics["proponents"].most_common(5)

        # Sort recent publications
        metrics["recent_publications"].sort(key=lambda x: x["data_pubblicazione"], reverse=True)
        metrics["recent_publications"] = metrics["recent_publications"][:10]

        return metrics

    def _calculate_health_metrics(self, health_data: List[Dict]) -> Dict[str, Any]:
        """Calculate health and SSL metrics from health data."""
        metrics = {
            "site_status": "unknown",
            "ssl_valid": False,
            "ssl_expires_days": None,
            "scraping_success_rate": 0.0,
            "avg_response_time": 0.0,
            "total_ssl_errors": 0,
            "total_http_errors": 0,
            "total_timeout_errors": 0,
            "connection_timeline": [],
            "error_distribution": Counter(),
            "performance_trends": [],
            "site_availability": 0.0,
        }

        if not health_data:
            return metrics

        # Get latest status
        latest_entry = health_data[-1] if health_data else {}
        metrics["site_status"] = latest_entry.get("site_status", "unknown")
        metrics["ssl_valid"] = latest_entry.get("ssl_valid", False)
        metrics["ssl_expires_days"] = latest_entry.get("ssl_expires_days")
        metrics["scraping_success_rate"] = latest_entry.get("scraping_success_rate", 0.0)
        metrics["avg_response_time"] = latest_entry.get("avg_response_time", 0.0)

        # Calculate totals from all entries
        for entry in health_data:
            metrics["total_ssl_errors"] += entry.get("ssl_errors", 0)
            metrics["total_http_errors"] += entry.get("http_errors", 0)
            metrics["total_timeout_errors"] += entry.get("timeout_errors", 0)

            # Connection timeline data
            timestamp = entry.get("timestamp", "")
            response_time = entry.get("response_time_ms", 0)
            if timestamp:
                try:
                    # Parse timestamp and format for chart
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    metrics["connection_timeline"].append({
                        "time": dt.strftime("%H:%M"),
                        "response_time": response_time,
                        "status": entry.get("site_status", "unknown")
                    })
                except Exception:
                    pass

        # Error distribution
        if metrics["total_ssl_errors"] > 0:
            metrics["error_distribution"]["SSL Errors"] = metrics["total_ssl_errors"]
        if metrics["total_http_errors"] > 0:
            metrics["error_distribution"]["HTTP Errors"] = metrics["total_http_errors"]
        if metrics["total_timeout_errors"] > 0:
            metrics["error_distribution"]["Timeout Errors"] = metrics["total_timeout_errors"]

        # Calculate site availability (last 24h)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_entries = []
        for entry in health_data:
            timestamp = entry.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if dt > recent_cutoff:
                        recent_entries.append(entry)
                except Exception:
                    pass

        if recent_entries:
            successful_connections = sum(1 for entry in recent_entries
                                         if entry.get("site_status") != "critical")
            metrics["site_availability"] = (successful_connections / len(recent_entries)) * 100

        # Performance trends (last 10 entries)
        metrics["performance_trends"] = [
            entry.get("avg_response_time", 0)
            for entry in health_data[-10:]
        ]

        return metrics

    def _categorize_by_keywords(self, oggetto: str) -> str:
        """Categorize deliberation by keywords in oggetto."""
        category_keywords = {
            "sanità": ["sanità", "sanitario", "salute", "ospedale", "asl", "medico"],
            "bilanci": ["bilancio", "budget", "finanziario", "euro", "costo", "spesa"],
            "governance": ["nomina", "incarico", "direttore", "presidente", "consiglio"],
            "ambiente": ["ambiente", "ambientale", "ecologia", "rifiuti", "verde"],
            "sociale": ["sociale", "assistenza", "famiglia", "minori", "anziani"],
            "turismo": ["turismo", "turistico", "promozione", "cultura", "eventi"],
            "trasporti": ["trasporti", "mobilità", "traffico", "strada", "ferrovia"],
            "lavoro": ["lavoro", "occupazione", "lavoratore", "formazione"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in oggetto for keyword in keywords):
                return category

        return "altro"

    def _generate_html_content(self, metrics: Dict[str, Any], data: List[Dict], health_metrics: Dict[str, Any]) -> str:
        """Generate complete HTML content for dashboard."""
        return f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ODG Liguria - Dashboard Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏛️ ODG Liguria - Dashboard Analytics</h1>
            <p class="subtitle">
                Monitoraggio deliberazioni e decreti della Regione Liguria
            </p>
            <div class="last-update">
                Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </div>
        </header>

        <div class="metrics-grid">
            {self._generate_metrics_cards(metrics)}
        </div>

        <div class="health-metrics-grid">
            {self._generate_health_metrics_cards(health_metrics)}
        </div>

        <div class="health-charts-grid">
            {self._generate_health_charts(health_metrics)}
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <h3>📊 Distribuzione per Categoria</h3>
                <canvas id="categoryChart"></canvas>
            </div>

            <div class="chart-container">
                <h3>👥 Distribuzione per Proponente</h3>
                <canvas id="proponentChart"></canvas>
            </div>

            <div class="chart-container">
                <h3>📈 Andamento Mensile</h3>
                <canvas id="monthlyChart"></canvas>
            </div>

            <div class="chart-container">
                <h3>✅ Stato Pubblicazione</h3>
                <canvas id="publicationChart"></canvas>
            </div>
        </div>

        <div class="recent-section">
            <h3>🆕 Pubblicazioni Recenti</h3>
            <div class="recent-list">
                {self._generate_recent_publications(metrics['recent_publications'])}
            </div>
        </div>
    </div>

    <script>
        {self._generate_javascript(metrics, health_metrics)}
    </script>
</body>
</html>
"""

    def _get_css_styles(self) -> str:
        """Get CSS styles for the dashboard."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                         Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }

        header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 15px;
        }

        .last-update {
            background: rgba(255,255,255,0.2);
            padding: 8px 15px;
            border-radius: 20px;
            display: inline-block;
            font-size: 0.9rem;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }

        .metric-label {
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .metric-change {
            font-size: 0.8rem;
            margin-top: 5px;
        }

        .positive { color: #10b981; }
        .negative { color: #ef4444; }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }

        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .chart-container h3 {
            margin-bottom: 20px;
            color: #333;
            font-size: 1.3rem;
        }

        .recent-section {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .recent-section h3 {
            margin-bottom: 20px;
            color: #333;
            font-size: 1.3rem;
        }

        .recent-list {
            display: grid;
            gap: 15px;
        }

        .recent-item {
            padding: 15px;
            background: #f8fafc;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }

        .recent-item-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 8px;
        }

        .recent-item-number {
            font-weight: bold;
            color: #667eea;
        }

        .recent-item-date {
            font-size: 0.9rem;
            color: #666;
        }

        .recent-item-title {
            font-size: 0.95rem;
            color: #333;
        }

        .dgr-badge {
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            margin-top: 5px;
        }

        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }

            header h1 {
                font-size: 2rem;
            }

            .charts-grid {
                grid-template-columns: 1fr;
            }

            .metric-value {
                font-size: 2rem;
            }
        }

        .refresh-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.9);
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            color: #666;
            z-index: 1000;
        }

        .health-metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }

        .health-card {
            border-left: 4px solid var(--accent-color, #667eea);
        }

        .health-charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }

        .status-critical { border-left-color: #ef4444 !important; }
        .status-degraded { border-left-color: #f59e0b !important; }
        .status-operational { border-left-color: #10b981 !important; }
        .status-unknown { border-left-color: #6b7280 !important; }
        """

    def _generate_metrics_cards(self, metrics: Dict[str, Any]) -> str:
        """Generate HTML for metrics cards."""
        cards = []

        # Total deliberations
        cards.append(
            f"""
            <div class="metric-card">
                <div class="metric-value">{metrics['total_deliberations']}</div>
                <div class="metric-label">Totale Deliberazioni</div>
            </div>
        """
        )

        # Publication rate
        cards.append(
            f"""
            <div class="metric-card">
                <div class="metric-value">{metrics['publication_rate']:.1f}%</div>
                <div class="metric-label">Tasso Pubblicazione</div>
            </div>
        """
        )

        # FS rate
        cards.append(
            f"""
            <div class="metric-card">
                <div class="metric-value">{metrics['fs_rate']:.1f}%</div>
                <div class="metric-label">Fuori Sacco</div>
            </div>
        """
        )

        # Average publication delay
        cards.append(
            f"""
            <div class="metric-card">
                <div class="metric-value">{metrics['avg_publication_delay']:.1f}</div>
                <div class="metric-label">Giorni Media Pubblicazione</div>
            </div>
        """
        )

        return "\n".join(cards)

    def _generate_health_metrics_cards(self, health_metrics: Dict[str, Any]) -> str:
        """Generate HTML for health metrics cards."""
        cards = []

        # Site Status Card
        status_color = {
            "operational": "#10b981",
            "degraded": "#f59e0b",
            "critical": "#ef4444",
            "unknown": "#6b7280"
        }.get(health_metrics.get("site_status", "unknown"), "#6b7280")

        cards.append(
            f"""
            <div class="metric-card health-card">
                <div class="metric-value" style="color: {status_color}">
                    {health_metrics.get('site_status', 'unknown').upper()}
                </div>
                <div class="metric-label">🌐 Stato Sito</div>
            </div>
        """
        )

        # SSL Status Card
        ssl_color = "#10b981" if health_metrics.get("ssl_valid") else "#ef4444"
        ssl_text = "VALIDO" if health_metrics.get("ssl_valid") else "INVALIDO"

        cards.append(
            f"""
            <div class="metric-card health-card">
                <div class="metric-value" style="color: {ssl_color}">{ssl_text}</div>
                <div class="metric-label">🔒 SSL Status</div>
                <div class="metric-change">
                    Scadenza: {health_metrics.get('ssl_expires_days', 'N/A')} giorni
                </div>
            </div>
        """
        )

        # Scraping Success Rate Card
        success_rate = health_metrics.get("scraping_success_rate", 0.0)
        rate_color = "#10b981" if success_rate > 80 else "#f59e0b" if success_rate > 50 else "#ef4444"

        cards.append(
            f"""
            <div class="metric-card health-card">
                <div class="metric-value" style="color: {rate_color}">{success_rate:.1f}%</div>
                <div class="metric-label">📊 Success Rate Scraping</div>
            </div>
        """
        )

        # Response Time Card
        response_time = health_metrics.get("avg_response_time", 0.0)
        time_color = "#10b981" if response_time < 1000 else "#f59e0b" if response_time < 3000 else "#ef4444"

        cards.append(
            f"""
            <div class="metric-card health-card">
                <div class="metric-value" style="color: {time_color}">{response_time:.0f}ms</div>
                <div class="metric-label">⚡ Tempo Risposta</div>
            </div>
        """
        )

        # Site Availability Card
        availability = health_metrics.get("site_availability", 0.0)
        avail_color = "#10b981" if availability > 95 else "#f59e0b" if availability > 80 else "#ef4444"

        cards.append(
            f"""
            <div class="metric-card health-card">
                <div class="metric-value" style="color: {avail_color}">{availability:.1f}%</div>
                <div class="metric-label">🔗 Disponibilità 24h</div>
            </div>
        """
        )

        # Total Errors Card
        total_errors = (health_metrics.get("total_ssl_errors", 0) +
                        health_metrics.get("total_http_errors", 0) +
                        health_metrics.get("total_timeout_errors", 0))
        error_color = "#10b981" if total_errors == 0 else "#f59e0b" if total_errors < 5 else "#ef4444"

        cards.append(
            f"""
            <div class="metric-card health-card">
                <div class="metric-value" style="color: {error_color}">{total_errors}</div>
                <div class="metric-label">❌ Errori Totali</div>
            </div>
        """
        )

        return "\n".join(cards)

    def _generate_health_charts(self, health_metrics: Dict[str, Any]) -> str:
        """Generate HTML for health monitoring charts."""
        charts = []

        # Success Rate Scraping 24h Chart
        charts.append(
            '''
            <div class="chart-container">
                <h3>📊 Success Rate Scraping 24h</h3>
                <canvas id="scrapingSuccessChart"></canvas>
            </div>
        '''
        )

        # Error Distribution Chart
        charts.append(
            '''
            <div class="chart-container">
                <h3>❌ Distribuzione Errori</h3>
                <canvas id="errorDistributionChart"></canvas>
            </div>
        '''
        )

        # Connection Timeline Chart
        charts.append(
            '''
            <div class=\"chart-container\">
                <h3>🔗 Timeline Connessioni</h3>
                <canvas id=\"connectionTimelineChart\"></canvas>
            </div>
        '''
        )

        # Site Availability Heatmap
        charts.append(
            '''
            <div class=\"chart-container\">
                <h3>🌡️ Heatmap Disponibilità Sito</h3>
                <canvas id=\"availabilityHeatmapChart\"></canvas>
            </div>
        '''
        )

        return "\n".join(charts)

    def _generate_recent_publications(self, publications: List[Dict]) -> str:
        """Generate HTML for recent publications list."""
        if not publications:
            return "<p>Nessuna pubblicazione recente trovata.</p>"

        items = []
        for pub in publications:
            dgr_info = ""
            if pub.get("dgr_numero"):
                dgr_info = f'<span class="dgr-badge">DGR {pub["dgr_numero"]}/{pub.get("dgr_anno", "")}</span>'

            items.append(
                f"""
                <div class="recent-item">
                    <div class="recent-item-header">
                        <span class="recent-item-number">#{pub.get('numero', 'N/A')}</span>
                        <span class="recent-item-date">{pub.get('data_pubblicazione', 'N/A')}</span>
                    </div>
                    <div class="recent-item-title">{pub.get('oggetto', 'N/A')}</div>
                    {dgr_info}
                </div>
            """
            )

        return "\n".join(items)

    def _generate_javascript(self, metrics: Dict[str, Any], health_metrics: Dict[str, Any]) -> str:
        """Generate JavaScript for charts and interactivity."""

        # Prepare data for charts
        category_data = {
            "labels": [cat[0].title() for cat in metrics["top_categories"]],
            "data": [cat[1] for cat in metrics["top_categories"]],
        }

        proponent_data = {
            "labels": [
                prop[0][:20] + "..." if len(prop[0]) > 20 else prop[0]
                for prop in metrics["top_proponents"]
            ],
            "data": [prop[1] for prop in metrics["top_proponents"]],
        }

        monthly_data = {
            "labels": list(metrics["monthly_distribution"].keys()),
            "data": list(metrics["monthly_distribution"].values()),
        }

        publication_data = {
            "labels": ["Pubblicati", "Non Pubblicati"],
            "data": [
                metrics["published_count"],
                metrics["total_deliberations"] - metrics["published_count"],
            ],
        }

        # Prepare health chart data
        error_distribution_data = {
            "labels": list(health_metrics.get("error_distribution", {}).keys()) or ["No Errors"],
            "data": list(health_metrics.get("error_distribution", {}).values()) or [0],
        }

        connection_timeline_data = {
            "labels": [entry.get("time", "") for entry in health_metrics.get("connection_timeline", [])] or ["00:00"],
            "data": [entry.get("response_time", 0) for entry in health_metrics.get("connection_timeline", [])] or [0],
        }

        performance_trends_data = {
            "labels": [f"Check {i+1}" for i in range(len(health_metrics.get("performance_trends", [])))],
            "data": health_metrics.get("performance_trends", [0]),
        }

        return f"""
        // Chart configuration
        Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", ' +
                                      'Roboto, Oxygen, Ubuntu, Cantarell, sans-serif';
        Chart.defaults.color = '#666';

        // Category Chart
        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
        new Chart(categoryCtx, {{
            type: 'doughnut',
            data: {{
                labels: {category_data['labels']},
                datasets: [{{
                    data: {category_data['data']},
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe',
                        '#43e97b', '#fa709a', '#fee140', '#a8edea', '#d299c2'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 20
                        }}
                    }}
                }}
            }}
        }});

        // Proponent Chart
        const proponentCtx = document.getElementById('proponentChart').getContext('2d');
        new Chart(proponentCtx, {{
            type: 'bar',
            data: {{
                labels: {proponent_data['labels']},
                datasets: [{{
                    label: 'Deliberazioni',
                    data: {proponent_data['data']},
                    backgroundColor: '#667eea',
                    borderColor: '#667eea',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // Monthly Chart
        const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');
        new Chart(monthlyCtx, {{
            type: 'line',
            data: {{
                labels: {monthly_data['labels']},
                datasets: [{{
                    label: 'Deliberazioni',
                    data: {monthly_data['data']},
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // Publication Status Chart
        const publicationCtx = document.getElementById('publicationChart').getContext('2d');
        new Chart(publicationCtx, {{
            type: 'pie',
            data: {{
                labels: {publication_data['labels']},
                datasets: [{{
                    data: {publication_data['data']},
                    backgroundColor: ['#10b981', '#ef4444']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 20
                        }}
                    }}
                }}
            }}
        }});

        // Auto-refresh functionality
        let refreshCounter = 30;

        function updateRefreshCounter() {{
            document.querySelector('.refresh-indicator').textContent = `Aggiornamento in ${{refreshCounter}}s`;

            if (refreshCounter <= 0) {{
                location.reload();
            }} else {{
                refreshCounter--;
                setTimeout(updateRefreshCounter, 1000);
            }}
        }}

        // Add refresh indicator
        document.body.insertAdjacentHTML('beforeend', '<div class="refresh-indicator">Aggiornamento in 30s</div>');
        updateRefreshCounter();

        // Health Charts
        
        // Scraping Success Rate Chart
        const scrapingSuccessCtx = document.getElementById('scrapingSuccessChart').getContext('2d');
        new Chart(scrapingSuccessCtx, {{
            type: 'gauge',
            data: {{
                datasets: [{{
                    data: [{health_metrics.get('scraping_success_rate', 0):.1f}, {100 - health_metrics.get('scraping_success_rate', 0):.1f}],
                    backgroundColor: ['#10b981', '#f3f4f6'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                cutout: '70%',
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        enabled: false
                    }}
                }}
            }}
        }});
        
        // Error Distribution Chart
        const errorDistributionCtx = document.getElementById('errorDistributionChart').getContext('2d');
        new Chart(errorDistributionCtx, {{
            type: 'doughnut',
            data: {{
                labels: {error_distribution_data['labels']},
                datasets: [{{
                    data: {error_distribution_data['data']},
                    backgroundColor: ['#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 15
                        }}
                    }}
                }}
            }}
        }});
        
        // Connection Timeline Chart
        const connectionTimelineCtx = document.getElementById('connectionTimelineChart').getContext('2d');
        new Chart(connectionTimelineCtx, {{
            type: 'line',
            data: {{
                labels: {connection_timeline_data['labels']},
                datasets: [{{
                    label: 'Response Time (ms)',
                    data: {connection_timeline_data['data']},
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Response Time (ms)'
                        }}
                    }}
                }}
            }}
        }});
        
        // Site Availability Heatmap Chart (using bar chart as approximation)
        const availabilityHeatmapCtx = document.getElementById('availabilityHeatmapChart').getContext('2d');
        new Chart(availabilityHeatmapCtx, {{
            type: 'bar',
            data: {{
                labels: {performance_trends_data['labels'][:10]},
                datasets: [{{
                    label: 'Performance',
                    data: {performance_trends_data['data'][:10]},
                    backgroundColor: function(context) {{
                        const value = context.parsed.y;
                        if (value < 1000) return '#10b981';
                        if (value < 3000) return '#f59e0b';
                        return '#ef4444';
                    }}
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Response Time (ms)'
                        }}
                    }}
                }}
            }}
        }});

        // Add click handlers for interactive elements
        document.querySelectorAll('.metric-card').forEach(card => {{
            card.addEventListener('click', function() {{
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {{
                    this.style.transform = 'translateY(-5px)';
                }}, 100);
            }});
        }});
        """


def main():
    """Example usage of DashboardGenerator."""
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    try:
        # Initialize dashboard generator
        dashboard = DashboardGenerator(
            notion_token=os.getenv("NOTION_TOKEN"),
            notion_database_id=os.getenv("NOTION_DATABASE_ID"),
            backup_dir="data/backups",
        )

        # Generate dashboard
        output_path = dashboard.generate_dashboard_html(
            output_path="dashboard.html", data_source="backup"
        )

        print(f"Dashboard generated: {output_path}")
        print("Open the file in your browser to view the dashboard.")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
