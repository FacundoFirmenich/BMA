from __future__ import annotations

from bma.taxonomy import CATEGORIES, classify_product


def test_explicit_fl_and_pl_are_separated() -> None:
    flower = classify_product("ANTHURIUM (FL) FLORES I PLANTAS")
    plant = classify_product("ANTHURIUM (PL) FLORES I PLANTAS")
    assert flower.subfamily == "FLOR_CORTADA"
    assert plant.subfamily == "PLANTA_VIVA"
    assert flower.basis == "EXPLICIT_FL_MARKER"
    assert plant.basis == "EXPLICIT_PL_MARKER"


def test_green_and_complement_are_separated() -> None:
    green = classify_product("EUCALIPTO ARBOLES, VERDES Y COMPLEMENTOS")
    complement = classify_product("RECIPIENTES VIDRIO ARBOLES, VERDES Y COMPLEMENTOS")
    assert green.subfamily == "ARBOLES_Y_VERDES"
    assert complement.subfamily == "COMPLEMENTOS"


def test_ambiguous_and_unknown_products_abstain() -> None:
    assert classify_product("STRELITZIA FLORES I PLANTAS").subfamily == "UNRESOLVED"
    unknown = classify_product("PRODUCTO NUEVO FLORES I PLANTAS")
    assert unknown.subfamily == "UNRESOLVED"
    assert unknown.basis == "NOT_IN_FROZEN_TRAINING_TAXONOMY"


def test_categories_include_explicit_abstention() -> None:
    assert CATEGORIES == (
        "FLOR_CORTADA",
        "PLANTA_VIVA",
        "ARBOLES_Y_VERDES",
        "COMPLEMENTOS",
        "UNRESOLVED",
    )
