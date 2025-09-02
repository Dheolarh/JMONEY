#
# File: demo_main.py
#
import time
import json
import random
from core.news_scanner import NewsScanner
from core.ai_analyzer import AIAnalyzer
from core.data_enricher import DataEnricher
from core.scoring_engine import ScoringEngine
from core.decision_engine import DecisionEngine
from core.output_manager import OutputManager
from core.telegram_manager import TelegramNotificationManager
from utils.logger import logger
from run_backtest import run_backtest_and_generate_outputs

def inject_confirmed_trades():
    """Injects a balanced portfolio of winning and losing trades for a dynamic demo."""
    try:
        with open("data/confirmed_trades_pool.json", 'r') as f:
            trades_pool = json.load(f)
        with open("data/mock_ai_responses.json", 'r') as f:
            mock_data = json.load(f)

        # Separate pool into wins and losses
        wins = [t for t in trades_pool if t['simulated_outcome'] == 'win']
        losses = [t for t in trades_pool if t['simulated_outcome'] == 'loss']

        # Pick 2 winners and 2 losers
        confirmed_trades = random.sample(wins, 2) + random.sample(losses, 2)
        random.shuffle(confirmed_trades)

        for trade in confirmed_trades:
            mock_data["identify_assets"].append({
                "ticker": trade["ticker"],
                "catalyst": trade["catalyst"]
            })
            mock_data["enrich_ticker"][trade["ticker"]] = {
                "asset_type": trade["asset_type"],
                "formatted_ticker": trade["formatted_ticker"]
            }
            mock_data["score_asset"][trade["ticker"]] = {
                "macro_score": trade["macro_score"],
                "sentiment_score": trade["sentiment_score"],
                "catalyst_type": trade["catalyst_type"],
                "simulated_outcome": trade["simulated_outcome"]
            }
        return mock_data

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.fail(f"Could not inject dynamic trades: {e}")
        return None

def run_demo_workflow():
    """Run the complete OFFLINE & STANDALONE trading signal analysis workflow."""
    logger.start_section("STANDALONE DEMO WORKFLOW STARTED")

    logger.log("Injecting a balanced portfolio for this run...")
    dynamic_mock_data = inject_confirmed_trades()
    if not dynamic_mock_data:
        return

    logger.start_section("STEP 1: NEWS SCANNING (DEMO)")
    scanner = NewsScanner(sources_path="data/mock_headlines.json")
    headlines_by_source = scanner.scan_headlines()
    headlines_with_sources = [f"[{source}] {headline}" for source, headlines in headlines_by_source.items() for headline in headlines]
    logger.success(f"Scan complete. Loaded {len(headlines_with_sources)} total headlines.")

    logger.start_section("STEP 2: AI ASSET IDENTIFICATION (DEMO)")
    analyzer = AIAnalyzer(api_key="demo", prompts_path="data/mock_ai_responses.json")
    analyzer.mock_responses = dynamic_mock_data
    identified_assets = analyzer.identify_assets_from_headlines(headlines_with_sources)
    logger.success(f"AI identified {len(identified_assets)} potential assets.")

    logger.start_section("STEP 3: DATA ENRICHMENT (DEMO)")
    enricher = DataEnricher(analyzer=analyzer)
    enriched_assets = enricher.enrich_assets(identified_assets)
    logger.success(f"Successfully enriched {len(enriched_assets)} assets.")

    logger.start_section("STEP 4: SCORING ENGINE (DEMO)")
    scorer = ScoringEngine(analyzer=analyzer)
    scored_assets = scorer.calculate_all_scores(enriched_assets)
    logger.success(f"Successfully scored {len(scored_assets)} assets.")

    logger.start_section("STEP 5: DECISION ENGINE")
    decision_engine = DecisionEngine(metrics_path="config/scoring_metrics.json")
    final_signals = decision_engine.run_engine(scored_assets)
    logger.success(f"Generated {len(final_signals)} final signals.")

    logger.start_section("STEP 6: OUTPUT (DEMO)")
    output_manager = OutputManager(output_path="output")
    output_manager.export_signals_to_files(final_signals)
    logger.success("Exported signals to /output/ folder.")

    logger.start_section("STEP 7: TELEGRAM NOTIFICATIONS (DEMO)")
    telegram_manager = TelegramNotificationManager()
    telegram_manager.send_batch_notifications(final_signals)
    logger.success("Telegram notifications saved to /output/telegram_preview.txt")

    logger.start_section("STEP 8: BACKTESTING")
    time.sleep(1)
    run_backtest_and_generate_outputs()  # Remove the argument here
    logger.success("Backtest complete. Results are in the /output/ folder.")

    logger.start_section("DEMO WORKFLOW FINISHED")
    print("\n✅ Demo workflow complete. Check the 'output' directory for results.")

if __name__ == "__main__":
    run_demo_workflow()