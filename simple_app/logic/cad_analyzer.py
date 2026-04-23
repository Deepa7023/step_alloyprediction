import logging
import os
import re
import time
import uuid

import numpy as np
import trimesh

from .step_engine_ocp import METAL_KEYWORDS, PreciseSTEPAnalyzer, detect_metal_from_step

logger = logging.getLogger(__name__)

BREP_EXTENSIONS = [".step", ".stp", ".iges", ".igs"]
MESH_EXTENSIONS = [".stl", ".obj", ".ply", ".glb", ".gltf", ".3mf", ".off", ".dae"]
SUPPORTED_CAD_EXTENSIONS = BREP_EXTENSIONS + MESH_EXTENSIONS


def _float_env(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sort_dimensions_mm(values):
    dims = sorted([max(_safe_float(v, 0.0), 0.001) for v in values], reverse=True)
    while len(dims) < 3:
        dims.append(0.001)
    return {"x": round(dims[0], 2), "y": round(dims[1], 2), "z": round(dims[2], 2)}


def _scale_to_mm(dimensions_mm, volume_mm3=None, surface_mm2=None):
    dims = [_safe_float(v, 0.001) for v in dimensions_mm.values()]
    max_dim = max(dims)
    median_dim = sorted(dims)[1]

    scale = 1.0
    scale_note = "input coordinates treated as mm"

    if max_dim > 100000:
        scale = 0.001
        scale_note = "input coordinates auto-scaled from micron-like units to mm"
    elif max_dim > 5000 and median_dim > 100:
        scale = 0.1
        scale_note = "input coordinates auto-scaled from tenth-mm-like units to mm"
    elif 0 < max_dim < 1:
        scale = 1000.0
        scale_note = "input coordinates auto-scaled from meter-like units to mm"

    scaled_dims = _sort_dimensions_mm([d * scale for d in dims])
    scaled_volume = volume_mm3 * (scale ** 3) if volume_mm3 is not None else None
    scaled_surface = surface_mm2 * (scale ** 2) if surface_mm2 is not None else None
    return scaled_dims, scaled_volume, scaled_surface, scale_note, scale


def _geometry_metrics_from_dims(dimensions):
    x, y, z = dimensions["x"], dimensions["y"], dimensions["z"]
    bbox_volume = float(x * y * z)
    bbox_surface = float(2.0 * ((x * y) + (y * z) + (x * z)))
    projected_area = float(max(x * y, y * z, x * z))
    return {
        "bbox_volume_mm3": bbox_volume,
        "bbox_surface_mm2": bbox_surface,
        "bbox_projected_area_mm2": projected_area,
    }


def _normalize_traits(volume_mm3, surface_mm2, dimensions, projected_area_mm2, topology, validation, note=""):
    dimensions = _sort_dimensions_mm(dimensions.values())
    bbox_metrics = _geometry_metrics_from_dims(dimensions)
    bbox_volume = bbox_metrics["bbox_volume_mm3"]
    bbox_surface = bbox_metrics["bbox_surface_mm2"]

    volume_mm3 = max(_safe_float(volume_mm3, 0.0), 0.001)
    surface_mm2 = max(_safe_float(surface_mm2, 0.0), 0.01)
    projected_area_mm2 = max(_safe_float(projected_area_mm2, 0.0), bbox_metrics["bbox_projected_area_mm2"])

    if bbox_volume > 0:
        volume_mm3 = min(volume_mm3, bbox_volume * 1.02)
    surface_mm2 = min(max(surface_mm2, bbox_surface * 0.22), bbox_surface * 1.25)
    projected_area_mm2 = min(projected_area_mm2, bbox_metrics["bbox_projected_area_mm2"] * 1.02)

    bbox_fill_ratio = round(volume_mm3 / max(bbox_volume, 1.0), 4) if bbox_volume > 0 else 0.0
    surface_efficiency = round(surface_mm2 / max(bbox_surface, 1.0), 4)

    validation = dict(validation or {})
    if note:
        existing = validation.get("note", "")
        validation["note"] = f"{existing}; {note}".strip("; ")
    validation["bbox_fill_ratio"] = bbox_fill_ratio
    validation["surface_efficiency"] = surface_efficiency

    return {
        "volume": float(round(volume_mm3, 3)),
        "surface_area": float(round(surface_mm2, 3)),
        "dimensions": dimensions,
        "projected_area": float(round(projected_area_mm2, 3)),
        "topology": topology or {},
        "validation": validation,
    }


def _load_mesh(file_path):
    mesh_raw = trimesh.load(file_path)
    if isinstance(mesh_raw, trimesh.Scene):
        parts = [g for g in mesh_raw.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if parts:
            prepared = [_prepare_mesh_part(part) for part in parts]
            prepared = [part for part in prepared if part is not None]
            if prepared:
                prepared.sort(key=_mesh_selection_key, reverse=True)
                return prepared[0]
    elif isinstance(mesh_raw, trimesh.Trimesh):
        return _prepare_mesh_part(mesh_raw)
    return None


def _prepare_mesh_part(mesh):
    if mesh is None or not isinstance(mesh, trimesh.Trimesh):
        return None
    try:
        part = mesh.copy()
        if hasattr(part, "remove_unreferenced_vertices"):
            part.remove_unreferenced_vertices()
        if hasattr(part, "remove_degenerate_faces"):
            part.remove_degenerate_faces()
        if hasattr(part, "remove_duplicate_faces"):
            part.remove_duplicate_faces()
        if hasattr(part, "remove_infinite_values"):
            part.remove_infinite_values()
        if hasattr(part, "merge_vertices"):
            part.merge_vertices()
        if hasattr(part, "process"):
            part.process(validate=True)

        if hasattr(part, "split"):
            components = [c for c in part.split(only_watertight=False) if isinstance(c, trimesh.Trimesh)]
            if components:
                components = [c for c in components if len(getattr(c, "vertices", [])) > 2]
                if components:
                    components.sort(key=_mesh_selection_key, reverse=True)
                    part = components[0]
        return part
    except Exception:
        return mesh


def _mesh_selection_key(mesh):
    try:
        if bool(getattr(mesh, "is_watertight", False)):
            return (2, abs(float(getattr(mesh, "volume", 0.0))), float(getattr(mesh, "area", 0.0)))
        return (1, float(getattr(mesh, "area", 0.0)), len(getattr(mesh, "faces", [])))
    except Exception:
        return (0, 0.0, 0.0)


def _mesh_dimensions(mesh):
    if mesh is None:
        return _sort_dimensions_mm([1.0, 1.0, 1.0]), "fallback axis-aligned bounding box"
    try:
        obb = mesh.bounding_box_oriented
        extents = obb.primitive.extents
        dims = _sort_dimensions_mm(extents.tolist())
        return dims, "trimesh oriented bounding box"
    except Exception:
        try:
            return _sort_dimensions_mm(mesh.extents.tolist()), "axis-aligned mesh extents"
        except Exception:
            return _sort_dimensions_mm([1.0, 1.0, 1.0]), "fallback axis-aligned bounding box"


def _mesh_projected_area(mesh, dimensions):
    try:
        if mesh is None:
            raise ValueError("mesh unavailable")
        oriented = mesh.copy()
        if hasattr(oriented, "remove_unreferenced_vertices"):
            oriented.remove_unreferenced_vertices()
        areas = []
        for axis in ([1, 0, 0], [0, 1, 0], [0, 0, 1]):
            proj = trimesh.path.polygons.projected(oriented, normal=axis)
            areas.append(float(abs(proj.area)))
        if areas:
            return max(areas)
    except Exception:
        pass
    return max(
        dimensions["x"] * dimensions["y"],
        dimensions["y"] * dimensions["z"],
        dimensions["x"] * dimensions["z"],
    )


def _mesh_validation(mesh):
    if mesh is None:
        return {"is_manifold": False, "integrity_score": 60}

    score = 55.0
    watertight = bool(getattr(mesh, "is_watertight", False))
    winding = bool(getattr(mesh, "is_winding_consistent", False))
    euler_ok = False
    try:
        euler_ok = mesh.euler_number >= 0
    except Exception:
        euler_ok = False

    if watertight:
        score += 25.0
    if winding:
        score += 10.0
    if euler_ok:
        score += 5.0
    try:
        if len(mesh.faces) > 20:
            score += 5.0
    except Exception:
        pass
    try:
        if mesh.area > 0:
            score += 5.0
    except Exception:
        pass
    return {"is_manifold": watertight, "integrity_score": int(_safe_float(score, 60.0))}


def _analyze_step_lightweight(file_path):
    point_pattern = re.compile(
        r"#(\d+)\s*=\s*CARTESIAN_POINT\s*\([^,]*,\s*\(\s*([-+0-9.Ee]+)\s*,\s*([-+0-9.Ee]+)\s*,\s*([-+0-9.Ee]+)\s*\)\s*\)",
        re.IGNORECASE,
    )
    vertex_pattern = re.compile(r"#\d+\s*=\s*VERTEX_POINT\s*\([^,]*,\s*#(\d+)\s*\)", re.IGNORECASE)

    point_map = {}
    vertex_refs = set()
    with open(file_path, "r", errors="ignore") as handle:
        for line in handle:
            match = point_pattern.search(line)
            if match:
                point_map[match.group(1)] = tuple(float(value) for value in match.groups()[1:])
            vertex_match = vertex_pattern.search(line)
            if vertex_match:
                vertex_refs.add(vertex_match.group(1))

    vertex_points = [point_map[ref] for ref in vertex_refs if ref in point_map]
    points = vertex_points if len(vertex_points) >= 2 else list(point_map.values())
    point_source = "VERTEX_POINT geometry" if len(vertex_points) >= 2 else "CARTESIAN_POINT bounding box"

    if len(points) < 2:
        raise ValueError(
            "STEP_LIGHTWEIGHT_PARSE_FAILURE: No usable CARTESIAN_POINT geometry was found. "
            "Export this part as binary STL/OBJ, or upload a STEP file with explicit B-Rep coordinates."
        )

    arr = np.array(points, dtype=float)
    mins = arr.min(axis=0)
    maxs = arr.max(axis=0)
    extents = np.maximum(maxs - mins, 0.001)
    raw_dimensions = _sort_dimensions_mm(extents.tolist())
    bbox_metrics = _geometry_metrics_from_dims(raw_dimensions)
    scaled_dimensions, bbox_volume_mm3, bbox_surface_mm2, scale_note, _ = _scale_to_mm(
        raw_dimensions,
        bbox_metrics["bbox_volume_mm3"],
        bbox_metrics["bbox_surface_mm2"],
    )
    scaled_bbox = _geometry_metrics_from_dims(scaled_dimensions)

    fill_factor = _float_env("STEP_LIGHTWEIGHT_FILL_FACTOR", 0.28)
    surface_factor = _float_env("STEP_LIGHTWEIGHT_SURFACE_FACTOR", 0.72)
    projected_area_factor = _float_env("STEP_LIGHTWEIGHT_PROJECTED_AREA_FACTOR", 0.94)

    estimated_volume = scaled_bbox["bbox_volume_mm3"] * fill_factor
    estimated_surface = scaled_bbox["bbox_surface_mm2"] * surface_factor
    estimated_projected_area = scaled_bbox["bbox_projected_area_mm2"] * projected_area_factor

    return _normalize_traits(
        volume_mm3=estimated_volume,
        surface_mm2=estimated_surface,
        dimensions=scaled_dimensions,
        projected_area_mm2=estimated_projected_area,
        topology={
            "solids": 1,
            "faces": 0,
            "edges": 0,
            "vertices": len(points),
        },
        validation={
            "is_manifold": False,
            "integrity_score": 48,
        },
        note=f"Render-safe STEP estimate from {point_source}; fill_factor={fill_factor}; surface_factor={surface_factor}; {scale_note}",
    )


def _brep_enabled():
    return os.getenv("CAD_BREP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def detect_metal_hint(file_path):
    text = os.path.basename(file_path).upper()
    try:
        with open(file_path, "r", errors="ignore") as handle:
            text = f"{text}\n{handle.read(16384).upper()}"
    except Exception:
        pass

    for keyword, metal_name in METAL_KEYWORDS.items():
        if keyword in text:
            return metal_name
    return None


def analyze_cad(file_path):
    analysis_id = str(uuid.uuid4())
    ext = os.path.splitext(file_path)[1].lower()
    mesh = None
    precise_data = {}
    detected_metal = None

    try:
        if ext not in SUPPORTED_CAD_EXTENSIONS:
            raise ValueError(
                f"UNSUPPORTED_CAD_FORMAT: {ext or 'unknown'} is not supported. "
                f"Supported formats: {', '.join(SUPPORTED_CAD_EXTENSIONS)}"
            )

        detected_metal = detect_metal_hint(file_path)
        if not detected_metal and ext in [".step", ".stp"]:
            detected_metal = detect_metal_from_step(file_path)
            if detected_metal:
                logger.info("METAL_DETECT: Auto-detected %s", detected_metal)

        if ext in BREP_EXTENSIONS and not _brep_enabled():
            traits = _analyze_step_lightweight(file_path)
            return {
                "analysis_id": analysis_id,
                "traits": traits,
                "engine": "STEP_LIGHTWEIGHT_RENDER_SAFE",
                "detected_metal": detected_metal,
                "metadata": {"location": "PENDING_SYNC", "timestamp": time.time()},
            }

        if ext in BREP_EXTENSIONS:
            analyzer = PreciseSTEPAnalyzer()
            precise_data = analyzer.analyze(file_path)
            if precise_data.get("status") == "success":
                logger.info("PRECISE_ENGINE: Analysis succeeded.")
            else:
                logger.warning("PRECISE_ENGINE: Failed (%s)", precise_data.get("reason"))

        try:
            mesh = _load_mesh(file_path)
        except Exception as exc:
            logger.warning("Trimesh load failed: %s", exc)

        if mesh is None and precise_data.get("status") != "success":
            reason = precise_data.get("reason", "No engine could parse this file")
            raise ValueError(
                f"GEOMETRY_PARSE_FAILURE: File {ext} could not be analyzed. "
                f"Engine report: {reason}. Please ensure it is a valid 3D file."
            )

        volume_mm3 = None
        surface_mm2 = None
        dimensions = None
        projected_area_mm2 = None
        scale_note = ""

        precise_volume_cm3 = precise_data.get("precise_volume_cm3")
        precise_surface_cm2 = precise_data.get("precise_surface_cm2")
        precise_dimensions = precise_data.get("dimensions")
        precise_projected_area = precise_data.get("projected_area_mm2")

        if precise_volume_cm3 is not None:
            volume_mm3 = float(precise_volume_cm3) * 1000.0
        elif mesh is not None:
            try:
                volume_mm3 = float(abs(mesh.volume))
            except Exception:
                volume_mm3 = None

        if precise_surface_cm2 is not None:
            surface_mm2 = float(precise_surface_cm2) * 100.0
        elif mesh is not None:
            try:
                surface_mm2 = float(mesh.area)
            except Exception:
                surface_mm2 = None

        dimension_source = "precise engine dimensions"
        if precise_dimensions:
            dimensions = _sort_dimensions_mm(precise_dimensions.values())
        elif mesh is not None:
            dimensions, dimension_source = _mesh_dimensions(mesh)
        else:
            dimensions = _sort_dimensions_mm([1.0, 1.0, 1.0])
            dimension_source = "fallback unit cube"

        dimensions, volume_mm3, surface_mm2, scale_note, scale_factor = _scale_to_mm(
            dimensions,
            volume_mm3,
            surface_mm2,
        )

        if precise_projected_area is not None:
            projected_area_mm2 = float(precise_projected_area) * (scale_factor ** 2)
        elif mesh is not None:
            projected_area_mm2 = _mesh_projected_area(mesh, dimensions) * (scale_factor ** 2 if scale_factor != 1.0 else 1.0)

        topology = precise_data.get(
            "topology",
            {
                "solids": 1,
                "faces": len(mesh.faces) if mesh is not None and hasattr(mesh, "faces") else 0,
                "edges": 0,
                "vertices": len(mesh.vertices) if mesh is not None and hasattr(mesh, "vertices") else 0,
            },
        )
        validation = precise_data.get("validation") or _mesh_validation(mesh)

        note_parts = []
        note_parts.append(f"dimension source: {dimension_source}")
        if scale_note and scale_note != "input coordinates treated as mm":
            note_parts.append(scale_note)
        if precise_data.get("status") == "success":
            note_parts.append("precise B-Rep geometry used where available")
        elif mesh is not None:
            note_parts.append("mesh-derived geometry with trimesh cleanup, component selection, and bounding-box consistency checks")

        traits = _normalize_traits(
            volume_mm3=volume_mm3,
            surface_mm2=surface_mm2,
            dimensions=dimensions,
            projected_area_mm2=projected_area_mm2,
            topology=topology,
            validation=validation,
            note="; ".join(note_parts),
        )

        logger.info(
            "GEOMETRY: dims=%s vol=%scm3 proj=%smm2 fill=%s",
            traits["dimensions"],
            round(traits["volume"] / 1000.0, 2),
            round(traits["projected_area"], 2),
            traits["validation"].get("bbox_fill_ratio"),
        )

        engine_name = "OCP_PRECISE" if precise_data.get("status") == "success" else "MESH_FALLBACK"
        return {
            "analysis_id": analysis_id,
            "traits": traits,
            "engine": engine_name,
            "detected_metal": detected_metal,
            "metadata": {"location": "PENDING_SYNC", "timestamp": time.time()},
        }

    except Exception as exc:
        logger.error("CRITICAL_FAILURE: %s", exc, exc_info=True)
        return {"error": str(exc)}
