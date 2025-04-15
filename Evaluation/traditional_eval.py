import json
import re


def extract_last_vql_1(text):
    """
    Extract the last occurrence of the Visualize word and the subsequent content as VQL from the text.
    """
    try:
        # Define a regular expression to precisely match VQL statements starting with Visualize.
        vql_pattern = re.compile(r'(Visualize\s+[A-Z]+\s+SELECT.*)', re.IGNORECASE | re.DOTALL)
        matches = vql_pattern.findall(text)
        if matches:
            last_vql = matches[-1].strip()
            # Remove any possible extra quotes and line breaks.
            last_vql = last_vql.replace('\n', ' ').replace('"', '').strip()
            return last_vql
        return None
    except Exception as e:
        print(f"Error occurred while extracting VQL: {e}")
        return None


def extract_last_vql(text):
    """
    Extract the last occurrence of the VQL statement from the text.
    """
    vql_pattern = re.compile(r'Final VQL:(.*)', re.IGNORECASE | re.DOTALL)
    matches = vql_pattern.findall(text)
    if matches:
        last_vql = matches[-1].strip()
        # Remove any possible extra quotes and line breaks.
        last_vql = last_vql.replace('\n', ' ').replace('"', '').strip()
        return last_vql
    return None


def extract_vis(vql):
    """
    Extract the VISUALIZE field from the VQL.
    """
    vql = vql.upper()
    parts = vql.split()
    if len(parts) > 1 and parts[0].upper() == 'VISUALIZE':
        return parts[1].upper()
    return None


def remove_space_before_comma(sql):
    result = ""
    for i, char in enumerate(sql):
        if char == ' ' and i > 0 and sql[i + 1] == ',':
            continue
        result += char
    return result


def extract_sql(vql):
    """
    Extract the SQL part from the VQL.
    """
    # Remove the VISUALIZE part.
    vql = vql.upper()
    vis = extract_vis(vql)
    if vis:
        vql = vql.replace(f"VISUALIZE {vis}", "").strip()
    # Check if it contains BIN BY.
    bin_by_index = vql.find('BIN')
    if bin_by_index != -1:
        return vql[:bin_by_index].strip()
    return vql.strip()


def extract_bin(vql):
    """
    Extract the BIN part from the VQL.
    """
    bin_by_index = vql.find('BIN')
    if bin_by_index != -1:
        return vql[bin_by_index:].strip()
    return None


def extract_select_columns(sql):
    """
    Extract the column names of the SELECT fields from the SQL.
    """
    if sql.startswith('SELECT'):
        select_part = sql[len('SELECT'):].strip()
        columns = select_part.split(',')
        columns = [col.strip().split(' ')[0].lower() for col in columns]  # Convert column names to lowercase.
        return columns
    return []


def word_match_accuracy(response, groundtruth):
    """
    Calculate the accuracy based on word matching.
    """
    response_words = response.split()
    groundtruth_words = groundtruth.split()
    if len(groundtruth_words) == 0:
        return 1 if len(response_words) == 0 else 0
    correct_count = sum(word in response_words for word in groundtruth_words)
    return correct_count / len(groundtruth_words)


def evaluate_accuracy(response_vql, groundtruth_vql):
    """
    Evaluate the accuracy of each part of the response VQL compared to the ground truth VQL.
    """
    # Extract the VISUALIZE field.
    response_vis = extract_vis(response_vql)
    groundtruth_vis = extract_vis(groundtruth_vql)
    vis_accuracy = response_vis == groundtruth_vis
    # Extract the SQL part.
    response_sql = extract_sql(response_vql)
    groundtruth_sql_1 = extract_sql(groundtruth_vql)
    groundtruth_sql = remove_space_before_comma(groundtruth_sql_1)
    # Compare SQL statements case-insensitively.
    sql_accuracy = 1 if response_sql is not None and groundtruth_sql is not None and response_sql.lower() == groundtruth_sql.lower() else 0

    # Extract the BIN part.
    response_bin = extract_bin(response_vql)
    groundtruth_bin = extract_bin(groundtruth_vql)
    # Compare the BIN part case-insensitively. First, check if it is None.
    if response_bin is None and groundtruth_bin is None:
        bin_accuracy = 1
    elif response_bin is None or groundtruth_bin is None:
        bin_accuracy = 0
    else:
        bin_accuracy = 1 if response_bin.lower() == groundtruth_bin.lower() else 0

    # Extract the SELECT columns.
    response_columns = extract_select_columns(response_sql)
    groundtruth_columns = extract_select_columns(groundtruth_sql)

    # Calculate the accuracy of the SELECT field column names.
    if len(groundtruth_columns) == 0:
        select_columns_accuracy = 1 if len(response_columns) == 0 else 0
    else:
        correct_count = sum(col in response_columns for col in groundtruth_columns)
        select_columns_accuracy = correct_count / len(groundtruth_columns)

    # Remove the VISUALIZE part.
    response_without_vis = response_vql.replace(f"Visualize {response_vis}", "").strip().lower() if response_vis else response_vql.strip().lower()
    groundtruth_without_vis_1 = groundtruth_vql.replace(f"Visualize {groundtruth_vis}", "").strip().lower() if groundtruth_vis else groundtruth_vql.strip().lower()
    groundtruth_without_vis = remove_space_before_comma(groundtruth_without_vis_1)
    # Compare the part without VISUALIZE case-insensitively.
    data_accuracy = 1 if response_without_vis == groundtruth_without_vis else 0

    # Overall accuracy: When both vis and data are correct, all_accuracy is counted as 1.
    all_accuracy = 1 if vis_accuracy and data_accuracy else 0

    return vis_accuracy, sql_accuracy, bin_accuracy, select_columns_accuracy, data_accuracy, all_accuracy


try:
    with open('test_result_{now}.json', 'r') as f:
        test_data = json.load(f)
except FileNotFoundError:
    print("The result file was not found. Please check the file path.")
    exit(1)

try:
    with open('test.json', 'r') as f:
        groundtruth_data = json.load(f)
except FileNotFoundError:
    print("The file test.json was not found. Please check the file path.")
    exit(1)

total_samples = len(test_data)
valid_samples = 0
vis_accuracies = []
sql_accuracies = []
bin_accuracies = []
select_columns_accuracies = []
data_accuracies = []
all_accuracies = []
vis_error_samples = []
data_error_db_ids = []
for i in range(total_samples):
    # Extract the last VQL from the response.
    response_text = test_data[i]['response_finetuned_model']
    response_vql = extract_last_vql_1(response_text)
    print(response_vql)
    if not response_vql:
        continue

    # Extract the ground truth VQL.
    groundtruth_text = groundtruth_data[i]['content_2']
    groundtruth_vql = extract_last_vql(groundtruth_text)
    if not groundtruth_vql:
        continue

    valid_samples += 1
    # Evaluate the accuracy.
    vis_acc, sql_acc, bin_acc, select_columns_acc, data_acc, all_acc = evaluate_accuracy(response_vql, groundtruth_vql)
    vis_accuracies.append(vis_acc)
    sql_accuracies.append(sql_acc)
    bin_accuracies.append(bin_acc)
    select_columns_accuracies.append(select_columns_acc)
    data_accuracies.append(data_acc)
    all_accuracies.append(all_acc)

    # Record samples with errors in the VISUALIZE field.
    if not vis_acc:
        response_vis = extract_vis(response_vql)
        groundtruth_vis = extract_vis(groundtruth_vql)
        vis_error_samples.append({
            'index': i,
            'response_vis': response_vis,
            'groundtruth_vis': groundtruth_vis,
            'response_vql': response_vql,
            'groundtruth_vql': groundtruth_vql
        })

    # Record the db_id of samples with errors in the data part.
    if not data_acc:
        db_id = groundtruth_data[i].get('db_id')
        if db_id:
            data_error_db_ids.append(db_id)

# Calculate the average accuracy.
avg_vis_accuracy = sum(vis_accuracies) / valid_samples if valid_samples > 0 else 0
avg_sql_accuracy = sum(sql_accuracies) / valid_samples if valid_samples > 0 else 0
avg_bin_accuracy = sum(bin_accuracies) / valid_samples if valid_samples > 0 else 0
avg_select_columns_accuracy = sum(select_columns_accuracies) / valid_samples if valid_samples > 0 else 0
avg_data_accuracy = sum(data_accuracies) / valid_samples if valid_samples > 0 else 0
avg_all_accuracy = sum(all_accuracies) / valid_samples if valid_samples > 0 else 0

print(f"Average accuracy of the VISUALIZE field: {avg_vis_accuracy}")
print(f"Average accuracy of the SQL part: {avg_sql_accuracy}")
print(f"Average accuracy of the BIN part: {avg_bin_accuracy}")
print(f"Average accuracy of the SELECT field column names: {avg_select_columns_accuracy}")
print(f"Average accuracy of the fields except VISUALIZE: {avg_data_accuracy}")
print(f"Overall average accuracy: {avg_all_accuracy}")
    
