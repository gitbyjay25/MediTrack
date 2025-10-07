# ML Model Training

```python
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
```

```python
medicine_df = pd.read_csv('medicine_clean.csv')
interaction_df = pd.read_csv('interaction_clean.csv')
print(medicine_df.shape, interaction_df.shape)
```

```python
medicine_df['is_core'] = (medicine_df['list_type'] == 'Core').astype(int)
interaction_df['severity_encoded'] = interaction_df['severity_level'].map({'High': 3, 'Medium': 2, 'Low': 1})
```

```python
medicine_lookup = medicine_df.set_index('medicine_name')
features = []
targets = []

for _, row in interaction_df.iterrows():
    drug1, drug2 = row['drug1'], row['drug2']
    if drug1 in medicine_lookup.index and drug2 in medicine_lookup.index:
        med1 = medicine_lookup.loc[drug1]
        med2 = medicine_lookup.loc[drug2]
        feature = [med1['is_core'], med2['is_core'], row['severity_encoded']]
        features.append(feature)
        targets.append(row['severity_encoded'])

X, y = np.array(features), np.array(targets)
```

```python
model = RandomForestClassifier(n_estimators=50, random_state=42)
model.fit(X, y)
print("Model trained")
```

```python
joblib.dump(model, 'model.pkl')

from google.colab import files
files.download('model.pkl')
print("Model downloaded to your computer")
```
