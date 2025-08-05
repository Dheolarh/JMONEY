import os
import asyncio
import time
import threading
import schedule
from dotenv import load_dotenv
from core.news_scanner import NewsScanner
from core.ai_analyzer import AIAnalyzer
from core.data_enricher import DataEnricher
from core.scoring_engine import ScoringEngine
from core.decision_engine import DecisionEngine
from core.output_manager import OutputManager
from core.telegram_manager import create_telegram_manager

def run_workflow():
    """
    Run the complete trading signal analysis workflow.
    Returns True if successful, False otherwise.
    """
    try:
        # --- Configuration Loading ---
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_KEY")
        sources_path = os.getenv("SOURCES_PATH", "config/sources.json")
        prompts_path = os.getenv("PROMPTS_PATH", "config/prompts.json")
        metrics_path = os.getenv("METRICS_PATH", "config/scoring_metrics.json")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        sheet_name = os.getenv("SHEET_NAME")
        
        print("--- Starting Trading Signal System ---")
        
        # --- STEP 1: Scan for news headlines ---
        print("\nSTEP 1: Scanning for news headlines...")
        scanner = NewsScanner(sources_path=sources_path)
        headlines_by_source = scanner.scan_headlines()
        
        # Create headlines with source info for AI processing
        headlines_with_sources = []
        for source_name, headlines in headlines_by_source.items():
            for headline in headlines:
                headlines_with_sources.append(f"[{source_name}] {headline}")
        
        print(f"--- ✅ STEP 1 COMPLETE --- (Total headlines: {len(headlines_with_sources)})")

        # --- STEP 2: Identify assets using AI ---
        print("\nSTEP 2: Analyzing headlines to identify assets...")
        analyzer = AIAnalyzer(api_key=openai_api_key, prompts_path=prompts_path)
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
            print("\nAI did not identify any assets. Workflow complete.")
            return True
        print(f"--- ✅ STEP 2 COMPLETE --- (Identified {len(identified_assets)} assets)")

        # --- STEP 3: Enrich assets with market data ---
        print("\nSTEP 3: Enriching identified assets with market data...")
        enricher = DataEnricher()
        enriched_assets = enricher.enrich_assets(identified_assets)
        if not enriched_assets:
            print("\nCould not enrich any assets with market data. Workflow complete.")
            return True
        print(f"--- ✅ STEP 3 COMPLETE --- (Successfully enriched {len(enriched_assets)} assets)")

        # --- STEP 4: Calculate scores for each asset ---
        print("\nSTEP 4: Calculating scores for each enriched asset...")
        scorer = ScoringEngine()
        scored_assets = scorer.calculate_all_scores(enriched_assets)
        print(f"--- ✅ STEP 4 COMPLETE --- (Successfully scored {len(scored_assets)} assets)")

        # --- STEP 5: Make final decision and check for confirmation ---
        print("\nSTEP 5: Making final decisions...")
        decision_engine = DecisionEngine(metrics_path=metrics_path)
        final_signals = decision_engine.run_engine(scored_assets)
        print(f"--- ✅ STEP 5 COMPLETE --- (Generated {len(final_signals)} final signals)")
        print("\n--- FINAL SIGNALS ---")
        for signal in final_signals:
            print(
                f"  - Ticker: {signal.get('ticker')}\n"
                f"    Strategy: {signal.get('strategy')}, Signal: {signal.get('signal')}\n"
                f"    JMoney Confirmed: {signal.get('jmoney_confirmed')}\n"
            )

        # --- STEP 6: Export final signals to Google Sheets ---
        print("\nSTEP 6: Exporting signals to Google Sheets...")
        output_manager = OutputManager(credentials_path=credentials_path, sheet_name=sheet_name)
        export_success = output_manager.export_signals_to_sheets(final_signals)
        if export_success:
            print(f"--- ✅ STEP 6 COMPLETE ---")
        else:
            print(f"--- ❌ STEP 6 FAILED --- (Google Sheets export failed)")
        
        # --- STEP 7: Send Telegram Notifications ---
        print("\nSTEP 7: Sending Telegram notifications...")
        telegram_manager = create_telegram_manager(output_manager=output_manager)
        
        if telegram_manager:
            try:
                # Send notifications for ALL signals
                if final_signals:
                    print(f"📱 Sending Telegram alerts for {len(final_signals)} signals...")
                    asyncio.run(telegram_manager.send_batch_notifications(final_signals))
                    print("--- ✅ STEP 7 COMPLETE ---")
                else:
                    print("📭 No signals to notify about")
                    print("--- ✅ STEP 7 COMPLETE (No alerts needed) ---")
                    
            except Exception as e:
                print(f"❌ Telegram notification error: {e}")
                print("--- ⚠️ STEP 7 FAILED (System continues without notifications) ---")
        else:
            print("⚠️ Telegram not configured - skipping notifications")
            print("--- ⚠️ STEP 7 SKIPPED ---")
        
        print("\n--- WORKFLOW FINISHED ---")
        return True
        
    except Exception as e:
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
