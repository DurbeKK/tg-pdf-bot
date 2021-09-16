"""
This module (containing only one function) will be used to display the file
sizes in a human-readable format to the user once the PDF compression is over.
"""

def convert_bytes(num):
    """
    This function will convert bytes to bytes, KB, MB.
    """
    for x in ['bytes', 'KB', 'MB']:
        if num < 1024.0:
            return f"{num:3.1f} {x}"
        num /= 1024.0
