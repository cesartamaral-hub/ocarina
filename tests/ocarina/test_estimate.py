"The speeds the pages use for their \"about 3 min\" (see ocarina/estimate.py)."

from ocarina import estimate
from ocarina.tts import models as model_files
from tests.ocarina.helpers import make_dutch_book

BOOKS = "/ocarina/api/books"


def test_a_model_not_tried_here_is_rated_by_its_catalog_speed(app):
    datapath = app.env_config.datapath
    model = {"id": "x-not-tried", "speed": 4}
    assert estimate.seconds_per_audio_second(datapath, model) == 0.2
    assert estimate.seconds_per_sentence(datapath, {"id": "x-not-tried", "speed": 1}) == 10.0
    mac = next(m for m in model_files.load_catalog() if model_files.is_builtin(m))
    assert estimate.seconds_per_audio_second(datapath, mac) == estimate.MAC_VOICE_SECONDS_PER_AUDIO_SECOND


def test_the_pages_get_a_speed_for_every_model_and_way_to_translate(app, client):
    with app.app_context():
        book_id = make_dutch_book("Tijd").id
    methods = client.get(f"{BOOKS}/{book_id}/translation").json["methods"]
    assert all(m["secondsPerSentence"] > 0 for m in methods)
    options = client.get(f"{BOOKS}/{book_id}/audio/options").json
    assert options["models"] and all(m["secondsPerSecondOfAudio"] > 0 for m in options["models"])
