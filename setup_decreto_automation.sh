#!/bin/bash
# Setup script per l'automazione completa del monitoraggio decreto

echo "🚀 SETUP AUTOMAZIONE DECRETO MONITORING"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "decreto_notion_sync.py" ]; then
    echo "❌ Errore: Script deve essere eseguito dalla directory odg-liguria-workflow"
    exit 1
fi

echo "📁 Directory corrente: $(pwd)"

# Make scripts executable
chmod +x decreto_auto_monitor.py
chmod +x decreto_notion_sync.py

echo "✅ Scripts resi eseguibili"

# Create cron job entry (commented out - user can uncomment if needed)
CRON_ENTRY="# Decreto monitoring - runs every 6 hours
# 0 */6 * * * cd $(pwd) && python3 decreto_auto_monitor.py >> decreto_monitor.log 2>&1

# Daily summary at 8 AM
# 0 8 * * * cd $(pwd) && python3 decreto_auto_monitor.py summary >> decreto_monitor.log 2>&1"

echo "📝 Esempio cron job entry:"
echo "$CRON_ENTRY"

# Create the cron suggestion file
echo "$CRON_ENTRY" > decreto_cron_example.txt
echo "💾 Esempio cron salvato in: decreto_cron_example.txt"

# Test the monitoring system
echo ""
echo "🧪 Testing monitoring system..."
python3 decreto_auto_monitor.py status

echo ""
echo "✅ SETUP COMPLETATO!"
echo ""
echo "🎯 COME UTILIZZARE IL SISTEMA:"
echo ""
echo "1. Controllo manuale:"
echo "   python3 decreto_notion_sync.py"
echo ""
echo "2. Monitoraggio automatico:"
echo "   python3 decreto_auto_monitor.py"
echo ""
echo "3. Controllo status:"
echo "   python3 decreto_auto_monitor.py status"
echo ""
echo "4. Forza controllo:"
echo "   python3 decreto_auto_monitor.py force"
echo ""
echo "5. Per automazione completa (opzionale):"
echo "   crontab -e"
echo "   # Aggiungi le righe da decreto_cron_example.txt"
echo ""
echo "📊 Il sistema monitora 50 deliberazioni e aggiorna"
echo "    automaticamente Notion quando vengono pubblicate!"
echo ""
echo "🎉 SISTEMA PRONTO PER L'USO!"