from json import loads
from re import search
from typing import TypedDict
from urllib.error import HTTPError
from urllib.request import urlopen

import obspython as obs


deezer_app_state_regex_pattern = \
    r"<script>window.__DZR_APP_STATE__ = (?P<deezer_app_state>.+)</script>"


class DeezerAppStateTabHomeOnline(TypedDict):
    SNG_TITLE: str
    ART_NAME: str
    ALB_TITLE: str


class DeezerAppStateTabHome(TypedDict, total=False):
    online: DeezerAppStateTabHomeOnline


class DeezerAppStateTab(TypedDict):
    home: DeezerAppStateTabHome


class DeezerAppState(TypedDict):
    TAB: DeezerAppStateTab


class InvalidProfileIdException(Exception):
    pass


def get_current_deezer_playing(profile_id: int):
    try:
        with urlopen(f"https://deezer.com/us/profile/{profile_id}") as res:
            res_text: str = res.read().decode("utf8")
            app_state: DeezerAppState = loads(search(deezer_app_state_regex_pattern,
                                                     res_text)["deezer_app_state"])

            if "online" not in app_state["TAB"]["home"]:
                return

            return app_state["TAB"]["home"]["online"]

    except HTTPError as e:
        if e.status != 404:
            raise e

        raise InvalidProfileIdException


def update_current_deezer_playing(text_source_name: str, profile_id: int):
    try:
        text_source = obs.obs_get_source_by_name(text_source_name)
        result = get_current_deezer_playing(profile_id)

        if not result:
            text = "Not Playing!"

        else:
            text = f"Playing {result['ART_NAME']} - {result['SNG_TITLE']} ({result['ALB_TITLE']})"

    except InvalidProfileIdException:
        text = "Invalid profile ID specified!"

    except HTTPError as e:
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
    obs.obs_data_set_default_string(settings, "deezer_profile_id", "")
    obs.obs_data_set_default_int(settings, "refresh_rate", 1)


def script_description():
    return "Replace textbox content with user's Deezer currently playing music!"


def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_text(props, "deezer_profile_id", "Deezer Profile ID",
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
    deezer_profile_id = obs.obs_data_get_string(settings, "deezer_profile_id")
    text_source_name = obs.obs_data_get_string(settings, "text_source")
    refresh_rate = obs.obs_data_get_int(settings, "refresh_rate")

    obs.remove_current_callback()
    obs.timer_add(lambda: update_current_deezer_playing(text_source_name, deezer_profile_id),
                                                 int((1 / refresh_rate) * 1000))

