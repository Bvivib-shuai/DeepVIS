## 🎉 Paper Accepted at IEEE VIS 2025
We are delighted to announce that our manuscript has been accepted for IEEE VIS 2025. The accepted work will appear in a special issue of IEEE Transactions on Visualization and Computer Graphics (TVCG).

You can view our preprint on [DeepVIS: Bridging Natural Language and Data Visualization Through Step-wise Reasoning](https://arxiv.org/abs/2508.01700).

# DeepVIS
Despite data visualization's power in uncovering patterns and sharing insights, crafting effective visuals demands knowledge of authoring tools and can disrupt the analysis process. Although large language models hold potential for auto-converting analysis intent into visualizations, current methods operate as black boxes lacking transparent reasoning, hindering users from grasping design rationales and improving subpar outputs.
![teaser](https://github.com/Bvivib-shuai/DeepVIS/blob/main/img/teaser.png)

To address this issue, first, we propose a Chain-of-Thought (COT) data construction process. We design a comprehensive CoT reasoning process for Natural-Language-to-Visualization (NL2VIS) and develop an automated pipeline to endow existing datasets with structured reasoning steps. Second, we introduce **nvBench-CoT**, a specialized dataset that records detailed step-by-step reasoning from ambiguous natural language descriptions to final visualizations. Finally, we propose **DeepVIS**, an interactive visual interface that is deeply integrated with the CoT reasoning process. It enables users to inspect reasoning steps, correct errors, and optimize visualization results.
![overview](https://github.com/Bvivib-shuai/DeepVIS/blob/main/img/overview.png)

# Database
The database files used when running evaluation.py can be downloaded from [database](https://github.com/TsinghuaDatabaseGroup/nvBench/blob/main/databases.zip).

# One-click execution script
Install the required dependencies: 
```bash
pip install -r requirements.txt
```

To train and test the NL2VIS-CoT model, simply run: 
```bash
python run.py.  
```

The run.py script will:  

(1) Download the nvBench-CoT dataset and Llama-3.1-8B-Instruct model.  

(2) Train the NL2VIS-CoT model on the training dataset.  

(3) Test the trained model on the test dataset.  

(4) Evaluate performance across five metrics.  

(5) Save the test results to output files.  

The test results will align with the **Chart Acc**, **Axis Acc**, **SQL Acc**, **Aata Acc**, and **All Acc** of **NL2VIS-CoT** in **Table 1: Performance Comparison** of the paper, demonstrating the reproducibility of our work.
