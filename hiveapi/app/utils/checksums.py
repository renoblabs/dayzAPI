"""
Checksum utilities for DayZ HiveAPI.

This module provides functions for computing stable checksums of data structures,
which are used for detecting conflicts and ensuring data integrity.
"""

import json
import hashlib
from typing import Union, Dict, List, Any

def compute_checksum(data: Union[Dict, List, Any]) -> str:
    """
    Compute a stable SHA-256 checksum of data.
    Uses canonical JSON representation with sorted keys to ensure consistency.
    
    Args:
        data: Dictionary, list, or other JSON-serializable data to checksum
        
    Returns:
        SHA-256 hexadecimal digest
    
    Examples:
        >>> compute_checksum({"b": 2, "a": 1})
        >>> compute_checksum({"a": 1, "b": 2})  # Same result as above
    """
    # Convert to canonical JSON (sorted keys, no whitespace)
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    
    # Compute SHA-256
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def compute_inventory_checksum(slots_json: Dict[str, Any]) -> str:
    """
    Compute a stable checksum for inventory slots.
    Wrapper around compute_checksum specialized for inventory data.
    
    Args:
        slots_json: Inventory slots data
        
    Returns:
        SHA-256 hexadecimal digest
    """
    return compute_checksum(slots_json)
