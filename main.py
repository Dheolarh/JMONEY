import os
import asyncio
import time
import threading
from core.backtester import Backtester
from core.optimizer import Optimizer
import schedule
from dotenv import load_dotenv
from core.news_scanner import NewsScanner
from core.ai_analyzer import AIAnalyzer
from core.data_enricher import DataEnricher
from core.scoring_engine import ScoringEngine
from core.decision_engine import DecisionEngine
from core.output_manager import OutputManager
from core.telegram_manager import create_telegram_manager
from core.portfolio_tracker import PortfolioTracker
from utils.logger import logger

# Global variable to hold the main workflow job
workflow_job = None
telegram_manager_instance = None # Global instance for notifications

def run_workflow(is_manual_trigger=False):
    """Run the complete trading signal analysis workflow."""
    logger.start_section("WORKFLOW STARTED")
    
    try:
        # --- Configuration Loading ---
        logger.log("Loading configuration...")
        load_dotenv()
        
        openai_key = os.getenv("OPENAI_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        
        if openai_key:
            ai_provider, ai_api_key = "openai", openai_key
            logger.info("Using OpenAI for AI analysis")
        elif gemini_key:
            ai_provider, ai_api_key = "gemini", gemini_key
            logger.info("Using Gemini for AI analysis")
        else:
            logger.fail("No AI API key found. Cannot proceed.")
            return False

        # --- STEP 0: Update Portfolio ---
        logger.start_section("STEP 0: PORTFOLIO UPDATE")
        portfolio_tracker = PortfolioTracker()
        portfolio_tracker.update_open_trades()
        logger.success("Portfolio updated.")

        # --- STEP 1: Scan for news headlines ---
        logger.start_section("STEP 1: NEWS SCANNING")
        scanner = NewsScanner(sources_path=os.getenv("SOURCES_PATH", "config/sources.json"))
        headlines_by_source = scanner.scan_headlines()
        headlines_with_sources = [f"[{source}] {headline}" for source, headlines in headlines_by_source.items() for headline in headlines]
        logger.success(f"Scan complete. Found {len(headlines_with_sources)} total headlines.")

        # --- STEP 2: Identify assets using AI ---
        logger.start_section("STEP 2: AI ASSET IDENTIFICATION")
        analyzer = AIAnalyzer(api_key=ai_api_key, prompts_path=os.getenv("PROMPTS_PATH", "config/prompts.json"), provider=ai_provider)
        identified_assets = analyzer.identify_assets_from_headlines(headlines_with_sources)
        if not identified_assets:
            logger.info("AI did not identify any assets. Workflow complete.")
            if is_manual_trigger and telegram_manager_instance:
                message = "✅ *Workflow Completed*\n\nAI did not identify any new tradeable assets from the latest headlines."
                telegram_manager_instance._send_message_sync(message)
            return True
        logger.success(f"AI identified {len(identified_assets)} potential assets.")

        # --- STEP 3: Enrich assets with market data ---
        logger.start_section("STEP 3: DATA ENRICHMENT")
        enricher = DataEnricher(analyzer=analyzer)
        enriched_assets = enricher.enrich_assets(identified_assets)
        if not enriched_assets:
            logger.info("Could not enrich any assets with market data. Workflow complete.")
            if is_manual_trigger and telegram_manager_instance:
                message = "✅ *Workflow Completed*\n\nCould not enrich any of the identified assets with market data."
                telegram_manager_instance._send_message_sync(message)
            return True
        logger.success(f"Successfully enriched {len(enriched_assets)} assets.")

        # --- STEP 4: Calculate scores for each asset ---
        logger.start_section("STEP 4: SCORING ENGINE")
        scorer = ScoringEngine(analyzer=analyzer)
        scored_assets = scorer.calculate_all_scores(enriched_assets)
        logger.success(f"Successfully scored {len(scored_assets)} assets.")

        # --- STEP 5: Make final decision and generate signals ---
        logger.start_section("STEP 5: DECISION ENGINE")
        decision_engine = DecisionEngine(metrics_path=os.getenv("METRICS_PATH", "config/scoring_metrics.json"))
        final_signals = decision_engine.run_engine(scored_assets)
        logger.success(f"Generated {len(final_signals)} final signals.")
        
        # --- Add confirmed trades to portfolio ---
        confirmed_signals = [s for s in final_signals if s.get('jmoney_confirmed')]
        if confirmed_signals:
            logger.log(f"Adding {len(confirmed_signals)} confirmed signals to portfolio...")
            for signal in confirmed_signals:
                portfolio_tracker.add_trade(signal)
            logger.success("Portfolio updated with new trades.")


        # --- STEP 6: Export final signals to Google Sheets ---
        logger.start_section("STEP 6: OUTPUT & NOTIFICATIONS")
        output_manager = OutputManager(credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), sheet_name=os.getenv("SHEET_NAME"))
        if output_manager.export_signals_to_sheets(final_signals):
            logger.success("Exported signals to Google Sheets.")
        else:
            logger.fail("Google Sheets export failed.")
        
        # --- STEP 7: Send Telegram Notifications ---
        if telegram_manager_instance and final_signals:
            logger.log("Sending Telegram notifications...")
            asyncio.run(telegram_manager_instance.send_batch_notifications(final_signals))
            logger.success("Telegram notifications sent.")
        
        if is_manual_trigger and telegram_manager_instance:
            message = f"✅ *Workflow Completed Successfully*\n\nGenerated and sent {len(final_signals)} new signals!"
            telegram_manager_instance._send_message_sync(message)
            
        logger.start_section("WORKFLOW FINISHED")
        return True
        
    except Exception as e:
        logger.fail(f"Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        if is_manual_trigger and telegram_manager_instance:
            message = f"❌ *Workflow Failed*\n\nAn error occurred: {e}"
            telegram_manager_instance._send_message_sync(message)
        return False

def setup_schedules(telegram_manager):
    """Setup all scheduled jobs for the system."""
    global workflow_job
    
    schedule.clear()
    
    workflow_job = schedule.every(4).hours.do(run_workflow)
    logger.info("Workflow scheduled to run every 4 hours.")

    if telegram_manager:
        schedule.every().day.at("08:00").do(telegram_manager.send_daily_summary)
        schedule.every().day.at("09:30").do(telegram_manager.send_market_open_notification)
        schedule.every().day.at("16:00").do(telegram_manager.send_market_close_summary)
        logger.info("Telegram notification jobs scheduled.")
    
    logger.success("All system schedules are configured.")

def trigger_manual_workflow_and_reschedule():
    """
    Handles a manual trigger from Telegram. It runs the workflow
    immediately and resets the timer for the next scheduled run.
    """
    global workflow_job
    
    logger.info("Manual workflow triggered via Telegram.")
    
    # Run the workflow with the manual flag
    success = run_workflow(is_manual_trigger=True)
    
    if success:
        logger.info("Resetting workflow schedule after manual run...")
        schedule.cancel_job(workflow_job)
        workflow_job = schedule.every(4).hours.do(run_workflow)
        logger.success("Workflow schedule has been reset. Next run in 4 hours.")
    else:
        logger.fail("Manual workflow failed. Schedule not reset.")
        
    return success

def run_scheduler():
    """Run the workflow scheduler in a separate thread."""
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    """
    Main function to run the complete JMONEY system.
    """
    global telegram_manager_instance
    load_dotenv()
    logger.start_section("JMONEY TRADING SYSTEM INITIALIZING")
    
    output_manager = OutputManager(credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), sheet_name=os.getenv("SHEET_NAME"))
    portfolio_tracker = PortfolioTracker()
    telegram_manager_instance = create_telegram_manager(output_manager=output_manager)
    
    logger.start_section("PERFORMING STRATEGY OPTIMIZATION")
    try:
        api_key = os.getenv("OPENAI_KEY") or os.getenv("GEMINI_API_KEY")
        ai_analyzer = AIAnalyzer(api_key=api_key, prompts_path="config/prompts.json")
        
        optimizer = Optimizer(
            output_manager=output_manager,
            metrics_path=os.getenv("METRICS_PATH", "config/scoring_metrics.json"),
            ai_analyzer=ai_analyzer
        )
        optimizer.run_optimization(iterations=2)
        
    except Exception as e:
        logger.fail(f"An error occurred during optimization: {e}")

    run_workflow()
    
    setup_schedules(telegram_manager_instance)
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.success("Scheduler started in background.")
    
    if telegram_manager_instance:
        telegram_manager_instance.bot.set_workflow_callback(trigger_manual_workflow_and_reschedule)
        telegram_manager_instance.bot.portfolio_tracker = portfolio_tracker
        logger.success("System is now running continuously!")
        logger.info("Send /start to your Telegram bot to begin.")
        telegram_manager_instance.bot.start_bot_polling()
        while True: time.sleep(1)
    else:
        logger.fail("Could not start Telegram bot. Exiting.")

if __name__ == "__main__":
    main()