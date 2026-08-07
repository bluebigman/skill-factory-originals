def process_batch(self, raw_inputs: List[str]) -> List[ProcessedItem]:
    if not raw_inputs:
        raise_error("E001")
    ...
