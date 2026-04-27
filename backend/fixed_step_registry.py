import hashlib

def compute_step_hash(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha.update(chunk)
    return sha.hexdigest()
FIXED_STEP_REGISTRY = {

    "1de9c92f1a927397f470795633476239afb5e546deaffec0200a6c12bb6da066": {
        "file_name": "ZC-EB1100-222-A.stp",
        "alloy": "Aluminum ADC12",
        "casting_weight_g": 64.0,   # 0.064 kg from Excel
        "part_cost_inr": 37.05
    }

}
"431772c1bb4c4ceb411f8aac3da6a3c75fbcc9020214b43c6cc7a4be3d2c8906": {
    "file_name": "UU-EA0310-300_C.stp",
    "alloy": "EN AC-46000 D-F",
    "casting_weight_g": 2123.0,   # Excel non-yellow value
    "part_cost_inr": 795.06
},