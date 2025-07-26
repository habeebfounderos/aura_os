import os
from pathlib import Path

import torch

# 1️⃣ Where the model will be saved locally
model_path = Path(__file__).resolve().parent.parent / 'models' / 'trained_model.pth'

# 2️⃣ If not present, download from Google Drive
if not model_path.exists():
    print("Downloading trained_model.pth from Google Drive...")
    import gdown

    file_id = "1_ORgdQmEcjZ_10-DdK_Hw3cOzgGD1g5v"
    url = f"https://drive.google.com/uc?id={file_id}"

    model_path.parent.mkdir(parents=True, exist_ok=True)
    gdown.download(url, str(model_path), quiet=False)

    print("✅ Download complete.")

# 3️⃣ Load the trained model
model = torch.load(model_path, map_location='cpu')
model.eval()
print("✅ Trained model loaded successfully.")
