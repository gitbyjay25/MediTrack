# Simple drug interaction checker
from database.db_config import execute_query

def check_drug_interaction(med1, med2):
    query = """
        SELECT * FROM interactions 
        WHERE (drug1 = %s AND drug2 = %s) OR (drug1 = %s AND drug2 = %s)
        ORDER BY 
            CASE severity_level 
                WHEN 'High' THEN 1 
                WHEN 'Medium' THEN 2 
                WHEN 'Low' THEN 3 
                ELSE 4 
            END
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
    
    return None
