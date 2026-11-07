"""
Numbers written as digits, said as words. A voice can be unsure what to do with "1995", "3%" or "2,5", and the learner never sees how a
number is said, so every speech engine is given the text with its digits written out in the language ("negentien honderd vijfennegentig",
"drie procent"), and the word panel shows the same words. `num2words` does the counting; this module decides what a digit run is.

A number that looks like a year (1000 to 2100, nothing attached) is said as a year; a number with a unit or a percent has the unit said in the
language (the small tables below; a unit not in them is left out and the number is said alone); an ordinal ("3e", "1er") is an ordinal.
"""

import re

from num2words import num2words

# Our language codes to num2words' where they differ.
LANG = {"nb": "no", "pt": "pt_BR", "pt-BR": "pt_BR", "pt-PT": "pt"}

# unit -> (singular, plural); one form when they are the same.
UNITS = {
    "nl": {"%": ("procent",), "€": ("euro",), "$": ("dollar",), "°": ("graad", "graden"), "°C": ("graad celsius", "graden celsius"), "km": ("kilometer",), "kg": ("kilo",), "m": ("meter",), "cm": ("centimeter",), "mm": ("millimeter",), "km/u": ("kilometer per uur",), "u": ("uur",)},
    "fr": {"%": ("pour cent",), "€": ("euro", "euros"), "$": ("dollar", "dollars"), "°": ("degré", "degrés"), "°C": ("degré celsius", "degrés celsius"), "km": ("kilomètre", "kilomètres"), "kg": ("kilo", "kilos"), "m": ("mètre", "mètres"), "cm": ("centimètre", "centimètres"), "mm": ("millimètre", "millimètres"), "km/h": ("kilomètre par heure", "kilomètres par heure"), "h": ("heure", "heures")},
    "pl": {"%": ("procent",), "€": ("euro",), "$": ("dolar", "dolarów"), "zł": ("złoty", "złotych"), "°": ("stopień", "stopni"), "°C": ("stopień Celsjusza", "stopni Celsjusza"), "km": ("kilometr", "kilometrów"), "kg": ("kilogram", "kilogramów"), "m": ("metr", "metrów"), "cm": ("centymetr", "centymetrów"), "mm": ("milimetr", "milimetrów"), "km/h": ("kilometr na godzinę", "kilometrów na godzinę")},
}
# Endings of an ordinal written with digits.
ORDINALS = {"nl": ("ste", "de", "e"), "fr": ("er", "re", "ère", "ème", "eme", "e", "è")}

_UNIT_NAMES = sorted({u for table in UNITS.values() for u in table}, key=len, reverse=True)
_ENDINGS = sorted({e for ends in ORDINALS.values() for e in ends}, key=len, reverse=True)
_NUMBER = r"\d{1,3}(?:[  ]\d{3})+(?:,\d+)?|\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?"
_PREFIX = "|".join(re.escape(u) for u in ("€", "$"))
_PATTERN = re.compile(
    rf"(?<![\w.,/])(?:(?P<pre>{_PREFIX})\s?)?(?P<num>{_NUMBER})"
    rf"(?:(?P<end>{'|'.join(_ENDINGS)})(?![\w])|\s?(?P<unit>{'|'.join(re.escape(u) for u in _UNIT_NAMES)})(?![\w]))?"
    r"(?![\w])"
)


def _fraction_zeros(token):
    "How many zeros end the decimals of a written number (\"2,50\" has one): a float forgets them, a voice should say them."
    frac = re.split(r"[.,]", token.replace("\u00a0", "").replace("\u202f", ""))[-1] if re.search(r"[.,]\d+$", token) and not re.fullmatch(r"\d{1,3}(\.\d{3})+", token) else ""
    return len(frac) - len(frac.rstrip("0")) if frac else 0


def value_of(token):
    "The number a digit run stands for (int, or float for a decimal), reading dots as thousands and the comma as the decimal point; None if it is not one."
    token = token.replace(" ", "").replace(" ", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", token):
        token = token.replace(".", "")
    token = token.replace(",", ".")
    try:
        return float(token) if "." in token else int(token)
    except ValueError:
        return None


def _say(value, lang, to="cardinal"):
    "num2words, or None when it does not know the language or the number."
    try:
        return num2words(value, lang=LANG.get(lang, lang), to=to)
    except (NotImplementedError, OverflowError, ValueError, KeyError):
        return None


def _is_year(value, unit, end):
    return isinstance(value, int) and 1000 <= value <= 2100 and not unit and not end


def _describe(match, code):
    "(words, kind) for one digit run with what is attached to it, or None to leave it as it is."
    value = value_of(match["num"])
    if value is None:
        return None
    unit, end = match["unit"] or match["pre"], match["end"]
    if end and end in ORDINALS.get(code, ()) and isinstance(value, int):
        words = _say(value, code, "ordinal")
        return (words, "ordinal") if words else None
    if end and end not in ORDINALS.get(code, ()):
        return None  # an ending this language does not use: not an ordinal
    kind = "year" if _is_year(value, unit, end) else "number"
    words = (_say(value, code, "year") if kind == "year" else None) or _say(value, code)
    if words is None:
        return None
    if isinstance(value, float):
        zeros = _fraction_zeros(match["num"])
        words += (" " + _say(0, code)) * zeros if zeros else ""
    if unit:
        forms = UNITS.get(code, {}).get(unit)
        if forms:
            spoken = forms[0] if value == 1 or len(forms) == 1 else forms[1]
            words = f"{words} {spoken}"
    return words, kind


def spoken(text, code):
    "The text with every number written as digits said in words, for a speech engine; unchanged for a language num2words does not know."
    if not text or not code or not re.search(r"\d", text):
        return text

    if code in ("fr", "pl"):  # these write 1 000 000 with spaces: make them one run
        text = re.sub(r"(?<![\d.,])\d{1,3}(?: \d{3})+(?![\d])", lambda m: m[0].replace(" ", "\u00a0"), text)

    def replace(match):
        before, after = text[max(0, match.start() - 2) : match.start()], text[match.end() : match.end() + 2]
        joined = re.search(r"\d[-:]$", before) or re.match(r"[-:]\d", after)  # a phone number, a time, a score: left to the voice
        if joined and not (len(match["num"]) == 4 and (re.search(r"\d{4}-$", text[max(0, match.start() - 5) : match.start()]) or re.match(r"-\d{4}(?!\d)", text[match.end() : match.end() + 6]))):
            return match[0]
        found = _describe(match, code)
        return found[0] if found else match[0]

    return _PATTERN.sub(replace, text)


def describe(text, code):
    "For the word panel: {words, kind} for a text that is one number (with its unit or ending), else None."
    match = _PATTERN.fullmatch((text or "").strip())
    found = _describe(match, code) if match else None
    return {"words": found[0], "kind": found[1]} if found else None
