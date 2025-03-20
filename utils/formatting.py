import pandas as pd
import numpy as np
import streamlit as st

def format_currency(value, precision=2, prefix="$", with_color=True):
    """Format a value as currency with color coding for positive/negative values.
    
    Args:
        value (float): The value to format
        precision (int): The number of decimal places
        prefix (str): Currency symbol prefix
        with_color (bool): Whether to apply color coding
        
    Returns:
        str: Formatted HTML string
    """
    # Handle None values
    if value is None:
        return "--"
    
    # Format the number
    formatted = f"{prefix}{abs(value):,.{precision}f}"
    
    # Apply color coding if requested
    if with_color:
        if value > 0:
            return f'<span class="profit">{formatted}</span>'
        elif value < 0:
            return f'<span class="loss">-{formatted}</span>'
        else:
            return formatted
    else:
        if value < 0:
            return f"-{formatted}"
        return formatted

def format_percentage(value, precision=2, with_color=True):
    """Format a value as percentage with color coding for positive/negative values.
    
    Args:
        value (float): The value to format
        precision (int): The number of decimal places
        with_color (bool): Whether to apply color coding
        
    Returns:
        str: Formatted HTML string
    """
    # Handle None values
    if value is None:
        return "--"
    
    # Format the number
    formatted = f"{abs(value):.{precision}f}%"
    
    # Apply color coding if requested
    if with_color:
        if value > 0:
            return f'<span class="profit">{formatted}</span>'
        elif value < 0:
            return f'<span class="loss">-{formatted}</span>'
        else:
            return formatted
    else:
        if value < 0:
            return f"-{formatted}"
        return formatted

def create_delta_badge(value, precision=2):
    """Create a badge for delta values with appropriate coloring.
    
    Args:
        value (float): The delta value
        precision (int): The number of decimal places
        
    Returns:
        str: HTML for the badge
    """
    if value is None:
        return ""
        
    badge_class = ""
    if value > 0:
        badge_class = "badge-success"
    elif value < 0:
        badge_class = "badge-danger"
    else:
        badge_class = "badge-warning"
    
    formatted = f"{abs(value):,.{precision}f}"
    sign = "+" if value > 0 else "-" if value < 0 else ""
    
    return f'<span class="badge {badge_class}">{sign}{formatted}</span>'

def format_number(value, precision=2, with_separator=True):
    """Format a number with appropriate precision.
    
    Args:
        value (float): The value to format
        precision (int): The number of decimal places
        with_separator (bool): Whether to include thousand separators
        
    Returns:
        str: Formatted number
    """
    if value is None:
        return "--"
        
    if with_separator:
        return f"{value:,.{precision}f}"
    else:
        return f"{value:.{precision}f}"

def apply_table_styles(df):
    """Apply styles to a DataFrame for displaying as a table.
    
    Args:
        df (pd.DataFrame): The DataFrame to style
        
    Returns:
        pd.DataFrame.style: Styled DataFrame
    """
    return df.style.format({
        'price': '${:.2f}',
        'value': '${:,.2f}',
        'pnl': '${:,.2f}',
        'funding': '${:,.4f}',
        'rate': '{:.4%}',
    }).applymap(
        lambda x: 'color: #05C270' if isinstance(x, (int, float)) and x > 0 else 
                 'color: #FF5C5C' if isinstance(x, (int, float)) and x < 0 else '',
        subset=['pnl', 'funding', 'rate']
    ) 