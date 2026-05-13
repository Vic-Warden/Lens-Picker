"""
controllers/optics_engine.py
Optical computation engine — vertex distance conversion and refractive utilities.

Strict separation: this module has no knowledge of the GUI or the database.
All formulas are documented with their physical assumptions.
"""

import math
from dataclasses import dataclass
from typing import Optional


# Input / output data structures

@dataclass
class SpectacleRx:
    """Spectacle refraction at the lens plane (frame plane)."""
    sphere: float          # diopters
    cylinder: float        # diopters (minus-cylinder convention)
    axis: int              # degrees 0-180
    addition: float        # diopters (0 if not presbyopic)
    vertex_distance: float = 12.0  # mm, vertex distance


@dataclass
class Keratometry:
    """Keratometry data."""
    r1: float       # flat meridian radius (mm)
    r2: float       # steep meridian radius (mm)
    axis_flat: int = 0  # axis of flat meridian (degrees)

    @property
    def k1_diopters(self) -> float:
        """Flat meridian K in diopters (keratometric index 1.3375)."""
        return _radius_to_diopters(self.r1)

    @property
    def k2_diopters(self) -> float:
        """Steep meridian K in diopters."""
        return _radius_to_diopters(self.r2)

    @property
    def km_diopters(self) -> float:
        """Mean K (Km) in diopters."""
        return (self.k1_diopters + self.k2_diopters) / 2.0

    @property
    def corneal_astigmatism_diopters(self) -> float:
        """Corneal astigmatism in diopters (absolute value)."""
        return abs(self.k2_diopters - self.k1_diopters)


@dataclass
class CLRx:
    """
    Contact lens refraction computed at the corneal plane.
    This is the ideal prescription BEFORE matching against the database.
    """
    sphere: float
    cylinder: float   # 0.00 for spherical
    axis: int         # cylinder axis (may differ from spectacle axis)
    addition: float
    vertex_distance: float = 0.0  # always 0 for a CL

    def __str__(self):
        cyl_str = f"  Cyl {self.cylinder:+.2f} x {self.axis}deg" if self.cylinder else ""
        add_str = f"  Add +{self.addition:.2f}" if self.addition else ""
        return f"Sph {self.sphere:+.2f}{cyl_str}{add_str}"


# Low-level utility functions

def _radius_to_diopters(radius_mm: float, index: float = 1.3375) -> float:
    """
    Convert radius of curvature (mm) to power in diopters.
    Formula: P = (n - 1) / r, with r in meters.
    Standard keratometric index = 1.3375.
    """
    if radius_mm <= 0:
        raise ValueError(f"Radius of curvature must be positive (received: {radius_mm})")
    return (index - 1.0) / (radius_mm / 1000.0)


def vertex_compensation(power_spectacle: float, vertex_mm: float) -> float:
    """
    Exact vertex distance compensation formula.

    Physical assumption:
        A lens of power F_v placed at distance d from the corneal plane
        is equivalent to a contact lens of power F_cl at the corneal plane:

            F_cl = F_v / (1 - d * F_v)    [d in meters]

    References: BS EN ISO 18369-1:2017; Rabbetts "Bennett & Rabbetts'
    Clinical Visual Optics", 4th ed.

    Args:
        power_spectacle: spectacle lens power (D)
        vertex_mm: vertex distance in millimeters

    Returns:
        Equivalent power at the corneal plane (D)
    """
    d_m = vertex_mm / 1000.0  # mm to m
    denominator = 1.0 - d_m * power_spectacle
    if abs(denominator) < 1e-9:
        raise ValueError("Infinite power — zero denominator.")
    return power_spectacle / denominator


def _round_to_step(value: float, step: float) -> float:
    """Round a value to the nearest manufacturing step."""
    return round(value / step) * step


def _normalize_cylinder_axis(axis: int) -> int:
    """Clamp axis to [1, 180]."""
    axis = axis % 180
    return axis if axis > 0 else 180


# Main computation engine

class OpticsEngine:
    """
    Computes contact lens refraction from spectacle refraction by applying
    vertex distance compensation meridian by meridian (exact method),
    then converts to standard sphere/cylinder/axis form.
    """

    def compute_cl_refraction(self, rx: SpectacleRx) -> CLRx:
        """
        Full conversion: spectacle refraction -> contact lens refraction.

        Algorithm (principal meridians):
          1. Decompose refraction into two meridional powers.
          2. Apply vertex compensation to each meridian.
          3. Recompose into sphere/cylinder/axis.
        """
        # 1. Meridional powers at the spectacle plane
        f_sphere = rx.sphere
        f_cylinder = rx.cylinder if rx.cylinder else 0.0
        axis_rad = math.radians(rx.axis)

        f_meridian_1 = f_sphere               # meridian perpendicular to cylinder (= sphere)
        f_meridian_2 = f_sphere + f_cylinder  # meridian of cylinder

        # 2. Vertex compensation per meridian
        d = rx.vertex_distance

        # Apply compensation only when |F| > 4 D (clinically significant)
        if abs(f_meridian_1) > 4.0:
            f1_cl = vertex_compensation(f_meridian_1, d)
        else:
            f1_cl = f_meridian_1

        if abs(f_meridian_2) > 4.0:
            f2_cl = vertex_compensation(f_meridian_2, d)
        else:
            f2_cl = f_meridian_2

        # 3. Recompose into sphere/cylinder form
        sph_cl = f1_cl
        cyl_cl = f2_cl - f1_cl

        # Clinical rounding: 0.25 D step for sphere
        sph_cl = _round_to_step(sph_cl, 0.25)
        cyl_cl = _round_to_step(cyl_cl, 0.25)

        # Enforce minus-cylinder convention
        if cyl_cl > 0:
            sph_cl += cyl_cl
            cyl_cl = -cyl_cl
            rx_axis = _normalize_cylinder_axis(rx.axis + 90)
        else:
            rx_axis = _normalize_cylinder_axis(rx.axis)

        # Cylinder < 0.25 D -> treat as spherical
        if abs(cyl_cl) < 0.25:
            cyl_cl = 0.0
            rx_axis = 0

        add = rx.addition if rx.addition else 0.0

        return CLRx(
            sphere=sph_cl,
            cylinder=cyl_cl,
            axis=rx_axis,
            addition=add,
            vertex_distance=0.0,
        )

    def estimate_sagittal_depth(self, r_mm: float, diameter_mm: float) -> float:
        """
        Sagittal depth of a spherical contact lens.
        Formula: sag = r - sqrt(r^2 - (diameter/2)^2)

        Useful for comparing BC fit against Km.
        """
        r = r_mm
        half_chord = diameter_mm / 2.0
        if r < half_chord:
            raise ValueError("Radius of curvature is smaller than the semi-diameter.")
        return r - math.sqrt(r**2 - half_chord**2)

    def recommend_bc_from_keratometry(
        self,
        kero: Keratometry,
        lens_diameter: float = 14.2,
        fitting_rule: str = "flat_k_plus_offset",
    ) -> float:
        """
        Empirical rule for base curve (BC) selection from Km.

        Available rules:
          - "flat_k_plus_offset": BC = flat_r + 0.10 mm  (classic SCL rule)
          - "mean_k":             BC = mean_r (used by some manufacturers)
          - "ortho_k_flat_k":     BC = flat_r + 0.50 mm  (initial ortho-K)

        Reference: Efron N. "Contact Lens Practice", 3rd ed. (2018) - p. 112.
        """
        r_flat = self.k1_to_radius(kero.k1_diopters)
        r_mean = (kero.r1 + kero.r2) / 2.0

        if fitting_rule == "flat_k_plus_offset":
            return round(r_flat + 0.10, 2)
        elif fitting_rule == "mean_k":
            return round(r_mean, 2)
        elif fitting_rule == "ortho_k_flat_k":
            return round(r_flat + 0.50, 2)
        else:
            return round(r_flat + 0.10, 2)

    @staticmethod
    def k1_to_radius(k_diopters: float, index: float = 1.3375) -> float:
        """Convert diopters to radius of curvature (mm)."""
        return (index - 1.0) / k_diopters * 1000.0