"""Frozen, abstention-preserving taxonomy for Mercabarna Flor v0.5.1.

The mapping is defined only over product labels observed in the authorized
2026-07-01..20 training window. Unknown or semantically ambiguous labels are
never guessed: they remain UNRESOLVED.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

FLOR_SUFFIX = " FLORES I PLANTAS"
GREEN_SUFFIX = " ARBOLES, VERDES Y COMPLEMENTOS"
CATEGORIES = ("FLOR_CORTADA", "PLANTA_VIVA", "ARBOLES_Y_VERDES", "COMPLEMENTOS", "UNRESOLVED")

FLOR_CORTADA = frozenset(
    {
        "ACHILLEA",
        "ALSTROEMERIA",
        "ANTHURIUM (FL)",
        "ANTIRRHINUM",
        "ASTER",
        "CELOSIA (FL)",
        "CHYYSANTHEMUM (FL)",
        "CLAVEL",
        "CLAVEL COLOMBIANO",
        "CLAVEL MINI",
        "CLAVEL POETA",
        "DELPHINIUM",
        "EUSTOMA (LISIANTUM)",
        "FLOR DE CERA",
        "FREESIA",
        "GERBERA (FL)",
        "GERMINI",
        "GIRASOL",
        "GLADIOLO",
        "HYACINTHUS (FL)",
        "IRIS",
        "LIATRIS",
        "LILIUM",
        "LIMONIUM (STATICE)",
        "MATTHIOLA (VIOLE)",
        "ORNITHOGALUM",
        "OTRAS FLORES DE TEMPORADA",
        "OTRAS FLORES DE TODO EL AÑO",
        "PAENOLIA",
        "PANICULATA",
        "RAMOS CONFECCIONADOS (BOUQUETS)",
        "ROSA COLOMBIA",
        "ROSA HOLANDA OTROS COLORES",
        "ROSA MULTIFLORA",
        "SOLIDASTER",
        "ZANTEDESCHIA (FL CALA)",
    }
)

PLANTA_VIVA = frozenset(
    {
        "ANTHURIUM (PL)",
        "CACTUS",
        "CALATHEA",
        "CHAMAEDOREA",
        "FICUS (OTRAS VARIEDADES)",
        "GUZMANIA",
        "HEDERA",
        "HIBISCUS",
        "HOWEIA (KENTIA)",
        "KALANCHOE",
        "MARANTA",
        "OTRAS AROMÁTICAS",
        "OTRAS PLANTAS DE TEMPORADA",
        "OTRAS PLANTAS DE TODO EL AÑO",
        "PELERGONIUM (GERANIO)",
        "PETUNIA",
        "PHALAENOPSIS (PL)",
        "PHILODENDRON",
        "ROSAL",
        "SANSEVIERIA",
        "SPATHIPHYLLUM",
        "VINCA",
    }
)

ARBOLES_Y_VERDES = frozenset(
    {
        "ASPARRAGUS PLUMOSOS",
        "BOJ",
        "EUCALIPTO",
        "FORNIO",
        "GALAX",
        "GINESTA VERDE",
        "HELECHO",
        "HELECHO DE ARBOL (TREE-FERN)",
        "HELECHO DE CUERO (LEATHRLEAF)",
        "HELECHO DE OSO (BEARGRASS)",
        "HEURA",
        "HOJA  DE CORDYLINE",
        "HOJA DE PHILODRENDON",
        "HOJA DE STRELITZIA",
        "LAUREL",
        "MADROÑO",
        "MIRIOCLADUS",
        "MUSGO (CAJAS)",
        "OTROS ARBOLES",
        "OTROS ARBUSTOS",
        "OTROS VERDES",
        "VIBURNUM",
        "ÁRBOLES FRUTALES",
    }
)

COMPLEMENTOS = frozenset(
    {
        "ARMADURAS",
        "CELOFANT (ROLLOS)",
        "CINTAS",
        "ENVOLTORIOS VARIOS",
        "ESPUMA ABSORBENTE (CAIXA)",
        "ESPUMA SECA (CAJA)",
        "FLOR SECA",
        "HERRAMIENTAS DIVERSAS",
        "OTROS COMPLEMENTOS",
        "RECIPIENTES CERÁMICA",
        "RECIPIENTES METÁLICOS",
        "RECIPIENTES PLASTICO",
        "RECIPIENTES VIDRIO",
    }
)

AMBIGUOUS = frozenset({"AGAPHANTUS", "HELICONIA", "HORTENSIAS", "STRELITZIA"})


@dataclass(frozen=True)
class TaxonomyDecision:
    product: str
    stem: str
    original_section: str
    subfamily: str
    basis: str

    def serializable(self) -> dict[str, str]:
        return asdict(self)


def split_product(product: str) -> tuple[str, str]:
    if product.endswith(FLOR_SUFFIX):
        return product[: -len(FLOR_SUFFIX)], "FLORES_I_PLANTAS"
    if product.endswith(GREEN_SUFFIX):
        return product[: -len(GREEN_SUFFIX)], "ARBOLES_VERDES_Y_COMPLEMENTOS"
    return product, "UNKNOWN_SECTION"


def classify_product(product: str) -> TaxonomyDecision:
    stem, section = split_product(product)
    if stem in FLOR_CORTADA:
        basis = "EXPLICIT_FL_MARKER" if "(FL" in stem else "FROZEN_COMMODITY_CLASS_CUT_FLOWER"
        category = "FLOR_CORTADA"
    elif stem in PLANTA_VIVA:
        basis = "EXPLICIT_PL_MARKER" if "(PL)" in stem else "FROZEN_COMMODITY_CLASS_LIVE_PLANT"
        category = "PLANTA_VIVA"
    elif stem in ARBOLES_Y_VERDES:
        basis = "FROZEN_ORIGINAL_SECTION_TREE_OR_GREEN"
        category = "ARBOLES_Y_VERDES"
    elif stem in COMPLEMENTOS:
        basis = "FROZEN_ORIGINAL_SECTION_NON_LIVE_COMPLEMENT"
        category = "COMPLEMENTOS"
    elif stem in AMBIGUOUS:
        basis = "AMBIGUOUS_LIVE_VS_CUT_OR_GREEN_ABSTAIN"
        category = "UNRESOLVED"
    else:
        basis = "NOT_IN_FROZEN_TRAINING_TAXONOMY"
        category = "UNRESOLVED"
    return TaxonomyDecision(product, stem, section, category, basis)
