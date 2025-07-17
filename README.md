# ODG Liguria Workflow

Sistema automatizzato per la gestione del workflow ODG (Ordine del Giorno) della Regione Liguria.

## Descrizione

Questo progetto fornisce un sistema completo per:
- Monitoraggio e processamento automatico delle email
- Gestione dei documenti allegati
- Validazione e trasformazione dei dati
- Generazione di report e output strutturati
- Dashboard di monitoraggio

## Prerequisiti

- Python 3.8+
- pip (Python package manager)
- Git

## Installazione Rapida

### 1. Clona il repository
```bash
git clone <repository-url>
cd odg-liguria-workflow
```

### 2. Setup automatico
```bash
chmod +x setup_environment.sh
./setup_environment.sh
```

### 3. Configura le variabili d'ambiente
```bash
cp .env.example .env
# Modifica .env con i tuoi valori
```

### 4. Configura l'applicazione
```bash
cp config.yaml.example config.yaml
# Modifica config.yaml con le tue impostazioni
```

## Installazione Manuale

### 1. Crea ambiente virtuale
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate     # Windows
```

### 2. Installa dipendenze
```bash
pip install -r requirements.txt
```

### 3. Inizializza il database
```bash
python -m src.database.init_db
```

### 4. Esegui i test
```bash
make test
```

## Utilizzo

### Comandi Make disponibili

```bash
# Installazione e setup
make install          # Installa tutte le dipendenze
make setup           # Setup completo dell'ambiente

# Esecuzione
make run             # Avvia l'applicazione principale
make dashboard       # Avvia la dashboard web

# Testing e Quality Assurance
make test            # Esegui tutti i test
make test-coverage   # Test con coverage report
make lint            # Controllo qualità del codice
make format          # Formatta il codice

# Verifica e manutenzione
make verify          # Verifica completa del sistema
make clean           # Pulisci file temporanei
make backup          # Crea backup dei dati
```

### Avvio dell'applicazione

#### Modalità sviluppo
```bash
make run
```

#### Modalità produzione
```bash
APP_ENV=production make run
```

#### Dashboard web
```bash
make dashboard
```
La dashboard sarà disponibile su `http://localhost:5000`

## Struttura del Progetto

```
odg-liguria-workflow/
├── src/                    # Codice sorgente
│   ├── core/              # Funzionalità core
│   ├── email/             # Gestione email
│   ├── processing/        # Elaborazione documenti
│   ├── database/          # Gestione database
│   ├── dashboard/         # Dashboard web
│   └── utils/             # Utilità
├── data/                  # Dati dell'applicazione
│   ├── input/            # File di input
│   ├── output/           # File di output
│   └── backups/          # Backup
├── tests/                 # Test
├── docs/                  # Documentazione
├── examples/              # Esempi di utilizzo
├── scripts/               # Script di utilità
├── templates/             # Template
└── logs/                  # Log files
```

## Configurazione

### Email
1. Configura le impostazioni IMAP/SMTP in `config.yaml`
2. Per Gmail, genera una password specifica per l'app
3. Imposta le credenziali in `.env`

### Database
Il sistema utilizza SQLite per default. Per cambiare database:
1. Modifica la sezione `database` in `config.yaml`
2. Installa i driver necessari
3. Aggiorna `DATABASE_URL` in `.env`

### Logging
I log sono salvati in `logs/odg_workflow.log` per default.
Personalizza il livello di log in `config.yaml`.

## Monitoraggio

### Dashboard
- **URL**: `http://localhost:5000`
- **Funzionalità**: 
  - Stato del sistema
  - Metriche di performance
  - Log in tempo reale
  - Gestione workflow

### Logging
- File di log: `logs/odg_workflow.log`
- Livelli: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Rotazione automatica dei log

## Troubleshooting

### Problemi comuni

#### Errore connessione email
```bash
# Verifica credenziali
make verify

# Controlla configurazione
cat config.yaml | grep -A 10 email
```

#### Errore database
```bash
# Reinizializza database
python -m src.database.init_db --reset

# Controlla permessi
ls -la data/
```

#### Errore dipendenze
```bash
# Reinstalla dipendenze
make clean
make install
```

### Log e debugging
```bash
# Visualizza log in tempo reale
tail -f logs/odg_workflow.log

# Esegui in modalità debug
APP_DEBUG=true make run
```

## Sviluppo

### Setup ambiente di sviluppo
```bash
# Installa dipendenze development
pip install -r requirements.txt

# Installa pre-commit hooks
pre-commit install

# Esegui test
make test
```

### Contribuire
1. Fork del repository
2. Crea un branch per la feature
3. Scrivi test per il nuovo codice
4. Esegui `make verify` prima del commit
5. Crea una Pull Request

## Sicurezza

- Non committare mai file `config.yaml` o `.env`
- Usa password specifiche per app per email
- Abilita cifratura per dati sensibili
- Controlla regolarmente i log per attività sospette

## Licenza

[Specificare la licenza]

## Supporto

Per supporto tecnico:
- Consulta la documentazione in `docs/`
- Controlla i log in `logs/`
- Apri un issue su GitHub

## Changelog

### v1.0.0
- Implementazione iniziale
- Gestione email IMAP/SMTP
- Processamento documenti
- Dashboard web
- Sistema di logging