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
    lars_corrected_axis: Optional[int] = None  # axis after LARS correction, None if no trial drift

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

    Toric/multifocal rules aligned with J&J Simplifit (2023):
      - Cyl ≤ −0.75 D  → fit as spherical multifocal (cylinder ignored)
      - Cyl −1.00/−1.25 D → fit as toric multifocal
      - Cyl −1.50/−1.75 D → toric multifocal + add −0.25 D to sphere
    """

    BC_DELTA_WARN = 0.30  

    # Astigmatism thresholds — J&J Simplifit multifocal protocol (2023)
    ASTIG_SPHERICAL_MF_MAX = 0.75   # D: below/equal → treat as spherical for multifocals
    ASTIG_TORIC_MF_LOW_MAX = 1.25   # D: 1.00–1.25 → toric multifocal, no sphere adjustment
    ASTIG_TORIC_MF_HIGH_MAX = 1.75  # D: 1.50–1.75 → toric multifocal + −0.25 D sphere
    ASTIG_THRESHOLD = 0.75          # D: general threshold for spherical vs toric (non-MF)

    def __init__(self):
        self._optics = OpticsEngine()

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
        recommended_bc = self._optics.recommend_bc_from_keratometry(kero)

        candidates = []

        for lens in LENS_DATABASE:
            if lens_type_filter and lens["type"] != lens_type_filter:
                continue
            if brand_filter and lens["brand"] not in brand_filter:
                continue

            result = self._evaluate_lens(lens, cl_rx, recommended_bc, kero)
            if result is not None:
                candidates.append(result)

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:top_n]

    # LARS axis correction

    @staticmethod
    def apply_lars(prescribed_axis: int, drift_degrees: int) -> int:
        """
        LARS (Left Add, Right Subtract) rule for toric over-refraction.

        When a toric trial lens is observed to have rotated during a fitting:
          - If the lens has drifted to the LEFT  (positive drift) → ADD the
            drift to the prescribed axis.
          - If the lens has drifted to the RIGHT (negative drift) → SUBTRACT
            the drift from the prescribed axis.

        Convention used here: drift_degrees > 0 means rotation to the left
        (counter-clockwise from the practitioner's view), drift_degrees < 0
        means rotation to the right (clockwise).

        # J&J LARS rule — Contact Lens Spectrum, Gasson & Morris (2010).
        Reference: Gasson A, Morris J. "The Contact Lens Manual", 4th ed.
                   (2010), p. 195.

        Args:
            prescribed_axis: axis from the refraction (degrees, 1–180)
            drift_degrees:   observed rotation of the trial lens;
                             positive = left drift, negative = right drift

        Returns:
            Corrected axis clamped to [1, 180].
        """
        corrected = prescribed_axis + drift_degrees  # left: add; right (neg): subtract
        corrected = corrected % 180
        return corrected if corrected > 0 else 180

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

        Multifocal cylinder handling follows J&J Simplifit rules (2023):
          ≤ 0.75 D  → spherical multifocal (SE already in cl_rx.sphere for MF)
          1.00–1.25 D → toric multifocal (no sphere adjustment)
          1.50–1.75 D → toric multifocal + −0.25 D sphere correction
        """
        warnings = []
        score = 0.0
        is_multifocal = lens.get("add_range") is not None
        need_addition = cl_rx.addition > 0.0
        abs_cyl = abs(cl_rx.cylinder)

        # Determine effective sphere (may be adjusted for high-cyl multifocal)
        effective_sphere = cl_rx.sphere
        mf_sphere_adjustment = 0.0

        if is_multifocal and need_addition:
            # J&J Simplifit multifocal cylinder rules
            if abs_cyl <= self.ASTIG_SPHERICAL_MF_MAX:
                # Treat as spherical multifocal — sphere already is SE (set upstream
                # by compute_cl_refraction_multifocal), no further adjustment needed.
                need_cylinder_mf = False
            elif abs_cyl <= self.ASTIG_TORIC_MF_LOW_MAX:
                # Toric multifocal — no sphere adjustment
                need_cylinder_mf = True
                mf_sphere_adjustment = 0.0
            elif abs_cyl <= self.ASTIG_TORIC_MF_HIGH_MAX:
                # Toric multifocal + −0.25 D on sphere
                need_cylinder_mf = True
                mf_sphere_adjustment = -0.25
                effective_sphere = cl_rx.sphere + mf_sphere_adjustment
                warnings.append(
                    f"High astigmatism ({cl_rx.cylinder:.2f} D): −0.25 D applied "
                    f"to sphere for toric multifocal fit (J&J Simplifit rule)."
                )
            else:
                # Beyond Simplifit range — standard toric rules apply
                need_cylinder_mf = True
        else:
            need_cylinder_mf = False  # not relevant for non-MF path

        # For non-multifocal lenses (or multifocals where we use standard logic)
        need_cylinder = abs_cyl >= self.ASTIG_THRESHOLD

        sph_min, sph_max = lens["sphere_range"]
        if not (sph_min <= effective_sphere <= sph_max):
            return None

        if is_multifocal and need_addition:
            # Use Simplifit-derived cylinder need
            if need_cylinder_mf:
                if lens["cylinder_range"] is None:
                    # Spherical lens for a patient needing toric multifocal
                    if abs_cyl > self.ASTIG_TORIC_MF_HIGH_MAX:
                        return None
                    else:
                        warnings.append(
                            f"Toric multifocal preferred (Cyl {cl_rx.cylinder:.2f} D) "
                            f"but this model has no toric version."
                        )
                        cyl_score = 10
                else:
                    cyl_min, cyl_max = lens["cylinder_range"]
                    if not (cyl_max <= cl_rx.cylinder <= cyl_min):
                        return None
                    cyl_score = 30
            else:
                # Spherical multifocal path (cyl ≤ 0.75 D)
                if lens["cylinder_range"] is not None:
                    cyl_score = 15
                    warnings.append("Toric multifocal available — patient astigmatism ≤ 0.75 D.")
                else:
                    cyl_score = 30
        else:
            # Standard (non-multifocal) cylinder logic
            if need_cylinder:
                if lens["cylinder_range"] is None:
                    if abs_cyl >= 1.00:
                        return None
                    else:
                        warnings.append(
                            f"Astigmatism {cl_rx.cylinder:.2f} D uncorrected "
                            f"(< 1.00 D, may be tolerated)."
                        )
                        cyl_score = 10
                else:
                    cyl_min, cyl_max = lens["cylinder_range"]
                    if not (cyl_max <= cl_rx.cylinder <= cyl_min):
                        return None
                    cyl_score = 30
            else:
                if lens["cylinder_range"] is not None:
                    cyl_score = 15
                    warnings.append("Toric lens available — patient is not astigmatic.")
                else:
                    cyl_score = 30

        add_score = 0
        ordered_addition = None
        if need_addition:
            if lens.get("add_range") is None:
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

        # Sphere score
        sph_range_width = sph_max - sph_min
        sph_margin = min(
            abs(effective_sphere - sph_min),
            abs(effective_sphere - sph_max)
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
        ordered_sph = _round_to_step(effective_sphere, sph_step)
        ordered_sph = max(sph_min, min(sph_max, ordered_sph))

        # Cylinder for toric path
        active_cyl_need = need_cylinder_mf if (is_multifocal and need_addition) else need_cylinder
        if active_cyl_need and lens["cylinder_range"] is not None:
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
            lars_corrected_axis=None,  # populated externally after trial lens assessment
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