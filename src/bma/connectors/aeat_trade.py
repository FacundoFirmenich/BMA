"""Bounded, in-memory reader for AEAT maximum-disaggregation trade archives.

The connector never persists the source ZIP. It validates the fixed-width
226-byte record contract, filters chapter 72 (iron and steel), and emits
monthly aggregates at flow x CN8 x partner-country resolution.
"""

from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Iterable

RECORD_LENGTH = 226
MAX_COMPRESSED_BYTES = 30_000_000
MAX_UNCOMPRESSED_BYTES = 250_000_000
MONTH_CODES = {
    1: ("enero", "en"),
    2: ("febrero", "fb"),
    3: ("marzo", "mz"),
    4: ("abril", "ab"),
    5: ("mayo", "my"),
    6: ("junio", "jn"),
    7: ("julio", "jl"),
    8: ("agosto", "ag"),
    9: ("septiembre", "sp"),
    10: ("octubre", "oc"),
    11: ("noviembre", "nv"),
    12: ("diciembre", "dc"),
}
BASE_URL = (
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/Aduanas/"
    "Comercio_exterior/maxima_desag_mens"
)


class AeatContractError(RuntimeError):
    """Raised when transport or record evidence violates the frozen contract."""


def archive_url(year: int, month: int) -> str:
    month_name, month_code = MONTH_CODES[month]
    return f"{BASE_URL}/{year}/{month_name}/cg{year % 100:02d}{month_code}74.zip"


def _integer(raw: bytes, label: str) -> int:
    if not raw or any(byte < 48 or byte > 57 for byte in raw):
        raise AeatContractError(f"non-numeric {label}: {raw!r}")
    return int(raw)


def parse_record(raw: bytes, *, expected_year: int, expected_month: int) -> dict[str, Any]:
    if len(raw) != RECORD_LENGTH:
        raise AeatContractError(f"record length {len(raw)} != {RECORD_LENGTH}")
    flow = raw[0:1].decode("ascii")
    if flow not in {"I", "E"}:
        raise AeatContractError(f"unknown flow {flow!r}")
    observed_year = 2000 + _integer(raw[1:3], "year")
    observed_month = _integer(raw[3:5], "month")
    if (observed_year, observed_month) != (expected_year, expected_month):
        raise AeatContractError(
            f"period mismatch {(observed_year, observed_month)} != {(expected_year, expected_month)}"
        )
    position12 = raw[25:37].decode("ascii").strip()
    if len(position12) < 8 or not position12[:8].isdigit():
        raise AeatContractError(f"invalid statistical position {position12!r}")
    return {
        "flow": flow,
        "cn8": position12[:8],
        "position12": position12,
        "customs_province": raw[5:7].decode("ascii"),
        "admission_date": raw[19:25].decode("ascii"),
        "declaration_type": raw[37:38].decode("ascii"),
        "additional_codes": raw[38:46].decode("ascii").strip(),
        "partner_country": raw[66:69].decode("ascii").strip(),
        "dispatch_country": raw[69:72].decode("ascii").strip(),
        "origin_destination_province": raw[75:77].decode("ascii"),
        "requested_customs_regime": raw[82:84].decode("ascii"),
        "preceding_customs_regime": raw[84:86].decode("ascii"),
        "weight_kg": _integer(raw[89:104], "weight") / 1000.0,
        "supplementary_units": _integer(raw[104:119], "units") / 1000.0,
        "statistical_value_eur": _integer(raw[119:131], "statistical value") / 100.0,
        "invoice_value_eur": _integer(raw[131:143], "invoice value") / 100.0,
        "container": raw[158:159].decode("ascii"),
        "transport_regime": raw[159:164].decode("ascii"),
        "border_transport_mode": raw[164:165].decode("ascii"),
        "internal_transport_mode": raw[165:166].decode("ascii"),
        "exchange_zone": raw[170:171].decode("ascii"),
        "transaction_nature": raw[172:174].decode("ascii"),
        "delivery_conditions": raw[174:177].decode("ascii"),
        "fiscal_province": raw[224:226].decode("ascii"),
    }


@dataclass
class _Aggregate:
    flow: str
    cn8: str
    partner_country: str
    weight_kg: float = 0.0
    supplementary_units: float = 0.0
    statistical_value_eur: float = 0.0
    invoice_value_eur: float = 0.0
    line_count: int = 0
    position12: set[str] = field(default_factory=set)
    customs_provinces: set[str] = field(default_factory=set)
    origin_destination_provinces: set[str] = field(default_factory=set)
    declaration_types: set[str] = field(default_factory=set)
    requested_customs_regimes: set[str] = field(default_factory=set)
    border_transport_modes: set[str] = field(default_factory=set)
    transaction_natures: set[str] = field(default_factory=set)
    delivery_conditions: set[str] = field(default_factory=set)
    dispatch_countries: set[str] = field(default_factory=set)

    def add(self, row: dict[str, Any]) -> None:
        self.weight_kg += row["weight_kg"]
        self.supplementary_units += row["supplementary_units"]
        self.statistical_value_eur += row["statistical_value_eur"]
        self.invoice_value_eur += row["invoice_value_eur"]
        self.line_count += 1
        for field_name, target in (
            ("position12", self.position12),
            ("customs_province", self.customs_provinces),
            ("origin_destination_province", self.origin_destination_provinces),
            ("declaration_type", self.declaration_types),
            ("requested_customs_regime", self.requested_customs_regimes),
            ("border_transport_mode", self.border_transport_modes),
            ("transaction_nature", self.transaction_natures),
            ("delivery_conditions", self.delivery_conditions),
            ("dispatch_country", self.dispatch_countries),
        ):
            value = row[field_name]
            if value:
                target.add(value)

    def serializable(self) -> dict[str, Any]:
        cell_id = f"{self.flow}|{self.cn8}|{self.partner_country or 'UNK'}.ґч›h‘йм¶»§q«^t“РРSХQWСTРФ’TU‘WУУ“H‚€™]\›€™\Э[‚‚™Y€ШЫЫќ[ќ[Э\ЧЬЭ[[X\ћJ™XЫЬ™О€\ЭЩXЭЬЭ‹[ћWWJHO€XЭЬЭ‹[ћWN‚€™\Э[€XЭЬЭ‹[ћWHHИ›€Ћ€[Љ™XЫЬ™К_B€›Ь€[YH[€
›XH‹
ђУУ•S•SХTЧСVT•КN‚€™\Э[Ы[YWHHИ›YX[—ШXњЫЫ]WЫЩЧЩ\њ›Ь€Ћ€ЫYX[Љ™XЫЬ™Л€ћЫ[Y_WШXњЫЫ]WЫЩЧЩ\њ›Ь€Љ_B€›Ь€ЫЫ\\]Ь€[€УУ•S•SХTЧСVT•О‚€™\Э[Щ€›XWЫZ[ќ\ЧЮШЫЫ\\]ЬџWЩ\њ›Ь€—HHЫYX[Љ™XЫЬ™Л€›XWЫZ[ќ\ЧЮШЫЫ\\]ЬџWЩ\њ›Ь€ЉB€™\Э[Щ€›ЫЭЭ\ЭњЧЮШЫЫ\\]ЬџH—HHШЫ\Э\—Ш›ЫЭЭ\
™XЫЬ™Л€›XWЫZ[ќ\ЧЮШЫЫ\\]ЬџWЩ\њ›Ь€ЉB€Y€[Љ™XЫЬ™КHУУ•S•SХTЧУRS—УЋ‚€™\Э[И™Ш]H—HH““ХСTХSPP“WТS”ХQ‘’PТQS•ФХTФ•‚€[Y€[
™\Э[Щ€›XWЫZ[ќ\ЧЮЫ[Y_WЩ\њ›Ь€—H›Ь€[YH[€
њ\њЪ\Э[ЩH‹Щ[ШЩ[ќ\€ЉJN‚€™\Э[И™Ш]H—HH‘ђU“ХTђP“WСTРФ’TU‘WУУ“H‚€[Y€[ћJ™\Э[Щ€›XWЫZ[ќ\ЧЮЫ[Y_WЩ\њ›Ь€—H€›Ь€[YH[€
њ\њЪ\Э[ЩH‹Щ[ШЩ[ќ\€ЉJN‚€™\Э[И™Ш]H—HH“RVQУФ—РQ‘T”СWСTРФ’TU‘WУУ“H‚€[ЩN‚€™\Э[И™Ш]H—HH“РРSХQWСTРФ’TU‘WУУ“H‚€™]\›€™\Э[‚‚™Y€ЬЭ]YћJ™XЫЬ™О€\ЭЩXЭЬЭ‹[ћWWKЭ[[X\љ^™\Ћ€Ш[X›VЦЫ\ЭЩXЭЬЭ‹[ћWWWKXЭЬЭ‹[ћWWJHO€XЭЬЭ‹[ћWN‚€ћWЩ›ЭО€XЭЬЭ‹\ЭЩXЭЬЭ‹[ћWWWHHY][XЭ
\Э
B€ћWШЫЌ€XЭЬЭ‹\ЭЩXЭЬЭ‹[ћWWWHHY][XЭ
\Э
B€›Ь€›ЭИ[€™XЫЬ™О‚€ћWЩ›ЭЦЬ›ЭЦИ™›ЭИ—WK\[™
›ЭКB€ћWШЫЌЬ›ЭЦИЫЌ—WK\[™
›ЭКB€™]\›€В€ћWЩ›ЭИЋ€ЪЩ^N€Э[[X\љ^™\ЉћWЩ›ЭЦЪЩ^WJH›Ь€Щ^H[€ЫЬќY
ћWЩ›ЭК_K€ћWШЫЌЋ€ЪЩ^N€Э[[X\љ^™\ЉћWШЫЌЪЩ^WJH›Ь€Щ^H[€ЫЬќY
ћWШЫЌ
HY€[ЉћWШЫЌЪЩ^WJHЏHЊK€B‚‚™Y€ќ[ЉЭ]]€]
HO€XЭЬЭ‹[ћWN‚€Y€Э]]™^\ЭК
N‚€Z\ЩHШ]QZ[\™J€љ[[]]X›HЭ]][™XYH^\ЭО€ЫЭ]]HЉB€Э]]›ZЩ\Љ\™[ќПUќYJB€Щ\]Y[ЩN€\ЭЩXЭЬЭ‹[ћWWHHЧB‚€Z[љ[™О€\ЭЩXЭЬЭ‹[ћWWHHЧB€›Ь€[Ыќ[€ђRS—УSУ•О‚€ШЭ[Y[ќH™]ЪЫ[Ыќ
QPT‹[Ыќ
B€Z[љ[™Л\[™
ШЭ[Y[ќ
B€Щ\]Y[ЩK\[™
€В€њЩ\]Y[ЩHЋ€[ЉЩ\]Y[ЩJH
ИK€™]™[ќЋ€•ђRS’S‘ЧУSУ•С‘UТQТS—УQSSФ–WРS‘РQСФ‘QРUQ‹€њ\љ[ЩЋ€ШЭ[Y[ќИњ\љ[Щ—K€\Ъ]™WЬЪLЌM€Ћ€ШЭ[Y[ќИњЫЭ\ЩH—VИ\Ъ]™WЬЪLЌM€—K€њ]ЧШ\Ъ]™WЬ\њЪ\ЭYЋ€[ЩK€B€
B€Z[љ[™ЧЪ\ЪHЭЬљ]WЩЮљ\ЪњЫЫ—Ы™]КЭ]]И•ђRS’S‘ЧРQСФ‘QРUTЛљњЫЫ‹™Ю€‹Z[љ[™КB€X\ИHШЩ[ЫX\КZ[љ[™КB€Y]Y]HHЫY]Y]JX\КB€\ќXЪ\][Ы—Щљ]Hљ]Ь\ќXЪ\][Ы—ЭЩZYЪКX\КB€]X[ќ]WЩљ]Hљ]ШЫЫќ[ќ[Э\ЧЭЩZYЪКX\ЛќЩZYЪЪЩИЉB€[љ]Э[YWЩљ]Hљ]ШЫЫќ[ќ[Э\ЧЭЩZYЪКX\ЛњЭ]\ЭXШ[Э[љ]Э[YWЩ]\—Ь\—ЪЩИЉB€\ќXЪ\][Ы—ШЫЫќ^HЬ\ќXЪ\][Ы—ШЫЫќ^
X\ЛY]Y]JCB€]X[ќ]WШЫЫќ^HШЫЫќ[ќ[Э\ЧШЫЫќ^
X\ЛY]Y]KќЩZYЪЪЩИЉCB€[љ]Э[YWШЫЫќ^HШЫЫќ[ќ[Э\ЧШЫЫќ^
X\ЛY]Y]KњЭ]\ЭXШ[Э[љ]Э[YWЩ]\—Ь\—ЪЩИЉCB‚€\ќXЪ\][Ы—Щњ™Y^™N€XЭЬЭ‹[ћWHHЯB€]X[ќ]WЩњ™Y^™N€XЭЬЭ‹[ћWHHЯB€[љ]Э[YWЩњ™Y^™N€XЭЬЭ‹[ћWHHЯB€›Ь€Щ[ЪY[€ЫЬќY
Y]Y]JN‚€^\ќИHЬ\ќXЪ\][Ы—Ь™YXЭ[ЫњК\ќXЪ\][Ы—ШЫЫќ^Y]Y]KЩ[ЪY
CB€\ќXЪ\][Ы—Щњ™Y^™VШЩ[ЪYHHВ€
Љ›Y]Y]VШЩ[ЪYK€™^\ќИЋ€^\ќЛ€›XWЬ›ШXљ[]HЋ€Э[J\ќXЪ\][Ы—Щљ]ИќЩZYЪИ—VЫ[YWH
€^\ќЦЫ[YWH›Ь€[YH[€T•PТTUSУ—СVT•КK€B€›Ь€ЫЫќ^љ]\™Щ][€
B€
]X[ќ]WШЫЫќ^]X[ќ]WЩљ]]X[ќ]WЩњ™Y^™JKB€
[љ]Э[YWШЫЫќ^[љ]Э[YWЩљ][љ]Э[YWЩњ™Y^™JKB€
N‚€^\ќЧШЫЫќ[ќ[Э\ИHШЫЫќ[ќ[Э\ЧЬ™YXЭ[ЫњКЫЫќ^Y]Y]KЩ[ЪY
CB€Y€^\ќЧШЫЫќ[ќ[Э\И\И›Ы™N‚€ЫЫќ[ќYB€›XWЫЩИHЭ[Jљ]ИќЩZYЪИ—VЫ[YWH
€^\ќЧШЫЫќ[ќ[Э\ЦЫ[YWH›Ь€[YH[€УУ•S•SХTЧСVT•КB€\™Щ]ШЩ[ЪYHHВ€
Љ›Y]Y]VШЩ[ЪYK€™^\ќЧЫЩЧЬШШ[HЋ€^\ќЧШЫЫќ[ќ[Э\Л€›XWЫЩЧЬ™YXЭ[Ы€Ћ€›XWЫЩЛ€›XWЬЪ[ќЋ€X]™^
›XWЫЩКK€B‚€њ™Y^™HHВ€њШЪ[XWЭ™\њЪ[Ы€Ћ€РТSPK€њЭ]\ИЋ€‘”“Ц‘S—Р‘Q“Ф‘WУ“Х‘SP‘T—РTђТU‘WУФS‘Q‹B€ќZ[љ[™ЧЬ\љ[ЩЋ€ИЊЊЌLH‹ЊЊЌLL—KB€ќ\™Щ]Ь\љ[ЩЋ€ЊЊЌLLH‹B€њЫЭ\ЩWЩљ[[]HЋ€ђQPUМЊЌСUФЧСQ’S’UU“ФИ‹€ќZ[љ[™ЧШYЩЬ™YШ]\ЧЬЪLЌM€Ћ€Z[љ[™ЧЪ\Ъ€ќ[љ]™\њЩWШЩ[ИЋ€[ЉY]Y]JK€њ\ќXЪ\][Ы—Щљ]Ћ€\ќXЪ\][Ы—Щљ]€њ]X[ќ]WЩљ]Ћ€]X[ќ]WЩљ]€њЭ]\ЭXШ[Э[љ]Э[YWЩљ]Ћ€[љ]Э[YWЩљ]€њ™YXЭ[ЫњИЋ€В€њ\ќXЪ\][Ы€Ћ€\ќXЪ\][Ы—Щњ™Y^™K€ќЩZYЪЪЩЧШЫЫ™][Ы[ЫЫ—Ь™\Щ[ЩHЋ€]X[ќ]WЩњ™Y^™K€њЭ]\ЭXШ[Э[љ]Э[YWЩ]\—Ь\—ЪЩЧШЫЫ™][Ы[ЫЫ—ЬЬЪ]]™WЭЩZYЪШ[™Э[YHЋ€[љ]Э[YWЩњ™Y^™K€K€њЩ[X[ќXЬИЋ€В€њЭ]\ЭXШ[Э[љ]Э[YHЋ€YЩЬ™YШ]HЭ]\ЭXШ[[YH]љYYћH™]X\ЬОИ›Э[€]XЭ[Ы‹ЬЭЬ€љ\›HљXЩH‹€њЭ\[Y[ќ\ћWЭ[љ]ИЋ€њ™]Z[™Y[€YЩЬ™YШ]\Иќ]›Э[Щ[Y™XШ]\ЩH[љ]И\™HЫЫ[[Щ]K\ЬXЪYљXИ‹€K€B€њ™Y^™WЪ\ЪHЭЬљ]WЩЮљ\ЪњЫЫ—Ы™]КЭ]]И•T‘СUФ‘QPХSУ—С”‘QV‘KљњЫЫ‹™Ю€‹њ™Y^™JB€Щ\]Y[ЩK\[™
€В€њЩ\]Y[ЩHЋ€[ЉЩ\]Y[ЩJH
ИK€™]™[ќЋ€•T‘СUФ‘QPХSУ—С”‘QV‘WХФ’US€‹€ќ\™Щ]Ь\љ[ЩЋ€ЊЊЌLLH‹B€њЪLЌM€Ћ€њ™Y^™WЪ\Ъ€B€
B‚€\™Щ]H™]ЪЫ[Ыќ
QPT‹T‘СUУSУ•
B€\™Щ]Ъ\ЪHЭЬљ]WЩЮљ\ЪњЫЫ—Ы™]КЭ]]И•T‘СUРQСФ‘QРUTЛљњЫЫ‹™Ю€‹\™Щ]
B€Щ\]Y[ЩK\[™
€В€њЩ\]Y[ЩHЋ€[ЉЩ\]Y[ЩJH
ИK€™]™[ќЋ€•T‘СUРTђТU‘WУФS‘QТS—УQSSФ–WРQ•T—С”‘QV‘H‹€ќ\™Щ]Ь\љ[ЩЋ€\™Щ]Ињ\љ[Щ—K€\Ъ]™WЬЪLЌM€Ћ€\™Щ]ИњЫЭ\ЩH—VИ\Ъ]™WЬЪLЌM€—K€YЩЬ™YШ]WЬЪLЌM€Ћ€\™Щ]Ъ\Ъ€Yќ\—Щњ™Y^™WЬЪLЌM€Ћ€њ™Y^™WЪ\Ъ€њ]ЧШ\Ъ]™WЬ\њЪ\ЭYЋ€[ЩK€B€
B€\™Щ]ЫX\HЬ›ЭЦИЩ[ЪY—N€›ЭИ›Ь€›ЭИ[€\™Щ]ИЩ[И—_B‚€\ќXЪ\][Ы—ЬШЫЬ™\О€\ЭЩXЭЬЭ‹[ћWWHHЧB€›Ь€Щ[ЪY™YXЭ[Ы€[€\ќXЪ\][Ы—Щњ™Y^™Kљ][\К
N‚€XЭX[H[ќ
Щ[ЪY[€\™Щ]ЫX\
B€›ЭИHКЉ›Y]Y]VШЩ[ЪYKЩ[ЪYЋ€Щ[ЪYXЭX[Ћ€XЭX[B€›ШXљ[]Y\ИHИ›XHЋ€™YXЭ[Ы–И›XWЬ›ШXљ[]H—K
Љњ™YXЭ[Ы–И™^\ќИ—_B€›Ь€[YK›ШXљ[]H[€›ШXљ[]Y\Лљ][\К
N‚€›ЭЦЩ€ћЫ[Y_WЬ›ШXљ[]H—HH›ШXљ[]B€›ЭЦЩ€ћЫ[Y_WШњљY\€—HHШњљY\ЉXЭX[›ШXљ[]JB€›ЭЦЩ€ћЫ[Y_WЫЩЧЫЬЬИ—HHЫЩЧЫЬЬКXЭX[›ШXљ[]JB€›Ь€ЫЫ\\]Ь€[€T•PТTUSУ—СVT•О‚€›ЭЦЩ€›XWЫZ[ќ\ЧЮШЫЫ\\]ЬџWШњљY\€—HH›ЭЦИ›XWШњљY\€—HH›ЭЦЩ€ћШЫЫ\\]ЬџWШњљY\€—B€\ќXЪ\][Ы—ЬШЫЬ™\Л\[™
›ЭКB‚€Y€ШЫЬ™WШЫЫќ[ќ[Э\Књ›Ю™[Ћ€XЭЬЭ‹[ћWKY]љXО€ЭЉHO€\ЭЩXЭЬЭ‹[ћWWN‚€ШЫЬ™\О€\ЭЩXЭЬЭ‹[ћWWHHЧB€›Ь€Щ[ЪY[€ЫЬќY
Щ]
њ›Ю™[ЉH	€Щ]
\™Щ]ЫX\
JN‚€XЭX[Э[YHHЬЬЪ]]™WЭ[YJ\™Щ]ЫX\ШЩ[ЪYKY]љXКB€Y€XЭX[Э[YH\И›Ы™N‚€ЫЫќ[ќYB€XЭX[ЫЩИHX]›ЩКXЭX[Э[YJB€™YXЭ[Ы€Hњ›Ю™[–ШЩ[ЪYB€›ЭИHКЉ›Y]Y]VШЩ[ЪYKЩ[ЪYЋ€Щ[ЪYXЭX[Ћ€XЭX[Э[Y_B€[Y\ИHИ›XHЋ€™YXЭ[Ы–И›XWЫЩЧЬ™YXЭ[Ы€—K
Љњ™YXЭ[Ы–И™^\ќЧЫЩЧЬШШ[H—_B€›Ь€[YK™YXЭYЫЩИ[€[Y\Лљ][\К
N‚€›ЭЦЩ€ћЫ[Y_WЬ™YXЭ[Ы€—HHX]™^
™YXЭYЫЩКB€›ЭЦЩ€ћЫ[Y_WШXњЫЫ]WЫЩЧЩ\њ›Ь€—HHXњКXЭX[ЫЩИH™YXЭYЫЩКB€›Ь€ЫЫ\\]Ь€[€УУ•S•SХTЧСVT•О‚€›ЭЦЩ€›XWЫZ[ќ\ЧЮШЫЫ\\]ЬџWЩ\њ›Ь€—HH
€›ЭЦИ›XWШXњЫЫ]WЫЩЧЩ\њ›Ь€—HH›ЭЦЩ€ћШЫЫ\\]ЬџWШXњЫЫ]WЫЩЧЩ\њ›Ь€—B€
B€ШЫЬ™\Л\[™
›ЭКB€™]\›€ШЫЬ™\В‚€]X[ќ]WЬШЫЬ™\ИHШЫЬ™WШЫЫќ[ќ[Э\К]X[ќ]WЩњ™Y^™KќЩZYЪЪЩИЉB€[љ]Э[YWЬШЫЬ™\ИHШЫЬ™WШЫЫќ[ќ[Э\К[љ]Э[YWЩњ™Y^™KњЭ]\ЭXШ[Э[љ]Э[YWЩ]\—Ь\—ЪЩИЉB€™]ЧШЩ[ИHЫЬќY
Щ]
\™Щ]ЫX\
HHЩ]
Y]Y]JJB€\ќXЪ\][Ы—ЬЭ[[X\ћHHЬ\ќXЪ\][Ы—ЬЭ[[X\ћJ\ќXЪ\][Ы—ЬШЫЬ™\КB€]X[ќ]WЬЭ[[X\ћHHШЫЫќ[ќ[Э\ЧЬЭ[[X\ћJ]X[ќ]WЬШЫЬ™\КB€[љ]Э[YWЬЭ[[X\ћHHШЫЫќ[ќ[Э\ЧЬЭ[[X\ћJ[љ]Э[YWЬШЫЬ™\КB‚€Э[[X\ћHHВ€њШЪ[XWЭ™\њЪ[Ы€Ћ€РТSPK€њЭ]\ИЋ€‘VPХUQФ‘U“ФФPХU‘WТS‘TХ’PSТУХU‹€ќZ[љ[™ЧЬ\љ[ЩЋ€ИЊЊЌLH‹ЊЊЌLL—KB€ќ\™Щ]Ь\љ[ЩЋ€ЊЊЌLLH‹B€њЫЭ\ЩWЩљ[[]HЋ€ђQPUМЊЌСUФЧСQ’S’UU“ФИ‹€њШЫЬHЋ€[Ъ\\‹MМ€\›Ы‹X[™\ЭY[X^[][KY]Z[™XЫЬ™ИYЩЬ™YШ]YћH›ЭИУЋ\ќ™\€‹€ќZ[љ[™ИЋ€В€›[ЫќИЋ€[ЉZ[љ[™КK€њ]ЧЫ[™\ИЋ€Э[J][VИњЫЭ\ЩH—VИќЭ[Ы[™\И—H›Ь€][H[€Z[љ[™КK€Ъ\\ЌМ—Ы[™\ИЋ€Э[J][VИњЫЭ\ЩH—VИЪ\\ЌМ—Ы[™\И—H›Ь€][H[€Z[љ[™КK€›[ЫќWШYЩЬ™YШ]WЬ›ЭЬИЋ€Э[J[Љ][VИЩ[И—JH›Ь€][H[€Z[љ[™КK€ќ[љ]™\њЩWШЩ[ИЋ€[ЉY]Y]JK€\Ъ]™WЬЪLЌM€Ћ€Ъ][VИњЫЭ\ЩH—VИ\Ъ]™WЬЪLЌM€—H›Ь€][H[€Z[љ[™ЧK€K€ќ\™Щ]Ћ€В€њ]ЧЫ[™\ИЋ€\™Щ]ИњЫЭ\ЩH—VИќЭ[Ы[™\И—K€Ъ\\ЌМ—Ы[™\ИЋ€\™Щ]ИњЫЭ\ЩH—VИЪ\\ЌМ—Ы[™\И—K€YЩЬ™YШ]WЬ›ЭЬИЋ€[Љ\™Щ]ИЩ[И—JK€љЫ›ЭЫ—ШЩ[ИЋ€[ЉЩ]
\™Щ]ЫX\
H	€Щ]
Y]Y]JJK€›™]ЧЫЭ]ЫЩ—ЭZ[љ[™ЧЭ[љ]™\њЩHЋ€[Љ™]ЧШЩ[КK€\Ъ]™WЬЪLЌM€Ћ€\™Щ]ИњЫЭ\ЩH—VИ\Ъ]™WЬЪLЌM€—K€K€њ\ќXЪ\][Ы€Ћ€\ќXЪ\][Ы—ЬЭ[[X\ћK€ќЩZYЪЪЩЧШЫЫ™][Ы[ЫЫ—Ь™\Щ[ЩHЋ€]X[ќ]WЬЭ[[X\ћK€њЭ]\ЭXШ[Э[љ]Э[YWЩ]\—Ь\—ЪЩИЋ€[љ]Э[YWЬЭ[[X\ћK€њЭX™Ь›Э\ИЋ€В€њ\ќXЪ\][Ы€Ћ€ЬЭ]YћJ\ќXЪ\][Ы—ЬШЫЬ™\ЛЬ\ќXЪ\][Ы—ЬЭ[[X\ћJK€ќЩZYЪЪЩИЋ€ЬЭ]YћJ]X[ќ]WЬШЫЬ™\ЛШЫЫќ[ќ[Э\ЧЬЭ[[X\ћJK€њЭ]\ЭXШ[Э[љ]Э[YHЋ€ЬЭ]YћJ[љ]Э[YWЬШЫЬ™\ЛШЫЫќ[ќ[Э\ЧЬЭ[[X\ћJK€K€Ш]\Ш[ЫЬ™\љ[™ИЋ€В€њЭ]\ИЋ€”TФЧС”‘QV‘WФ‘PСQTЧХT‘СUУФS€‹€ќ\™Щ]Ь™YXЭ[Ы—Щњ™Y^™WЬЪLЌM€Ћ€њ™Y^™WЪ\Ъ€™]™[ќИЋ€Щ\]Y[ЩK€K€њ]ЧЬЭЬYЩHЋ€В€њЫЭ\ЩWЮљ\Ь\њЪ\ЭYЫШШ[HЋ€[ЩK€њЫЭ\ЩWЮљ\Ь\њЪ\ЭYЪ[—Ш\ќYXЭЋ€[ЩK€›Ы™WШ\Ъ]™WЪ[—ЫY[[ЬћWШ]ШWЭ[YHЋ€ќYK€K€ЫZ[WШ›Э[™\ћHЋ€В€њ›ЬЬXЭ]™WЭ[Y][Ы€Ћ€[ЩK€њЪ[™ЫWЬ™]›ЬЬXЭ]™WЪЫЭ]Ћ€ќYK€љ[™\ЭљX[ЩЫXZ[—Щ^[њЪ[Ы€Ћ€ќYK€ќ[њШXЭ[Ы—ЬљXЩWЭ[Y][Ы€Ћ€[ЩK€™ЫШ[ЬЭ\\љ[Ьљ]HЋ€[ЩK€њ›Ы[Э[Ы€Ћ€““ЧФ“УSХSУ—ФТS‘УWФ‘U“ФФPХU‘WУSУ•‹€K€B€ЭЬљ]WЩЮљ\ЪњЫЫ—Ы™]КЭ]]И”T•PТTUSУ—ФРУФ‘TЛљњЫЫ‹™Ю€‹\ќXЪ\][Ы—ЬШЫЬ™\КB€ЭЬљ]WЩЮљ\ЪњЫЫ—Ы™]КЭ]]И•СRQТФРУФ‘TЛљњЫЫ‹™Ю€‹]X[ќ]WЬШЫЬ™\КB€ЭЬљ]WЩЮљ\ЪњЫЫ—Ы™]КЭ]]И•S’UХђSQWФРУФ‘TЛљњЫЫ‹™Ю€‹[љ]Э[YWЬШЫЬ™\КB€Ьљ]WЪњЫЫ—Ы™]КЭ]]ИђРUTРSФСTUQSђСWУQСT‹љњЫЫ€‹ИњШЪ[XWЭ™\њЪ[Ы€Ћ€РТSPK™]™[ќИЋ€Щ\]Y[Щ_JB€Ьљ]WЪњЫЫ—Ы™]КЭ]]И”‘TХSФХSSPT–KљњЫЫ€‹Э[[X\ћJB€Ьљ]WЪњЫЫ—Ы™]КЭ]]И“‘UЧХT‘СUРСSЛљњЫЫ€‹ИњШЪ[XWЭ™\њЪ[Ы€Ћ€РТSPKЩ[ЪYИЋ€™]ЧШЩ[ЯJB€ЛX[љY™\ЭЪ\ЪHЬљ]WЫX[љY™\Э
Э]]
B€™]\›€КЉњЭ[[X\ћK›X[љY™\ЭЬЪLЌM€Ћ€X[љY™\ЭЪ\Ъ›Э]]Ћ€ЭЉЭ]]
_B‚‚™Y€XZ[Љ
HO€[ќ‚€\њЩ\€H\™Ь\њЩKђ\™Э[Y[ќ\њЩ\Љ\ШЬљ\[ЫЏWЧЩШЧЧКB€\њЩ\‹YШ\™Э[Y[ќ
‹K[Э]]‹\OT]™\]Z\™YUќYJB€\™ЬИH\њЩ\‹њ\њЩWШ\™ЬК
B€™\Э[Hќ[Љ\™ЬЛ›Э]]
B€љ[ќ
ђ“PWФ‘TХSФХSSPT–OH€
ИњЫЫ‹™[\К™\Э[[њЭ\™WШ\ШЪZOQ[ЩKЫЬќЪЩ^\ПUќYJJB€™]\›€‚‚љY€ЧЫ[YWЧИOH—ЧЫXZ[—ЧИЋ‚€Z\ЩHЮ\Э[Q^]
XZ[Љ
JB