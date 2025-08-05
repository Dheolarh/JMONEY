import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

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
            "Timestamp", "Ticker", "Source", "Signal", "Strategy", "Direction", 
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
            

            technical_score = s.get('technical_score', 0)
            zs_score = s.get('zs10_score', 0)
            macro_score = s.get('macro_score', 0)
            sentiment_score = s.get('sentiment_score', 0)
            confidence_score = round((technical_score + macro_score + (10 - zs_score)) / 3, 1)
            

            signal = s.get('signal', 'Neutral')
            direction = "Long" if signal == "Buy" else "Short" if signal == "Sell" else "Neutral"
            
            data_to_export.append({
                "Timestamp": timestamp,
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
                "Technical Score": f"{technical_score}/10",
                "ZS-10+ Score": f"{zs_score}/10",
                "Macro Score": f"{macro_score}/10",
                "Sentiment Score": f"{sentiment_score}/10",
                "Confidence Score": f"{confidence_score}/10",
                "Catalyst": catalyst_type,
                "Summary": catalyst_headline,
                "JMoney Confirmed": 'YES' if s.get('jmoney_confirmed', False) else 'NO',
                "Reasoning": s.get('confirmation_reason', 'Ticker doesn\'t meet confirmation requirements')
            })
        
        if duplicates_skipped > 0:
            print(f"    Skipped {duplicates_skipped} duplicate entries")
        
        df = pd.DataFrame(data_to_export, columns=headers)
        
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
