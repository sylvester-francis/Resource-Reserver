Avoid duplication of code by creating reusable functions or components. When you notice similar code blocks, refactor them into a single function or component that can be called with different parameters. This improves maintainability and reduces the risk of bugs.---
description: This file provides instructions to avoid code duplication by creating reusable functions or components.
applyTo: **/*.*
--- 
Avoid duplication of code by creating reusable functions or components. When you notice similar code blocks, refactor them into a single function or component that can be called with different parameters. This improves maintainability and reduces the risk of bugs.
For example, if you have multiple instances of similar logic for data processing, consider creating a function like this:

```python
def process_data(data, parameter):    
    # Common data processing logic
    result = []
    for item in data:
        # Process item based on parameter
        processed_item = item * parameter  # Example operation
        result.append(processed_item)
    return result
```     
Then, you can call this function with different parameters instead of duplicating the logic:

```python
data_set_1 = [1, 2, 3]
data_set_2 = [4, 5, 6]  
processed_1 = process_data(data_set_1, 2)
processed_2 = process_data(data_set_2, 3)
```
This approach not only reduces code duplication but also makes it easier to update the logic in one place if needed.
