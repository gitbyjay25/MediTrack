# Simple drug interaction checker
import random
from database.db_config import execute_query

def check_drug_interaction(med1, med2):
    """Check for drug interaction between two medicines"""
    
    # Check database first
    query = """
        SELECT * FROM interactions 
        WHERE (med1 = %s AND med2 = %s) OR (med1 = %s AND med2 = %s)
        ORDER BY severity_level DESC 
        LIMIT 1
    """
    result = execute_query(query, (med1, med2, med2, med1))
    
    if result and result[0]:
        interaction = result[0]
        return {
            'severity': interaction['severity_level'],
            'description': interaction['description'],
            'recommendation': interaction['recommendation']
        }
    
    # If no database interaction found, use simple rules
    interaction = check_basic_interactions(med1, med2)
    return interaction

def check_basic_interactions(med1, med2):
    """Basic rule-based interaction checking"""
    
    # Simple interaction rules
    interactions = [
        {
            'meds': ['aspirin', 'wafarin'],
            'severity': 'high',
            'description': 'Increased bleeding risk',
            'recommendation': 'Monitor bleeding closely'
        },
        {
            'meds': ['aspirin', 'ibuprofen'],
            'severity': 'medium',
            'description': 'Gastric irritation risk',
            'recommendation': 'Take with food, monitor stomach'
        }  
    ]
    
    med1_lower = med1.lower()
    med2_lower = med2.lower()
    
    for interaction in interactions:
        if med1_lower in interaction['meds'] and med2_lower in interaction['meds']:
            return {
                'severity': interaction['severity'],
                'description': interaction['description'],
                'recommendation': interaction['recommendation']
            }
    
    return None
