from json import loads
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import obspython as obs


def get_chesscom_record(username: str):
    if username == "":
        return

    with urlopen(f"https://api.chess.com/pub/player/{username}/stats") as res:
        win = 0
        loss = 0
        draw = 0

        for value in loads(res.read().decode("utf8")).values():
            if isinstance(value, dict) and "record" in value:
                win += int(value["record"]["win"])
                loss += int(value["record"]["loss"])
                draw += int(value["record"]["draw"])

        return win, loss, draw


def update_chesscom_record(text_source_name: str, username: str):
    try:
        text_source = obs.obs_get_source_by_name(text_source_name)
        result = get_chesscom_record(username)

        if not result:
            text = "No chess.com username specified!"

        else:
            win, loss, draw = result
            text = f"chess.com - {username} - Wins: {win}, Losses: {loss}, Draws: {draw}"

    except HTTPError as e:
        if e.status == 404:
            text = f"Invalid chess.com username: {username}!"

        else:
            text = None
            raise e

    finally:
        if text:
            settings = obs.obs_data_create()
            obs.obs_data_set_string(settings, "text", text)
            obs.obs_source_update(text_source, settings)
            obs.obs_data_release(settings)

        if text_source:
            obs.obs_source_release(text_source)


def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "chesscom_username", "")
    obs.obs_data_set_default_int(settings, "refresh_rate", 1)


def script_description():
    return "Replace textbox content with user's chess.com stats!"


def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_text(props, "chesscom_username", "chess.com username",
                                obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "refresh_rate", "Refresh Rate (Hz)", 1, 60, 1)

    p = obs.obs_properties_add_list(props, "text_source", "Text Source",
                                    obs.OBS_COMBO_TYPE_EDITABLE,
                                    obs.OBS_COMBO_FORMAT_STRING)
    sources = obs.obs_enum_sources()

    if sources:
        for source in sources:
            source_id = obs.obs_source_get_id(source)

            if source_id == "text_gdiplus_v2":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p, name, name)

        obs.source_list_release(sources)

    return props


def script_update(settings):
    chesscom_username = obs.obs_data_get_string(settings, "chesscom_username")
    text_source_name = obs.obs_data_get_string(settings, "text_source")
    refresh_rate = obs.obs_data_get_int(settings, "refresh_rate")

    obs.remove_current_callback()
    obs.timer_add(lambda: update_chesscom_record(text_source_name, chesscom_username),
                                                 int((1 / refresh_rate) * 1000))
