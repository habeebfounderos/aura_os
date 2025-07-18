from flask import Blueprint, request, jsonify, send_file
import os
import json
import zipfile
import tempfile
from datetime import datetime
import ezdxf
from PIL import Image, ImageDraw, ImageFont
import numpy as np

floor_plan_bp = Blueprint("floor_plan", __name__)

@floor_plan_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "AURA OS Floor Plan Generator"}), 200

@floor_plan_bp.route("/generate", methods=["POST"])
def generate_floor_plan():
    try:
        data = request.get_json()
        
        # Extract parameters
        prompt = data.get('prompt', 'Modern bungalow')
        site_width = data.get('site_width', 20)
        site_height = data.get('site_height', 30)
        required_rooms = data.get('required_rooms', ['living_room', 'kitchen', 'bedroom', 'bathroom'])
        climate_zone = data.get('climate_zone', 'temperate')
        
        # Generate floor plan data (mock implementation)
        floor_plan_data = generate_mock_floor_plan(prompt, site_width, site_height, required_rooms, climate_zone)
        
        # Create temporary directory for files
        with tempfile.TemporaryDirectory() as temp_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"floor_plan_{timestamp}"
            
            # Generate DWG file
            dwg_path = os.path.join(temp_dir, f"{base_filename}.dwg")
            generate_dwg_file(floor_plan_data, dwg_path)
            
            # Generate IFC file
            ifc_path = os.path.join(temp_dir, f"{base_filename}.ifc")
            generate_ifc_file(floor_plan_data, ifc_path)
            
            # Generate PNG preview
            png_path = os.path.join(temp_dir, f"{base_filename}_preview.png")
            generate_png_preview(floor_plan_data, png_path)
            
            # Save JSON data
            json_path = os.path.join(temp_dir, f"{base_filename}_data.json")
            with open(json_path, 'w') as f:
                json.dump(floor_plan_data, f, indent=2)
            
            # Create ZIP file
            zip_path = os.path.join(temp_dir, f"{base_filename}.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(dwg_path, f"{base_filename}.dwg")
                zipf.write(ifc_path, f"{base_filename}.ifc")
                zipf.write(png_path, f"{base_filename}_preview.png")
                zipf.write(json_path, f"{base_filename}_data.json")
            
            return send_file(zip_path, as_attachment=True, download_name=f"{base_filename}.zip")
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def generate_mock_floor_plan(prompt, site_width, site_height, required_rooms, climate_zone):
    """Generate mock floor plan data"""
    
    # Mock room layouts based on requirements
    rooms = []
    x_offset = 2  # Setback from boundary
    y_offset = 2
    current_x = x_offset
    current_y = y_offset
    
    room_sizes = {
        'living_room': (6, 5),
        'kitchen': (4, 3),
        'bedroom': (4, 4),
        'bathroom': (2, 2),
        'garage': (6, 6),
        'study': (3, 3),
        'laundry': (2, 2)
    }
    
    for room in required_rooms:
        if room in room_sizes:
            width, height = room_sizes[room]
            
            # Ensure room fits within site boundaries
            if current_x + width > site_width - x_offset:
                current_x = x_offset
                current_y += 5
            
            rooms.append({
                'name': room.replace('_', ' ').title(),
                'type': room,
                'x': current_x,
                'y': current_y,
                'width': width,
                'height': height,
                'area': width * height
            })
            
            current_x += width + 1
    
    return {
        'prompt': prompt,
        'site_dimensions': {'width': site_width, 'height': site_height},
        'climate_zone': climate_zone,
        'rooms': rooms,
        'total_area': sum(room['area'] for room in rooms),
        'generated_at': datetime.now().isoformat()
    }

def generate_dwg_file(floor_plan_data, output_path):
    """Generate DWG file using ezdxf"""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Draw site boundary
    site = floor_plan_data['site_dimensions']
    msp.add_lwpolyline([
        (0, 0), (site['width'], 0), 
        (site['width'], site['height']), (0, site['height']), (0, 0)
    ])
    
    # Draw rooms
    for room in floor_plan_data['rooms']:
        # Room boundary
        x, y, w, h = room['x'], room['y'], room['width'], room['height']
        msp.add_lwpolyline([
            (x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)
        ])
        
        # Room label
        msp.add_text(
            room['name'],
            dxfattribs={'height': 0.5}
        ).set_pos((x + w/2, y + h/2))
    
    doc.saveas(output_path)

def generate_ifc_file(floor_plan_data, output_path):
    """Generate basic IFC file"""
    ifc_content = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('{os.path.basename(output_path)}','{datetime.now().isoformat()}',('AURA OS'),('AURA OS'),'IFC2X3','AURA OS','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;

DATA;
#1= IFCPROJECT('0YvhMWKXj0kugbFTYE2$V2',#2,'AURA OS Floor Plan',$,$,$,$,(#9),#8);
#2= IFCOWNERHISTORY(#6,#7,$,.ADDED.,$,$,$,{datetime.now().timestamp()});
#6= IFCPERSONANDORGANIZATION(#3,#5,$);
#3= IFCPERSON($,'AURA','OS',$,$,$,$,$);
#5= IFCORGANIZATION($,'AURA OS',$,$,$);
#7= IFCAPPLICATION(#5,'1.0','AURA OS','AURA_OS');
#8= IFCUNITASSIGNMENT((#10,#11,#15,#19,#20,#21));
#9= IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#12,$);
#10= IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#11= IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#12= IFCAXIS2PLACEMENT3D(#13,$,$);
#13= IFCCARTESIANPOINT((0.,0.,0.));
#15= IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);
#19= IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);
#20= IFCSIUNIT(*,.TIMEUNIT.,$,.SECOND.);
#21= IFCSIUNIT(*,.FREQUENCYUNIT.,$,.HERTZ.);
ENDSEC;

END-ISO-10303-21;
"""
    
    with open(output_path, 'w') as f:
        f.write(ifc_content)

def generate_png_preview(floor_plan_data, output_path):
    """Generate PNG preview image"""
    site = floor_plan_data['site_dimensions']
    scale = 20  # pixels per meter
    
    # Create image
    img_width = int(site['width'] * scale)
    img_height = int(site['height'] * scale)
    img = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw site boundary
    draw.rectangle([0, 0, img_width-1, img_height-1], outline='black', width=2)
    
    # Draw rooms
    colors = ['lightblue', 'lightgreen', 'lightyellow', 'lightcoral', 'lightgray']
    for i, room in enumerate(floor_plan_data['rooms']):
        x = int(room['x'] * scale)
        y = int(room['y'] * scale)
        w = int(room['width'] * scale)
        h = int(room['height'] * scale)
        
        color = colors[i % len(colors)]
        draw.rectangle([x, y, x + w, y + h], fill=color, outline='black')
        
        # Add room label
        try:
            font = ImageFont.load_default()
            text = room['name']
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = x + (w - text_width) // 2
            text_y = y + (h - text_height) // 2
            draw.text((text_x, text_y), text, fill='black', font=font)
        except:
            pass
    
    img.save(output_path)
