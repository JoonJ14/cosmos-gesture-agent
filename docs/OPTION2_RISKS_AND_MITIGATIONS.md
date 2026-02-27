# OPTION2_RISKS_AND_MITIGATIONS

## Risks and mitigations for teacher-student loop

1. **Label noise from ambiguous frames**
- Mitigation: require multi-frame context windows and conservative reject defaults for uncertain classes.

2. **Teacher latency too high for real-time gate**
- Mitigation: keep teacher as selective gate (safe mode) and use timeout-based no-execute policy.

3. **Student overfitting to synthetic or narrow user behavior**
- Mitigation: diversify capture scenarios and include hard negatives across users and lighting conditions.

4. **Class imbalance (few positive command examples)**
- Mitigation: active sampling of rare intents and weighted training objectives.

5. **Policy drift between student and teacher**
- Mitigation: periodic calibration set and disagreement dashboards keyed by `event_id` and reason category.

6. **Unsafe false positives in social/reaching contexts**
- Mitigation: explicit negative classes (`self_grooming`, `reaching_object`, `conversation_gesture`) and stricter decision thresholds.

7. **Schema contract breakage across services**
- Mitigation: strict schema validation in verifier and integration tests that reject additional fields.

8. **Privacy concerns from frame retention**
- Mitigation: default to landmark summaries, minimal retention windows, and configurable frame redaction/disable.
