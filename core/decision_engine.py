import json
from .trade_calculator import TradeCalculator 

class DecisionEngine:
    """
    Applies the final strategy mapping and confirmation logic to scored assets.
    """
    def __init__(self, metrics_path: str):
        """
        Initializes the DecisionEngine.
        """
        self.metrics = self._load_metrics(metrics_path)
        self.trade_calculator = TradeCalculator()

    def _load_metrics(self, path: str) -> dict:
        """Loads scoring metrics from a JSON file."""
        print(f"Loading scoring metrics from: {path}")
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: The metrics file was not found at '{path}'")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Could not decode the JSON from '{path}'")
            return {}

    def _map_strategy(self, asset: dict) -> dict:
        """
        Returns strategy type, signal, and reasoning based on asset scores.
        """
        tech_score = asset.get('technical_score', 5)
        macro_score = asset.get('macro_score', 5)
        zs10_score = asset.get('zs10_score', 5)
        catalyst = asset.get('catalyst_type', "None")
        sentiment_score = asset.get('sentiment_score', 5)

        strategy = "Neutral"
        signal = "Neutral"
        reasoning = []

        if zs10_score >= 7:
            strategy = "Short / Avoid"
            signal = "Avoid"
            reasoning.append("High trap risk detected by ZS-10+ score")
        elif catalyst.lower() in ["fed", "earnings", "cpi", "jobs"] and zs10_score < 5:
            strategy = "Boost"
            signal = "Buy" if tech_score >= 6 else "Sell"
            reasoning.append(f"Catalyst detected: {catalyst}")
        elif tech_score >= 8 and macro_score >= 6 and zs10_score < 4:
            strategy = "Zen"
            signal = "Buy" if tech_score >= 8 else "Sell"
            reasoning.append("Strong technical and macro confirmation, low trap risk")
        elif tech_score < 5 and macro_score < 5:
            strategy = "Neutral"
            signal = "Neutral"
            reasoning.append("Weak technical and macro scores")
        elif sentiment_score > 8 and 4 <= zs10_score < 7:
            strategy = "Caution"
            signal = "Caution"
            reasoning.append("High retail sentiment with moderate trap risk")
        else:
            reasoning.append("No clear signal")

        asset['strategy'] = strategy
        asset['signal'] = signal
        asset['reasoning'] = "; ".join(reasoning)
        return asset

    def _check_jmoney_confirmation(self, asset: dict) -> dict:
        """
        Checks if a signal meets the 'JMoney Confirmed' criteria.
        """
        if not self.metrics or "jmoney_confirmation" not in self.metrics:
            asset['jmoney_confirmed'] = False
            asset['confirmation_reason'] = "No confirmation rules configured"
            return asset

        rules = self.metrics['jmoney_confirmation']['rules']
        required_conditions = self.metrics['jmoney_confirmation']['required_conditions']
        
        conditions_met = 0
        failed_reasons = []
        met_reasons = []
        
        # Check technical score
        if asset.get('technical_score', 0) >= rules.get('technical_score', 8):
            conditions_met += 1
            met_reasons.append(f"Technical score: {asset.get('technical_score', 0)}/10")
        else:
            failed_reasons.append(f"Technical score too low: {asset.get('technical_score', 0)}/10 (need ≥{rules.get('technical_score', 8)})")
        
        # Check macro score
        if asset.get('macro_score', 0) >= rules.get('macro_score', 6):
            conditions_met += 1
            met_reasons.append(f"Macro score: {asset.get('macro_score', 0)}/10")
        else:
            failed_reasons.append(f"Macro score too low: {asset.get('macro_score', 0)}/10 (need ≥{rules.get('macro_score', 6)})")
        
        # Check ZS-10+ score (lower is better)
        if asset.get('zs10_score', 10) < 4:
            conditions_met += 1
            met_reasons.append(f"Low trap risk: {asset.get('zs10_score', 10)}/10")
        else:
            failed_reasons.append(f"High trap risk: {asset.get('zs10_score', 10)}/10 (need <4)")
        
        # Check catalyst presence
        if asset.get('catalyst_type', "None").lower() != "none":
            conditions_met += 1
            met_reasons.append(f"Strong catalyst: {asset.get('catalyst_type', 'Present')}")
        else:
            failed_reasons.append("No significant catalyst detected")

        # Determine confirmation status
        is_confirmed = conditions_met >= required_conditions
        asset['jmoney_confirmed'] = is_confirmed
        
        # Create detailed confirmation reason
        if is_confirmed:
            strategy = asset.get('strategy', 'Unknown')
            asset['confirmation_reason'] = f"{strategy} strategy: {', '.join(met_reasons[:2])}"  # Show top 2 reasons
        else:
            asset['confirmation_reason'] = f"Failed: {failed_reasons[0] if failed_reasons else 'Unknown criteria'}"
        
        return asset

    def run_engine(self, scored_assets: list[dict]) -> list[dict]:
        """
        Runs the full decision engine, now including trade parameter calculations.
        """
        final_signals = []
        for asset in scored_assets:
            print(f"--> Making decision for: {asset.get('ticker')}")
            
            asset_with_strategy = self._map_strategy(asset)
            
            trade_params = self.trade_calculator.calculate_trade_parameters(
                market_data=asset.get('market_data'),
                signal=asset_with_strategy.get('signal')
            )
            asset_with_strategy.update(trade_params)
            
            confirmed_asset = self._check_jmoney_confirmation(asset_with_strategy)
            
            final_signals.append(confirmed_asset)
        
        return final_signals
