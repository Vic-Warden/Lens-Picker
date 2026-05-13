# LensAdvisor — Contact Lens Fitting Assistant

Desktop application (Python/PyQt5) for orthoptists.  
Unified internal recommendation engine for CooperVision, Alcon, Bausch + Lomb, Johnson & Johnson, and FitBetter.

---

## Project structure

```
LensAdvisor/
|
+-- main.py                        <- Entry point — run the application here
|
+-- requirements.txt               <- Python dependencies
|
+-- controllers/                   <- Business logic (MVC — Controllers)
|   +-- __init__.py
|   +-- optics_engine.py           <- Optical computation: meridional vertex conversion
|   +-- matching_engine.py         <- Lens matching engine
|
+-- data/                          <- Data models (MVC — Models)
|   +-- __init__.py
|   +-- lens_database.py           <- Local contact lens database
|
+-- views/                         <- Graphical interface (MVC — View)
    +-- __init__.py
    +-- main_window.py             <- Main PyQt5 window
```

---

## Installation

### 1. Prerequisites
- Python 3.8 or higher
- pip

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
python main.py
```

---

## Usage

1. Enter the spectacle refraction (Sphere, Cylinder, Axis, Addition) for the right and left eye.
2. Enter keratometry data (R1 flat meridian, R2 steep meridian) in millimeters.
3. Adjust vertex distance (default 12 mm).
4. Apply optional filters (wear type: daily / monthly, brands).
5. Click "Calculate & Recommend".
6. Results display the best-matched lenses with compatibility score, exact order (Sph, Cyl, Axis, BC, Diameter, Addition), and clinical warnings.

---

## MVC architecture

| Layer      | File                             | Role                                                     |
|------------|----------------------------------|----------------------------------------------------------|
| View       | `views/main_window.py`           | PyQt5 interface — input and display only                 |
| Controller | `controllers/optics_engine.py`   | Optical formulas, vertex conversion, keratometry         |
| Controller | `controllers/matching_engine.py` | Filtering, scoring, and lens selection                   |
| Model      | `data/lens_database.py`          | Local contact lens database                              |

---

## Extending the database

To add a lens, open `data/lens_database.py` and add an entry to `LENS_DATABASE` following this schema:

```python
{
    "id": "BRAND_MODEL",
    "brand": "Brand name",
    "platform": "Manufacturer platform",
    "model": "Model name",
    "type": "daily",          # daily | monthly | biweekly | orthokeratology
    "material": "Material name",
    "dk_t": 120,              # Oxygen transmissibility
    "water_content": 45,      # % water content
    "base_curves": [8.6],     # Available BCs (mm)
    "diameters": [14.2],      # Available diameter(s) (mm)
    "sphere_range": (-10.00, +6.00),
    "cylinder_range": None,   # None if spherical, (min, max) if toric
    "cylinder_steps": None,
    "axis_steps": None,
    "sphere_steps": 0.25,
    "add_range": None,        # (min, max) if multifocal
    "notes": "Short description",
}
```

---

## Matching algorithm (summary)

1. Filtering: exclude lenses outside sphere, cylinder, and addition ranges.
2. BC selection: base curve closest to the recommended BC (flat_K + 0.10 mm).
3. Rounding: powers rounded to the model's manufacturing steps.
4. Composite score (0-100):
   - Sphere compatibility:         40 pts
   - Cylinder compatibility:       30 pts
   - BC compatibility:             20 pts
   - Multifocal / ortho-K bonus:   10 pts
   - Dk/t >= 140 bonus:            +3 pts
5. Clinical warnings generated automatically (deviated BC, uncorrected astigmatism, etc.)

---

## Clinical disclaimer

This software is a decision-support tool intended for qualified healthcare professionals.  
It does not replace clinical examination or the judgment of the orthoptist or ophthalmologist.  
All prescriptions must be validated by an authorised practitioner.