"""
Notion Integrator for ODG Liguria Workflow.
Handles bidirectional sync with Notion database for deliberations.
"""

import logging
import time
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from notion_client import Client
from notion_client.errors import APIErrorCode, APIResponseError


class SyncDirection(Enum):
    """Sync direction options."""
    TO_NOTION = "to_notion"
    FROM_NOTION = "from_notion"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class DeliberationFlags:
    """Auto-generated flags for deliberations."""
    budget_alto: bool = False
    urgente: bool = False
    governance: bool = False
    sanita: bool = False
    ambiente: bool = False
    sociale: bool = False
    personale: bool = False
    
    def to_dict(self) -> Dict[str, bool]:
        """Convert flags to dictionary."""
        return {
            'Budget Alto': self.budget_alto,
            'Urgente': self.urgente,
            'Governance': self.governance,
            'Sanità': self.sanita,
            'Ambiente': self.ambiente,
            'Sociale': self.sociale,
            'Personale': self.personale
        }


@dataclass
class NotionPage:
    """Notion page representation."""
    page_id: str
    title: str
    properties: Dict[str, Any]
    last_edited: datetime
    
    def __post_init__(self):
        if isinstance(self.last_edited, str):
            self.last_edited = datetime.fromisoformat(self.last_edited.replace('Z', '+00:00'))


class NotionIntegrator:
    """Integrator for Notion database sync."""
    
    def __init__(self, token: str, database_id: str, rate_limit: float = 0.33):
        """
        Initialize Notion integrator.
        
        Args:
            token: Notion API token
            database_id: Database ID for deliberations
            rate_limit: Minimum seconds between API calls (3 requests/second max)
        """
        self.client = Client(auth=token)
        self.database_id = database_id
        self.rate_limit = rate_limit
        self.last_request_time = 0
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Database schema
        self.database_schema = {
            "Seduta": {"type": "number"},
            "Numero": {"type": "number"},
            "Oggetto": {"type": "rich_text"},
            "Proponente": {"type": "rich_text"},
            "FS": {"type": "checkbox"},
            "Pubblicato": {"type": "checkbox"},
            "Sintesi_Rapida": {"type": "rich_text"},
            "URL_Decreto": {"type": "url"},
            "Categoria": {"type": "select"},
            "Data_Seduta": {"type": "date"},
            "Data_Pubblicazione": {"type": "date"},
            "Note": {"type": "rich_text"},
            "Budget": {"type": "rich_text"},
            "Urgenza": {"type": "select"},
            "Stakeholder": {"type": "multi_select"},
            "Keywords": {"type": "multi_select"},
            "Stato_Sync": {"type": "select"},
            "Ultimo_Update": {"type": "date"},
            # Auto-generated flags
            "Budget Alto": {"type": "checkbox"},
            "Urgente": {"type": "checkbox"},
            "Governance": {"type": "checkbox"},
            "Sanità": {"type": "checkbox"},
            "Ambiente": {"type": "checkbox"},
            "Sociale": {"type": "checkbox"},
            "Personale": {"type": "checkbox"}
        }
        
        # Flag generation patterns
        self.flag_patterns = {
            'budget_alto': [
                r'(?:\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:euro|€)',
                r'(?:budget|bilancio|stanziamento|finanziamento).{0,50}(?:\d{1,3}(?:\.\d{3})*)',
                r'(?:milioni|mila|migliaia).{0,20}(?:euro|€)',
                r'(?:costo|spesa|importo).{0,50}(?:\d{1,3}(?:\.\d{3})*)'
            ],
            'urgente': [
                r'(?:urgente|urgenza|immediato|straordinario)',
                r'(?:fuori sacco|FS)',
                r'(?:emergenza|eccezionale|tempestivo)',
                r'(?:scadenza|termine|proroga)'
            ],
            'governance': [
                r'(?:nomina|incarico|delega|rappresentante)',
                r'(?:consiglio|commissione|comitato)',
                r'(?:direttore|presidente|amministratore)',
                r'(?:governance|amministrazione|gestione)'
            ],
            'sanita': [
                r'(?:sanità|sanitario|salute|medico)',
                r'(?:ospedale|asl|policlinico|arpal)',
                r'(?:terapia|diagnosi|cura|paziente)',
                r'(?:farmaceutico|sanitaria|prevenzione)'
            ],
            'ambiente': [
                r'(?:ambiente|ambientale|ecologia)',
                r'(?:inquinamento|rifiuti|sostenibilità)',
                r'(?:verde|parco|natura|protezione)',
                r'(?:clima|energia|rinnovabile|emissioni)'
            ],
            'sociale': [
                r'(?:sociale|assistenza|welfare)',
                r'(?:famiglia|minori|anziani|disabili)',
                r'(?:inclusione|integrazione|servizi)',
                r'(?:sostegno|aiuto|supporto)'
            ],
            'personale': [
                r'(?:personale|dipendente|lavoratore)',
                r'(?:assunzione|contratto|concorso)',
                r'(?:stipendio|retribuzione|indennità)',
                r'(?:ferie|permessi|malattia)'
            ]
        }
        
        self.logger.info(f"NotionIntegrator initialized with database: {database_id}")
    
    def setup_logging(self) -> None:
        """Setup logging configuration."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _rate_limit(self) -> None:
        """Apply rate limiting for Notion API."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_notion_request(self, operation: str, **kwargs) -> Any:
        """Make rate-limited Notion API request with error handling."""
        self._rate_limit()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if operation == 'query_database':
                    return self.client.databases.query(**kwargs)
                elif operation == 'retrieve_database':
                    return self.client.databases.retrieve(**kwargs)
                elif operation == 'update_database':
                    return self.client.databases.update(**kwargs)
                elif operation == 'create_page':
                    return self.client.pages.create(**kwargs)
                elif operation == 'update_page':
                    return self.client.pages.update(**kwargs)
                elif operation == 'retrieve_page':
                    return self.client.pages.retrieve(**kwargs)
                else:
                    raise ValueError(f"Unknown operation: {operation}")
                    
            except APIResponseError as e:
                if e.code == APIErrorCode.RateLimited:
                    # Exponential backoff for rate limiting
                    retry_after = getattr(e, 'retry_after', 2 ** attempt)
                    self.logger.warning(f"Rate limited, retrying after {retry_after}s")
                    time.sleep(retry_after)
                elif attempt < max_retries - 1:
                    self.logger.warning(f"API error (attempt {attempt + 1}): {e}")
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"API error after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Unexpected error (attempt {attempt + 1}): {e}")
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"Unexpected error after {max_retries} attempts: {e}")
                    raise
        
        raise RuntimeError(f"Failed to complete {operation} after {max_retries} attempts")
    
    def create_or_update_database(self) -> bool:
        """
        Create or update the Notion database schema.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Creating or updating database schema")
            
            # Check if database exists and get current schema
            try:
                current_db = self._make_notion_request(
                    'retrieve_database',
                    database_id=self.database_id
                )
                self.logger.info("Database exists, checking schema")
                
                # Compare and update schema if needed
                return self._update_database_schema(current_db)
                
            except APIResponseError as e:
                if e.code == APIErrorCode.ObjectNotFound:
                    self.logger.error("Database not found. Please create it manually in Notion.")
                    return False
                else:
                    raise
                    
        except Exception as e:
            self.logger.error(f"Error creating/updating database: {str(e)}")
            return False
    
    def _update_database_schema(self, current_db: Dict) -> bool:
        """Update database schema with missing properties."""
        try:
            current_properties = current_db.get('properties', {})
            updates_needed = {}
            
            for prop_name, prop_config in self.database_schema.items():
                if prop_name not in current_properties:
                    self.logger.info(f"Adding missing property: {prop_name}")
                    updates_needed[prop_name] = self._create_property_config(prop_config)
            
            if updates_needed:
                self.logger.info(f"Updating database with {len(updates_needed)} new properties")
                
                self._make_notion_request(
                    'update_database',
                    database_id=self.database_id,
                    properties=updates_needed
                )
                
                self.logger.info("Database schema updated successfully")
            else:
                self.logger.info("Database schema is up to date")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating database schema: {str(e)}")
            return False
    
    def _create_property_config(self, prop_config: Dict) -> Dict:
        """Create Notion property configuration."""
        prop_type = prop_config['type']
        
        if prop_type == 'number':
            return {"number": {}}
        elif prop_type == 'rich_text':
            return {"rich_text": {}}
        elif prop_type == 'checkbox':
            return {"checkbox": {}}
        elif prop_type == 'url':
            return {"url": {}}
        elif prop_type == 'date':
            return {"date": {}}
        elif prop_type == 'select':
            return {
                "select": {
                    "options": self._get_select_options(prop_config.get('name', ''))
                }
            }
        elif prop_type == 'multi_select':
            return {
                "multi_select": {
                    "options": self._get_multiselect_options(prop_config.get('name', ''))
                }
            }
        else:
            return {"rich_text": {}}  # Default fallback
    
    def _get_select_options(self, property_name: str) -> List[Dict]:
        """Get select options for specific properties."""
        if property_name == 'Categoria':
            return [
                {"name": "Sanità", "color": "red"},
                {"name": "Bilanci", "color": "green"},
                {"name": "Governance", "color": "blue"},
                {"name": "Ambiente", "color": "yellow"},
                {"name": "Sociale", "color": "purple"},
                {"name": "Altro", "color": "gray"}
            ]
        elif property_name == 'Urgenza':
            return [
                {"name": "Bassa", "color": "green"},
                {"name": "Normale", "color": "yellow"},
                {"name": "Alta", "color": "red"}
            ]
        elif property_name == 'Stato_Sync':
            return [
                {"name": "Sincronizzato", "color": "green"},
                {"name": "Aggiornato", "color": "blue"},
                {"name": "Errore", "color": "red"}
            ]
        else:
            return []
    
    def _get_multiselect_options(self, property_name: str) -> List[Dict]:
        """Get multi-select options for specific properties."""
        if property_name == 'Keywords':
            return [
                {"name": "Budget", "color": "green"},
                {"name": "Personale", "color": "blue"},
                {"name": "Appalti", "color": "yellow"},
                {"name": "Autorizzazioni", "color": "purple"}
            ]
        elif property_name == 'Stakeholder':
            return [
                {"name": "ASL", "color": "red"},
                {"name": "Ospedale", "color": "blue"},
                {"name": "Comune", "color": "green"},
                {"name": "Provincia", "color": "yellow"}
            ]
        else:
            return []
    
    def sync_deliberations(self, deliberations: List[Dict], 
                          direction: SyncDirection = SyncDirection.TO_NOTION) -> Dict[str, int]:
        """
        Sync deliberations with Notion database.
        
        Args:
            deliberations: List of deliberation dictionaries
            direction: Sync direction
            
        Returns:
            Dictionary with sync statistics
        """
        stats = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            self.logger.info(f"Starting sync of {len(deliberations)} deliberations ({direction.value})")
            
            if direction in [SyncDirection.TO_NOTION, SyncDirection.BIDIRECTIONAL]:
                stats = self._sync_to_notion(deliberations, stats)
            
            if direction in [SyncDirection.FROM_NOTION, SyncDirection.BIDIRECTIONAL]:
                stats = self._sync_from_notion(deliberations, stats)
            
            self.logger.info(f"Sync completed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error during sync: {str(e)}")
            stats['errors'] += 1
            return stats
    
    def _sync_to_notion(self, deliberations: List[Dict], stats: Dict[str, int]) -> Dict[str, int]:
        """Sync deliberations to Notion."""
        # Get existing pages to avoid duplicates
        existing_pages = self._get_existing_pages()
        
        for deliberation in deliberations:
            try:
                # Check if page already exists
                existing_page = self._find_existing_page(deliberation, existing_pages)
                
                if existing_page:
                    # Update existing page
                    if self._update_notion_page(existing_page, deliberation):
                        stats['updated'] += 1
                    else:
                        stats['skipped'] += 1
                else:
                    # Create new page
                    if self._create_notion_page(deliberation):
                        stats['created'] += 1
                    else:
                        stats['errors'] += 1
                        
            except Exception as e:
                self.logger.error(f"Error syncing deliberation {deliberation.get('numero', 'N/A')}: {str(e)}")
                stats['errors'] += 1
        
        return stats
    
    def _sync_from_notion(self, deliberations: List[Dict], stats: Dict[str, int]) -> Dict[str, int]:
        """Sync deliberations from Notion (placeholder for future implementation)."""
        self.logger.info("Sync from Notion not yet implemented")
        return stats
    
    def _get_existing_pages(self) -> List[NotionPage]:
        """Get all existing pages from the database."""
        try:
            pages = []
            has_more = True
            next_cursor = None
            
            while has_more:
                query_params = {
                    'database_id': self.database_id,
                    'page_size': 100
                }
                
                if next_cursor:
                    query_params['start_cursor'] = next_cursor
                
                response = self._make_notion_request('query_database', **query_params)
                
                for page in response['results']:
                    pages.append(NotionPage(
                        page_id=page['id'],
                        title=self._extract_title(page),
                        properties=page['properties'],
                        last_edited=page['last_edited_time']
                    ))
                
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
            
            self.logger.info(f"Found {len(pages)} existing pages")
            return pages
            
        except Exception as e:
            self.logger.error(f"Error getting existing pages: {str(e)}")
            return []
    
    def _find_existing_page(self, deliberation: Dict, existing_pages: List[NotionPage]) -> Optional[NotionPage]:
        """Find existing page for a deliberation."""
        seduta = deliberation.get('seduta')
        numero = deliberation.get('numero')
        
        if not seduta or not numero:
            return None
        
        for page in existing_pages:
            try:
                page_seduta = self._extract_property_value(page.properties, 'Seduta', 'number')
                page_numero = self._extract_property_value(page.properties, 'Numero', 'number')
                
                if page_seduta == seduta and page_numero == numero:
                    return page
            except Exception:
                continue
        
        return None
    
    def _create_notion_page(self, deliberation: Dict) -> bool:
        """Create a new Notion page for deliberation."""
        try:
            # Generate flags
            flags = self._generate_flags(deliberation)
            
            # Build properties
            properties = self._build_page_properties(deliberation, flags)
            
            # Create page
            self._make_notion_request(
                'create_page',
                parent={'database_id': self.database_id},
                properties=properties
            )
            
            self.logger.debug(f"Created page for deliberation {deliberation.get('numero', 'N/A')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating page: {str(e)}")
            return False
    
    def _update_notion_page(self, page: NotionPage, deliberation: Dict) -> bool:
        """Update existing Notion page."""
        try:
            # Generate flags
            flags = self._generate_flags(deliberation)
            
            # Build properties
            properties = self._build_page_properties(deliberation, flags)
            
            # Update page
            self._make_notion_request(
                'update_page',
                page_id=page.page_id,
                properties=properties
            )
            
            self.logger.debug(f"Updated page for deliberation {deliberation.get('numero', 'N/A')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating page: {str(e)}")
            return False
    
    def _build_page_properties(self, deliberation: Dict, flags: DeliberationFlags) -> Dict:
        """Build Notion page properties from deliberation data."""
        properties = {}
        
        # Basic properties
        if 'seduta' in deliberation:
            properties['Seduta'] = {'number': int(deliberation['seduta'])}
        
        if 'numero' in deliberation:
            properties['Numero'] = {'number': int(deliberation['numero'])}
        
        if 'oggetto' in deliberation:
            properties['Oggetto'] = {
                'rich_text': [{'text': {'content': deliberation['oggetto'][:2000]}}]
            }
        
        if 'proponente' in deliberation:
            properties['Proponente'] = {
                'rich_text': [{'text': {'content': deliberation['proponente'][:2000]}}]
            }
        
        if 'fs_flag' in deliberation:
            properties['FS'] = {'checkbox': deliberation['fs_flag']}
        
        # Additional properties from extracted info
        if 'extracted_info' in deliberation:
            info = deliberation['extracted_info']
            
            if hasattr(info, 'category'):
                properties['Categoria'] = {'select': {'name': info.category.value.title()}}
            
            if hasattr(info, 'urgency'):
                urgency_map = {'normale': 'Normale', 'alta': 'Alta', 'bassa': 'Bassa'}
                properties['Urgenza'] = {'select': {'name': urgency_map.get(info.urgency, 'Normale')}}
            
            if hasattr(info, 'budget') and info.budget:
                properties['Budget'] = {
                    'rich_text': [{'text': {'content': f"€{info.budget}"}}]
                }
        
        # Synthesis
        if 'sintesi_rapida' in deliberation:
            properties['Sintesi_Rapida'] = {
                'rich_text': [{'text': {'content': deliberation['sintesi_rapida'][:2000]}}]
            }
        
        # Publication status
        if 'pubblicato' in deliberation:
            properties['Pubblicato'] = {'checkbox': deliberation['pubblicato']}
        
        if 'url_decreto' in deliberation:
            properties['URL_Decreto'] = {'url': deliberation['url_decreto']}
        
        # Publication date
        if 'data_pubblicazione' in deliberation and deliberation['data_pubblicazione']:
            properties['Data_Pubblicazione'] = {'date': {'start': deliberation['data_pubblicazione']}}
        
        # Notes with DGR number
        note_parts = []
        if 'dgr_numero' in deliberation and deliberation['dgr_numero']:
            dgr_anno = deliberation.get('dgr_anno', '')
            if dgr_anno:
                note_parts.append(f"DGR n. {deliberation['dgr_numero']}/{dgr_anno}")
            else:
                note_parts.append(f"DGR n. {deliberation['dgr_numero']}")
        
        if note_parts:
            properties['Note'] = {
                'rich_text': [{'text': {'content': ' | '.join(note_parts)}}]
            }
        
        # Auto-generated flags
        flag_dict = flags.to_dict()
        for flag_name, flag_value in flag_dict.items():
            properties[flag_name] = {'checkbox': flag_value}
        
        # Sync metadata
        properties['Stato_Sync'] = {'select': {'name': 'Sincronizzato'}}
        properties['Ultimo_Update'] = {'date': {'start': datetime.now().isoformat()}}
        
        return properties
    
    def _generate_flags(self, deliberation: Dict) -> DeliberationFlags:
        """Generate auto-flags based on deliberation content."""
        flags = DeliberationFlags()
        
        # Combine text for analysis
        text = ' '.join([
            deliberation.get('oggetto', ''),
            deliberation.get('proponente', ''),
            str(deliberation.get('tipo_atto', ''))
        ]).lower()
        
        # Check each flag pattern
        for flag_name, patterns in self.flag_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    setattr(flags, flag_name, True)
                    break
        
        # Special budget logic
        if flags.budget_alto:
            # More sophisticated budget analysis could be added here
            pass
        
        # Special urgency logic
        if deliberation.get('fs_flag', False):
            flags.urgente = True
        
        return flags
    
    def _extract_title(self, page: Dict) -> str:
        """Extract title from Notion page."""
        try:
            title_prop = page['properties'].get('Oggetto', {})
            if title_prop.get('rich_text'):
                return title_prop['rich_text'][0]['text']['content']
            return f"Deliberazione {page['properties'].get('Numero', {}).get('number', 'N/A')}"
        except Exception:
            return "Untitled"
    
    def _extract_property_value(self, properties: Dict, prop_name: str, prop_type: str) -> Any:
        """Extract property value from Notion page properties."""
        try:
            prop = properties.get(prop_name, {})
            
            if prop_type == 'number':
                return prop.get('number')
            elif prop_type == 'rich_text':
                rich_text = prop.get('rich_text', [])
                if rich_text:
                    return rich_text[0]['text']['content']
                return None
            elif prop_type == 'checkbox':
                return prop.get('checkbox', False)
            elif prop_type == 'select':
                select = prop.get('select')
                return select['name'] if select else None
            elif prop_type == 'date':
                date = prop.get('date')
                return date['start'] if date else None
            else:
                return None
                
        except Exception:
            return None
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """Get sync statistics from database."""
        try:
            # Query database for sync statistics
            response = self._make_notion_request(
                'query_database',
                database_id=self.database_id,
                page_size=1
            )
            
            total_pages = response.get('object') == 'list' and len(response.get('results', []))
            
            return {
                'total_pages': total_pages,
                'database_id': self.database_id,
                'last_sync': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting sync statistics: {str(e)}")
            return {'error': str(e)}


def main():
    """Example usage of NotionIntegrator."""
    import os
    
    # Get credentials from environment
    notion_token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not database_id:
        print("Error: NOTION_TOKEN and NOTION_DATABASE_ID environment variables required")
        return
    
    try:
        integrator = NotionIntegrator(notion_token, database_id)
        
        # Create or update database
        if integrator.create_or_update_database():
            print("Database schema updated successfully")
        else:
            print("Failed to update database schema")
            return
        
        # Example deliberation
        deliberations = [{
            'seduta': '3929',
            'numero': '1',
            'oggetto': 'AZIENDA PUBBLICA DI SERVIZI ALLA PERSONA OPERE PIE RIUNITE DEVOTO MARINI SIVORI',
            'proponente': 'BUCCI Marco',
            'tipo_atto': 'Deliberazione',
            'fs_flag': True,
            'sintesi_rapida': 'Nomina rappresentante regionale in azienda pubblica'
        }]
        
        # Sync deliberations
        stats = integrator.sync_deliberations(deliberations)
        print(f"Sync completed: {stats}")
        
        # Get statistics
        sync_stats = integrator.get_sync_statistics()
        print(f"Database statistics: {sync_stats}")
        
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()