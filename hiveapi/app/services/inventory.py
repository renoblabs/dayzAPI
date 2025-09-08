"""
Inventory service for DayZ HiveAPI.

This module handles inventory operations and checksums for conflict detection.
Implements CRDT-like operations for inventory synchronization.
"""

import json
import hashlib
import logging
from typing import Dict, List, Any, Union
import copy

logger = logging.getLogger(__name__)

def compute_checksum(data: Union[Dict, List]) -> str:
    """
    Compute a stable SHA-256 checksum of inventory data.
    Uses canonical JSON representation to ensure consistency.
    
    Args:
        data: Dictionary or list to checksum
        
    Returns:
        SHA-256 hexadecimal digest
    """
    # Convert to canonical JSON (sorted keys, no whitespace)
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    
    # Compute SHA-256
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def compute_inventory_checksum(slots_json: Dict[str, Any]) -> str:
    """
    Compute a stable checksum for inventory slots.
    
    Args:
        slots_json: Inventory slots data
        
    Returns:
        SHA-256 hexadecimal digest
    """
    return compute_checksum(slots_json)

def apply_ops(slots_json: Dict[str, Any], ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply a list of operations to inventory slots.
    Operations are applied sequentially in order.
    
    Args:
        slots_json: Current inventory slots
        ops: List of operations to apply
        
    Returns:
        Updated inventory slots
    """
    # Create a deep copy to avoid modifying the original
    result = copy.deepcopy(slots_json)
    
    # Process each operation
    for op in ops:
        op_type = op.get('op', '').lower()
        path = op.get('path', '')
        item = op.get('item', {})
        
        if not path:
            logger.warning(f"Skipping operation with empty path: {op}")
            continue
            
        try:
            if op_type == 'add':
                result = apply_add_op(result, path, item)
            elif op_type == 'remove':
                result = apply_remove_op(result, path, item)
            elif op_type == 'move':
                result = apply_move_op(result, path, item)
            elif op_type == 'update':
                result = apply_update_op(result, path, item)
            else:
                logger.warning(f"Unknown operation type: {op_type}")
        except Exception as e:
            logger.error(f"Error applying operation {op_type} at {path}: {str(e)}")
    
    return result

def get_path_value(data: Dict[str, Any], path: str) -> Any:
    """
    Get a value at a specific path in a nested dictionary.
    
    Args:
        data: Dictionary to navigate
        path: Dot-separated path (e.g., "slots.backpack.items")
        
    Returns:
        Value at the path or None if not found
    """
    if not path:
        return data
        
    parts = path.split('.')
    current = data
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
            
    return current

def set_path_value(data: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
    """
    Set a value at a specific path in a nested dictionary.
    Creates intermediate dictionaries if they don't exist.
    
    Args:
        data: Dictionary to modify
        path: Dot-separated path (e.g., "slots.backpack.items")
        value: Value to set
        
    Returns:
        Modified dictionary
    """
    if not path:
        # Replace entire data
        if isinstance(value, dict):
            return value
        else:
            logger.warning("Cannot replace root with non-dict value")
            return data
    
    result = copy.deepcopy(data)
    parts = path.split('.')
    current = result
    
    # Navigate to the parent of the target
    for i, part in enumerate(parts[:-1]):
        if part not in current:
            current[part] = {}
        current = current[part]
    
    # Set the value
    current[parts[-1]] = value
    return result

def delete_path_value(data: Dict[str, Any], path: str) -> Dict[str, Any]:
    """
    Delete a value at a specific path in a nested dictionary.
    
    Args:
        data: Dictionary to modify
        path: Dot-separated path (e.g., "slots.backpack.items")
        
    Returns:
        Modified dictionary
    """
    if not path:
        logger.warning("Cannot delete root path")
        return data
    
    result = copy.deepcopy(data)
    parts = path.split('.')
    current = result
    
    # Navigate to the parent of the target
    for i, part in enumerate(parts[:-1]):
        if part not in current:
            # Path doesn't exist, nothing to delete
            return result
        current = current[part]
    
    # Delete the value if it exists
    if parts[-1] in current:
        del current[parts[-1]]
    
    return result

def apply_add_op(data: Dict[str, Any], path: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply an 'add' operation to add an item at the specified path.
    
    Args:
        data: Current inventory data
        path: Path where to add the item
        item: Item to add
        
    Returns:
        Updated inventory data
    """
    target = get_path_value(data, path)
    
    if target is None:
        # Path doesn't exist, create it with the item
        return set_path_value(data, path, item)
    elif isinstance(target, list):
        # Append to list
        new_list = target + [item]
        return set_path_value(data, path, new_list)
    elif isinstance(target, dict):
        # Merge dictionaries
        new_dict = {**target, **item}
        return set_path_value(data, path, new_dict)
    else:
        # Replace value
        return set_path_value(data, path, item)

def apply_remove_op(data: Dict[str, Any], path: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a 'remove' operation to remove an item.
    
    Args:
        data: Current inventory data
        path: Path to the item to remove
        item: Item details (may contain id or other identifying info)
        
    Returns:
        Updated inventory data
    """
    # If item has an id field, we might be removing from a list by id
    if 'id' in item and isinstance(item['id'], str):
        parent_path = '.'.join(path.split('.')[:-1])
        parent = get_path_value(data, parent_path)
        
        if isinstance(parent, list):
            # Filter out the item with matching id
            new_list = [i for i in parent if i.get('id') != item['id']]
            return set_path_value(data, parent_path, new_list)
    
    # Simple path deletion
    return delete_path_value(data, path)

def apply_move_op(data: Dict[str, Any], path: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a 'move' operation to move an item from one location to another.
    
    Args:
        data: Current inventory data
        path: Destination path
        item: Item to move, including 'from_path' field
        
    Returns:
        Updated inventory data
    """
    from_path = item.get('from_path')
    if not from_path:
        logger.warning("Move operation missing from_path")
        return data
    
    # Get the item to move
    move_item = get_path_value(data, from_path)
    if move_item is None:
        logger.warning(f"Item at {from_path} not found for move operation")
        return data
    
    # Remove from source
    intermediate = delete_path_value(data, from_path)
    
    # Add to destination
    return apply_add_op(intermediate, path, move_item)

def apply_update_op(data: Dict[str, Any], path: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply an 'update' operation to update properties of an item.
    
    Args:
        data: Current inventory data
        path: Path to the item to update
        item: New properties to set
        
    Returns:
        Updated inventory data
    """
    target = get_path_value(data, path)
    
    if target is None:
        # Path doesn't exist, create it
        return set_path_value(data, path, item)
    elif isinstance(target, dict):
        # Merge dictionaries
        new_dict = {**target, **item}
        return set_path_value(data, path, new_dict)
    else:
        # Replace value
        return set_path_value(data, path, item)

def detect_conflicts(old_slots: Dict[str, Any], new_slots: Dict[str, Any]) -> bool:
    """
    Detect potential conflicts between two inventory states.
    This is a simple implementation that checks for key differences.
    
    Args:
        old_slots: Previous inventory state
        new_slots: New inventory state
        
    Returns:
        True if potential conflicts detected, False otherwise
    """
    # For MVP, just check if any keys were removed
    if isinstance(old_slots, dict) and isinstance(new_slots, dict):
        for key in old_slots:
            if key not in new_slots:
                return True
                
            if isinstance(old_slots[key], dict) and isinstance(new_slots[key], dict):
                if detect_conflicts(old_slots[key], new_slots[key]):
                    return True
    
    return False
