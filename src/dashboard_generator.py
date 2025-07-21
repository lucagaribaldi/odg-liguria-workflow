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

            # Calculate metrics
            metrics = self._calculate_metrics(data)

            # Generate HTML
            html_content = self._generate_html_content(metrics, data)

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

    def _generate_html_content(self, metrics: Dict[str, Any], data: List[Dict]) -> str:
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
        {self._generate_javascript(metrics)}
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

    def _generate_javascript(self, metrics: Dict[str, Any]) -> str:
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
