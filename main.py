import os
import asyncio
import time
import threading
import schedule
import logging
from datetime import datetime
from dotenv import load_dotenv
from core.news_scanner import NewsScanner
from core.ai_analyzer import AIAnalyzer
from core.data_enricher import DataEnricher
from core.scoring_engine import ScoringEngine
from core.decision_engine import DecisionEngine
from core.output_manager import OutputManager
from core.telegram_manager import create_telegram_manager

class SimpleLogger:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)
        self.logger = logging.getLogger('jmoney')
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            
            # File handler
            file_handler = logging.FileHandler('logs/jmoney.log')
            file_handler.setLevel(logging.INFO)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def log_info(self, message: str):
        self.logger.info(message)
    
    def log_error(self, message: str):
        self.logger.error(message)
    
    def log_workflow_start(self, workflow_type: str):
        self.log_info(f"WORKFLOW START: {workflow_type}")
    
    def log_workflow_end(self, workflow_type: str, success: bool, results_count: int = 0):
        status = "SUCCESS" if success else "FAILED"
        self.log_info(f"WORKFLOW END: {workflow_type} | Status: {status} | Results: {results_count}")
    
    def log_workflow_stage(self, stage: str):
        self.log_info(f"STAGE: {stage}")

# Global logger instance
_logger = SimpleLogger()

def log_info(message: str):
    _logger.log_info(message)

def log_error(message: str):
    _logger.log_error(message)

def log_workflow_start(workflow_type: str):
    _logger.log_workflow_start(workflow_type)

def log_workflow_end(workflow_type: str, success: bool, results_count: int = 0):
    _logger.log_workflow_end(workflow_type, success, results_count)

def log_workflow_stage(stage: str):
    _logger.log_workflow_stage(stage)

def run_workflow():
    """
    Run the complete trading signal analysis workflow.
    Returns True if successful, False otherwise.
    """
    log_workflow_start("trading_analysis")
    
    try:
        # --- Configuration Loading ---
        log_workflow_stage("Loading configuration")
        load_dotenv()
        
        # Try OpenAI first, fallback to Gemini if needed
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        openai_api_key = os.getenv("OPENAI_KEY")
        
        # Select AI provider - OpenAI first
        if openai_api_key:
            ai_provider = "openai"
            ai_api_key = openai_api_key
            log_info("Using OpenAI GPT-4o-mini for AI analysis")
            print("🤖 AI Provider: OpenAI GPT-4o-mini")
        elif gemini_api_key:
            ai_provider = "gemini"
            ai_api_key = gemini_api_key
            log_info("Using Google Gemini 1.5-flash for AI analysis")
            print("🤖 AI Provider: Google Gemini 1.5-flash")
        else:
            log_error("No AI API key found - cannot proceed")
            print("❌ Error: No AI API key found in environment variables")
            print("Please set either OPENAI_KEY or GEMINI_API_KEY")
            return False
        
        sources_path = os.getenv("SOURCES_PATH", "config/sources.json")
        prompts_path = os.getenv("PROMPTS_PATH", "config/prompts.json")
        metrics_path = os.getenv("METRICS_PATH", "config/scoring_metrics.json")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        sheet_name = os.getenv("SHEET_NAME")
        
        log_info("Configuration loaded successfully")
        log_info("--- Starting Trading Signal System ---")
        print("--- Starting Trading Signal System ---")
        
        # --- STEP 1: Scan for news headlines ---
        log_workflow_stage("Scanning for news headlines")
        print("\nSTEP 1: Scanning for news headlines...")
        scanner = NewsScanner(sources_path=sources_path)
        headlines_by_source = scanner.scan_headlines()
        
        # Create headlines with source info for AI processing
        headlines_with_sources = []
        for source_name, headlines in headlines_by_source.items():
            for headline in headlines:
                headlines_with_sources.append(f"[{source_name}] {headline}")
        
        print(f"--- ✅ STEP 1 COMPLETE --- (Total headlines: {len(headlines_with_sources)})")
        log_info(f"Headlines scanning completed: {len(headlines_with_sources)} headlines from {len(headlines_by_source)} sources")

        # --- STEP 2: Identify assets using AI ---
        log_workflow_stage("Analyzing headlines with AI to identify assets")
        print("\nSTEP 2: Analyzing headlines to identify assets...")
        analyzer = AIAnalyzer(api_key=ai_api_key, prompts_path=prompts_path, provider=ai_provider)
        identified_assets = analyzer.identify_assets_from_headlines(headlines_with_sources)
        
        # Extract source information from the catalyst text
        for asset in identified_assets:
            catalyst = asset.get('catalyst', '')
            # Extract source from [Source] prefix if present
            if catalyst.startswith('[') and ']' in catalyst:
                source_end = catalyst.find(']')
                source_name = catalyst[1:source_end]
                asset['source'] = source_name
                # Clean the catalyst text by removing source prefix
                asset['catalyst'] = catalyst[source_end + 1:].strip()
            else:
                # Fallback: try to match catalyst with original headlines
                asset['source'] = 'Unknown'
                for source_name, headlines in headlines_by_source.items():
                    for headline in headlines:
                        if catalyst.lower() in headline.lower() or headline.lower() in catalyst.lower():
                            asset['source'] = source_name
                            break
                    if asset['source'] != 'Unknown':
                        break
        
        if not identified_assets:
            log_info("AI did not identify any assets - workflow complete")
            print("\nAI did not identify any assets. Workflow complete.")
            return True
        
        log_info(f"AI identified {len(identified_assets)} assets: {[asset.get('ticker', 'Unknown') for asset in identified_assets]}")
        print(f"--- ✅ STEP 2 COMPLETE --- (Identified {len(identified_assets)} assets)")

        # --- STEP 3: Enrich assets with market data ---
        log_workflow_stage("Enriching identified assets with market data")
        print("\nSTEP 3: Enriching identified assets with market data...")
        enricher = DataEnricher()
        enriched_assets = enricher.enrich_assets(identified_assets)
        if not enriched_assets:
            log_info("Could not enrich any assets with market data - workflow complete")
            print("\nCould not enrich any assets with market data. Workflow complete.")
            return True
        
        log_info(f"Successfully enriched {len(enriched_assets)} assets with market data")
        print(f"--- ✅ STEP 3 COMPLETE --- (Successfully enriched {len(enriched_assets)} assets)")

        # --- STEP 4: Calculate scores for each asset ---
        log_workflow_stage("Calculating scores for enriched assets")
        print("\nSTEP 4: Calculating scores for each enriched asset...")
        scorer = ScoringEngine(analyzer=analyzer)  # Pass the same analyzer instance
        scored_assets = scorer.calculate_all_scores(enriched_assets)
        log_info(f"Successfully scored {len(scored_assets)} assets")
        print(f"--- ✅ STEP 4 COMPLETE --- (Successfully scored {len(scored_assets)} assets)")

        # --- STEP 5: Make final decision and check for confirmation ---
        log_workflow_stage("Making final trading decisions")
        print("\nSTEP 5: Making final decisions...")
        decision_engine = DecisionEngine(metrics_path=metrics_path)
        final_signals = decision_engine.run_engine(scored_assets)
        
        confirmed_signals = [s for s in final_signals if s.get('jmoney_confirmed')]
        log_info(f"Generated {len(final_signals)} signals, {len(confirmed_signals)} confirmed")
        print(f"--- ✅ STEP 5 COMPLETE --- (Generated {len(final_signals)} final signals)")
        print("\n--- FINAL SIGNALS ---")
        for signal in final_signals:
            print(
                f"  - Ticker: {signal.get('ticker')}\n"
                f"    Strategy: {signal.get('strategy')}, Signal: {signal.get('signal')}\n"
                f"    JMoney Confirmed: {signal.get('jmoney_confirmed')}\n"
            )

        # --- STEP 6: Export final signals to Google Sheets ---
        log_workflow_stage("Exporting signals to Google Sheets")
        print("\nSTEP 6: Exporting signals to Google Sheets...")
        output_manager = OutputManager(credentials_path=credentials_path, sheet_name=sheet_name)
        export_success = output_manager.export_signals_to_sheets(final_signals)
        if export_success:
            log_info(f"Successfully exported {len(final_signals)} signals to Google Sheets")
            print(f"--- ✅ STEP 6 COMPLETE ---")
        else:
            log_error("Google Sheets export failed")
            print(f"--- ❌ STEP 6 FAILED --- (Google Sheets export failed)")
        
        # --- STEP 7: Send Telegram Notifications ---
        log_workflow_stage("Sending Telegram notifications")
        print("\nSTEP 7: Sending Telegram notifications...")
        telegram_manager = create_telegram_manager(output_manager=output_manager)
        
        if telegram_manager:
            try:
                # Send notifications for ALL signals
                if final_signals:
                    log_info(f"Sending Telegram alerts for {len(final_signals)} signals")
                    print(f"📱 Sending Telegram alerts for {len(final_signals)} signals...")
                    asyncio.run(telegram_manager.send_batch_notifications(final_signals))
                    log_info("Telegram notifications sent successfully")
                    print("--- ✅ STEP 7 COMPLETE ---")
                else:
                    log_info("No signals to notify about")
                    print("📭 No signals to notify about")
                    print("--- ✅ STEP 7 COMPLETE (No alerts needed) ---")
                    
            except Exception as e:
                log_error(f"Telegram notification error: {e}")
                print(f"❌ Telegram notification error: {e}")
                print("--- ⚠️ STEP 7 FAILED (System continues without notifications) ---")
        else:
            log_info("Telegram not configured - skipping notifications")
            print("⚠️ Telegram not configured - skipping notifications")
            print("--- ⚠️ STEP 7 SKIPPED ---")
        
        print("\n--- WORKFLOW FINISHED ---")
        log_workflow_end("trading_analysis", success=True)
        log_info("Trading analysis workflow completed successfully")
        return True
        
    except Exception as e:
        log_error(f"Workflow failed: {e}")
        log_workflow_end("trading_analysis", success=False)
        print(f"❌ Workflow failed: {e}")
        return False

def setup_scheduled_workflow():
    """Setup scheduled workflow execution."""
    # Run workflow every 4 hours during market hours
    schedule.every(4).hours.do(run_workflow)
    
    # You can add more scheduling options here
    # schedule.every().day.at("09:30").do(run_workflow)  # Market open
    # schedule.every().day.at("13:30").do(run_workflow)  # Mid day
    # schedule.every().day.at("15:30").do(run_workflow)  # Pre close
    
    print("⏰ Scheduled workflow: Every 4 hours")

def run_scheduler():
    """Run the workflow scheduler in a separate thread."""
    print("🕐 Starting workflow scheduler...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def main():
    """
    Main function to run the complete JMONEY system with both 
    workflow automation and interactive Telegram bot.
    """
    load_dotenv()
    
    print("🚀 Starting JMONEY Trading System...")
    print("📡 Initializing Telegram bot...")
    
    # Initialize output manager for Google Sheets access
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    sheet_name = os.getenv("SHEET_NAME")
    output_manager = OutputManager(credentials_path=credentials_path, sheet_name=sheet_name)
    
    # Initialize Telegram manager with output_manager for sheet access
    telegram_manager = create_telegram_manager(output_manager=output_manager)
    
    if not telegram_manager:
        print("❌ Failed to initialize Telegram bot. Check your configuration.")
        print("💡 Make sure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in .env")
        return
    
    # Set up workflow callback for /fetch command
    telegram_manager.bot.set_workflow_callback(run_workflow)
    
    # Run initial workflow
    print("🔄 Running initial workflow...")
    run_workflow()
    
    # Setup scheduled workflow
    setup_scheduled_workflow()
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    print("🤖 Starting Telegram bot for interactive commands...")
    print("✅ System is now running continuously!")
    print("📱 Send /start to your Telegram bot to begin")
    print("🔄 Use /fetch to manually trigger workflow")
    print("⏰ Automatic workflow runs every 4 hours")
    print("🛑 Press Ctrl+C to stop the system")
    
    try:
        # Start the bot and keep it running
        telegram_manager.bot.start_bot_polling()
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down JMONEY system...")
        telegram_manager.bot.stop_bot()
        print("✅ System stopped successfully")

def run_telegram_bot_only():
    """
    Run only the Telegram bot for interactive commands (legacy function).
    """
    load_dotenv()  
    # Initialize output manager for Google Sheets access
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    sheet_name = os.getenv("SHEET_NAME")
    output_manager = OutputManager(credentials_path=credentials_path, sheet_name=sheet_name)
    
    telegram_manager = create_telegram_manager(output_manager=output_manager)
    
    if telegram_manager:
        print("🤖 Starting interactive Telegram bot...")
        telegram_manager.bot.start_bot_polling()
        
        print("✅ Telegram bot is running! Send /start to begin.")
        print("Press Ctrl+C to stop the bot.")
        
        try:
            telegram_manager.bot.updater.idle()
        except KeyboardInterrupt:
            print("\n🛑 Stopping Telegram bot...")
            telegram_manager.bot.stop_bot()
    else:
        print("❌ Could not start Telegram bot. Check your configuration.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--bot-only":
        # Run Telegram bot interactively (legacy mode)
        print("🚀 Starting JMONEY Telegram Bot in interactive mode...")
        load_dotenv()  
        run_telegram_bot_only()
    elif len(sys.argv) > 1 and sys.argv[1] == "--workflow-only":
        # Run workflow once and exit
        print("🔄 Running JMONEY workflow once...")
        load_dotenv()  
        run_workflow()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-telegram":
        # Test Telegram notifications
        print("🧪 Testing Telegram notifications...")
        load_dotenv()  
        # Initialize output manager for Google Sheets access
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        sheet_name = os.getenv("SHEET_NAME")
        output_manager = OutputManager(credentials_path=credentials_path, sheet_name=sheet_name)
        
        telegram_manager = create_telegram_manager(output_manager=output_manager)
        if telegram_manager:
            asyncio.run(telegram_manager.test_notification())
        else:
            print("❌ Telegram not configured properly")
    else:
        # Run complete system
        main()
