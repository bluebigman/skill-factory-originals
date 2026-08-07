valid, err_code = validate_input(input_data)
if not valid:
    raise ValueError(error_message(err_code))
