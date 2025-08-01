import os
import zipfile
import io
import json
import ezdxf
from PIL import Image
import torch
import torch.nn as nn
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import gdown

# --- Generator Model Definition (MUST be identical to your train.py) ---
class Generator(nn.Module):
    def __init__(self, latent_dim, output_channels):
        super(Generator, self).__init__()
        self.main = nn.Sequential(
            # Input: latent_dim Z vector
            nn.ConvTranspose2d(latent_dim, 256, 4, 1, 0, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(True),
            # State size. 256 x 4 x 4
            nn.ConvTranspose2d(256, 128, 4, 2, 1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(True),
            # State size. 128 x 8 x 8
            nn.ConvTranspose2d(128, 64, 4, 2, 1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(True),
            # State size. 64 x 16 x 16
            nn.ConvTranspose2d(64, output_channels, 4, 2, 1, bias=False),
            nn.Tanh()
            # Final state size. output_channels x 32 x 32
        )

    def forward(self, input):
        return self.main(input)

# --- Flask Blueprint Setup ---
floor_plan_bp = Blueprint("floor_plan", __name__)

# --- Model Loading Logic ---

# Define model parameters (MUST match your trained model)
LATENT_DIM = 100
OUTPUT_CHANNELS = 1 # Grayscale output

# 1. Define where the model will be saved locally
model_path = Path(__file__).resolve().parent.parent / 'models' / 'trained_model.pth'

# 2. If not present, download from Google Drive
if not model_path.exists():
    print(f"Model not found at {model_path}. Downloading from Google Drive...")
    file_id = "1KPgFgEFANOMWVpS7IZ3Fb53lZ8jhlmkF" # Your Google Drive file ID
    url = f"https://drive.google.com/uc?id={file_id}"

    model_path.parent.mkdir(parents=True, exist_ok=True)
    gdown.download(url, str(model_path), quiet=False)
    print("✅ Model download complete.")

# 3. Instantiate the Generator model and load the state_dict
model = Generator(LATENT_DIM, OUTPUT_CHANNELS)

try:
    # Use map_location to ensure model loads on CPU
    state_dict = torch.load(model_path, map_location=torch.device("cpu"))
    model.load_state_dict(state_dict)
    model.eval() # Set the model to evaluation mode
    print("✅ Trained model loaded successfully and set to evaluation mode.")
except Exception as e:
    print(f"Error loading model state_dict: {e}")
    model = None # Set model to None if loading fails

# --- Mock Generation (Fallback) ---
def mock_generate_floor_plan(prompt_data):
    print("Using mock model for generation.")
    # Create a dummy image
    dummy_image = Image.new("RGB", (256, 256), color = (73, 109, 137))
    # Create dummy JSON data
    json_data = {"prompt": prompt_data, "generated_by": "mock_model"}
    return dummy_image, json_data

# --- API Endpoints ---

@floor_plan_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

@floor_plan_bp.route("/generate", methods=["POST"])
def generate_floor_plan():
    prompt_data = request.json
    if not prompt_data:
        return jsonify({"error": "Invalid input"}), 400

    generated_image = None
    json_output = {}

    if model is None:
        # Use mock model if the real one failed to load
        generated_image, json_output = mock_generate_floor_plan(prompt_data)
    else:
        # --- Use the Real Trained Model ---
        print("Using real trained model for generation.")
        try:
            with torch.no_grad():
                # Create a random latent vector (noise) as input
                # In a real application, you would derive this from the prompt_data
                noise = torch.randn(1, LATENT_DIM, 1, 1, device=torch.device("cpu"))
                
                # Generate the floor plan tensor
                output_tensor = model(noise).squeeze(0)
                
                # Convert tensor to a PIL Image
                # Denormalize from [-1, 1] to [0, 255]
                output_tensor = (output_tensor * 0.5 + 0.5) * 255
                # Permute from CxHxW to HxWxC for numpy/PIL
                output_array = output_tensor.permute(1, 2, 0).cpu().numpy().astype("uint8")
                # Squeeze to remove the channel dimension for grayscale
                generated_image = Image.fromarray(output_array.squeeze(), 'L') # 'L' mode for grayscale

            json_output = {"prompt": prompt_data, "generated_by": "real_model"}

        except Exception as e:
            print(f"Error during real model generation: {e}")
            # Fallback to mock if generation fails
            generated_image, json_output = mock_generate_floor_plan(prompt_data)

    # --- File Generation (DWG, IFC, PNG) ---
    # (This part remains the same as your original code)
    # ... (Your existing code for creating DWG, IFC, and the ZIP file) ...

    # For demonstration, let's create a simple ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Save PNG preview
        png_buffer = io.BytesIO()
        generated_image.save(png_buffer, format="PNG")
        zip_file.writestr("preview.png", png_buffer.getvalue())

        # Save JSON data
        zip_file.writestr("data.json", json.dumps(json_output, indent=2))

        # Create a dummy DWG for now
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_line((0, 0), (10, 10))
        dwg_buffer = io.BytesIO()
        doc.write(dwg_buffer)
        zip_file.writestr("floor_plan.dwg", dwg_buffer.getvalue())

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name="aura_os_floor_plan.zip",
        mimetype="application/zip"
    )

