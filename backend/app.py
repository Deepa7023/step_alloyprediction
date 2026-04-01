from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import socket
import time
from dotenv import load_dotenv
from .logic.cad_analyzer import analyze_cad
from .logic.cost_engine import calculate_hpdc_cost
from .logic.market_fetcher import market_fetcher

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='static')
CORS(app)

def get_local_ip():
    """Detect the actual local IP address of the host."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# Storage configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global storage for analysis (In-memory for demo)
part_cache = {}

@app.route('/', methods=['GET'])
def index():
    """Serve the lightweight Mission Control HUD"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy", 
        "version": "1.3.0_MASTER", 
        "host_ip": get_local_ip(),
        "kernels": ["OCP_CASCADE", "TRIMESH_RAY", "GAMA_GProp"]
    })


@app.route('/api/agent/process', methods=['POST'])
def agent_process():
    """
    Unified Agentic Endpoint: One-Click Analysis & Estimation.
    Expects: file (CAD), metal, annual_volume, location_multiplier (optional)
    """
    if 'file' not in request.files:
        return jsonify({"error": "No CAD file provided"}), 400
        
    file = request.files['file']
    metal = request.form.get('metal', "Aluminum_A380")
    
    # User requested to remove default volume (detect and allow empty)
    vol_raw = request.form.get('annual_volume')
    annual_volume = int(vol_raw) if vol_raw and vol_raw.strip() != "" else None
    
    location_multiplier = float(request.form.get('location_multiplier', 1.0))
    location_name = request.form.get('location_name', "Global_Standard_Node")
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        filename = f"agent_{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # 1. Analyze CAD (OCP + Trimesh)
        analysis_result = analyze_cad(file_path)
        if "error" in analysis_result:
            return jsonify(analysis_result), 500
            
        traits = analysis_result["traits"]
        
        # 2. Fetch Live Market Price
        live_prices = market_fetcher.get_live_prices()
        live_price = live_prices.get(metal, {}).get('current_price')
        exchange_rate = market_fetcher.get_exchange_rate()
        
        # 3. Calculate HPDC Cost (Handle None volume as 1 for base calculation but flag it)
        calc_volume = annual_volume if annual_volume is not None else 1
        cost_report = calculate_hpdc_cost(
            traits, metal, calc_volume, 0, location_multiplier, live_price_per_kg=live_price
        )
        
        # Add metadata for location and currency
        cost_report["exchange_rate"] = exchange_rate
        cost_report["unit_cost_inr"] = round(cost_report["total_unit_cost"] * exchange_rate, 2)
        
        return jsonify({
            "status": "success",
            "agent_report": {
                "file": file.filename,
                "technical_matrix": traits,
                "cost_estimation": cost_report,
                "market_snapshot": {
                    "metal": metal,
                    "spot_price_usd": live_price,
                    "spot_price_inr": round(live_price * exchange_rate, 2),
                    "location": location_name,
                    "timestamp": time.ctime(),
                    "next_sync": time.ctime(market_fetcher.cache["last_updated"] + market_fetcher.ttl)
                },
                "engine": analysis_result.get("engine")
            }
        })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    # ... EXISTING ANALYZE LOGIC ...
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Analyze using Dual-Kernel (OCP + Trimesh)
        result = analyze_cad(file_path)
        if "error" in result:
            return jsonify(result), 500
            
        # Cache traits with its analysis_id
        analysis_id = result["analysis_id"]
        part_cache[analysis_id] = result["traits"]
        
        return jsonify({
            "analysis_id": analysis_id,
            "traits": result["traits"],
            "engine": result.get("engine", "UNKNOWN")
        })


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "instance_id": socket.gethostname()
    })

@app.route('/api/estimate', methods=['POST'])
def estimate():
    data = request.json
    analysis_id = data.get('analysis_id')
    metal = data.get('metal', "Aluminum_A380")
    annual_volume = data.get('annual_volume')
    if annual_volume is not None:
        annual_volume = int(annual_volume)
    else:
        annual_volume = 1
    sliders = int(data.get('sliders', 0))
    location_multiplier = float(data.get('location_multiplier', 1.0))
    
    if analysis_id not in part_cache:
        return jsonify({"error": "Analysis ID not found"}), 404
        
    traits = part_cache[analysis_id]
    live_prices = market_fetcher.get_live_prices()
    live_price = live_prices.get(metal, {}).get('current_price')
    exchange_rate = market_fetcher.get_exchange_rate()
    
    cost_data = calculate_hpdc_cost(
        traits, metal, annual_volume, sliders, location_multiplier, live_price_per_kg=live_price
    )

    cost_data["exchange_rate"] = exchange_rate
    cost_data["total_unit_cost_inr"] = round(cost_data["total_unit_cost"] * exchange_rate, 2)
    
    return jsonify({
        "cost_breakdown": cost_data,
        "parameters": {
            "metal": metal, "annual_volume": annual_volume, "sliders": sliders,
            "location_multiplier": location_multiplier, 
            "live_market_price_usd": live_price,
            "live_market_price_inr": round(live_price * exchange_rate, 2)
        }
    })

@app.route('/api/search-location', methods=['GET'])
def search_location():
    query = request.args.get('q', '')
    results = market_fetcher.search_location(query)
    return jsonify(results)

@app.route('/api/market-data', methods=['GET'])
def market_data():
    live_prices = market_fetcher.get_live_prices()
    locations = market_fetcher.get_location_indices()
    exchange_rate = market_fetcher.get_exchange_rate()
    next_sync_ts = market_fetcher.cache["last_updated"] + market_fetcher.ttl
    return jsonify({
        "metals": list(live_prices.keys()),
        "plant_locations": locations,
        "current_base_rates": live_prices,
        "exchange_rate": exchange_rate,
        "exchange_rates": {"INR": exchange_rate}, # Match frontend expectation
        "last_updated": market_fetcher.cache["last_updated"],
        "next_sync": next_sync_ts,
        "next_sync_display": time.ctime(next_sync_ts)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
