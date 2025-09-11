import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
from typing import Dict
import os
import requests
from utils.logger import logger

class OutputManager:
    """
    Manages the output of final signals to external sources like Google Sheets.
    """
    def __init__(self, credentials_path: str, sheet_name: str):
        """
        Initializes the OutputManager.

        Args:
            credentials_path: Path to the Google service account JSON file.
            sheet_name: The name of the Google Sheet to write to.
        """
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'  
        ]
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheet_name = sheet_name

    def _get_worksheet(self):
        """Gets the specific worksheet to write to."""
        try:
            sheet = self.client.open(self.sheet_name).sheet1
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            if len(self.sheet_name) > 20 and '/' not in self.sheet_name:
                try:
                    print(f"Trying to open by ID: {self.sheet_name}")
                    sheet = self.client.open_by_key(self.sheet_name).sheet1
                    return sheet
                except Exception as e:
                    print(f"Could not open by ID either: {e}")
            
            print(f"Error: Spreadsheet '{self.sheet_name}' not found.")
            print("💡 Try using the spreadsheet ID instead of name:")
            print("1. Copy your spreadsheet URL")
            print("2. Extract the ID (long string between /d/ and /edit)")
            print("3. Update SHEET_NAME in your .env file with the ID")
            return None
        except Exception as e:
            print(f"An error occurred while accessing the sheet: {e}")
            return None

    def _get_signal_emoji(self, decision: str) -> str:
        """Get emoji for signal decision."""
        emoji_map = {
            'Buy': '🟢',
            'Sell': '🔴', 
            'Hold': '🟡',
            'Avoid': '⚪'
        }
        return emoji_map.get(decision, '⚪')

    def _format_monetary_value(self, value):
        """Format monetary values with dollar sign."""
        if value == 'N/A' or value == '' or value is None:
            return 'N/A'
        
        # If it's already a string with $ (including reference values), return as is
        if isinstance(value, str) and ('$' in value or '(ref)' in value):
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

    def export_signals_to_sheets(self, signals: list[dict]) -> bool:
        """
        Exports the final signals with all relevant data to Google Sheets.
        """
        worksheet = self._get_worksheet()
        if not worksheet:
            print("Cannot export to Google Sheets.")
            return

        print(f"--> Exporting {len(signals)} signals to Google Sheet: '{self.sheet_name}'")

        headers = [
            "Timestamp", "Validee", "Ticker", "Source", "Signal", "Strategy", "Direction", 
            "Entry", "Stop Loss", "TP1", "TP2", "TP Strategy",
            "Technical Score", "ZS-10+ Score", "Macro Score", "Sentiment Score",
            "Confidence Score", "Catalyst", "Summary", "JMoney Confirmed", "Reasoning"
        ]
        
        existing_data = []
        try:
            existing_records = worksheet.get_all_records()
            existing_data = [(record.get('Ticker', ''), record.get('Summary', ''), record.get('Timestamp', '')) for record in existing_records]
        except Exception as e:
            print(f"    Note: Could not check for existing data: {e}")
        
        data_to_export = []
        duplicates_skipped = 0
        
        for s in signals:
            ticker = s.get('ticker', 'Unknown')
            catalyst_type = s.get('catalyst_type', 'None')  
            catalyst_headline = s.get('catalyst', s.get('reasoning', 'N/A')) 
            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            
            is_duplicate = False
            for existing_ticker, existing_headline, existing_timestamp in existing_data:
                if (existing_ticker == ticker and 
                    existing_headline == catalyst_headline):
                    is_duplicate = True
                    break
            
            if is_duplicate:
                duplicates_skipped += 1
                print(f"    Skipping duplicate: {ticker} - {catalyst_headline[:50]}...")
                continue
            
            signal = s.get('signal', 'Neutral')
            direction = "Long" if signal == "Buy" else "Short" if signal == "Sell" else "Neutral"
            
            data_to_export.append({
                "Timestamp": timestamp,
                "Validee": self._get_signal_emoji(signal),
                "Ticker": ticker,
                "Source": s.get('source', 'Unknown'),
                "Signal": signal,
                "Strategy": s.get('strategy', 'N/A'),
                "Direction": direction,
                "Entry": self._format_monetary_value(s.get('entry', 'N/A')),
                "Stop Loss": self._format_monetary_value(s.get('stop_loss', 'N/A')),
                "TP1": self._format_monetary_value(s.get('tp1', 'N/A')),
                "TP2": self._format_monetary_value(s.get('tp2', 'N/A')),
                "TP Strategy": s.get('tp_strategy', 'Manual exit required'),
                "Technical Score": f"{s.get('technical_score', 0)}/10",
                "ZS-10+ Score": f"{s.get('zs10_score', 0)}/10",
                "Macro Score": f"{s.get('macro_score', 0)}/10",
                "Sentiment Score": f"{s.get('sentiment_score', 0)}/10",
                "Confidence Score": f"{s.get('confidence_score', 0.0)}/10",
                "Catalyst": catalyst_type,
                "Summary": catalyst_headline,
                "JMoney Confirmed": 'YES' if s.get('jmoney_confirmed', False) else 'NO',
                "Reasoning": s.get('confirmation_reason', 'Ticker doesn\'t meet confirmation requirements')
            })
        
        if duplicates_skipped > 0:
            print(f"    Skipped {duplicates_skipped} duplicate entries")
        
        df = pd.DataFrame(data_to_export, columns=headers)
        df = df.fillna('N/A')

        try:
            # Get existing data
            existing_data = worksheet.get_all_records()
            if not existing_data:
                # If sheet is empty, add headers first
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            else:
                # Append new data without headers
                worksheet.append_rows(df.values.tolist())
        except Exception as e:
            print(f"Error appending data, trying to clear and rewrite: {e}")
            # Fallback: clear and write all data
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            
        print("    ...export complete.")
        return True

    def write_price_alert(self, alert: dict) -> bool:
        """Append a price alert row to a dedicated 'Price Alerts' worksheet (create if missing)."""
        try:
            try:
                sheet = self.client.open(self.sheet_name)
            except Exception as e:
                print(f"    Could not open spreadsheet to write alert: {e}")
                return False

            alerts_title = 'Price Alerts'
            try:
                worksheet = sheet.worksheet(alerts_title)
            except Exception:
                worksheet = sheet.add_worksheet(title=alerts_title, rows=1000, cols=20)

            # Ensure headers exist
            headers = ['Timestamp', 'Ticker', 'Source A', 'Price A', 'Source B', 'Price B', 'Diff %', 'Note']
            try:
                existing = worksheet.get_all_records()
                if not existing:
                    worksheet.append_rows([headers])
            except Exception:
                # best-effort: ignore
                pass

            row = [alert.get(h, 'N/A') for h in headers]
            worksheet.append_rows([row])
            print("    Price alert written to Google Sheet.")
            return True
        except Exception as e:
            print(f"    Failed to write price alert: {e}")
            return False

    def write_confirmation(self, row: dict) -> bool:
        """Append a confirmed trade row to a 'Confirmations' worksheet."""
        try:
            try:
                sheet = self.client.open(self.sheet_name)
            except Exception as e:
                print(f"    Could not open spreadsheet to write confirmation: {e}")
                return False

            title = 'Confirmations'
            try:
                worksheet = sheet.worksheet(title)
            except Exception:
                worksheet = sheet.add_worksheet(title=title, rows=1000, cols=20)

            headers = ['Timestamp', 'Ticker', 'Technical Score', 'Macro Score', 'ZS10 Score', 'Catalyst', 'Confirmed', 'Reason']
            try:
                existing = worksheet.get_all_records()
                if not existing:
                    worksheet.append_rows([headers])
            except Exception:
                pass

            row_values = [row.get(h, 'N/A') for h in headers]
            worksheet.append_rows([row_values])
            print("    Confirmation written to Google Sheet.")
            return True
        except Exception as e:
            print(f"    Failed to write confirmation: {e}")
            return False

    def write_metrics(self, metrics: Dict[str, object]):
        """Append a metrics snapshot to a 'Metrics' sheet.

        The row contains Timestamp, Metrics(JSON).
        This method is resilient: if Sheets aren't configured it logs locally.
        """
        try:
            sheet_name = os.environ.get('SHEET_NAME')
            if not sheet_name or not self.client:
                logger.info('Sheets not configured; writing metrics to local log instead')
                logger.structured('metrics_snapshot', metrics=metrics)
                return

            sh = self.client.open(sheet_name)
            try:
                ws = sh.worksheet('Metrics')
            except Exception:
                ws = sh.add_worksheet('Metrics', rows=1000, cols=10)

            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            metrics_json = json.dumps(metrics)
            row = [timestamp, metrics_json]
            ws.append_row(row)
            logger.success('Appended metrics snapshot to Metrics sheet')
        except Exception as e:
            logger.fail(f'Failed to write metrics to sheet: {e}. Falling back to local structured log')
            logger.structured('metrics_snapshot', metrics=metrics)

    def _alert_id_from_dict(self, alert: dict) -> str:
        """Create a stable alert id from alert content (ticker + timestamp or whole payload hash).

        This is used to deduplicate alerts across runs.
        """
        try:
            key_parts = []
            if 'Ticker' in alert:
                key_parts.append(str(alert.get('Ticker')))
            if 'Timestamp' in alert:
                key_parts.append(str(alert.get('Timestamp')))
            # Fallback to hashing the JSON body
            if not key_parts:
                key_parts.append(json.dumps(alert, sort_keys=True))
            raw = '||'.join(key_parts)
            # Simple stable hash
            import hashlib
            return hashlib.sha1(raw.encode('utf-8')).hexdigest()
        except Exception:
            return str(int(pd.Timestamp.now().timestamp()))

    def write_alert(self, alert: dict, id_key: str = None) -> bool:
        """Idempotently write an alert to the 'Alerts' sheet.

        If `id_key` is provided it will be used as the stable id; otherwise we compute one.
        Returns True if a new alert was written, False if it was a duplicate or skipped.
        """
        alert_id = id_key or self._alert_id_from_dict(alert)
        try:
            sheet_name = os.environ.get('SHEET_NAME')
            if not sheet_name or not self.client:
                logger.info('Sheets not configured; logging alert locally')
                logger.structured('alert', alert=alert, alert_id=alert_id)
                return True

            sh = self.client.open(sheet_name)

            # Ensure index sheet exists and check for existing id
            try:
                idx_ws = sh.worksheet('_alerts_index')
            except Exception:
                idx_ws = sh.add_worksheet('_alerts_index', rows=1000, cols=5)

            # Try to find the alert_id quickly
            try:
                found = idx_ws.find(alert_id)
                if found:
                    logger.info(f"Alert {alert_id} already recorded; skipping write")
                    return False
            except Exception:
                # find() raised because not found or not supported; continue
                pass

            # Append to main Alerts sheet
            try:
                alerts_ws = sh.worksheet('Alerts')
            except Exception:
                alerts_ws = sh.add_worksheet('Alerts', rows=1000, cols=20)

            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            alerts_ws.append_row([timestamp, alert_id, json.dumps(alert)])

            # Record index entry for dedupe
            try:
                idx_ws.append_row([alert_id, timestamp, json.dumps({'ticker': alert.get('Ticker')})])
            except Exception:
                # If index append fails, don't treat as fatal
                logger.info('Could not append to alerts index; continuing')

            logger.success(f'Wrote new alert {alert_id} to Alerts sheet')
            return True

        except Exception as e:
            logger.fail(f'Failed to write alert to sheet: {e}. Falling back to local structured log')
            logger.structured('alert', alert=alert, alert_id=alert_id)
            return False

    def send_alert(self, alert: dict, id_key: str = None) -> bool:
        """Higher-level alert API. Writes alert to Sheets and can be extended to POST to webhooks.

        Returns True if alert was written/sent, False otherwise.
        """
        written = self.write_alert(alert, id_key=id_key)
        # Placeholder for webhook integration: future extension point
        try:
            webhook_url = os.environ.get('ALERT_WEBHOOK_URL')
            if webhook_url:
                try:
                    requests.post(webhook_url, json={'alert': alert, 'alert_id': id_key or self._alert_id_from_dict(alert)}, timeout=5)
                    logger.info('Posted alert to webhook')
                except Exception as e:
                    logger.info(f'Failed posting alert to webhook: {e}')
        except Exception:
            pass

        return written