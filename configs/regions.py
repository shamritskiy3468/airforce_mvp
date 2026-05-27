from engine.config import AreaConfig


# Practical macro-region for the simulator: Europe + CIS core.
# NOTE:
# The project still uses a rectangular area model, so this is an approximation.
# It covers Europe, the Caucasus, Belarus, the Baltics, European Russia,
# Kazakhstan, and Central Asia without stretching all the way to the Pacific.
EUROPE_CIS_AREA = AreaConfig(
    min_lat=34.0,
    max_lat=72.0,
    min_lon=-25.0,
    max_lon=90.0,
)
