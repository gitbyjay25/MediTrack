# Simple Data Cleaning

```python
import pandas as pd
import numpy as np
```

```python
medicine_df = pd.read_csv('medicine.txt', on_bad_lines='skip')
interaction_df = pd.read_csv('interaction.txt', on_bad_lines='skip')
print(medicine_df.shape, interaction_df.shape)
```

```python
medicine_df = medicine_df.replace('N/A', np.nan)
interaction_df = interaction_df.replace('N/A', np.nan)

medicine_df['medicine_name'] = medicine_df['medicine_name'].str.strip()
interaction_df['drug1'] = interaction_df['drug1'].str.strip()
interaction_df['drug2'] = interaction_df['drug2'].str.strip()
```

```python
medicine_df.to_csv('medicine_clean.csv', index=False)
interaction_df.to_csv('interaction_clean.csv', index=False)

from google.colab import files
files.download('medicine_clean.csv')
files.download('interaction_clean.csv')
print("Files downloaded to your computer")
```
