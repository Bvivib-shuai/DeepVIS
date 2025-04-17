import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import re
from io import StringIO
import calendar
from datetime import datetime

def parse_vql(vql_query):
    vql_query = ' '.join(vql_query.split())
    
    column_pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
    agg_function_pattern = r'(?:COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT)\s*\(\s*(?:\*|' + column_pattern + r')\s*\)'
    column_or_agg_pattern = f'(?:{agg_function_pattern}|{column_pattern})'
    
    parts = {
        'visualize': r'^Visualize\s+(?P<chart_type>line|bar|pie|scatter)\s+',
        'select': rf'SELECT\s+(?P<select_cols>{column_or_agg_pattern}\s*,\s*{column_or_agg_pattern})\s+',
        'from': rf'FROM\s+(?P<from_tables>{column_pattern})\s*',
        'where': r'(?:WHERE\s+(?P<where_cond>(?:(?!GROUP\s+BY|ORDER\s+BY|LIMIT|BIN).)+)\s*)?',
        'group': rf'(?:GROUP\s+BY\s+(?P<group_cols>{column_or_agg_pattern})\s*)?',
        'order': rf'(?:ORDER\s+BY\s+(?P<order_cols>{column_or_agg_pattern}))(?:\s+(?P<order_dir>ASC|DESC)\s*)?',
        'limit': r'(?:LIMIT\s+(?P<limit_num>\d+)\s*)?',
        'bin': rf'(?:BIN\s+(?P<bin_col>{column_pattern})\s+BY\s+(?P<bin_unit>day|weekday|month|year)\s*)?$'
    }
    
    result = {}
    remaining_query = vql_query
    
    try:
        match = re.match(parts['visualize'], remaining_query, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid VISUALIZE clause. Must be: Visualize line|bar|pie|scatter")
        result.update(match.groupdict())
        remaining_query = remaining_query[match.end():].strip()
        
        match = re.match(parts['select'], remaining_query, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid SELECT clause. Must specify exactly two columns/aggregations separated by comma")
        result.update(match.groupdict())
        remaining_query = remaining_query[match.end():].strip()
        
        select_columns = [col.strip() for col in result['select_cols'].split(',')]
        if len(select_columns) != 2:
            raise ValueError("SELECT must specify exactly two columns/aggregations separated by comma")
        
        match = re.match(parts['from'], remaining_query, re.IGNORECASE)
        if not match:
            raise ValueError(f"Invalid FROM clause. Must specify one table name. Remaining: '{remaining_query}'")
        result.update(match.groupdict())
        remaining_query = remaining_query[match.end():].strip()
        
        if remaining_query.startswith('WHERE'):
            match = re.match(parts['where'], remaining_query, re.IGNORECASE)
            if not match:
                raise ValueError("Invalid WHERE clause")
            result.update({k:v for k,v in match.groupdict().items() if v})
            remaining_query = remaining_query[match.end():].strip()
        
        if remaining_query.startswith('GROUP BY'):
            match = re.match(parts['group'], remaining_query, re.IGNORECASE)
            if not match:
                raise ValueError("Invalid GROUP BY clause")
            result.update({k:v for k,v in match.groupdict().items() if v})
            remaining_query = remaining_query[match.end():].strip()
        
        if remaining_query.startswith('ORDER BY'):
            match = re.match(parts['order'], remaining_query, re.IGNORECASE)
            if not match:
                raise ValueError("Invalid ORDER BY clause")
            result.update({k:v for k,v in match.groupdict().items() if v})
            remaining_query = remaining_query[match.end():].strip()
        
        if remaining_query.startswith('LIMIT'):
            match = re.match(parts['limit'], remaining_query, re.IGNORECASE)
            if not match:
                raise ValueError("Invalid LIMIT clause")
            result.update({k:v for k,v in match.groupdict().items() if v})
            remaining_query = remaining_query[match.end():].strip()
        
        if remaining_query.startswith('BIN'):
            match = re.match(parts['bin'], remaining_query, re.IGNORECASE)
            if not match:
                raise ValueError("Invalid BIN clause")
            result.update({k:v for k,v in match.groupdict().items() if v})
            remaining_query = remaining_query[match.end():].strip()
        
        if remaining_query:
            raise ValueError(f"Unrecognized query parts: {remaining_query}")
        
        return result
    
    except Exception as e:
        raise ValueError(f"Query parsing failed: {str(e)}")

def execute_query(db_path, parsed_vql):
    try:
        select_cols = parsed_vql['select_cols']
        from_tables = parsed_vql['from_tables']
        
        if parsed_vql.get('bin_col'):
            bin_col = parsed_vql['bin_col']
            bin_unit = parsed_vql['bin_unit'].lower()
            
            if bin_unit == 'day':
                bin_expr = f"date({bin_col})" 
            elif bin_unit == 'weekday':
                bin_expr = f"strftime('%w', {bin_col})"
            elif bin_unit == 'month':
                bin_expr = f"strftime('%m', {bin_col})"  
            elif bin_unit == 'year':
                bin_expr = f"strftime('%Y', {bin_col})"  
            
            select_cols = select_cols.replace(bin_col, bin_expr)
            
            if not parsed_vql.get('group_cols'):
                parsed_vql['group_cols'] = bin_expr
        
        sql = f"SELECT {select_cols} FROM {from_tables}"
        
        if parsed_vql.get('where_cond'):
            sql += f" WHERE {parsed_vql['where_cond']}"
        
        if parsed_vql.get('group_cols'):
            sql += f" GROUP BY {parsed_vql['group_cols']}"
        
        if parsed_vql.get('order_cols'):
            order_dir = f" {parsed_vql.get('order_dir', '')}"
            sql += f" ORDER BY {parsed_vql['order_cols']}{order_dir}"
        
        if parsed_vql.get('limit_num'):
            sql += f" LIMIT {parsed_vql['limit_num']}"
        
        conn = sqlite3.connect(db_path)
        
        df = pd.read_sql_query(sql, conn)
        
        conn.close()
        
        return df
    
    except sqlite3.Error as e:
        raise ValueError(f"Database error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Query execution failed: {str(e)}")

def generate_svg(df, parsed_vql):
    try:
        plt.figure(figsize=(10, 6))
        chart_type = parsed_vql['chart_type'].lower()
        x_col = df.columns[0]
        y_col = df.columns[1]
        
        if parsed_vql.get('bin_col'):
            bin_unit = parsed_vql['bin_unit']
            
            if bin_unit == 'weekday':
                weekday_map = {
                    '0': 'Sun', '1': 'Mon', '2': 'Tue',
                    '3': 'Wed', '4': 'Thu', '5': 'Fri', '6': 'Sat'
                }
                df[x_col] = df[x_col].astype(str).map(weekday_map)
            elif bin_unit == 'month':
                df[x_col] = df[x_col].apply(lambda x: calendar.month_abbr[int(x)])
        
        if chart_type == 'line':
            plt.plot(df[x_col], df[y_col], marker='o')
            plt.grid(True)
        elif chart_type == 'bar':
            plt.bar(df[x_col], df[y_col])
        elif chart_type == 'pie':
            plt.pie(df[y_col], labels=df[x_col], autopct='%1.1f%%')
        elif chart_type == 'scatter':
            plt.scatter(df[x_col], df[y_col])
        
        plt.xticks(rotation=45 if len(df[x_col]) > 5 else 0)
        plt.tight_layout()
        
        svg_buffer = StringIO()
        plt.savefig(svg_buffer, format='svg', bbox_inches='tight')
        plt.close()
        
        return svg_buffer.getvalue()
    
    except Exception as e:
        plt.close()
        raise ValueError(f"Chart generation failed: {str(e)}")

def vql_to_svg(vql_query, db_path):
    try:
        parsed_vql = parse_vql(vql_query)
        
        df = execute_query(db_path, parsed_vql)
        
        svg_data = generate_svg(df, parsed_vql)
        
        return svg_data
    
    except Exception as e:
        raise ValueError(f"VQL to SVG conversion failed: {str(e)}")

if __name__ == "__main__":
    test_db = "database/company_employee/company_employee.sqlite"  # path of your database
    
    test_queries = [
        "Visualize PIE SELECT Industry, COUNT(Industry) FROM company GROUP BY Industry"
    ]
    
    for i, query in enumerate(test_queries, 1):
        try:
            svg_output = vql_to_svg(query, test_db)
            with open(f"output_{i}.svg", "w") as f:
                f.write(svg_output)
            print(f"Chart {i} generated successfully!")
        except Exception as e:
            print(f"Error in query {i}: {str(e)}")
