import pandas as pd
import json
import os
from datetime import datetime

class OutputManager:
    """
    (DEMO VERSION)
    Manages the output of final signals to local JSON and CSV files.
    """
    def __init__(self, output_path: str):
        self.output_path = output_path
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def _get_signal_emoji(self, decision: str) -> str:
        emoji_map = {'Buy': '🟢', 'Sell': '🔴', 'Hold': '🟡', 'Avoid': '⚪'}
        return emoji_map.get(decision, '⚪')

    def export_signals_to_files(self, signals: list[dict]):
        """
        Exports the final signals to signals.csv and signals.json.
        """
        if not signals:
            print("No signals to export.")
            return

        print(f"--> Exporting {len(signals)} signals to '{self.output_path}'")

        # Prepare data for DataFrame
        data_to_export = []
        for s in signals:
            signal = s.get('signal', 'Neutral')
            direction = "Long" if signal == "Buy" else "Short" if signal == "Sell" else "Neutral"
            data_to_export.append({
                "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "Validee": self._get_signal_emoji(signal),
                "Ticker": s.get('ticker', 'Unknown'),
                "Source": s.get('source', 'Unknown'),
                "Signal": signal,
                "Strategy": s.get('strategy', 'N/A'),
                "Direction": direction,
                "Entry": s.get('entry', 'N/A'),
                "Stop Loss": s.get('stop_loss', 'N/A'),
                "TP1": s.get('tp1', 'N/A'),
                "TP2": s.get('tp2', 'N/A'),
                "Confidence Score": s.get('confidence_score', 0.0),
                "Catalyst": s.get('catalyst_type', 'None'),
                "Summary": s.get('catalyst', ''),
                "JMoney Confirmed": 'YES' if s.get('jmoney_confirmed', False) else 'NO',
                "Reasoning": s.get('confirmation_reason', '')
            })

        df = pd.DataFrame(data_to_export)

        # Save to CSV
        csv_path = os.path.join(self.output_path, "signals.csv")
        df.to_csv(csv_path, index=False)
        print(f"    ...signals.csv saved.")

        # Save to JSON
        json_path = os.path.join(self.output_path, "signals.json")
        df.to_json(json_path, orient='records', indent=2)
        print(f"    ...signals.json saved.")