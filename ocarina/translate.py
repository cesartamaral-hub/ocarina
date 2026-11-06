"""
Sentence translation: on this Mac with a small model (offline, no limits), or through an online service you choose
(MyMemory: free, no account; or DeepL: your own key).

Translations are cached on disk, so the same sentence never uses your daily quota twice and works offline once seen.
The sentence goes to the service you picked, and nowhere else (with the local model it does not leave this Mac).
"""

import hashlib
import json
import os
import re

import requests

from ocarina import dictionary, keystore, offline, paths
from ocarina.localllm import local_model
from ocarina.tts import models as model_files

TIMEOUT = 10
USER_AGENT = "Ocarina/1.0 (personal language-learning app)"
LOCAL_MODEL = "qwen3-4b-instruct-mlx"
MAX_CHARS = {"mymemory": 500, "deepl": 2000, "local": 1000}
PROVIDERS = {
    "local": {
        "name": "Local model",
        "needsKey": False,
        "description": "Offline, private and without limits, with a 2.3 GB model you download once. Good for ordinary sentences; it can invent words for rare vocabulary.",
    },
    "mymemory": {"name": "MyMemory", "needsKey": False, "description": "Free, no account. About 5,000 characters a day (50,000 with an email address)."},
    "deepl": {"name": "DeepL", "needsKey": True, "description": "The best quality. Needs your own free API key from deepl.com (500,000 characters a month)."},
}
TARGETS = {"en": "English", "nl": "Dutch", "fr": "French", "de": "German", "es": "Spanish", "it": "Italian", "pt": "Portuguese", "pl": "Polish"}

# Lute language name (lower case) -> ISO code. Names in the language itself are included.
CODES = {
    "dutch": "nl", "nederlands": "nl", "polish": "pl", "polski": "pl", "french": "fr", "français": "fr", "francais": "fr",
    "english": "en", "german": "de", "deutsch": "de", "spanish": "es", "español": "es", "italian": "it", "portuguese": "pt",
    "russian": "ru", "czech": "cs", "swedish": "sv", "danish": "da", "norwegian": "nb", "finnish": "fi", "greek": "el",
    "turkish": "tr", "hungarian": "hu", "romanian": "ro", "bulgarian": "bg", "ukrainian": "uk", "croatian": "hr",
    "serbian": "sr", "slovak": "sk", "slovenian": "sl", "catalan": "ca", "japanese": "ja", "korean": "ko", "arabic": "ar",
    "hebrew": "he", "hindi": "hi", "thai": "th", "vietnamese": "vi", "indonesian": "id", "afrikaans": "af", "latvian": "lv",
    "lithuanian": "lt", "estonian": "et", "albanian": "sq", "icelandic": "is", "irish": "ga", "welsh": "cy", "basque": "eu",
}
DEEPL_TARGETS = {"en": "EN-GB", "pt": "PT-PT"}


LOCAL_PROMPT = (
    "You translate single sentences for a language learner. "
    "Reply with the {target} translation only: no notes, no quotes."
)  # kept short on purpose: longer instructions made the small model's translations stilted


class TranslateError(Exception):
    "A sentence could not be translated; code says what kind of problem it is, the message says it in words."

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code  # offline, quota, bad_key, no_key, unsupported_language, too_long, bad_input, failed


def code_for(language_name):
    "ISO code of a Lute language, or None if the app does not know it."
    return CODES.get(language_name.strip().lower())


def _cache_path(datapath, provider, source, target, text):
    "Where a translation is kept. provider is the service, or local:<model> for a model on this Mac (see cache_provider)."
    key = hashlib.sha256("\n".join([provider, source, target, text]).encode("utf-8")).hexdigest()
    return os.path.join(paths.cache(datapath, "translation"), key[:2], key + ".json")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return strip_marks(json.load(f)["translation"]) or None
    except (OSError, ValueError, KeyError):
        return None


# The marks a model writes at the end of its turn; they are not part of a translation (some models, not stopped by them, wrote them over and over).
END_MARKS = ("<end_of_turn>", "<start_of_turn>", "<|im_end|>", "<|endoftext|>", "<eos>")


def strip_marks(text):
    "A translation up to the first end-of-turn mark."
    for mark in END_MARKS:
        text = text.split(mark, 1)[0]
    return text.strip()


def _write(path, translation):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"translation": translation}, f, ensure_ascii=False)
    os.replace(tmp, path)


def _get(url, **kw):
    try:
        return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, **kw)
    except requests.exceptions.RequestException as e:
        raise TranslateError("No connection to the translation service.", "offline") from e


def _mymemory(text, source, target, email):
    params = {"q": text, "langpair": f"{source}|{target}"}
    if email:
        params["de"] = email
    response = _get("https://api.mymemory.translated.net/get", params=params)
    try:
        body = response.json()
    except ValueError as e:
        raise TranslateError("MyMemory sent an answer that could not be read.", "failed") from e
    answer = (body.get("responseData") or {}).get("translatedText") or ""
    status = int(body.get("responseStatus") or response.status_code)
    if status == 429 or body.get("quotaFinished") or "MYMEMORY WARNING" in answer.upper():
        raise TranslateError(
            "MyMemory's free limit for today is used up. Add an email address in Settings for ten times more, or use DeepL.", "quota"
        )
    if status != 200 or not answer:
        raise TranslateError(f"MyMemory could not translate this ({body.get('responseDetails') or status}).", "failed")
    return answer


def _deepl(text, source, target, key):
    host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
    try:
        response = requests.post(
            f"https://{host}/v2/translate",
            headers={"User-Agent": USER_AGENT, "Authorization": f"DeepL-Auth-Key {key}"},
            json={"text": [text], "source_lang": source.upper(), "target_lang": DEEPL_TARGETS.get(target, target.upper())},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        raise TranslateError("No connection to the translation service.", "offline") from e
    if response.status_code == 403:
        raise TranslateError("DeepL did not accept the API key. Check it in Settings.", "bad_key")
    if response.status_code == 456:
        raise TranslateError("Your DeepL quota for this month is used up.", "quota")
    if response.status_code == 429:
        raise TranslateError("DeepL says there were too many requests. Try again in a moment.", "failed")
    if response.status_code != 200:
        raise TranslateError(f"DeepL answered with an error ({response.status_code}).", "failed")
    try:
        return response.json()["translations"][0]["text"]
    except (ValueError, KeyError, IndexError) as e:
        raise TranslateError("DeepL sent an answer that could not be read.", "failed") from e


def cache_provider(provider, model_id):
    "What a translation is filed under: each model on this Mac keeps its own (the first model keeps the key it always had)."
    return provider if provider != "local" or model_id in (None, LOCAL_MODEL) else f"local:{model_id}"


def _local(text, source_name, source, target, engine, model_id=None):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    model = model_files.find_model(model_id or LOCAL_MODEL)
    if model is None or model_files.kind_of(model) != "text":
        raise TranslateError("That translation model is not in the list any more. Pick another in Settings.", "no_model")
    if engine is None and not model_files.is_installed(model):
        raise TranslateError(f"Download {model['name']} in Settings first.", "no_model")
    # Models with their own prompt format (TranslateGemma) are given the text and the two languages, nothing more.
    extra = {"style": model.get("prompt"), "source": source, "target": target, "text": text} if model.get("prompt") == "translategemma" else {}
    try:
        answer = local_model.complete(model, LOCAL_PROMPT.format(target=TARGETS[target]), f"{source_name} sentence:\n{text}", engine=engine, **extra)
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise TranslateError(f"The translation model failed ({type(e).__name__}).", "failed") from e
    answer = strip_marks(answer).strip("\"“”").strip()
    if not answer:
        raise TranslateError("The translation model gave no answer.", "failed")
    return answer


def settings_for(settings, source):
    "The settings with the model on this Mac that was chosen for this source language, when one was (else the general one)."
    chosen = (settings.get("localModelByLanguage") or {}).get(source)
    return {**settings, "localModel": chosen} if chosen else settings


def translate(datapath, settings, language_name, text, use_cache=True, local_engine=None):
    """
    Translate a sentence from a Lute language into the target language. settings: {provider, target, email, localModel}.
    Returns {translation, provider, source, target, cached}. Raises TranslateError. use_cache=False always asks the service (to test a key). local_engine overrides the local model's engine (tests).
    """
    text = re.sub(r"\s+", " ", (text or "").replace("​", "")).strip()
    if not text:
        raise TranslateError("There is nothing to translate.", "bad_input")
    provider, target = settings["provider"], settings["target"]
    if provider != "local" and offline.is_on():
        raise TranslateError(f"{PROVIDERS[provider]['name']} needs the internet, and Work offline is on. Choose a local model, or turn it off in Settings → General.", "offline_mode")
    if len(text) > MAX_CHARS[provider]:
        raise TranslateError(f"This is too long for {PROVIDERS[provider]['name']} ({MAX_CHARS[provider]} characters at most).", "too_long")
    source = code_for(language_name)
    if source is None:
        raise TranslateError(f"Ocarina does not know the language code for {language_name} yet.", "unsupported_language")
    if source == target:
        raise TranslateError(f"The sentence is already in {TARGETS.get(target, target)}. Pick another target language in Settings.", "bad_input")
    model_id = settings_for(settings, source).get("localModel")
    path = _cache_path(datapath, cache_provider(provider, model_id), source, target, text)
    cached = _read(path) if use_cache else None
    if cached is not None:
        return {"translation": cached, "provider": provider, "source": source, "target": target, "cached": True}
    if provider == "local":
        answer = _local(text, dictionary.section_name(language_name), source, target, local_engine, model_id)
    elif provider == "deepl":
        key = keystore.get(datapath, "deepl")
        if not key:
            raise TranslateError("Add your DeepL API key in Settings first.", "no_key")
        answer = _deepl(text, source, target, key)
    else:
        answer = _mymemory(text, source, target, settings.get("email"))
    _write(path, answer)
    return {"translation": answer, "provider": provider, "source": source, "target": target, "cached": False}
