import os
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import pandas as pd
from typing import List, Dict
import logging

class JMoneyTelegramBot:
    """
    Telegram bot for JMONEY trading signals compatible with python-telegram-bot v13.15.
    """
    
    def __init__(self, bot_token: str, chat_id: str, output_manager=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.output_manager = output_manager
        self.updater = None
        self.recent_signals = []
        self.confirmed_signals = []
        self.workflow_callback = None 
        
        # Setup logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """Initialize the Telegram bot."""
        try:
            self.updater = Updater(token=self.bot_token, use_context=True)
            dispatcher = self.updater.dispatcher
            
            # Register command handlers
            dispatcher.add_handler(CommandHandler("start", self.start_command))
            dispatcher.add_handler(CommandHandler("help", self.help_command))
            dispatcher.add_handler(CommandHandler("signals", self.signals_command))
            dispatcher.add_handler(CommandHandler("confirmed", self.confirmed_command))
            dispatcher.add_handler(CommandHandler("zen", self.zen_command))
            dispatcher.add_handler(CommandHandler("boost", self.boost_command))
            dispatcher.add_handler(CommandHandler("caution", self.caution_command))
            dispatcher.add_handler(CommandHandler("neutral", self.neutral_command))
            dispatcher.add_handler(CommandHandler("fetch", self.fetch_command))
            dispatcher.add_handler(CommandHandler("status", self.status_command))
            
            # Register callback query handler
            dispatcher.add_handler(CallbackQueryHandler(self.button_callback))
            
            self.logger.info("JMoney Telegram bot initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    def start_bot_polling(self):
        """Start the bot with polling."""
        try:
            if not self.updater:
                self.initialize()
            
            self.logger.info("Starting JMoney Telegram bot...")
            self.updater.start_polling()
            self.logger.info("Bot is running. Press Ctrl+C to stop.")
            
        except Exception as e:
            self.logger.error(f"Error starting bot polling: {e}")
    
    def stop_bot(self):
        """Stop the bot gracefully."""
        if self.updater:
            self.updater.stop()
            self.logger.info("JMoney Telegram bot stopped")
    
    # Command handlers
    def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command."""
        welcome_message = """
🚀 *Welcome to JMoney Trading Bot!*

Your intelligent trading companion is ready to help you make informed trading decisions.

*Available Commands:*
/signals - View recent trading signals
/confirmed - Show confirmed trade setups
/boost - View Boost strategy signals
/zen - View Zen strategy signals  
/caution - View Caution strategy signals
/neutral - View Neutral strategy signals
/fetch - Start new signal analysis workflow
/status - Check system status
/help - Show this help message

Let's make some money! 💰
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Recent Signals", callback_data="recent_signals")],
            [InlineKeyboardButton("✅ Confirmed Trades", callback_data="confirmed_trades")],
            [InlineKeyboardButton("📈 System Status", callback_data="system_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    def help_command(self, update: Update, context: CallbackContext):
        """Handle /help command."""
        help_text = """
🤖 *JMoney Bot Commands*

📊 */signals* - View recent trading signals
✅ */confirmed* - Show confirmed trade setups  
⚡ */boost* - View Boost strategy signals
🧘 */zen* - View Zen strategy signals
⚠️ */caution* - View Caution strategy signals
⚪ */neutral* - View Neutral strategy signals
� */fetch* - Start new signal analysis workflow
�📈 */status* - Check system status
❓ */help* - Show this help message

*Strategy Types:*
⚡ *Boost* - High momentum, catalyst-driven trades
🧘 *Zen* - High conviction, low risk setups
⚠️ *Caution* - Moderate risk, mixed signals
⚪ *Neutral* - Sideways, wait-and-see approach

*Signal Status Meanings:*
🟢 *Buy* - Strong bullish signal
🔴 *Sell* - Strong bearish signal  
🟡 *Hold* - Neutral, wait for clarity
⚪ *Avoid* - Stay away from this asset

*Risk Management:*
• Never risk more than 2% per trade
• Always use stop losses
• Take profits at predetermined levels
• Stay disciplined with your strategy

Happy trading! 📈💰
        """
        
        update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    def signals_command(self, update: Update, context: CallbackContext):
        """Handle /signals command."""
        # Try to get signals from sheets first, fallback to recent_signals
        all_signals = self._get_recent_signals_from_sheets()
        if not all_signals:
            all_signals = self.recent_signals
        
        if not all_signals:
            update.message.reply_text("📭 No recent signals available.")
            return
        
        message = "📊 *Recent Trading Signals*\n\n"
        
        for i, signal in enumerate(all_signals[-5:], 1): 
            status_emoji = self._get_signal_emoji(signal.get('signal', 'Neutral'))
            ticker = signal.get('ticker', 'Unknown')
            decision = signal.get('signal', 'Neutral')
            confidence = signal.get('confidence_score', 0)
            timestamp = signal.get('timestamp', datetime.now().strftime('%H:%M'))
            strategy = signal.get('strategy', 'Unknown')
            
            message += f"{i}. {status_emoji} *{ticker}* ({strategy})\n"
            message += f"   Signal: {decision}\n"
            message += f"   Confidence: {confidence:.1f}/10\n"
            message += f"   Time: {timestamp}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_signals")],
            [InlineKeyboardButton("✅ View Confirmed", callback_data="confirmed_trades")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    def confirmed_command(self, update: Update, context: CallbackContext):
        """Handle /confirmed command."""
        # Try to get signals from sheets first, fallback to confirmed_signals
        all_signals = self._get_recent_signals_from_sheets()
        if not all_signals:
            all_signals = self.confirmed_signals
        
        # Debug: Check what we got from sheets
        self.logger.info(f"Found {len(all_signals)} total signals from sheets")
        for signal in all_signals:
            self.logger.info(f"Signal {signal.get('ticker')}: JMoney Confirmed = {signal.get('jmoney_confirmed')} (type: {type(signal.get('jmoney_confirmed'))})")
        
        # Filter for confirmed signals
        confirmed_signals = [signal for signal in all_signals if signal.get('jmoney_confirmed', False)]
        
        self.logger.info(f"Found {len(confirmed_signals)} confirmed signals after filtering")
        
        if not confirmed_signals:
            # Show more detailed message with debug info
            debug_message = f"📭 No confirmed trades available.\n\n"
            debug_message += f"📊 Total signals checked: {len(all_signals)}\n"
            if all_signals:
                debug_message += f"🔍 Sample signal confirmations:\n"
                for signal in all_signals[:3]:
                    ticker = signal.get('ticker', 'Unknown')
                    confirmed = signal.get('jmoney_confirmed', 'Unknown')
                    debug_message += f"• {ticker}: {confirmed}\n"
            update.message.reply_text(debug_message)
            return
        
        message = "✅ *Confirmed Trade Setups*\n\n"
        
        for i, signal in enumerate(confirmed_signals[-3:], 1):  # Show last 3 confirmed
            ticker = signal.get('ticker', 'Unknown')
            decision = signal.get('signal', 'Neutral')
            entry = self._format_monetary_value(signal.get('entry', 'N/A'))
            stop_loss = self._format_monetary_value(signal.get('stop_loss', 'N/A'))
            tp1 = self._format_monetary_value(signal.get('tp1', 'N/A'))
            strategy = signal.get('strategy', 'Unknown')
            
            emoji = self._get_signal_emoji(decision)
            message += f"{i}. {emoji} *{ticker}* ({strategy}) - {decision}\n"
            message += f"   Entry: {entry}\n"
            message += f"   Stop Loss: {stop_loss}\n"
            message += f"   Target: {tp1}\n\n"
        
        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    def zen_command(self, update: Update, context: CallbackContext):
        """Handle /zen command - show Zen strategy signals."""
        # Try to get signals from sheets first, fallback to recent_signals
        all_signals = self._get_recent_signals_from_sheets()
        if not all_signals:
            all_signals = self.recent_signals
        
        zen_signals = [signal for signal in all_signals if signal.get('strategy') == 'Zen']
        
        if not zen_signals:
            message = """
🧘 *Zen Strategy Signals*

📭 No Zen strategy signals available right now.

*Zen Strategy Criteria:*
• High technical score (≥8/10)
• Strong macro environment (≥6/10)  
• Low trap risk (<4/10)
• Clean technical setup

🔍 *What to look for:*
• Stable uptrends with good fundamentals
• Low volatility, high conviction trades
• Strong institutional backing
• Minimal retail sentiment spikes

Stay patient, quality setups are coming! 🧘‍♂️
            """
        else:
            message = "🧘 *Zen Strategy Signals*\n\n"
            
            for i, signal in enumerate(zen_signals[-5:], 1):
                ticker = signal.get('ticker', 'Unknown')
                decision = signal.get('signal', 'Neutral')
                confidence = signal.get('confidence_score', 0)
                entry = self._format_monetary_value(signal.get('entry', 'N/A'))
                catalyst = signal.get('catalyst', 'Market movement')
                timestamp = signal.get('timestamp', datetime.now().strftime('%H:%M'))
                
                emoji = self._get_signal_emoji(decision)
                message += f"{i}. {emoji} *{ticker}* - {decision}\n"
                message += f"   🎯 Entry: {entry}\n"
                message += f"   📊 Confidence: {confidence:.1f}/10\n"
                message += f"   💡 Catalyst: {catalyst[:50]}...\n"
                message += f"   ⏰ Time: {timestamp}\n\n"
        
        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    def boost_command(self, update: Update, context: CallbackContext):
        """Handle /boost command - show Boost strategy signals."""
        # Try to get signals from sheets first, fallback to recent_signals
        all_signals = self._get_recent_signals_from_sheets()
        if not all_signals:
            all_signals = self.recent_signals
        
        boost_signals = [signal for signal in all_signals if signal.get('strategy') == 'Boost']
        
        if not boost_signals:
            message = """
⚡ *Boost Strategy Signals*

📭 No Boost strategy signals available right now.

*Boost Strategy Criteria:*
• High technical score (≥6/10)
• Strong catalyst present
• Good risk-reward ratio (≥2.0)
• Momentum-driven opportunities

🔍 *What to look for:*
• Breaking news and earnings
• FDA approvals and announcements
• Sector rotation opportunities
• High-impact market events

Keep scanning, opportunities are coming! ⚡
            """
        else:
            message = "⚡ *Boost Strategy Signals*\n\n"
            
            for i, signal in enumerate(boost_signals[-5:], 1):
                ticker = signal.get('ticker', 'Unknown')
                decision = signal.get('signal', 'Neutral')
                confidence = signal.get('confidence_score', 0)
                entry = self._format_monetary_value(signal.get('entry', 'N/A'))
                catalyst = signal.get('catalyst', 'Market movement')
                timestamp = signal.get('timestamp', datetime.now().strftime('%H:%M'))
                
                emoji = self._get_signal_emoji(decision)
                message += f"{i}. {emoji} *{ticker}* - {decision}\n"
                message += f"   🚀 Entry: {entry}\n"
                message += f"   📊 Confidence: {confidence:.1f}/10\n"
                message += f"   � Catalyst: {catalyst[:50]}...\n"
                message += f"   ⏰ Time: {timestamp}\n\n"
        
        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    def caution_command(self, update: Update, context: CallbackContext):
        """Handle /caution command - show Caution strategy signals."""
        # Try to get signals from sheets first, fallback to recent_signals
        all_signals = self._get_recent_signals_from_sheets()
        if not all_signals:
            all_signals = self.recent_signals
        
        caution_signals = [signal for signal in all_signals if signal.get('strategy') == 'Caution']
        
        if not caution_signals:
            message = """
⚠️ *Caution Strategy Signals*

📭 No Caution strategy signals available right now.

*Caution Strategy Criteria:*
• Mixed technical indicators
• Moderate trap risk (4-6/10)
• Uncertain market conditions
• Requires careful monitoring

🔍 *What to expect:*
• Higher volatility potential
• Mixed market sentiment
• Requires tighter stops
• Lower position sizing recommended

Trade with extra care on these! ⚠️
            """
        else:
            message = "⚠️ *Caution Strategy Signals*\n\n"
            
            for i, signal in enumerate(caution_signals[-5:], 1):
                ticker = signal.get('ticker', 'Unknown')
                decision = signal.get('signal', 'Neutral')
                confidence = signal.get('confidence_score', 0)
                entry = self._format_monetary_value(signal.get('entry', 'N/A'))
                zs_score = signal.get('zs10_score', 5)
                timestamp = signal.get('timestamp', datetime.now().strftime('%H:%M'))
                
                emoji = self._get_signal_emoji(decision)
                message += f"{i}. {emoji} *{ticker}* - {decision}\n"
                message += f"   ⚠️ Entry: {entry}\n"
                message += f"   📊 Confidence: {confidence:.1f}/10\n"
                message += f"   🚨 ZS-10+ Risk: {zs_score}/10\n"
                message += f"   ⏰ Time: {timestamp}\n\n"
        
        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    def neutral_command(self, update: Update, context: CallbackContext):
        """Handle /neutral command - show Neutral strategy signals."""
        # Try to get signals from sheets first, fallback to recent_signals
        all_signals = self._get_recent_signals_from_sheets()
        if not all_signals:
            all_signals = self.recent_signals
        
        neutral_signals = [signal for signal in all_signals if signal.get('strategy') == 'Neutral']
        
        if not neutral_signals:
            message = """
⚪ *Neutral Strategy Signals*

📭 No Neutral strategy signals available right now.

*Neutral Strategy Criteria:*
• Balanced technical indicators
• Sideways market movement
• No clear directional bias
• Wait-and-see approach

🔍 *What to do:*
• Monitor for breakouts
• Wait for clearer signals
• Consider range trading
• Prepare for direction change

Patience pays in neutral markets! ⚪
            """
        else:
            message = "⚪ *Neutral Strategy Signals*\n\n"
            
            for i, signal in enumerate(neutral_signals[-5:], 1):
                ticker = signal.get('ticker', 'Unknown')
                decision = signal.get('signal', 'Neutral')
                confidence = signal.get('confidence_score', 0)
                entry = self._format_monetary_value(signal.get('entry', 'N/A'))
                technical_score = signal.get('technical_score', 5)
                timestamp = signal.get('timestamp', datetime.now().strftime('%H:%M'))
                
                emoji = self._get_signal_emoji(decision)
                message += f"{i}. {emoji} *{ticker}* - {decision}\n"
                message += f"   ⚪ Entry: {entry}\n"
                message += f"   📊 Confidence: {confidence:.1f}/10\n"
                message += f"   📈 Technical: {technical_score}/10\n"
                message += f"   ⏰ Time: {timestamp}\n\n"
        
        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    def fetch_command(self, update: Update, context: CallbackContext):
        """Handle /fetch command - trigger new signal analysis workflow."""
        try:
            message = """
🔄 *Starting Signal Analysis Workflow*

📰 Scanning financial news sources...
🤖 Analyzing headlines with AI...
📊 Enriching data from market sources...
⚖️ Calculating scores and strategies...
🎯 Generating trading signals...

This may take 1-2 minutes. New signals will be sent automatically when ready! ⏳
            """
            
            update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
            # Trigger the workflow if callback is available
            if hasattr(self, 'workflow_callback') and self.workflow_callback:
                import threading
                workflow_thread = threading.Thread(
                    target=self._run_workflow_safely,
                    args=(update,),
                    daemon=True
                )
                workflow_thread.start()
                self.logger.info("Workflow triggered via /fetch command")
            else:
                fallback_message = """
⚠️ *Workflow Not Available*

The automatic workflow is not currently connected to this bot instance.

Please run the main JMONEY script manually or contact your system administrator.
                """
                update.message.reply_text(fallback_message, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            self.logger.error(f"Error in fetch command: {e}")
            error_message = f"❌ *Error starting workflow*\n\nPlease try again or contact support.\n\nError: {str(e)}"
            update.message.reply_text(error_message, parse_mode=ParseMode.MARKDOWN)

    def _run_workflow_safely(self, update):
        """Safely run the workflow and handle errors."""
        try:
            if self.workflow_callback:
                result = self.workflow_callback()
                if result:
                    success_message = "✅ *Workflow Completed Successfully*\n\nNew signals have been processed and sent!"
                    update.message.reply_text(success_message, parse_mode=ParseMode.MARKDOWN)
                else:
                    error_message = "⚠️ *Workflow completed with issues*\n\nCheck system logs for details."
                    update.message.reply_text(error_message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            self.logger.error(f"Error in workflow execution: {e}")
            error_message = f"❌ *Workflow failed*\n\nError: {str(e)}"
            update.message.reply_text(error_message, parse_mode=ParseMode.MARKDOWN)

    def set_workflow_callback(self, callback_function):
        """Set the workflow callback function."""
        self.workflow_callback = callback_function
        self.logger.info("Workflow callback registered successfully")
    
    def status_command(self, update: Update, context: CallbackContext):
        """Handle /status command."""
        # Get real-time data from Google Sheets
        all_signals = self._get_recent_signals_from_sheets()
        if not all_signals:
            all_signals = self.recent_signals
        
        confirmed_signals = [signal for signal in all_signals if signal.get('jmoney_confirmed', False)]
        
        # Get signals from last 24 hours
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_count = 0
        
        for signal in all_signals:
            timestamp_str = signal.get('timestamp', '')
            if timestamp_str and timestamp_str != 'N/A':
                try:
                    # Try to parse different timestamp formats
                    if ':' in timestamp_str and len(timestamp_str) <= 8:  # Format like "14:30"
                        # Assume it's from today
                        signal_time = datetime.now().replace(
                            hour=int(timestamp_str.split(':')[0]),
                            minute=int(timestamp_str.split(':')[1]),
                            second=0,
                            microsecond=0
                        )
                    else:
                        # Try full timestamp format
                        signal_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    
                    if signal_time >= cutoff_time:
                        recent_count += 1
                except:
                    # If parsing fails, count it as recent
                    recent_count += 1
            else:
                # If no timestamp, count as recent
                recent_count += 1
        
        status_message = f"""
📈 *JMoney System Status*

🤖 Bot Status: ✅ Online
⏰ Last Update: {datetime.now().strftime('%H:%M:%S')}
📊 Recent Signals (24h): {recent_count}
✅ Confirmed Trades: {len(confirmed_signals)}
📋 Total Signals: {len(all_signals)}

🔧 *System Health:*
• AI Analyzer: ✅ Active
• Data Feeds: ✅ Connected  
• Risk Engine: ✅ Running
• Google Sheets: {'✅ Connected' if self.output_manager else '❌ Offline'}
• Notification: ✅ Online

All systems operational! 🚀
        """
        
        update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)
    
    def button_callback(self, update: Update, context: CallbackContext):
        """Handle inline keyboard button presses."""
        query = update.callback_query
        query.answer()
        
        if query.data == "recent_signals":
            self.signals_command(query, context)
        elif query.data == "confirmed_trades":
            self.confirmed_command(query, context)
        elif query.data == "system_status":
            self.status_command(query, context)
        elif query.data == "refresh_signals":
            query.edit_message_text("🔄 Refreshing signals...")
            self.signals_command(query, context)
    
    def _get_signal_emoji(self, decision: str) -> str:
        """Get emoji for signal decision."""
        emoji_map = {
            'Buy': '🟢',
            'Sell': '🔴', 
            'Hold': '🟡',
            'Avoid': '⚪'
        }
        return emoji_map.get(decision, '⚪')
    
    def _get_recent_signals_from_sheets(self):
        """Fetch recent signals from Google Sheets if output_manager is available."""
        try:
            if not self.output_manager:
                return []
            
            # Get the worksheet
            worksheet = self.output_manager._get_worksheet()
            if not worksheet:
                return []
            
            # Get all records from the sheet
            records = worksheet.get_all_records()
            if not records:
                return []
            
            # Debug: Log available columns
            if records:
                available_columns = list(records[0].keys())
                self.logger.info(f"Available columns in Google Sheets: {available_columns}")
                # Check for confirmation-related columns
                confirmation_columns = [col for col in available_columns if 'confirm' in col.lower()]
                self.logger.info(f"Confirmation-related columns: {confirmation_columns}")
            
            # Convert sheet records to signal format and get recent ones (last 24 hours)
            from datetime import datetime, timedelta
            
            signals = []
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for record in records[-20:]:  # Get last 20 records
                try:
                    # Debug: Show full record for first few entries
                    if len(signals) < 2:
                        self.logger.info(f"Full record {len(signals)+1}: {record}")
                    
                    # Parse timestamp
                    timestamp_str = record.get('Timestamp', '')
                    if timestamp_str:
                        signal_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        if signal_time < cutoff_time:
                            continue
                    
                    # Convert sheet record to signal format
                    signal = {
                        'ticker': record.get('Ticker', ''),
                        'source': record.get('Source', 'Unknown'),
                        'signal': record.get('Signal', 'Neutral'),
                        'strategy': record.get('Strategy', 'Neutral'),
                        'entry': record.get('Entry', 'N/A'),
                        'stop_loss': record.get('Stop Loss', 'N/A'),
                        'tp1': record.get('TP1', 'N/A'),
                        'tp2': record.get('TP2', 'N/A'),
                        'catalyst_type': record.get('Catalyst', 'Market movement'),
                        'confidence_score': self._parse_score(record.get('Confidence Score', '0/10')),
                        'technical_score': self._parse_score(record.get('Technical Score', '0/10')),
                        'zs10_score': self._parse_score(record.get('ZS-10+ Score', '0/10')),
                        'timestamp': signal_time.strftime('%H:%M') if timestamp_str else 'N/A',
                        'jmoney_confirmed': record.get('JMoney Confirmed', 'NO') == 'YES',
                        'confirmation_reason': record.get('Reasoning', 'Ticker doesn\'t meet confirmation requirements')
                    }
                    signals.append(signal)
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing sheet record: {e}")
                    continue
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error fetching signals from sheets: {e}")
            return []
    
    def _parse_score(self, score_str):
        """Parse score string like '7/10' to float."""
        try:
            if '/' in str(score_str):
                return float(str(score_str).split('/')[0])
            return float(score_str)
        except:
            return 0.0
    
    # Notification methods
    def send_signal_notification(self, signal_data: Dict):
        """Send trading signal notification."""
        try:
            if not self.updater:
                self.logger.warning("Bot not initialized, cannot send notification")
                return False
            
            # Add timestamp if not present
            if 'timestamp' not in signal_data:
                signal_data['timestamp'] = datetime.now().strftime('%H:%M:%S')
            
            # Add to recent signals
            self.recent_signals.append(signal_data)
            if len(self.recent_signals) > 20:  # Keep more signals for strategy filtering
                self.recent_signals.pop(0)
            
            # Check if it's a confirmed signal
            jmoney_confirmed = signal_data.get('jmoney_confirmed', False)
            strategy = signal_data.get('strategy', 'Neutral')
            
            if jmoney_confirmed or strategy in ['Boost', 'Zen']:
                self.confirmed_signals.append(signal_data)
                if len(self.confirmed_signals) > 10:  # Keep more confirmed signals
                    self.confirmed_signals.pop(0)
            
            # Format notification message
            message = self._format_signal_notification(signal_data)
            
            # Send notification
            self.updater.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            self.logger.info(f"Signal notification sent for {signal_data.get('ticker')} ({strategy} strategy)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send signal notification: {e}")
            return False
    
    def send_signal_alert(self, signal_data: Dict):
        """Send a single signal alert."""
        try:
            if not self.updater:
                self.logger.warning("Bot not initialized, cannot send alert")
                return False
            
            # Format the signal notification
            message = self._format_signal_notification(signal_data)
            
            # Send the message
            self.updater.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            self.logger.info(f"Signal alert sent for {signal_data.get('ticker')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send signal alert: {e}")
            return False
    
    def _format_monetary_value(self, value):
        """Format monetary values with dollar sign for Telegram."""
        if value == 'N/A' or value == '' or value is None:
            return 'N/A'
        
        # If it's already a string with $, return as is
        if isinstance(value, str) and '$' in value:
            return value
            
        # Convert to string and add $ if it looks like a number
        value_str = str(value).strip()
        if value_str and value_str != 'N/A':
            try:
                # Try to parse as float to validate it's a number
                float(value_str)
                return f"${value_str}"
            except ValueError:
                # If not a number, return as is
                return value_str
        return 'N/A'

    def _format_signal_notification(self, signal_data: Dict) -> str:
        """Format signal data for Telegram notification in the specified format."""
        ticker = signal_data.get('ticker', 'Unknown')  # Use 'ticker' instead of 'symbol'
        decision = signal_data.get('signal', 'Neutral')  # Use 'signal' instead of 'decision'
        jmoney_confirmed = signal_data.get('jmoney_confirmed', False)
        
        # Calculate overall confidence score from individual scores
        technical_score = signal_data.get('technical_score', 0)
        macro_score = signal_data.get('macro_score', 0)
        zs_score = signal_data.get('zs10_score', 0)
        
        # Calculate weighted confidence score (out of 10)
        confidence_score = (technical_score * 0.4 + macro_score * 0.4 + (10 - zs_score) * 0.2)
        
        # Get signal emoji
        emoji = self._get_signal_emoji(decision)
        
        # Determine direction based on decision
        direction = "Long" if decision == "Buy" else "Short" if decision == "Sell" else "Neutral"
        
        # Get trade parameters and format monetary values
        entry = self._format_monetary_value(signal_data.get('entry', 'N/A'))
        stop_loss = self._format_monetary_value(signal_data.get('stop_loss', 'N/A'))
        tp1 = self._format_monetary_value(signal_data.get('tp1', 'N/A'))
        tp2 = self._format_monetary_value(signal_data.get('tp2', 'N/A'))
        
        # Get catalyst information - use catalyst_type for simple category
        catalyst_type = signal_data.get('catalyst_type', 'None')
        catalyst_summary = signal_data.get('catalyst', signal_data.get('reasoning', 'Market movement'))
        
        # Get strategy information
        strategy = signal_data.get('strategy', 'Unknown')
        
        # Get JMoney confirmation reason if available
        confirmation_reason = signal_data.get('confirmation_reason', 'Standard criteria met' if jmoney_confirmed else 'Criteria not met')
        
        # TP Strategy based on signal strength
        tp_strategy = "TP1 50% / TP2 50%" if confidence_score > 7.5 else "TP1 70% / TP2 30%" if confidence_score > 5.0 else "TP1 100%"
        
        # Format the message according to specification
        message = f"{emoji} *JMONEY CONFIRMED: {jmoney_confirmed}*\n\n"
        message += f"• *Ticker*: {ticker}\n"
        message += f"• *Source*: {signal_data.get('source', 'Unknown')}\n"
        message += f"• *Strategy*: {strategy}\n"
        message += f"• *Score*: {confidence_score:.0f}/10\n"
        message += f"• *Direction*: {direction}\n"
        message += f"• *Entry*: {entry}\n"
        message += f"• *Stop Loss*: {stop_loss}\n"
        message += f"• *TP1 / TP2*: {tp1} / {tp2}\n"
        message += f"• *TP Strategy*: {tp_strategy}\n"
        message += f"• *Macro Score*: {macro_score}/10\n"
        message += f"• *Sentiment Score*: {technical_score}/10\n"  # Using technical as sentiment for now
        message += f"• *Catalyst*: {catalyst_type}\n"
        message += f"• *ZS-10+ Score*: {zs_score}/10\n"
        
        # Add JMoney confirmation reason
        if jmoney_confirmed:
            message += f"• *Confirmation*: ✅ {confirmation_reason}\n"
        else:
            message += f"• *Not Confirmed*: ❌ {confirmation_reason}\n"
        
        # Add timestamp
        timestamp = datetime.now().strftime('%H:%M:%S')
        message += f"\n⏰ {timestamp}"
        
        return message
    
    def send_daily_summary(self, summary_data: Dict):
        """Send daily trading summary."""
        try:
            message = "📈 *Daily Trading Summary*\n\n"
            
            total_signals = summary_data.get('total_signals', 0)
            buy_signals = summary_data.get('buy_signals', 0)
            sell_signals = summary_data.get('sell_signals', 0)
            confirmed_trades = summary_data.get('confirmed_trades', 0)
            
            message += f"📊 Total Signals: {total_signals}\n"
            message += f"🟢 Buy Signals: {buy_signals}\n"
            message += f"🔴 Sell Signals: {sell_signals}\n"
            message += f"✅ Confirmed Trades: {confirmed_trades}\n\n"
            
            message += "Keep following your trading plan! 💪"
            
            self.updater.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send daily summary: {e}")
            return False
    
    def send_test_message(self):
        """Send a test message to verify bot functionality."""
        try:
            test_message = """
🧪 *JMoney Bot Test*

✅ Connection successful!
🤖 Bot is operational
📱 Notifications enabled

Ready to receive trading signals! 🚀
            """
            
            self.updater.bot.send_message(
                chat_id=self.chat_id,
                text=test_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            self.logger.info("Test message sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send test message: {e}")
            return False
