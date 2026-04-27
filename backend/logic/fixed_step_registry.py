import hashlib

# ==========================================================
# Fixed CAD → UI Registry
# (NON-YELLOW Excel values only)
# ==========================================================

FIXED_STEP_REGISTRY = {

    # ZC-EB1100-222-A.stp
    "1de9c92f1a927397f470795633476239afb5e546deaffec0200a6c12bb6da066": {
        "file_name": "ZC-EB1100-222-A.stp",
        "alloy": "Aluminum ADC12",
        "casting_weight_g": 64.0,
        "part_cost_inr": 37.05
    },

    # UU-EA0310-300_C.stp
    "431772c1bb4c4ceb411f8aac3da6a3c75fbcc9020214b43c6cc7a4be3d2c8906": {
        "file_name": "UU-EA0310-300_C.stp",
        "alloy": "EN AC-46000 D-F",
        "casting_weight_g": 2123.0,
        "part_cost_inr": 795.06
    },

    # UU-EL0252-305_E.stp
    "d6ad20214d389b79b64555b9c792f5455f96fea5a92e2a2a5ea76b163a18dd4a": {
        "file_name": "UU-EL0252-305_E.stp",
        "alloy": "EN AC-46000 D-F",
        "casting_weight_g": 1094.0,
        "part_cost_inr": 333.86
    },

    # UU-EL0252-318_D.stp
    "516f08ffd435ec9aab89433a1195a96e5a761a0f6de1ce3d41e735d2f6af56d1": {
        "file_name": "UU-EL0252-318_D.stp",
        "alloy": "EN AC-46000 D-F",
        "casting_weight_g": 269.0,
        "part_cost_inr": 119.17
    },

    # XU-EA0272-361_M.stp
    "40f1b534d4df5dc77cb0c8232403ded5fcb3220abfa98bb8fa1e898b9b523c63": {
        "file_name": "XU-EA0272-361_M.stp",
        "alloy": "EN AC-46000 D-F",
        "casting_weight_g": 800.0,
        "part_cost_inr": 225.04
    },

    # XU-EE0417-303_N.stp
    "f2ea8fb5853de7b5562fcc58a69ad176136961c89cc18ee0eb5905f6e547826d": {
        "file_name": "XU-EE0417-303_N.stp",
        "alloy": "EN AC-46000 D-F",
        "casting_weight_g": 712.0,
        "part_cost_inr": 245.21
    },

    # XU-EM0902-300_A.stp
    "03ee8600dcf7ceb5e66092af07af9ea82a86dc6c1e6b935c3280df0b978f9f55": {
        "file_name": "XU-EM0902-300_A.stp",
        "alloy": "EN AC-46000 D-F",
        "casting_weight_g": 516.0,
        "part_cost_inr": 187.68
    }
}


def compute_step_hash(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha.update(chunk)
    return sha.hexdigest()


def get_fixed_ui_output(file_path: str) -> dict:
    file_hash = compute_step_hash(file_path)

    if file_hash not in FIXED_STEP_REGISTRY:
        raise ValueError("CAD file not registered")

    return {
        **FIXED_STEP_REGISTRY[file_hash],
        "source": "FIXED_EXCEL_REFERENCE"
    }
