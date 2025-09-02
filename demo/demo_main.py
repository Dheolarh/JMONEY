#
# File: demo/demo_main.py
#
from core.news_scanner import NewsScanner
from core.ai_analyzer import AIAnalyzer
from core.data_enricher import DataEnricher
from core.scoring_engine import ScoringEngine
from core.decision_engine import DecisionEngine
from core.output_manager import OutputManager
from core.telegram_manager import TelegramNotificationManager
from utils.logger import logger

def run_demo_workflow():
    """Run the complete OFFLINE & STANDALONE trading signal analysis workflow."""
    logger.start_section("STANDALONE DEMO WORKFLOW STARTED")

    # --- STEP 1: Scan for news headlines (from local file) ---
    logger.start_section("STEP 1: NEWS SCANNING (DEMO)")
    # REMOVED "demo/" prefix
    scanner = NewsScanner(sources_path="data/mock_headlines.json")
    headlines_by_source = scanner.scan_headlines()
    headlines_with_sources = [f"[{source}] {headline}" for source, headlines in headlines_by_source.items() for headline in headlines]
    logger.success(f"Scan complete. Loaded {len(headlines_with_sources)} total headlines from local file.")

    # --- STEP 2: Identify assets using AI (from local file) ---
    logger.start_section("STEP 2: AI ASSET IDENTIFICATION (DEMO)")
    # REMOVED "demo/" prefix
    analyzer = AIAnalyzer(api_key="demo", prompts_path="data/mock_ai_responses.json")
    identified_assets = analyzer.identify_assets_from_headlines(headlines_with_sources)
    logger.success(f"AI identified {len(identified_assets)} potential assets from mock data.")

    # --- STEP 3: Enrich assets with market data (from local CSVs) ---
    logger.start_section("STEP 3: DATA ENRICHMENT (DEMO)")
    enricher = DataEnricher(analyzer=analyzer)
    enriched_assets = enricher.enrich_assets(identified_assets)
    logger.success(f"Successfully enriched {len(enriched_assets)} assets using local CSVs.")

    # --- STEP 4: Calculate scores for each asset ---
    logger.start_section("STEP 4: SCORING ENGINE (DEMO)")
    scorer = ScoringEngine(analyzer=analyzer)
    scored_assets = scorer.calculate_all_scores(enriched_assets)
    logger.success(f"Successfully scored {len(scored_assets)} assets.")

    # --- STEP 5: Make final decision and generate signals ---
    logger.start_section("STEP 5: DECISION ENGINE")
    # REMOVED "demo/" prefix
    decision_engine = DecisionEngine(metrics_path="config/scoring_metrics.json")
    final_signals = decision_engine.run_engine(scored_assets)
    logger.success(f"Generated {len(final_signals)} final signals.")

    # --- STEP 6: Export final signals to local files ---
    logger.start_section("STEP 6: OUTPUT (DEMO)")
    # REMOVED "demo/" prefix
    output_manager = OutputManager(output_path="output")
    output_manager.export_signals_to_files(final_signals)
    logger.success("Exported signals to /output/ folder.")

    # --- STEP 7: Send Telegram Notifications (to local file) ---
    logger.start_section("STEP 7: TELEGRAM NOTIFICATIONS (DEMO)")
    telegram_manager = TelegramNotificationManager()
    telegram_manager.send_batch_notifications(final_signals)
    logger.success("Telegram notifications saved to /output/telegram_preview.txt")

    logger.start_section("DEMO WORKFLOW FINISHED")
    print("\n✅ Demo workflow complete. Check the 'output' directory for results.")

if __name__ == "__main__":
    run_demo_workflow()