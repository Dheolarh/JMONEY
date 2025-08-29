import json
import random
from .backtester import Backtester
from .output_manager import OutputManager
from .decision_engine import DecisionEngine
from .ai_analyzer import AIAnalyzer

class Optimizer:
    """
    Optimizes scoring weights using an AI-driven iterative approach.
    """
    def __init__(self, output_manager: OutputManager, metrics_path: str, ai_analyzer: AIAnalyzer):
        self.output_manager = output_manager
        self.backtester = Backtester(output_manager)
        self.metrics_path = metrics_path
        self.ai_analyzer = ai_analyzer
        self.ticker_cache = {}

    def _get_ai_suggested_params(self, last_params: dict, last_performance: dict) -> dict:
        """Asks the AI to suggest new parameters based on the last run."""
        print("    --> Asking AI for new parameter suggestions...")
        
        system_message = (
            "You are a quantitative analyst specializing in optimizing trading algorithms. "
            "Your task is to suggest new parameters to improve a strategy's backtested performance. "
            "Respond with only a valid JSON object with the keys 'technical_score' and 'macro_score'."
        )
        
        user_prompt = (
            f"The current trading strategy uses two confirmation rules: a minimum 'technical_score' and a minimum 'macro_score'. "
            f"We are trying to find the optimal values for these scores.\n\n"
            f"Previous Test:\n"
            f"- technical_score: {last_params.get('technical_score')}\n"
            f"- macro_score: {last_params.get('macro_score')}\n"
            f"- win_rate: {last_performance.get('win_rate', 0):.2f}%\n\n"
            f"Goal: Suggest a *new* set of parameters that might increase the win_rate. Be analytical. For example, "
            f"if the win rate is low, perhaps the rules are too loose and need to be stricter (higher scores). "
            f"If very few trades are happening, the rules might be too tight.\n\n"
            f"Parameter Ranges:\n"
            f"- 'technical_score' must be between 6.0 and 9.5.\n"
            f"- 'macro_score' must be between 5.0 and 8.5."
        )

        try:
            response_text = self.ai_analyzer._call_ai_provider(system_message, user_prompt, max_tokens=100)
            cleaned_response = self.ai_analyzer._clean_ai_response(response_text)
            new_params = json.loads(cleaned_response)
            print(f"    ...AI suggested: {new_params}")
            return new_params
        except Exception as e:
            print(f"    [WARNING] AI suggestion failed: {e}. Falling back to random suggestion.")
            # Fallback to a random suggestion if AI fails
            return {
                'technical_score': round(random.uniform(6.0, 9.5), 1),
                'macro_score': round(random.uniform(5.0, 8.5), 1)
            }
        
    def _ai_normalize_ticker(self, ticker: str, source: str) -> str:
        cache_key = f"{ticker}|{source}"
        if cache_key in self.ticker_cache:
            return self.ticker_cache[cache_key]
        prompt = (
            f"Given the trading ticker '{ticker}', what is the correct ticker format to use for the {source} data source (e.g., Yahoo Finance)? "
            "Reply with only the correct ticker string."
        )
        normalized = self.ai_analyzer._call_ai_provider("", prompt, max_tokens=20)
        normalized = normalized.strip()
        self.ticker_cache[cache_key] = normalized
        return normalized

    def run_optimization(self, iterations: int = 2):
        print("--- Starting AI-Driven Optimization ---")
    
        worksheet = self.output_manager._get_worksheet()
        if not worksheet:
            print("Cannot optimize without access to Google Sheets.")
            return
    
        all_signals = worksheet.get_all_records()
        decision_engine = DecisionEngine(metrics_path=self.metrics_path)
    
        best_params = {}
        best_performance = {"win_rate": -1}
    
        current_params = decision_engine.metrics.get('jmoney_confirmation', {}).get('rules', {})
        if not current_params:
            current_params = {'technical_score': 7.5, 'macro_score': 6.0}
    
        for i in range(max(2, iterations)):
            print(f"\n--- Iteration {i + 1}/{max(2, iterations)} ---")
            print(f"Testing params: {current_params}")
    
            temp_metrics = {"jmoney_confirmation": {"required_conditions": 3, "rules": current_params}}
            decision_engine.metrics = temp_metrics
    
            normalized_signals = []
            for signal in all_signals:
                ticker = signal.get('Ticker') or signal.get('ticker')
                if not ticker:
                    continue
                normalized_ticker = self._ai_normalize_ticker(ticker, "yahoo")
                signal['Ticker'] = normalized_ticker
                normalized_signals.append(signal)
    
            backtest_results = self.backtester.run_backtest(normalized_signals)
            print(f"Performance: Win Rate = {backtest_results.get('win_rate', 0):.2f}%")
    
            if backtest_results.get('win_rate', 0) > best_performance.get('win_rate', -1):
                best_performance = backtest_results
                best_params = current_params
                print(f"New best performance found!")
    
            # Always get new params for next iteration (even if only 2 iterations)
            current_params = self._get_ai_suggested_params(current_params, backtest_results)
    
        print(f"\n--- Optimization Complete ---")
        print(f"Best Win Rate Found: {best_performance.get('win_rate', 0):.2f}%")
        print(f"Best Parameters: {best_params}")
    
        if best_params:
            final_metrics = {"jmoney_confirmation": {"required_conditions": 3, "rules": best_params}}
            with open(self.metrics_path, 'w') as f:
                json.dump(final_metrics, f, indent=2)
            print(f"\n✅ {self.metrics_path} has been updated with the optimal parameters.")