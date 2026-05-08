import pandas as pd

from audit_cohérence.core.base_metric import BaseMetric
from audit_cohérence.core.models import ANOMALY_COLUMNS
from audit_cohérence.metric_cohérence.rules.code_normalisation import check_code_normalisation
from audit_cohérence.metric_cohérence.rules.sequence_chronologie import check_sequence_vs_chronologie
from audit_cohérence.metric_cohérence.rules.session_types import (
    check_type_encoding_consistency,
    check_unexpected_session_types,
)


class CoherenceMetric(BaseMetric):
    name = "coherence"
    description = "Cohérence inter-sources des données IDU — 3 axes"

    def run(self, data: dict) -> pd.DataFrame:
        rows: list[dict] = []
        rows += check_code_normalisation(data)          # Axe 1
        rows += check_unexpected_session_types(data)    # Axe 4
        rows += check_sequence_vs_chronologie(data)     # Axe 6
        rows += check_type_encoding_consistency(data)   # Axe 8

        if not rows:
            return self._empty_df()
        return pd.DataFrame(rows)[ANOMALY_COLUMNS]
