if batch_mode or (isinstance(input_data, list) and len(input_data) > 1):
    return self._process_batch(input_data, output_format)
