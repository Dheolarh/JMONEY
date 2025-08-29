import json
import numpy as np
from .backtester import Backtester
from .output_manager import OutputManager
from .decision_engine import DecisionEngine

class Optimizer:
    """
    Optimizes scoring weights based on backtesting results using Grid Search.
    """
    def __init__(self, output_manager: OutputManager, metrics_path: str):
        self.output_manager = output_manager
        self.backtester = Backtester(output_manager)
        self.metrics_path = metrics_path

    def run_optimization(self):
        """
        Runs the Grid Search optimization process.
        """
        print("--- Starting Optimization ---")

        param_grid = {
            'technical_score': np.arange(6.0, 9.5, 0.5),
            'macro_score': np.arange(5.0, 8.5, 0.5)
        }

        best_params = {}
        best_performance = -1

        # Get all signals from Google Sheets to use for backtesting
        worksheet = self.output_manager._get_worksheet()
        if not worksheet:
            print("Cannot optimize without access to Google Sheets.")
            return

        all_signals = worksheet.get_all_records()

        decision_engine = DecisionEngine(metrics_path=self.metrics_path)

        # --- Grid Search ---
        for tech_score in param_grid['technical_score']:
            for macro_score in param_grid['macro_score']:
                print(f"\nTesting params: technical_score={tech_score}, macro_score={macro_score}")
                
                # Temporarily update metrics for the decision engine
                temp_metrics = {
                    "jmoney_confirmation": {
                        "required_conditions": 3,
                        "rules": {
                            "technical_score": tech_score,
                            "macro_score": macro_score
                        }
                    }
                }
                
                decision_engine.metrics = temp_metrics
                

                backtest_results = self.backtester.run_backtest(all_signals)

                # Evaluate performance (e.g., based on win rate)
                if backtest_results['win_rate'] > best_performance:
                    best_performance = backtest_results['win_rate']
                    best_params = {'technical_score': tech_score, 'macro_score': macro_score}
        
        print(f"\n--- Optimization Complete ---")
        print(f"Best Win Rate: {best_performance:.2f}%")
        print(f"Best Parameters: {best_params}")

        final_metrics = {
            "jmoney_confirmation": {
                "required_conditions": 3,
                "rules": best_params
            }
        }
        with open(self.metrics_path, 'w') as f:
            json.dump(final_metrics, f, indent=2)
        
        print(f"\n✅ {self.metrics_path} has been updated with the optimal parameters.")