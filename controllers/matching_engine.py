"""
controllers/matching_engine.py
Matching engine: selects and ranks contact lenses from the database
based on the computed CL refraction and keratometry data.

MVC separation: this module has no knowledge of the GUI.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from controllers.optics_engine import CLRx, Keratometry, OpticsEngine
from data.lens_database import LENS_DATABASE


# Score and results

@dataclass
class LensCandidate:
    """A candidate produced by the matching engine with its score and order."""
    lens_data: Dict[str, Any]          # raw database entry
    score: float                        # 0-100 (higher is better)
    ordered_sphere: float
    ordered_cylinder: float
    ordered_axis: int
    ordered_bc: float
    ordered_diameter: float
    ordered_addition: Optional[str]
    warnings: List[str] = field(default_factory=list)
    fit_notes: str = ""

    @property
    def brand(self): return self.lens_data["brand"]
    @property
    def model(self): return self.lens_data["model"]
    @property
    def platform(self): return self.lens_data["platform"]
    @property
    def lens_type(self): return self.lens_data["type"]
    @property
    def material(self): return self.lens_data["material"]
    @property
    def dk_t(self): return self.lens_data["dk_t"]


# Matching engine

class MatchingEngine:
    """
    Multi-criteria selection algorithm.

    Steps:
      1. Mandatory filtering: computed power must be within the lens manufacturing range.
      2. Select the BC closest to the optical recommendation.
      3. Round powers to manufacturing steps.
      4. Composite score:
           - Sphere compatibility     (40 pts)
           - Cylinder compatibility   (30 pts)
           - BC compatibility         (20 pts)
           - Presbyopia / ortho-K bonus (10 pts)
      5. Generate clinical warnings.
    """

    BC_DELTA_WARN = 0.30    # mm: deviation between recommended and available BC
    ASTIG_THRESHOLD = 0.75  # D: cylinder above which a toric lens is required

    def __init__(self):
        self._optics = OpticsEngine()

    # Main API

    def find_candidates(
        self,
        cl_rx: CLRx,
        kero: Keratometry,
        lens_type_filter: Optional[str] = None,
        brand_filter: Optional[List[str]] = None,
        top_n: int = 5,
    ) -> List[LensCandidate]:
        """
        Return the top_n best lenses for the given refraction and keratometry.

        Args:
            cl_rx:            computed CL refraction
            kero:             keratometry data
            lens_type_filter: "daily" | "monthly" | "biweekly" | None
            brand_filter:     list of brands to include (None = all)
            top_n:            number of results to return

        Returns:
            List sorted by descending score.
        """
        # 1. Recommended BC
        recommended_bc = self._optics.recommend_bc_from_keratometry(kero)

        candidates = []

        for lens in LENS_DATABASE:
            # Preliminary filters
            if lens_type_filter and lens["type"] != lens_type_filter:
                continue
            if brand_filter and lens["brand"] not in brand_filter:
                continue

            result = self._evaluate_lens(lens, cl_rx, recommended_bc, kero)
            if result is not None:
                candidates.append(result)

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:top_n]

    # Lens evaluation

    def _evaluate_lens(
        self,
        lens: Dict,
        cl_rx: CLRx,
        recommended_bc: float,
        kero: Keratometry,
    ) -> Optional[LensCandidate]:
        """
        Evaluate a candidate lens.
        Returns None if the lens is incompatible (out of mandatory range).
        """
        warnings = []
        score = 0.0
        need_cylinder = abs(cl_rx.cylinder) >= self.ASTIG_THRESHOLD
        need_addition = cl_rx.addition > 0.0

        # Test 1: sphere range
        sph_min, sph_max = lens["sphere_range"]
        if not (sph_min <= cl_rx.sphere <= sph_max):
            return None  # out of range -> hard exclusion

        # Test 2: cylinder
        if need_cylinder:
            if lens["cylinder_range"] is None:
                # Spherical lens for an astigmatic patient
                # Allowed but penalised if astigmatism >= 1.00 D
                if abs(cl_rx.cylinder) >= 1.00:
                    return None  # too much astigmatism for a spherical lens
                else:
                    warnings.append(
                        f"Astigmatism {cl_rx.cylinder:.2f} D uncorrected "
                        f"(< 1.00 D, may be tolerated)."
                    )
                    cyl_score = 10
            else:
                cyl_min, cyl_max = lens["cylinder_range"]  # negative values
                if not (cyl_max <= cl_rx.cylinder <= cyl_min):
                    return None  # astigmatisme outside toric range
                cyl_score = 30
        else:
            if lens["cylinder_range"] is not None:
                # Toric lens for a non-astigmatic patient: possible but suboptimal
                cyl_score = 15
                warnings.append("Toric lens available — patient is not astigmatic.")
            else:
                cyl_score = 30

        # Test 3: addition
        add_score = 0
        ordered_addition = None
        if need_addition:
            if lens.get("add_range") is None:
                # No multifocal version -> exclude if addition >= 1.50 D
                if cl_rx.addition >= 1.50:
                    return None
                else:
                    warnings.append("Multifocal version not available for this model.")
            else:
                add_min, add_max = lens["add_range"]
                if cl_rx.addition < add_min:
                    ordered_addition = _format_addition(add_min, lens)
                    warnings.append(f"Minimum addition {add_min:.2f} D used.")
                elif cl_rx.addition > add_max:
                    ordered_addition = _format_addition(add_max, lens)
                    warnings.append(f"Maximum addition {add_max:.2f} D used.")
                else:
                    add_step = lens.get("add_steps", 0.50)
                    add_val = _round_to_step(cl_rx.addition, add_step)
                    ordered_addition = _format_addition(add_val, lens)
                add_score = 10

        # Sphere score: higher when power is well within range (not at limits)
        sph_range_width = sph_max - sph_min
        sph_margin = min(
            abs(cl_rx.sphere - sph_min),
            abs(cl_rx.sphere - sph_max)
        )
        sph_score = 40 * min(1.0, sph_margin / (sph_range_width / 4 + 0.01))

        # BC selection and score
        best_bc = min(lens["base_curves"], key=lambda bc: abs(bc - recommended_bc))
        bc_delta = abs(best_bc - recommended_bc)

        if bc_delta > self.BC_DELTA_WARN:
            warnings.append(
                f"Selected BC ({best_bc:.2f} mm) deviates by {bc_delta:.2f} mm "
                f"from recommended BC ({recommended_bc:.2f} mm). Verify fit."
            )
        bc_score = 20 * max(0, 1 - bc_delta / 0.5)

        # Round powers to manufacturing steps
        sph_step = lens.get("sphere_steps", 0.25)
        ordered_sph = _round_to_step(cl_rx.sphere, sph_step)
        ordered_sph = max(sph_min, min(sph_max, ordered_sph))  # clamp to range

        if need_cylinder and lens["cylinder_range"] is not None:
            cyl_step = lens.get("cylinder_steps", 0.50)
            ordered_cyl = _round_to_step(cl_rx.cylinder, cyl_step)
            cyl_min_v, cyl_max_v = lens["cylinder_range"]
            ordered_cyl = max(cyl_max_v, min(cyl_min_v, ordered_cyl))
            ordered_axis = _round_axis_to_step(cl_rx.axis, lens.get("axis_steps", 10))
        else:
            ordered_cyl = 0.0
            ordered_axis = 0

        # Total score
        total_score = sph_score + cyl_score + bc_score + add_score

        # Dk/t bonus: favour high-oxygen-transmissibility lenses
        if lens["dk_t"] >= 140:
            total_score = min(100, total_score + 3)
        elif lens["dk_t"] >= 100:
            total_score = min(100, total_score + 1)

        fit_notes = lens.get("fitting_notes", lens.get("notes", ""))

        return LensCandidate(
            lens_data=lens,
            score=round(total_score, 1),
            ordered_sphere=ordered_sph,
            ordered_cylinder=ordered_cyl,
            ordered_axis=ordered_axis,
            ordered_bc=best_bc,
            ordered_diameter=lens["diameters"][0],
            ordered_addition=ordered_addition,
            warnings=warnings,
            fit_notes=fit_notes,
        )


# Private helpers

def _round_to_step(value: float, step: float) -> float:
    return round(value / step) * step


def _round_axis_to_step(axis: int, step: int) -> int:
    """Round axis to the nearest manufacturing step (e.g. 10 degrees)."""
    rounded = round(axis / step) * step
    if rounded == 0:
        rounded = step
    if rounded == 180:
        rounded = 180
    return rounded


def _format_addition(add_val: float, lens: Dict) -> str:
    """Format addition value with manufacturer designation if available."""
    designations = lens.get("add_designations")
    if designations:
        add_min, add_max = lens["add_range"]
        if add_val <= add_min:
            return f"+{add_val:.2f} ({designations[0]})"
        elif add_val >= add_max:
            return f"+{add_val:.2f} ({designations[-1]})"
        else:
            mid = designations[len(designations) // 2]
            return f"+{add_val:.2f} ({mid})"
    return f"+{add_val:.2f}"
