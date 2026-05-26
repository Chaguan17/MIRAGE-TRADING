import logging

logger = logging.getLogger(__name__)

class ConsensusEngine:
    # Umbrales de conflicto configurables
    GLOBAL_CONFLICT_THRESHOLD = 0.8
    LAYER_CONFLICT_THRESHOLD = 0.7
    EPSILON = 1e-9

    def __init__(self, layer_weights):
        self.lw = layer_weights

    def calculate_consensus(self, basic, structure, context):
        """Calcula el consenso final mediante votación ponderada entre capas."""
        b_action, b_conf, b_name = self._layer_vote(basic)
        s_action, s_conf, s_name = self._layer_vote(structure)
        c_action, c_conf, c_name = self._layer_vote(context)

        final_votes = {1: 0.0, 0: 0.0}
        layers = [
            (b_action, b_conf, self.lw.get('basic', 1.0)),
            (s_action, s_conf, self.lw.get('structure', 1.0)),
            (c_action, c_conf, self.lw.get('context', 1.0)),
        ]

        for action, conf, weight in layers:
            if action is not None:
                final_votes[action] += conf * weight

        if final_votes[1] == 0 and final_votes[0] == 0:
            return None, 0, 'None'

        v_max = max(final_votes[1], final_votes[0])
        v_min = min(final_votes[1], final_votes[0])

        # Detección de conflicto global entre capas
        if v_min > 0 and (v_min / v_max) > self.GLOBAL_CONFLICT_THRESHOLD:
            return None, 0, 'Global Consensus Conflict'

        winner = max(final_votes, key=final_votes.get)
        total = final_votes[1] + final_votes[0] + self.EPSILON
        final_conf = final_votes[winner] / total
        
        # Selección de nombre basada en prioridad: Estructura > Básico > Contexto
        priority_map = [
            (s_action, s_name),
            (b_action, b_name),
            (c_action, c_name)
        ]
        
        method_name = next((name for act, name in priority_map if act == winner), 'Unknown')

        return winner, final_conf, method_name

    def _layer_vote(self, signals):
        """Calcula el ganador dentro de una sola capa."""
        votes = {1: 0.0, 0: 0.0}
        best_conf, best_method = 0, 'None'
        
        for name, (action, conf) in signals.items():
            if action is not None:
                votes[action] += conf
                if conf > best_conf:
                    best_conf, best_method = conf, name
                    
        if votes[1] == 0 and votes[0] == 0:
            return None, 0, 'None'

        v_max = max(votes[1], votes[0])
        v_min = min(votes[1], votes[0])
        if v_min > 0 and (v_min / v_max) > self.LAYER_CONFLICT_THRESHOLD:
            return None, 0, 'Layer Conflict'

        winner = max(votes, key=votes.get)
        total = votes[1] + votes[0] + self.EPSILON
        return winner, votes[winner] / total, best_method