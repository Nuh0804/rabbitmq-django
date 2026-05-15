import base64
import re
import sys
from urllib.parse import urlparse
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class Validator:
    @staticmethod
    def validate_phone_number(value):
        """Validates a phone number.

        Args:
            value: A string representing the phone number to validate.

        Returns:
            True if the phone number is valid, False otherwise.
        """
        pattern = r'^(?:\+255|255|0)[67]\d{8}$'
        return True if re.match(pattern, value) else False

    @staticmethod
    def validate_email(value):
        """Validates an email address.

        Args:
            value: A string representing the email address to validate.

        Returns:
            True if the email address is valid, False otherwise.
        """
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return True if re.match(pattern, value) else False

    @staticmethod
    def validate_url(value):
        try:
            result = urlparse(value)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    @staticmethod
    def validate_base64_string_size(value):
        """
        Validates the size of a base64 string.
        
        Args:
            value (str): The base64 string to be validated.
            
        Returns:
            bool: True if the size of the decoded string is less than or equal to 20 MB (megabytes),
                  False otherwise.
        """
        # Decode the base64 string to bytes
        decoded_bytes = base64.b64decode(value)

        # Get the size of the decoded bytes in bytes
        size_in_bytes = sys.getsizeof(decoded_bytes)

        # Convert bytes to kilobytes for a more readable size
        size_in_kilobytes = size_in_bytes / 1024
        return True if size_in_kilobytes <= 20 * 1024 else False
    
    @staticmethod
    def is_strong_password(password):
        try:
            validate_password(password)
            return True
    
        except ValidationError as _:
            return False
