#!/usr/bin/env python3
"""
Script di monitoraggio automatico per decreto con notifiche.
Può essere eseguito tramite cron job per monitoraggio continuo.
"""

import json
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

class DecretoAutoMonitor:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.log_file = self.script_dir / "decreto_monitor.log"
        
    def log_message(self, message: str):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + "\n")
    
    def should_run_check(self) -> bool:
        """Determine if we should run a check based on last run time."""
        
        try:
            with open('decreto_status_tracking.json', 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
            
            last_updated = tracking_data.get('last_updated')
            if not last_updated:
                return True
            
            last_update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00').replace('+00:00', ''))
            time_since_last = datetime.now() - last_update_time
            
            # Run check if more than 6 hours since last update
            return time_since_last > timedelta(hours=6)
            
        except (FileNotFoundError, KeyError, ValueError):
            return True
    
    def run_decreto_sync(self) -> dict:
        """Run the decreto sync script and return results."""
        
        try:
            # Run the decreto_notion_sync.py script
            result = subprocess.run(
                [sys.executable, 'decreto_notion_sync.py'],
                capture_output=True,
                text=True,
                cwd=self.script_dir,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                self.log_message("✅ Decreto sync completed successfully")
                
                # Try to find the latest report file
                report_files = list(self.script_dir.glob("decreto_sync_report_*.json"))
                if report_files:
                    latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
                    
                    with open(latest_report, 'r', encoding='utf-8') as f:
                        return json.load(f)
                
                return {'status': 'completed', 'found_published': 0}
            else:
                self.log_message(f"❌ Decreto sync failed: {result.stderr}")
                return {'status': 'error', 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            self.log_message("⏰ Decreto sync timed out after 10 minutes")
            return {'status': 'timeout'}
        except Exception as e:
            self.log_message(f"💥 Unexpected error: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def send_notification(self, results: dict):
        """Send notification if new publications found."""
        
        if results.get('found_published', 0) > 0:
            self.log_message(f"🎉 NOTIFICATION: {results['found_published']} new publications found!")
            
            # Create notification summary
            notification_summary = {
                'timestamp': datetime.now().isoformat(),
                'type': 'new_publications',
                'count': results['found_published'],
                'notion_updated': results.get('notion_updated', 0),
                'deliberations': results.get('newly_published', [])
            }
            
            # Save notification log
            notification_file = self.script_dir / "decreto_notifications.jsonl"
            with open(notification_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(notification_summary) + "\n")
            
            # Log details
            for pub in results.get('newly_published', [])[:5]:  # Show first 5
                self.log_message(f"   📄 DGR {pub['numero']}: {pub['oggetto'][:50]}...")
            
            return True
        
        return False
    
    def generate_daily_summary(self):
        """Generate a daily summary of monitoring activity."""
        
        today = datetime.now().date()
        daily_logs = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip() and str(today) in line:
                        daily_logs.append(line.strip())
        except FileNotFoundError:
            pass
        
        if daily_logs:
            self.log_message(f"📊 Daily summary: {len(daily_logs)} log entries today")
            
            # Count different types of activities
            checks_run = sum(1 for log in daily_logs if "sync completed" in log)
            publications_found = sum(1 for log in daily_logs if "new publications found" in log)
            
            summary = {
                'date': str(today),
                'total_logs': len(daily_logs),
                'checks_run': checks_run,
                'publications_found': publications_found,
                'latest_activity': daily_logs[-1] if daily_logs else None
            }
            
            # Save daily summary
            summary_file = self.script_dir / f"daily_summary_{today.strftime('%Y%m%d')}.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            return summary
        
        return None
    
    def cleanup_old_files(self, days_to_keep: int = 30):
        """Clean up old report and log files."""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned_count = 0
        
        # Clean up old sync reports
        for report_file in self.script_dir.glob("decreto_sync_report_*.json"):
            if report_file.stat().st_mtime < cutoff_date.timestamp():
                report_file.unlink()
                cleaned_count += 1
        
        # Clean up old daily summaries
        for summary_file in self.script_dir.glob("daily_summary_*.json"):
            if summary_file.stat().st_mtime < cutoff_date.timestamp():
                summary_file.unlink()
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.log_message(f"🧹 Cleaned up {cleaned_count} old files")
    
    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle."""
        
        self.log_message("🚀 Starting decreto auto-monitoring cycle")
        
        # Check if we should run
        if not self.should_run_check():
            self.log_message("⏭️ Skipping check - too soon since last update")
            return
        
        # Run decreto sync
        self.log_message("🔍 Running decreto sync...")
        results = self.run_decreto_sync()
        
        if results.get('status') == 'error':
            self.log_message(f"❌ Monitoring failed: {results.get('error', 'Unknown error')}")
            return
        elif results.get('status') == 'timeout':
            self.log_message("⏰ Monitoring timed out")
            return
        
        # Send notifications if needed
        notification_sent = self.send_notification(results)
        
        # Log results
        checked = results.get('checked', 0)
        found = results.get('found_published', 0)
        notion_updated = results.get('notion_updated', 0)
        
        self.log_message(f"📊 Results: {checked} checked, {found} published, {notion_updated} Notion updated")
        
        if notification_sent:
            self.log_message("📧 Notification sent for new publications")
        
        # Clean up old files periodically
        if datetime.now().hour == 2:  # Run cleanup at 2 AM
            self.cleanup_old_files()
        
        self.log_message("✅ Monitoring cycle completed")
    
    def show_status(self):
        """Show current monitoring status."""
        
        print("📊 DECRETO MONITORING STATUS")
        print("=" * 40)
        
        # Check last run
        try:
            with open('decreto_status_tracking.json', 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
            
            last_updated = tracking_data.get('last_updated')
            total_deliberations = tracking_data.get('total_deliberations', 0)
            
            print(f"Total deliberations tracked: {total_deliberations}")
            print(f"Last update: {last_updated}")
            
            # Count statuses
            statuses = {}
            for key, data in tracking_data.get('decreto_status', {}).items():
                status = data.get('decreto_publication', {}).get('status', 'unknown')
                statuses[status] = statuses.get(status, 0) + 1
            
            print("\nStatus breakdown:")
            for status, count in statuses.items():
                print(f"  {status}: {count}")
            
        except FileNotFoundError:
            print("❌ No tracking data found")
        
        # Show recent notifications
        notification_file = self.script_dir / "decreto_notifications.jsonl"
        if notification_file.exists():
            print("\n📧 Recent notifications:")
            with open(notification_file, 'r', encoding='utf-8') as f:
                notifications = [json.loads(line) for line in f if line.strip()]
            
            for notif in notifications[-3:]:  # Show last 3
                timestamp = notif['timestamp'][:19].replace('T', ' ')
                count = notif['count']
                print(f"  {timestamp}: {count} new publications")
        
        # Show log file size and recent activity
        if self.log_file.exists():
            log_size = self.log_file.stat().st_size / 1024  # KB
            print(f"\nLog file size: {log_size:.1f} KB")
            
            # Show last few log entries
            print("\nRecent activity:")
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
            
            for log in logs[-5:]:  # Show last 5 entries
                print(f"  {log.strip()}")

def main():
    """Main entry point for auto-monitoring."""
    
    monitor = DecretoAutoMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            monitor.show_status()
        elif command == "force":
            print("🔧 Forcing decreto sync run...")
            monitor.log_message("🔧 Manual force run requested")
            results = monitor.run_decreto_sync()
            monitor.send_notification(results)
        elif command == "summary":
            summary = monitor.generate_daily_summary()
            if summary:
                print("📊 Daily Summary Generated")
                print(json.dumps(summary, indent=2))
            else:
                print("📭 No activity today")
        else:
            print("Usage: python3 decreto_auto_monitor.py [status|force|summary]")
    else:
        # Normal monitoring cycle
        monitor.run_monitoring_cycle()

if __name__ == "__main__":
    main()