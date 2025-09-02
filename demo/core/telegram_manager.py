#
# File: demo/core/telegram_manager.py
#
import os
from datetime import datetime

class TelegramNotificationManager:
    """
    (DEMO VERSION - FINAL)
    Manages Telegram notifications by writing them to a local file
    using the full, correct message format from the main system.
    """
    def __init__(self, output_path: str = "output"):
        self.output_path = output_path
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        self.output_file = os.path.join(self.output_path, "telegram_preview.txt")
        # Clear the file at the start of a run with UTF-8 encoding for emojis
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(f"--- Telegram Preview Log Generated at {datetime.now()} ---\n\n")

    def _get_signal_emoji(self, decision: str) -> str:
        emoji_map = {'Buy': '🟢', 'Sell': '🔴', 'Hold': '🟡', 'Avoid': '⚪'}
        return emoji_map.get(decision, '⚪')

    def _format_signal_notification(self, signal_data: dict) -> str:
        """
        (FULL VERSION) Formats signal data to match the original system's output.
        """
        ticker = signal_data.get('ticker', 'Unknown')
        decision = signal_data.get('signal', 'Neutral')
        jmoney_confirmed = signal_data.get('jmoney_confirmed', False)
        emoji = self._get_signal_emoji(decision)
        direction = "Long" if decision == "Buy" else "Short" if decision == "Sell" else "Neutral"
        
        # Safely format monetary values that might be strings with percentages
        def format_value(value):
            if isinstance(value, str):
                return value
            if isinstance(value, (int, float)):
                 # Fewer decimals for forex/crypto, more for stocks
                decimals = 4 if value < 10 else 2
                return f"${value:.{decimals}f}"
            return "N/A"

        entry = format_value(signal_data.get('entry'))
        stop_loss = format_value(signal_data.get('stop_loss'))
        tp1 = signal_data.get('tp1', 'N/A') # Keep string as is
        tp2 = signal_data.get('tp2', 'N/A') # Keep string as is

        message = f"{emoji} JMONEY CONFIRMED: {jmoney_confirmed}\n\n"
        message += f"• Ticker: {ticker}\n"
        message += f"• Source: {signal_data.get('source', 'Unknown')}\n"
        message += f"• Strategy: {signal_data.get('strategy', 'Unknown')}\n"
        message += f"• Score: {signal_data.get('confidence_score', 0.0):.0f}/10\n"
        message += f"• Direction: {direction}\n"
        message += f"• Entry: {entry}\n"
        message += f"• Stop Loss: {stop_loss}\n"
        message += f"• TP1 / TP2: {tp1} / {tp2}\n"
        message += f"• TP Strategy: {signal_data.get('tp_strategy', 'N/A')}\n"
        message += f"• Macro Score: {signal_data.get('macro_score', 0)}/10\n"
        message += f"• Sentiment Score: {signal_data.get('sentiment_score', 0)}/10\n"
        message += f"• Catalyst: {signal_data.get('catalyst_type', 'N/A')}\n"
        message += f"• ZS-10+ Score: {signal_data.get('zs10_score', 0)}/10\n"
        
        if jmoney_confirmed:
            message += f"• Confirmation: ✅ {signal_data.get('confirmation_reason', '')}\n"
        else:
            message += f"• Not Confirmed: ❌ {signal_data.get('confirmation_reason', '')}\n"

        message += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}\n"
        message += "========================================\n\n"
        return message

    def send_batch_notifications(self, signals: list[dict]):
        if not signals:
            print("📭 No signals to notify about")
            return

        print(f"📱 Writing Telegram previews for {len(signals)} signals...")
        full_output = ""
        for signal in signals:
            full_output += self._format_signal_notification(signal)

        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(full_output)