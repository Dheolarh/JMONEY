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
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Error: The metrics file was not found at '{path}'")
            return {}

    def run_engine(self, scored_assets: list[dict]) -> list[dict]:
        """
        Runs the full decision engine.
        """
        final_signals = []
        for asset in scored_assets:
            # Map strategy, calculate confidence, etc. (logic remains the same)
            asset = self._map_strategy(asset)
            
            confidence_score = (
                asset.get('technical_score', 0) * 0.4 +
                asset.get('macro_score', 0) * 0.4 +
                (10 - asset.get('zs10_score', 5)) * 0.2
            )
            asset['confidence_score'] = round(confidence_score, 1)

            # Calculate dynamic trade parameters
            trade_params = self.trade_calculator.calculate_trade_parameters(
                market_data=asset.get('market_data'),
                signal=asset.get('signal'),
                confidence_score=asset['confidence_score']
            )
            asset.update(trade_params)
            
            asset = self._check_jmoney_confirmation(asset)
            final_signals.append(asset)
        
        return final_signals
    
    # _map_strategy and _check_jmoney_confirmation methods remain the same
    def _map_strategy(self, asset: dict) -> dict:
        tech_score = asset.get('technical_score', 5)
        macro_score = asset.get('macro_score', 5)
        zs10_score = asset.get('zs10_score', 5)
        catalyst = asset.get('catalyst_type', "None")
        sentiment_score = asset.get('sentiment_score', 5)
        strategy = "Neutral"
        signal = "Hold"
        reasoning = []
        if zs10_score >= 7:
            strategy, signal = "Short / Avoid", "Avoid"
            reasoning.append("High trap risk detected")
        elif catalyst.lower() in ["fed", "earnings", "cpi", "jobs"] and zs10_score < 5:
            strategy, signal = "Boost", "Buy" if tech_score >= 6 else "Sell"
            reasoning.append(f"Catalyst detected: {catalyst}")
        elif tech_score >= 8 and macro_score >= 6 and zs10_score < 4:
            strategy, signal = "Zen", "Buy" if tech_score >= 8 else "Sell"
            reasoning.append("Strong technical and macro confirmation")
        elif tech_score < 5 and macro_score < 5:
            strategy, signal = "Neutral", "Hold"
            reasoning.append("Weak technical and macro scores")
        elif sentiment_score > 8 and 4 <= zs10_score < 7:
            strategy, signal = "Caution", "Hold"
            reasoning.append("High retail sentiment with moderate trap risk")
        else:
            reasoning.append("No clear signal")
        asset['strategy'], asset['signal'], asset['reasoning'] = strategy, signal, "; ".join(reasoning)
        return asset

    def _check_jmoney_confirmation(self, asset: dict) -> dict:
        # This function remains unchanged from the previous update
        # It correctly reads from config files
        if "jmoney_confirmation" not in self.metrics:
            asset['jmoney_confirmed'] = False
            asset['confirmation_reason'] = "No confirmation rules configured"
            return asset
        rules = self.metrics['jmoney_confirmation']['rules']
        required_conditions = self.metrics['jmoney_confirmation'].get('required_conditions', 99)
        conditions_met, failed_reasons, met_reasons = 0, [], []
        
        min_tech_score = rules.get('technical_score', 99)
        if asset.get('technical_score', 0) >= min_tech_score:
            conditions_met += 1
            met_reasons.append(f"Tech score: {asset.get('technical_score', 0)}/10")
        else:
            failed_reasons.append(f"Tech score low: {asset.get('technical_score', 0)} (need ≥{min_tech_score})")
        
        min_macro_score = rules.get('macro_score', 99)
        if asset.get('macro_score', 0) >= min_macro_score:
            conditions_met += 1
            met_reasons.append(f"Macro score: {asset.get('macro_score', 0)}/10")
        else:
            failed_reasons.append(f"Macro score low: {asset.get('macro_score', 0)} (need ≥{min_macro_score})")

        max_zs10_score = rules.get('zs10_score_max', 0)
        if asset.get('zs10_score', 10) < max_zs10_score:
            conditions_met += 1
            met_reasons.append(f"Low trap risk: {asset.get('zs10_score', 10)}/10")
        else:
            failed_reasons.append(f"High trap risk: {asset.get('zs10_score', 10)} (need <{max_zs10_score})")
            
        if rules.get('catalyst_required', False):
            if asset.get('catalyst_type', "None").lower() != "none":
                conditions_met += 1
                met_reasons.append(f"Catalyst: {asset.get('catalyst_type')}")
            else:
                failed_reasons.append("Catalyst required but not found")

        is_confirmed = conditions_met >= required_conditions
        asset['jmoney_confirmed'] = is_confirmed
        if is_confirmed:
            asset['confirmation_reason'] = f"{asset.get('strategy', 'Unknown')}: {', '.join(met_reasons[:2])}"
        else:
            asset['confirmation_reason'] = f"Failed: {failed_reasons[0] if failed_reasons else 'Criteria not met'}"
        return asset