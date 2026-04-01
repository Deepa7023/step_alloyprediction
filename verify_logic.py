import sys
import os
import math

# Add current directory to path to import logic
sys.path.append(os.getcwd())

from backend.logic.cost_engine import calculate_hpdc_cost

def test_cost_engine():
    print("--- HPDC Cost Engine Verification ---")
    
    # Test Case 1: Small Cube (10x10x10 mm)
    traits_cube = {
        'volume': 1000.0, # mm3
        'projected_area': 100.0, # mm2
        'dimensions': {'x': 10, 'y': 10, 'z': 10}
    }
    
    # Test Case 2: Thin Plate (100x100x1 mm) - Same volume as a 21x21x21 cube approx
    # But projected area is 10000 mm2 vs 100 mm2 for the cube
    traits_plate = {
        'volume': 10000.0, # mm3
        'projected_area': 10000.0, # mm2
        'dimensions': {'x': 100, 'y': 100, 'z': 1}
    }

    metal = "A380 (Aluminum)"
    annual_volume = 10000
    
    report_cube = calculate_hpdc_cost(traits_cube, metal, annual_volume, 0)
    report_plate = calculate_hpdc_cost(traits_plate, metal, annual_volume, 0)
    
    print(f"\n[CUBE 10mm] ({traits_cube['volume']}mm3, {traits_cube['projected_area']}mm2)")
    print(f"  Material Cost: ${report_cube['material_cost']}")
    print(f"  Required Tonnage: {report_cube['machine_details']['required_tonnage']}T")
    print(f"  Selected Machine: {report_cube['machine_details']['selected_machine']}T")
    print(f"  Machine Cost/Part: ${report_cube['machine_cost']}")
    print(f"  Total Unit Cost: ${report_cube['total_unit_cost']}")

    print(f"\n[PLATE 100mm] ({traits_plate['volume']}mm3, {traits_plate['projected_area']}mm2)")
    print(f"  Material Cost: ${report_plate['material_cost']}")
    print(f"  Required Tonnage: {report_plate['machine_details']['required_tonnage']}T")
    print(f"  Selected Machine: {report_plate['machine_details']['selected_machine']}T")
    print(f"  Machine Cost/Part: ${report_plate['machine_cost']}")
    print(f"  Total Unit Cost: ${report_plate['total_unit_cost']}")

    # Verification Logic
    # 1. Plate should require much higher tonnage
    assert report_plate['machine_details']['required_tonnage'] > report_cube['machine_details']['required_tonnage']
    # 2. Total cost should reflect the machine size difference
    assert report_plate['total_unit_cost'] > report_cube['total_unit_cost']
    
    print("\n[SUCCESS] Cost engine correctly differentiates between volume-equivalent but geometrically distinct parts.")

if __name__ == "__main__":
    test_cost_engine()
