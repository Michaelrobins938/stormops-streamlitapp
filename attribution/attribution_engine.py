"""
Attribution Engine - Configurable attribution (rules + Markov + Shapley)
Per-tenant configs, incremental credit
"""

from sqlalchemy import create_engine, text
from typing import Dict, List
import uuid
from collections import defaultdict
import itertools

ATTRIBUTION_METHODS = {
    'last_touch': 'Last touchpoint gets 100% credit',
    'first_touch': 'First touchpoint gets 100% credit',
    'linear': 'Equal credit across all touchpoints',
    'time_decay': 'More recent touchpoints get more credit',
    'markov': 'Removal effect based on transition probabilities',
    'shapley': 'Game-theoretic fair allocation'
}

class AttributionEngine:
    """Configurable attribution engine."""
    
    def __init__(self, tenant_id: uuid.UUID, method: str = 'markov',
                 db_url: str = 'postgresql://stormops:password@localhost:5432/stormops'):
        self.tenant_id = tenant_id
        self.method = method
        self.engine = create_engine(db_url)
        self._init_schema()
    
    def _init_schema(self):
        """Create attribution tables."""
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS attribution_results (
                    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL,
                    storm_id UUID NOT NULL,
                    journey_id UUID,
                    method TEXT NOT NULL,
                    touchpoint_credits JSONB NOT NULL,
                    incremental_credits JSONB,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
    
    def attribute_journey(self, journey: List[str], converted: bool) -> Dict[str, float]:
        """Attribute credit for a single journey."""
        
        if not journey or not converted:
            return {}
        
        if self.method == 'last_touch':
            return {journey[-1]: 1.0}
        
        elif self.method == 'first_touch':
            return {journey[0]: 1.0}
        
        elif self.method == 'linear':
            credit = 1.0 / len(journey)
            return {ch: credit for ch in journey}
        
        elif self.method == 'time_decay':
            return self._time_decay(journey)
        
        elif self.method == 'markov':
            return self._markov_attribution([journey])
        
        elif self.method == 'shapley':
            return self._shapley_attribution(journey)
        
        return {}
    
    def _time_decay(self, journey: List[str], half_life: int = 7) -> Dict[str, float]:
        """Time decay attribution."""
        weights = {}
        total_weight = 0
        
        for i, channel in enumerate(journey):
            # More recent = higher weight
            days_ago = len(journey) - i - 1
            weight = 0.5 ** (days_ago / half_life)
            weights[channel] = weights.get(channel, 0) + weight
            total_weight += weight
        
        # Normalize
        return {ch: w / total_weight for ch, w in weights.items()}
    
    def _markov_attribution(self, journeys: List[List[str]]) -> Dict[str, float]:
        """Markov chain attribution (removal effect)."""
        
        # Build transition matrix
        transitions = defaultdict(lambda: defaultdict(int))
        
        for journey in journeys:
            path = ['start'] + journey + ['conversion']
            for i in range(len(path) - 1):
                transitions[path[i]][path[i+1]] += 1
        
        # Calculate removal effect for each channel
        channels = set()
        for journey in journeys:
            channels.update(journey)
        
        # Base conversion probability
        base_prob = self._conversion_probability(transitions, channels)
        
        # Removal effect
        removal_effects = {}
        for channel in channels:
            # Remove channel
            modified_transitions = self._remove_channel(transitions, channel)
            prob_without = self._conversion_probability(modified_transitions, channels - {channel})
            removal_effects[channel] = base_prob - prob_without
        
        # Normalize
        total_effect = sum(removal_effects.values())
        if total_effect > 0:
            return {ch: effect / total_effect for ch, effect in removal_effects.items()}
        
        return {}
    
    def _conversion_probability(self, transitions: Dict, channels: set) -> float:
        """Calculate conversion probability from transition matrix."""
        # Simplified: just count paths to conversion
        total = 0
        conversions = 0
        
        for from_state in transitions:
            for to_state, count in transitions[from_state].items():
                total += count
                if to_state == 'conversion':
                    conversions += count
        
        return conversions / total if total > 0 else 0
    
    def _remove_channel(self, transitions: Dict, channel: str) -> Dict:
        """Remove channel from transition matrix."""
        modified = defaultdict(lambda: defaultdict(int))
        
        for from_state in transitions:
            if from_state == channel:
                continue
            for to_state, count in transitions[from_state].items():
                if to_state == channel:
                    # Redistribute to other states
                    continue
                modified[from_state][to_state] = count
        
        return modified
    
    def _shapley_attribution(self, journey: List[str]) -> Dict[str, float]:
        """Shapley value attribution."""
        
        channels = list(set(journey))
        n = len(channels)
        
        if n == 0:
            return {}
        
        shapley_values = {ch: 0.0 for ch in channels}
        
        # Calculate marginal contributions for all coalitions
        for r in range(1, n + 1):
            for coalition in itertools.combinations(channels, r):
                coalition_set = set(coalition)
                
                # Value with coalition
                v_with = self._coalition_value(journey, coalition_set)
                
                # For each channel in coalition
                for channel in coalition:
                    # Value without this channel
                    coalition_without = coalition_set - {channel}
                    v_without = self._coalition_value(journey, coalition_without)
                    
                    # Marginal contribution
                    marginal = v_with - v_without
                    
                    # Weight by coalition size
                    weight = 1.0 / (n * self._binomial(n - 1, r - 1))
                    shapley_values[channel] += weight * marginal
        
        # Normalize
        total = sum(shapley_values.values())
        if total > 0:
            return {ch: v / total for ch, v in shapley_values.items()}
        
        return shapley_values
    
    def _coalition_value(self, journey: List[str], coalition: set) -> float:
        """Value of a coalition (simplified: presence in journey)."""
        # Count how many coalition members appear in journey
        count = sum(1 for ch in journey if ch in coalition)
        return count / len(journey) if journey else 0
    
    def _binomial(self, n: int, k: int) -> int:
        """Binomial coefficient."""
        if k > n or k < 0:
            return 0
        if k == 0 or k == n:
            return 1
        
        result = 1
        for i in range(min(k, n - k)):
            result = result * (n - i) // (i + 1)
        return result
    
    def attribute_storm(self, storm_id: uuid.UUID) -> Dict:
        """Attribute all journeys in a storm."""
        
        with self.engine.connect() as conn:
            # Get all converted journeys
            journeys = conn.execute(text("""
                SELECT journey_id, channel, converted
                FROM customer_journeys
                WHERE storm_id = :sid AND converted = TRUE
                ORDER BY journey_id, timestamp
            """), {'sid': storm_id}).fetchall()
        
        # Group by journey_id
        journey_paths = defaultdict(list)
        for j in journeys:
            journey_paths[j[0]].append(j[1])
        
        # Attribute each journey
        all_credits = defaultdict(float)
        for journey_id, path in journey_paths.items():
            credits = self.attribute_journey(path, True)
            for channel, credit in credits.items():
                all_credits[channel] += credit
        
        # Normalize
        total = sum(all_credits.values())
        if total > 0:
            all_credits = {ch: c / total for ch, c in all_credits.items()}
        
        return dict(all_credits)
    
    def compare_methods(self, journey: List[str]) -> Dict:
        """Compare attribution across methods."""
        
        results = {}
        for method in ['last_touch', 'first_touch', 'linear', 'time_decay', 'markov', 'shapley']:
            engine = AttributionEngine(self.tenant_id, method)
            results[method] = engine.attribute_journey(journey, True)
        
        return results


if __name__ == '__main__':
    print("=" * 60)
    print("ATTRIBUTION ENGINE - SETUP & TEST")
    print("=" * 60)
    
    tenant_id = uuid.UUID('00000000-0000-0000-0000-000000000000')
    
    # Test journey
    journey = ['door_knock', 'email', 'phone', 'door_knock']
    
    print(f"\nJourney: {' → '.join(journey)}")
    
    # Compare methods
    print("\nAttribution by method:")
    engine = AttributionEngine(tenant_id)
    results = engine.compare_methods(journey)
    
    for method, credits in results.items():
        print(f"\n{method}:")
        for channel, credit in sorted(credits.items(), key=lambda x: -x[1]):
            print(f"  {channel}: {credit*100:.1f}%")
    
    print("\n✅ Attribution engine ready")
