"""
From a chrF score to the grade the model page shows. Bands were set on the first measurement (2026-11-06; Qwen3 4B and TranslateGemma 4B over
56 languages) by reading what translations at each level look like:

    A  62 and up   reads well and is close to a human translation
    B  55 to 62    good; the wording sometimes differs from the reference, the meaning is right
    C  48 to 55    the gist is right but mistakes show
    D  38 to 48    unreliable: check it against something else
    X  below 38    mostly wrong in our test (made-up words and sentences)
    None           the model refused the language (most of the sentences failed)

Grades rank, they do not promise accuracy: ten sentences is a small sample (a few points of noise), and chrF rewards wording close to the
reference. They are measured by Ocarina (ocarina/quality/quality.json) and can be measured again on the user's Mac.
"""

BANDS = [(62.0, "A"), (55.0, "B"), (48.0, "C"), (38.0, "D")]
SENTENCES = 10


def grade(chrf, errors=0, sentences=SENTENCES):
    "The grade letter for a score, 'X' when it is below the lowest band, None when the model failed most of the sentences."
    if errors * 2 >= sentences:
        return None
    for floor, letter in BANDS:
        if chrf >= floor:
            return letter
    return "X"
