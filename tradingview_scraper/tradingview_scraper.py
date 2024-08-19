from pydantic import BaseModel, field_validator

class Symbols(BaseModel):
    symbol: str
    export_type: str = None

    @field_validator('export_type')
    def check_export_type(cls, value):
        if value not in ['csv', 'json', None]:
            raise ValueError("export_type must be either 'csv', 'json', or None")
        return value

    @field_validator('symbol')
    def validate_symbol(cls, value):
        # Add any specific validation rules for symbol here
        if not value.isalnum():
            raise ValueError("symbol must be alphanumeric")
        return value
