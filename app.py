def build_logical_xpath(element):
    """
    Constructs the logical XPath by traversing upwards and collecting 
    ALL 'path' attributes and 'id' flags (data/policy) to handle nested 
    and inherited groups correctly.
    """
    path_segments = []
    current = element
    
    while current is not None:
        # Check for 'path' attribute first (covers most nested groups) 
        if 'path' in current.attrib:
            path_segments.insert(0, current.get('path')) [cite: 14]
        
        # Check for root-level identifiers (data or policy) 
        elif current.tag == 'object' and 'id' in current.attrib:
            object_id = current.get('id').lower() [cite: 15]
            if object_id in ['data', 'policy']:
                path_segments.insert(0, object_id) [cite: 15]
        
        # Stop if we hit the top-level container [cite: 16]
        elif current.tag in ('model', 'ManuScript'):
            break [cite: 16]
            
        current = current.getparent() [cite: 16]
    
    # Filter out empty segments and join with slashes
    return "/".join([seg for seg in path_segments if seg]) [cite: 16]
