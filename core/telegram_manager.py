import asyncio
import os
from datetime import datetime, time
import schedule
from core.telegram_bot import JMoneyTelegramBot
from typing import List, Dict

class TelegramNotificationManager:
    """
    Manages Telegram notifications and scheduling for the JMONEY system.
    """
    
    def __init__(self, bot_token: str = None, chat_id: str = None, output_manager=None):
        """
        Initialize the Telegram notification manager.
        
        Args:
            bot_token: Telegram bot token (defaults to environment variable)
            chat_id: Target chat ID (defaults to environment variable)
            output_manager: OutputManager instance for accessing data
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.output_manager = output_manager
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram bot token and chat ID are required. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file.")
        
        self.bot = JMoneyTelegramBot(self.bot_token, self.chat_id, self.output_manager)
        # Initialize the bot immediately and verify success
        if not self.bot.initialize():
            raise ValueError("Failed to initialize Telegram bot. Check your bot token and network connection.")
        self.setup_schedule()

    def setup_schedule(self):
        """Set up scheduled notifications."""
        # Daily summary at 8:00 AM
        schedule.every().day.at("08:00").do(self.send_daily_summary)
        
        # Market open notification (9:30 AM EST)
        schedule.every().day.at("09:30").do(self.send_market_open_notification)
        
        # Market close summary (4:00 PM EST)  
        schedule.every().day.at("16:00").do(self.send_market_close_summary)

    async def send_signal_notification(self, signal: Dict):
        """
        Send notification for a new trading signal.
        
        Args:
            signal: Dictionary containing signal information
        """
        try:
            self.bot.send_signal_alert(signal)
            print(f"✅ Telegram notification sent for {signal.get('ticker', 'Unknown')} signal")
        except Exception as e:
            print(f"❌ Failed to send Telegram notification: {e}")

    async def send_batch_notifications(self, signals: List[Dict]):
        """
        Send notifications for multiple signals.
        
        Args:
            signals: List of signal dictionaries
        """
        if not signals:
            print("📭 No signals to notify about")
            return
        
        print(f"📱 Sending Telegram notifications for {len(signals)} signals...")
        
        for signal in signals:
            await self.send_signal_notification(signal)
            await asyncio.sleep(1)

    def send_daily_summary(self):
        """Send daily summary (called by scheduler)."""
        asyncio.run(self.bot.send_daily_summary())

    def send_market_open_notification(self):
        """Send market open notification."""
        message = """
🔔 **MARKET OPEN NOTIFICATION**

🇺🇸 **US Markets are now OPEN!**

📊 JMONEY system is actively monitoring for new opportunities...
🎯 Confirmed signals will be sent as they develop

Use `/signals` to view current opportunities.
        """
        
        asyncio.run(self._send_message(message))

    def send_market_close_summary(self):
        """Send market close summary."""
        message = """
🛑 **MARKET CLOSE SUMMARY**

🇺🇸 **US Markets are now CLOSED**

📊 Today's trading session complete
🎯 Bot will continue monitoring overnight developments
📈 Crypto and forex markets remain active

Use `/status` to view system performance.
        """
        
        asyncio.run(self._send_message(message))

    async def _send_message(self, message: str):
        """Helper method to send a simple message."""
        try:
            await self.bot.application.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"❌ Failed to send scheduled message: {e}")

    async def send_system_alert(self, alert_type: str, message: str):
        """
        Send system alerts (errors, warnings, etc.).
        
        Args:
            alert_type: Type of alert ("error", "warning", "info")
            message: Alert message
        """
        icons = {
            "error": "🚨",
            "warning": "⚠️", 
            "info": "ℹ️",
            "success": "✅"
        }
        
        icon = icons.get(alert_type, "📢")
        
        alert_message = f"""
{icon} **SYSTEM ALERT - {alert_type.upper()}**

{message}

🕐 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        try:
            await self.bot.application.bot.send_message(
                chat_id=self.chat_id,
                text=alert_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"❌ Failed to send system alert: {e}")

    def start_bot_background(self):
        """Start the Telegram bot in the background."""
        print("🚀 Starting Telegram bot in background mode...")
        
        import threading
        bot_thread = threading.Thread(target=self.bot.start_bot_polling, daemon=True)
        bot_thread.start()
        
        print("✅ Telegram bot started successfully!")
        return bot_thread

    def run_scheduler(self):
        """Run the notification scheduler."""
        print("⏰ Starting notification scheduler...")
        
        while True:
            schedule.run_pending()
            import time
            time.sleep(60)  # Check every minute

    async def test_notification(self):
        """Send a test notification to verify setup."""
        test_signal = {
            'ticker': 'TEST',
            'strategy': 'ZEN',
            'signal': 'Buy',
            'entry': 100.00,
            'stop_loss': 95.00,
            'tp1': 110.00,
            'tp2': 120.00,
            'technical_score': 9,
            'macro_score': 8,
            'sentiment_score': 7,
            'catalyst': 'Test notification for JMONEY system setup',
            'jmoney_confirmed': True,
            'asset_type': 'test'
        }
        
        print("📧 Sending test notification...")
        await self.send_signal_notification(test_signal)
        print("✅ Test notification sent successfully!")

def create_telegram_manager(output_manager=None) -> TelegramNotificationManager:
    """
    Create and return a TelegramNotificationManager instance.
    
    Args:
        output_manager: OutputManager instance for accessing Google Sheets data
        
    Returns:
        TelegramNotificationManager instance
    """
    try:
        return TelegramNotificationManager(output_manager=output_manager)
    except ValueError as e:
        print(f"❌ Telegram setup error: {e}")
        print("💡 Make sure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in your .env file")
        return None
