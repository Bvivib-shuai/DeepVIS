# DeepVIS
Despite data visualization's power in uncovering patterns and sharing insights, crafting effective visuals demands knowledge of authoring tools and can disrupt the analysis process. Although large language models hold potential for auto-converting analysis intent into visualizations, current methods operate as black boxes lacking transparent reasoning, hindering users from grasping design rationales and improving subpar outputs.
![teaser](https://anonymous.4open.science/r/DeepVIS-9C33/img/teaser.png)

To address this issue, first, we propose a Chain-of-Thought (COT) data construction process. We design a comprehensive CoT reasoning process for Natural-Language-to-Visualization (NL2VIS) and develop an automated pipeline to endow existing datasets with structured reasoning steps. Second, we introduce **CoT-nvBench**, a specialized dataset that records detailed step-by-step reasoning from ambiguous natural language descriptions to final visualizations. Finally, we propose **DeepVIS**, an interactive visual interface that is deeply integrated with the CoT reasoning process. It enables users to inspect reasoning steps, correct errors, and optimize visualization results.
![overview](https://anonymous.4open.science/r/DeepVIS-9C33/img/overview.png)

# Demo Video
For a detailed demonstration of how DeepVIS system works, check out our [System Demo Video](https://anonymous.4open.science/r/DeepVIS-9C33/Demo%20Video.mp4).

# Comparative Analysis
We display vqls and generated charts between our model(**NL2VIS-CoT**) and seven representative NL2VIS models with different architectures. 
![overview](https://anonymous.4open.science/r/DeepVIS-9C33/img/Comparative_analysis.png)
**Question:** 
Draw a chart showing the ten majors with the highest numbers of students whose city of residence is known, with the counts tallied for each major.  
**VQLs:**  
**NL2VIS-CoT:**
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT(STUID) DESC LIMIT 10  
**Seq2Vis:**
VISUALIZE BAR SELECT MAJOR, COUNT(*) FROM STUDENT GROUP BY MAJOR  
**Transformer:** 
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT(STUID) DESC  
**ncNet:** 
VISUALIZE BAR SELECT MAJOR, COUNT(*) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY MAJOR DESC LIMIT 10  
**RGVisNet:** 
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT(STUID) ASC LIMIT 10  
**Llama3.1-8B-SFT:**
VISUALIZE PIE SELECT MAJOR, COUNT() FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT() DESC LIMIT 10  
**ChartGPT:**
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR  
**GPT-4o-mini:**
VISUALIZE BAR SELECT MAJOR, COUNT(STUID) FROM STUDENT WHERE CITY_CODE IS NOT NULL GROUP BY MAJOR ORDER BY COUNT(STUID) ASC LIMIT 10  


# Prompts for generating CoT steps
Please simulate a complete reasoning process to explain the Pre-entered Correct VQL, based on the provided Question, Database Schema and Constraints below. Pretend that you are analyzing the Pre-entered Correct VQL for the first time and detail why each part of it is structured as such.

Question:   
{question}  
Database Schema:  
{db_schema}  
Pre-entered Correct VQL:  
[VQL]  
Constraints:  
The VQL template is as follows:  
Visualize [TYPE] SELECT [COLUMNS] FROM [TABLES] [WHERE] [GROUP BY] [ORDER BY] [SORT DIRECTION] [LIMIT] BIN [BIN_COLUMN] BY [BIN_TIME_UNIT]  
The constraints for each part are as follows:  
1. VISUALIZE field: Only BAR, PIE, LINE, and SCATTER are allowed as values. It is used to specify the data visualization chart type of the query results. Analyze the nature of the question and the database schema to explain why the [TYPE] in the Pre-entered Correct VQL is chosen.  
2. SELECT field: There must be exactly two columns from the database in the SELECT clause. These columns must be either directly from the columns listed in the Database Schema or valid derivations based on those columns (COUNT, AVG, MAX and MIN). Explain why the [COLUMNS] in the Pre-entered Correct VQL are selected considering the question and the database schema.  
3. FROM field: Only add the table names that must be used to complete the natural-language query. Evaluate the question and the database schema to explain why the [TABLES] in the Pre-entered Correct VQL are necessary to answer the question. Describe the connection between these tables and the data required by the question.  
4. WHERE field: Analyze the natural-language query and the database schema to determine whether there is a filtering requirement. When there are clear limiting conditions, accurately explain why the WHERE clause logic expressions in the Pre-entered Correct VQL are formed this way, considering the conditional logical relationships to match the query intent. The columns used in the conditions must be from the Database Schema or valid derivations.  
5. Grouping:   
If you need to group or aggregate the time column in the SELECT clause by a time unit (day, weekday, month, or year) and the current table does not have a column that meets this time - unit requirement, then use the BIN [BIN_COLUMN] BY [BIN_TIME_UNIT] part. [BIN_COLUMN] should be a time column from the Database Schema, and [BIN_TIME_UNIT] should be the appropriate time unit (day, weekday, month, or year).  
When the dataset needs to be grouped and it is not related to time, add other columns in the GROUP BY clause as grouping bases in sequence, with earlier - used grouping bases placed more forward. The columns in the GROUP BY clause must be from the Database Schema or valid derivations. Explain why the GROUP BY and BIN (if applicable) parts in the Pre-entered Correct VQL are set up based on the question and the database schema.  
6. LIMIT field: Add a LIMIT clause at the end of the VQL to specify the maximum number of rows to return. If there is no limit requirement, leave it empty. Explain why the LIMIT clause (if present) in the Pre-entered Correct VQL is included or not, considering factors such as the amount of data needed to answer the question and performance implications.  

Now, please reason according to the following strict format:  
Step 1:  
Reasoning for Chart Type: [Explain why the chart type in the Pre-entered Correct VQL is chosen based on the question and the database schema]  
Chart Type: [Fill in the chart type from the Pre-entered Correct VQL here]  
Step 2:  
Reasoning for FROM: [Explain why the tables in the FROM clause of the Pre-entered Correct VQL are chosen based on the question and the database schema]  
FROM: [Table names for the FROM clause from the Pre-entered Correct VQL]  
Reasoning for SELECT: [Explain why the columns in the SELECT clause of the Pre-entered Correct VQL are chosen based on the question and the database schema]  
SELECT: [Columns for the SELECT clause from the Pre-entered Correct VQL]  
Reasoning for WHERE: [Explain why the conditions in the WHERE clause of the Pre-entered Correct VQL are set based on the question and the database schema]  
WHERE: [Conditions for the WHERE clause from the Pre-entered Correct VQL]  
Step 3:  
Reasoning for GROUP BY: [Explain why the columns in the GROUP BY clause of the Pre-entered Correct VQL are used for grouping based on the question and the database schema]  
GROUP BY: [Columns for the GROUP BY clause from the Pre-entered Correct VQL]  
Reasoning for BIN: [If applicable, explain why the BIN_COLUMN and BIN_TIME_UNIT in the Pre-entered Correct VQL are used based on the time - related grouping requirements and the database schema]  
BIN: [BIN_COLUMN from the Pre-entered Correct VQL]  
BY: [BIN_TIME_UNIT from the Pre-entered Correct VQL]  
Step 4:   
Reasoning for ORDER BY: [Explain why the columns in the ORDER BY clause of the Pre-entered Correct VQL are used for sorting based on the question and the database schema]  
ORDER BY: [Columns for the ORDER BY clause from the Pre-entered Correct VQL]  
Reasoning for SORT DIRECTION: [Based on the analysis of the question requirements and the database schema, explain why the ASC or DESC (or empty) in the Pre-entered Correct VQL is used for each column in the ORDER BY clause]  
SORT DIRECTION: [ASC|DESC|empty from the Pre-entered Correct VQL]  
Reasoning for LIMIT: [Explain why the LIMIT clause (if present) in the Pre-entered Correct VQL is set as such based on various factors]  
LIMIT: [Number of rows for the LIMIT clause from the Pre-entered Correct VQL]  
Step 5:  
Inspection: Check whether the reasoning results of the first four steps are reasonable.   
Final VQL: Combine the above content with the VQL template to obtain the final VQL result.  



