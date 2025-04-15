import json
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

with open('processed_nvbench.json', 'r', encoding='utf-8') as f:
    dataset = json.load(f)


url = "Fill in the specific API request URL"
headers = {
    "Content-Type": "Fill in the appropriate content type, e.g., application/json",
    "Authorization": "Fill in the actual authorization token, usually in the format of Bearer <token>"
}

def format_VQL(vql):
    aggregations = ["SUM", "AVG", "COUNT", "MAX", "MIN"]
    parts = vql.split()
    new_parts = []
    i = 0
    while i < len(parts):
        part = parts[i].upper()
        if part == "VISUALIZE":
            new_parts.append("VISUALIZE")
            i += 1
            if i < len(parts):
                new_parts.append(parts[i].upper())
        elif part in ["SELECT", "FROM", "WHERE", "GROUP", "ORDER", "BIN", "LIMIT"]:
            new_parts.append(part)
            if part in ["GROUP", "ORDER", "BIN"]:
                i += 1
                if i < len(parts) and parts[i].upper() == "BY":
                    new_parts.append("BY")
        elif any(agg in part for agg in aggregations):
            for agg in aggregations:
                if agg in part:
                    new_parts.append(part.replace(agg.lower(), agg))
                    break
        else:
            new_parts.append(parts[i])
        i += 1
    return " ".join(new_parts)

def build_prompt(question, db_schema, VQL):
    constraint_text = """Please simulate a complete reasoning process to explain the Pre - entered Correct VQL, based on the provided Question and Database Schema below. Pretend that you are analyzing the Pre - entered Correct VQL for the first time and detail why each part of it is structured as such.

Question:  
{question}  
Database Schema:  
{db_schema}
Pre - entered Correct VQL:
[VQL]

During the reasoning process, you need to follow these constraints:
The VQL template is as follows:
Visualize [TYPE] SELECT [COLUMNS] FROM [TABLES] [WHERE] [GROUP BY] [ORDER BY] [SORT DIRECTION] [LIMIT] BIN [BIN_COLUMN] BY [BIN_TIME_UNIT]
The constraints for each part are as follows:
1. VISUALIZE field: Only BAR, PIE, LINE, and SCATTER are allowed as values. It is used to specify the data visualization chart type of the query results. Analyze the nature of the question and the database schema to explain why the [TYPE] in the Pre - entered Correct VQL is chosen.
2. SELECT field: There must be exactly two columns from the database in the SELECT clause. These columns must be either directly from the columns listed in the Database Schema or valid derivations based on those columns (COUNT, AVG, MAX and MIN). Explain why the [COLUMNS] in the Pre - entered Correct VQL are selected considering the question and the database schema.
3. FROM field: Only add the table names that must be used to complete the natural - language query. Evaluate the question and the database schema to explain why the [TABLES] in the Pre - entered Correct VQL are necessary to answer the question. Describe the connection between these tables and the data required by the question.
4. WHERE field: Analyze the natural - language query and the database schema to determine whether there is a filtering requirement. When there are clear limiting conditions, accurately explain why the WHERE clause logic expressions in the Pre - entered Correct VQL are formed this way, considering the conditional logical relationships to match the query intent. The columns used in the conditions must be from the Database Schema or valid derivations.
5. Grouping:
    If you need to group or aggregate the time column in the SELECT clause by a time unit (day, weekday, month, or year) and the current table does not have a column that meets this time - unit requirement, then use the BIN [BIN_COLUMN] BY [BIN_TIME_UNIT] part. [BIN_COLUMN] should be a time column from the Database Schema, and [BIN_TIME_UNIT] should be the appropriate time unit (day, weekday, month, or year).
    When the dataset needs to be grouped and it is not related to time, add other columns in the GROUP BY clause as grouping bases in sequence, with earlier - used grouping bases placed more forward. The columns in the GROUP BY clause must be from the Database Schema or valid derivations. Explain why the GROUP BY and BIN (if applicable) parts in the Pre - entered Correct VQL are set up based on the question and the database schema.
6. LIMIT field: Add a LIMIT clause at the end of the VQL to specify the maximum number of rows to return. If there is no limit requirement, leave it empty. Explain why the LIMIT clause (if present) in the Pre - entered Correct VQL is included or not, considering factors such as the amount of data needed to answer the question and performance implications.

Now, please reason according to the following strict format:
Step 1: 
Reasoning for Chart Type: [Explain why the chart type in the Pre - entered Correct VQL is chosen based on the question and the database schema]
Chart Type: [Fill in the chart type from the Pre - entered Correct VQL here]

Step 2: 
Reasoning for FROM: [Explain why the tables in the FROM clause of the Pre - entered Correct VQL are chosen based on the question and the database schema]
FROM: [Table names for the FROM clause from the Pre - entered Correct VQL]
Reasoning for SELECT: [Explain why the columns in the SELECT clause of the Pre - entered Correct VQL are chosen based on the question and the database schema]
SELECT: [Columns for the SELECT clause from the Pre - entered Correct VQL]
Reasoning for WHERE: [Explain why the conditions in the WHERE clause of the Pre - entered Correct VQL are set based on the question and the database schema]
WHERE: [Conditions for the WHERE clause from the Pre - entered Correct VQL]

Step 3: 
Reasoning for GROUP BY: [Explain why the columns in the GROUP BY clause of the Pre - entered Correct VQL are used for grouping based on the question and the database schema]
GROUP BY: [Columns for the GROUP BY clause from the Pre - entered Correct VQL]
Reasoning for BIN: [If applicable, explain why the BIN_COLUMN and BIN_TIME_UNIT in the Pre - entered Correct VQL are used based on the time - related grouping requirements and the database schema]
BIN: [BIN_COLUMN from the Pre - entered Correct VQL]
BY: [BIN_TIME_UNIT from the Pre - entered Correct VQL]

Step 4: 
Reasoning for ORDER BY: [Explain why the columns in the ORDER BY clause of the Pre - entered Correct VQL are used for sorting based on the question and the database schema]
ORDER BY: [Columns for the ORDER BY clause from the Pre - entered Correct VQL]
Reasoning for SORT DIRECTION: [Based on the analysis of the question requirements and the database schema, explain why the ASC or DESC (or empty) in the Pre - entered Correct VQL is used for each column in the ORDER BY clause]
SORT DIRECTION: [ASC|DESC|empty from the Pre - entered Correct VQL]
Reasoning for LIMIT: [Explain why the LIMIT clause (if present) in the Pre - entered Correct VQL is set as such based on various factors]
LIMIT: [Number of rows for the LIMIT clause from the Pre - entered Correct VQL]


"""
    return constraint_text.replace("{question}", question).replace("{db_schema}", "\n".join(db_schema)).replace("[VQL]", VQL)


def process_item(item):
    question = item["question"]
    db_schema = item["Database Schema"]
    VQL = item["VQL"]
    formatted_VQL = format_VQL(VQL)

    prompt = build_prompt(question, db_schema, formatted_VQL)

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        reasoning_content = result["choices"][0]["message"]["content"]

        new_item = item.copy()
        new_item["reasoning_content"] = reasoning_content

        print("\nQuestion:", question)
        print("Reasoning Content:", reasoning_content)
        print("-" * 80)

        return new_item
    except requests.RequestException as e:
        print(f"Request error: {e}")
        new_item = item.copy()
        new_item["reasoning_content"] = f"Request error: {e}"
        return new_item
    except (KeyError, IndexError):
        print("Error parsing the response. The response format may not meet expectations.")
        new_item = item.copy()
        new_item["reasoning_content"] = "Error parsing the response. The response format may not meet expectations."
        return new_item

new_dataset = []
with ThreadPoolExecutor(max_workers=50) as executor:
    results = list(tqdm(executor.map(process_item, dataset), total=len(dataset), desc="Processing items", unit="item"))
    new_dataset.extend(results)

with open('processed_nvbench_with_reasoning.json', 'w', encoding='utf-8') as f:
    json.dump(new_dataset, f, ensure_ascii=False, indent=4)
