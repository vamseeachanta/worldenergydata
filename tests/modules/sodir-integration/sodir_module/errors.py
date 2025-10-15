"""
SODIR module custom exceptions and error handling.
"""


class SodirError(Exception):
    """Base exception for SODIR module."""
    pass


class SodirAPIError(SodirError):
    """Exception raised for SODIR API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        """
        Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_data: Response data from API if available
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class SodirConfigurationError(SodirError):
    """Exception raised for configuration errors."""
    pass


class SodirDataError(SodirError):
    """Exception raised for data processing errors."""
    pass


class SodirValidationError(SodirError):
    """Exception raised for data validation errors."""
    pass


class SodirRateLimitError(SodirAPIError):
    """Exception raised when API rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
        """
        super().__init__(message, status_code=429)
        self.retry_after = retry_after