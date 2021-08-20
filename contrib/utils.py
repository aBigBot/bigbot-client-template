import base64
import datetime
import json
import re
import threading
import typing
import urllib.parse as urlparse
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from django_middleware_global_request.middleware import get_request
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests
from textdistance import levenshtein


base64_regex = re.compile(r"^data:(?P<mimetype>[^;]+);base64,(?P<data>.+)$")

bg = lambda text, color: "\33[48;5;" + str(color) + "m" + text + "\33[0m"
fg = lambda text, color: "\33[38;5;" + str(color) + "m" + text + "\33[0m"


def append_error(data: dict, *errors, key: str = "error"):
    """Appends error to a dictionary field"""
    if key not in data:
        data[key] = []
    elif not isinstance(data[key], list):
        value = data[key]
        data[key] = [value]

    for error in errors:
        data[key].append(error)

    return data


def append_url(server, url):
    """Appends an url path to a server's URI"""
    if server[-1] == url[0] and server[-1] == "/":
        return server + url[1:]
    if server[-1] == "/" or url[0] == "/":
        return server + url
    return f"{server}/{url}"


def base64_decode(string):
    base64_bytes = string.encode("ascii")
    string_bytes = base64.b64decode(base64_bytes)
    return string_bytes.decode("ascii")


def base64_encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.b64encode(string_bytes)
    return base64_bytes.decode("ascii")


def build_otp_mail_content(otp):
    from contrib.mixin import request
    from django.template import Context, Template

    host = settings.HTTP_PROTOCOL + "://" + settings.SERVER_HOST
    data = {
        "title": "One time password",
        "summary": "You can use this one time password to authenticate your account. Do not share this with anyone.",
        "button": otp,
        "HOST": host,
    }
    f = open(settings.BASE_DIR + "/static/mail/project-letter/mail-content.html", "r")
    content = f.read()
    t = Template(content)
    html = t.render(Context(data))
    return html


def build_url(url, params):
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)


def clean_text(string: str) -> str:
    """Removes punctuation, extra spaces, and lowercases a string."""
    import re

    f = filter(lambda c: c.isalnum() or c.isspace() or c in ["-", "_"], string.strip().lower())
    res = "".join(f)
    res = re.sub(r"\s\s+", " ", res)
    res = re.sub(r"\t", " ", res)
    res = re.sub(r"\n", " ", res)
    return res


def create_event(data, user_creds):
    data = format_data(data)
    expiry = datetime.timedelta(seconds=user_creds.expires_in) + user_creds.updated
    if expiry < timezone.now():
        try:
            user_creds = refresh_token(user_creds)
        except ValidationError as e:
            return {"success": False, "error": e}
    creds = Credentials.from_authorized_user_info(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "access_token": user_creds.access_token,
            "refresh_token": user_creds.refresh_token,
        },
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    calendarService = build("calendar", "v3", credentials=creds)
    return {
        "success": True,
        "data": calendarService.events()
        .insert(calendarId="primary", body=data, sendUpdates="all")
        .execute(),
    }


def format_data(data):
    final_data = {
        "end": {"timezone": "Asia/Kolkata"},
        "start": {"timezone": "Asia/Kolkata"},
        "attendees": [],
    }
    # if data['all_day'] == 'yes':
    #     final_data['end']['date'] = data['end_date']
    #     final_data['start']['date'] = data['start_date']
    # else:
    final_data["end"]["date"] = data["end_date"]
    final_data["start"]["date"] = data["start_date"]

    final_data["end"]["datetime"] = data["end_date"] + " 00:00:00"
    final_data["start"]["datetime"] = data["start_date"] + " 00:00:00"
    for attendee in data["required_attendees"].split(","):
        final_data["attendees"].append({"email": attendee, "optional": False})
    if data["summary"]:
        final_data["summary"] = data["summary"]
    if data["description"]:
        final_data["description"] = data["description"]

    print("===============data=================")
    print(data)
    return final_data


def fuzzy_search(needle: str, hay: str) -> typing.Tuple[float, str]:
    """Fuzzy search needle in hay.
    Args:
        needle (str): String to look for.
        hay (str): String to look into.

    Returns:
        Tuple[float, str]: A tuple with two values, the first value is float 0 and 1 where 0 means
            that no similar string to the needle was found, and 1 means a perfect match. The second
            value is the substring found.
    """

    hay = clean_text(hay)
    hay_length = len(hay)
    needle = clean_text(needle)
    needle_length = len(needle)

    if needle_length > hay_length:
        needle = needle[:hay_length]

    position = 0
    similarity = 0
    for i in range(hay_length):
        if i + needle_length > hay_length:
            break
        substring = hay[i : i + needle_length]
        tmp_similarity = levenshtein.normalized_similarity(needle.lower(), substring.lower())
        if tmp_similarity > similarity:
            position = i
            similarity = tmp_similarity

    if similarity == 0:
        return 0.0, ""
    return similarity, hay[position : position + needle_length]


def get_body(request):
    if request.META.get("CONTENT_TYPE", "").lower() == "application/json" and len(request.body) > 0:
        try:
            return json.loads(request.body)
        except Exception as e:
            pass
    return False


def get_bool(request, key):
    object = request.POST.get(key)
    if not object:
        return False
    else:
        if object.lower() == "true":
            return True
    return False


def get_date(request, key):
    object = request.POST.get(key, False)
    if not object:
        return False
    import datetime

    date_format = "%Y-%m-%d"
    try:
        datetime.datetime.strptime(object, date_format)
        return object
    except ValueError:
        return False


def get_dispose_script():
    html = """
<script>
    var obj = window.self;
    obj.opener = window.self;
    obj.close();
</script>
"""
    return html


def get_email(request, key):
    object = request.POST.get(key, False)
    if not object:
        return False
    try:
        validate_email(object)
    except ValidationError as e:
        return False
    else:
        return object


def get_float(request, key):
    object = request.POST.get(key)
    if object:
        return float(object)
    return 0.0


def get_full_url(url):
    return append_url(
        "{}://{}".format(settings.HTTP_PROTOCOL, settings.SERVER_HOST),
        url,
    )


def get_int(request, key):
    object = request.POST.get(key)
    if object:
        return int(object)
    return 0


def get_int_arr(request, key):
    arr = []
    for item in request.POST.getlist(key):
        arr.append(int(item))
    return arr


def get_string(request, key):
    object = request.POST.get(key, False)
    if not object:
        return False
    elif len(object.strip()) != 0:
        return object
    return False


def is_date(value):
    import datetime

    try:
        datetime.datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        pass
    return False


def is_datetime(value):
    import datetime

    try:
        datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        pass
    return False


def levenshtein_distance(a: str, b: str) -> float:
    return levenshtein.normalized_similarity(a.lower(), b.lower())


def log(object):
    print(object)


def log_exception(e):
    raise e


def normalize_uuid(uuid: str):
    """Adds dashes to uuid if it does not have it"""
    uuid = str(uuid)
    if not "-" in uuid:
        return f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
    return uuid


def parse_base64(base64_string):
    match = base64_regex.match(base64_string)
    if match is None:
        raise Exception("Invalid base64 string")
    data = match.group("data")
    mimetype = match.group("mimetype")
    return data, mimetype


def print_six(row, format, end="\n"):
    for col in range(6):
        color = row * 6 + col - 2
        if color >= 0:
            text = "{:3d}".format(color)
            print(format(text, color), end=" ")
        else:
            print(end="    ")  # four spaces
    print(end=end)


def refresh_token(user_creds):
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": user_creds.refresh_token,
        },
    )
    data = resp.json()
    print(resp, "------")
    if resp.status_code != 200:
        user_creds.access_token = ""
        user_creds.save()
        raise ValidationError("Error occurred while refreshing token")
    user_creds.access_token = data["access_token"]
    user_creds.expires_in = data["expires_in"]
    user_creds.save()
    return user_creds


def text2int(textnum, numwords={}):
    """Parses a number written in word form"""

    if not numwords:
        units = [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirdteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
        ]
        tens = [
            "",
            "",
            "twenty",
            "thirdty",
            "forty",
            "fifty",
            "sixty",
            "seventy",
            "eighty",
            "ninety",
        ]
        scales = ["hundred", "thousand", "million", "billion", "trillion"]

        numwords["and"] = (1, 0)
        for idx, word in enumerate(units):
            numwords[word] = (1, idx)
        for idx, word in enumerate(tens):
            numwords[word] = (1, idx * 10)
        for idx, word in enumerate(scales):
            numwords[word] = (10 ** (idx * 3 or 2), 0)

    textnum = textnum.replace("-", " ")
    current = result = 0

    for word in textnum.split():
        if word not in numwords:
            raise Exception("Illeal word: " + word)

        scale, increment = numwords[word]

        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current


def web_preview(url: str) -> typing.Tuple[str, str, str]:
    """Extracts title, description and thumbnail from an url

    Args:
        url (str)

    Returns:
        Tuple[str, str, str]: A tuple with witht the title, description and url, in that order.
    """
    from webpreview import GenericPreview, OpenGraph, Schema, TwitterCard

    def not_none(*args):
        for item in args:
            if item is None or item == "":
                return False
        return True

    def process_image_url(request_url, image_url, force_absolute_url):
        if image_url is None:
            return None
        if not force_absolute_url:
            return image_url
        if image_url[:4] == "http":
            return image_url

        parsed_image_url = urlparse.urlparse(image_url)

        if not parsed_image_url.netloc and force_absolute_url:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(request_url)
            path = image_url if image_url.startswith("/") else "{}{}".format(path, image_url)
            url_components = [scheme, netloc, path, None, None, None]
            return urlparse.urlunparse(url_components)

    def process_url(obj, storage, *args, **kwargs):
        result = obj(*args, **kwargs)
        storage["result"] = result
        return result

    def select_value(new, old):
        if old is None or old == "":
            return new
        return old

    opengraph_result = {}
    opengraph_thread = threading.Thread(
        target=process_url,
        args=[OpenGraph, opengraph_result, url, ["og:title", "og:description", "og:image"]],
        kwargs={"content": None, "headers": None, "parser": None, "timeout": None},
    )
    opengraph_thread.start()

    twitter_result = {}
    twitter_thread = threading.Thread(
        target=process_url,
        args=[
            TwitterCard,
            twitter_result,
            url,
            ["twitter:title", "twitter:description", "twitter:image"],
        ],
        kwargs={"content": None, "headers": None, "parser": None, "timeout": None},
    )
    twitter_thread.start()

    schema_result = {}
    schema_thread = threading.Thread(
        target=process_url,
        args=[Schema, schema_result, url, ["name", "description", "image"]],
        kwargs={"content": None, "headers": None, "parser": None, "timeout": None},
    )
    schema_thread.start()

    generic_result = {}
    generic_thread = threading.Thread(
        target=process_url,
        args=[GenericPreview, generic_result, url],
        kwargs={"content": None, "headers": None, "parser": None, "timeout": None},
    )
    generic_thread.start()

    description, image, title = None, None, None

    opengraph_thread.join()
    og = opengraph_result["result"]
    description = select_value(og.description, description)
    image = select_value(process_image_url(url, og.image, True), image)
    title = select_value(og.title, title)
    if not_none(description, image, title):
        return title, description, image

    twitter_thread.join()
    tc = twitter_result["result"]
    description = select_value(tc.description, description)
    image = select_value(process_image_url(url, tc.image, True), image)
    title = select_value(tc.title, title)
    if not_none(description, image, title):
        return title, description, image

    schema_thread.join()
    s = schema_result["result"]
    description = select_value(s.description, description)
    image = select_value(process_image_url(url, s.image, True), image)
    title = select_value(s.name, title)
    if not_none(description, image, title):
        return title, description, image

    generic_thread.join()
    gp = generic_result["result"]
    gp = GenericPreview(url, timeout=None, headers=None, content=None, parser=None)
    description = select_value(gp.description, description)
    image = select_value(process_image_url(url, gp.image, True), image)
    title = select_value(gp.title, title)

    return title, description, image


class FakeQuery:
    def __init__(self, items=[]):
        self.items = items

    def __iter__(self):
        return self.items

    def __str__(self):
        return f"<FakeQuery: {str(self.items)}>"

    def count(self):
        return len(self.items)

    def first(self):
        if len(self.items) > 0:
            return self.items[0]
        return None
