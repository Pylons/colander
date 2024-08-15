import re
from unittest import mock
import warnings

import pytest
import translationstring


def _assert_trstring(found, expected):
    assert isinstance(found, translationstring.TranslationString)
    assert str(found) == expected


def test_all___call___w_empty_subs():
    import colander

    node = object()
    value = "testing"
    all_ = colander.All()
    assert list(all_.validators) == []

    all_(node, value)  # no raise


def test_all___call___w_one_sub_wo_raise():
    import colander

    node = object()
    value = "testing"
    validator = mock.Mock(spec_set=(), return_value=None)
    all_ = colander.All(validator)
    assert list(all_.validators) == [validator]

    all_(node, value)  # no raise

    validator.assert_called_once_with(node, value)


def test_all___call___w_one_sub_w_raise():
    import colander

    node = object()
    value = "testing"
    validator = mock.Mock(
        spec_set=(),
        side_effect=colander.Invalid(node, "testing"),
    )
    all_ = colander.All(validator)
    assert list(all_.validators) == [validator]

    with pytest.raises(colander.Invalid) as exc:
        all_(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["testing"]

    validator.assert_called_once_with(node, value)


def test_all___call___w_multi_subs_w_one_raises():
    import colander

    node = object()
    value = "testing"
    validator_1 = mock.Mock(spec_set=(), return_value=None)
    validator_2 = mock.Mock(
        spec_set=(),
        side_effect=colander.Invalid(node, "testing"),
    )
    all_ = colander.All(validator_1, validator_2)
    assert list(all_.validators) == [validator_1, validator_2]

    with pytest.raises(colander.Invalid) as exc:
        all_(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["testing"]

    validator_1.assert_called_once_with(node, value)
    validator_2.assert_called_once_with(node, value)


def test_all___call___w_multi_subs_w_many_raises():
    import colander

    node = object()
    value = "testing"
    validator_1 = mock.Mock(
        spec_set=(),
        side_effect=colander.Invalid(node, ["testing 1a", "testing 1b"]),
    )
    validator_2 = mock.Mock(
        spec_set=(),
        side_effect=colander.Invalid(node, "testing 2"),
    )
    all_ = colander.All(validator_1, validator_2)
    assert list(all_.validators) == [validator_1, validator_2]

    with pytest.raises(colander.Invalid) as exc:
        all_(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["testing 1a", "testing 1b", "testing 2"]

    validator_1.assert_called_once_with(node, value)
    validator_2.assert_called_once_with(node, value)


def test_any___call___w_empty_subs():
    import colander

    node = object()
    value = "testing"
    any_ = colander.Any()
    assert list(any_.validators) == []

    any_(node, value)  # no raise


def test_any___call___w_one_sub_wo_raise():
    import colander

    node = object()
    value = "testing"
    validator = mock.Mock(spec_set=(), return_value=None)
    any_ = colander.Any(validator)
    assert list(any_.validators) == [validator]

    any_(node, value)  # no raise

    validator.assert_called_once_with(node, value)


def test_any___call___w_one_sub_w_raise():
    import colander

    node = object()
    value = "testing"
    validator = mock.Mock(
        spec_set=(),
        side_effect=colander.Invalid(node, "testing"),
    )
    any_ = colander.Any(validator)
    assert list(any_.validators) == [validator]

    with pytest.raises(colander.Invalid) as exc:
        any_(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["testing"]


def test_any___call___w_multi_subs_w_one_raises():
    import colander

    node = object()
    value = "testing"
    validator_1 = mock.Mock(spec_set=(), return_value=None)
    validator_2 = mock.Mock(
        spec_set=(),
        side_effect=colander.Invalid(node, "testing"),
    )
    any_ = colander.Any(validator_1, validator_2)
    assert list(any_.validators) == [validator_1, validator_2]

    any_(node, value)

    validator_1.assert_called_once_with(node, value)
    validator_2.assert_called_once_with(node, value)


def test_any___call___w_multi_subs_w_all_raise():
    import colander

    node = object()
    value = "testing"
    validator_1 = mock.Mock(
        spec_set=(),
        side_effect=colander.Invalid(node, ["testing 1a", "testing 1b"]),
    )
    validator_2 = mock.Mock(
        spec_set=(),
        side_effect=colander.Invalid(node, "testing 2"),
    )
    any_ = colander.Any(validator_1, validator_2)
    assert list(any_.validators) == [validator_1, validator_2]

    with pytest.raises(colander.Invalid) as exc:
        any_(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["testing 1a", "testing 1b", "testing 2"]

    validator_1.assert_called_once_with(node, value)
    validator_2.assert_called_once_with(node, value)


def test_function___init___w_msg_none_and_message_none():
    import colander

    def func(node, value):
        pass

    fv = colander.Function(func)

    _assert_trstring(fv.msg, "Invalid value")


def test_function___init___w_msg_set_and_message_none():
    import colander

    def func(node, value):
        pass

    fv = colander.Function(func, "Testing")

    assert fv.msg == "Testing"


def test_function___init___w_msg_set_and_message_set():
    import colander

    def func(node, value):
        pass

    with pytest.raises(ValueError):
        colander.Function(func, "msg", "message")


def test_function___init___w_msg_none_and_message_set():
    import colander

    def func(node, value):
        pass

    with warnings.catch_warnings(record=True) as warned:
        fv = colander.Function(func, message="message")

    assert fv.msg == "message"  # really?
    assert len(warned) == 1
    assert warned[0].category is DeprecationWarning


def test_function___call___returing_falsish_non_string():
    import colander

    node = object()
    value = "testing"

    func = mock.Mock(spec_set=[], return_value=None)

    fv = colander.Function(func, "Testing")

    with pytest.raises(colander.Invalid) as exc:
        fv(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["Testing"]
    func.assert_called_once_with(value)


def test_function___call___returing_truthy_non_string():
    import colander

    node = object()
    value = "testing"

    func = mock.Mock(spec_set=[], return_value=True)

    fv = colander.Function(func, "Testing")

    fv(node, value)  # no raise

    func.assert_called_once_with(value)


def test_function___call___returing_empty_string():
    import colander

    node = object()
    value = "testing"

    func = mock.Mock(spec_set=[], return_value=None)

    fv = colander.Function(func, "Testing")

    with pytest.raises(colander.Invalid) as exc:
        fv(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["Testing"]
    func.assert_called_once_with(value)


def test_function___call___returing_nonempty_string():
    import colander

    node = object()
    value = "testing"

    func = mock.Mock(spec_set=[], return_value="failed")

    fv = colander.Function(func, "Testing")

    with pytest.raises(colander.Invalid) as exc:
        fv(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["failed"]
    func.assert_called_once_with(value)


def test_regex___init___w_str_pattern_defaults():
    import colander

    pattern = "^Testing$"

    rgx = colander.Regex(pattern)

    assert isinstance(rgx.match_object, re.Pattern)
    assert rgx.match_object.pattern == pattern
    assert rgx.match_object.flags == re.UNICODE  # 're' adds it
    _assert_trstring(rgx.msg, "String does not match expected pattern")


def test_regex___init___w_str_pattern_w_custom_flags():
    import colander

    pattern = "^Testing$"

    rgx = colander.Regex(pattern, flags=re.IGNORECASE)

    assert isinstance(rgx.match_object, re.Pattern)
    assert rgx.match_object.pattern == pattern
    assert rgx.match_object.flags == re.IGNORECASE | re.UNICODE  # 're' adds
    _assert_trstring(rgx.msg, "String does not match expected pattern")


def test_regex___init___w_regex_object_w_message():
    import colander

    pattern = "^Testing$"
    compiled = re.compile(pattern)

    rgx = colander.Regex(compiled, "Testing")

    assert rgx.match_object is compiled
    assert rgx.msg == "Testing"


def test_regex___call___hit():
    import colander

    node = object()
    pattern = "^Testing$"
    compiled = re.compile(pattern)
    rgx = colander.Regex(compiled, "Should not raise")

    rgx(node, "Testing")  # no raise


def test_regex___call___miss():
    import colander

    node = object()
    pattern = "^Not Testing$"
    compiled = re.compile(pattern)
    rgx = colander.Regex(compiled, "Should raise")

    with pytest.raises(colander.Invalid) as exc:
        rgx(node, "Testing")

    assert exc.value.node is node
    assert exc.value.messages() == ["Should raise"]


def test_email___init___wo_msg():
    import colander

    email = colander.Email()

    _assert_trstring(email.msg, "Invalid email address")


def test_email___init___w_msg():
    import colander

    email = colander.Email("Testing")

    assert email.msg == "Testing"


def test_dataurl___init__w_defaults():
    import colander

    durl = colander.DataURL()

    _assert_trstring(durl.url_err, "Not a data URL")
    _assert_trstring(durl.mimetype_err, "Invalid MIME type")
    _assert_trstring(durl.base64_err, "Invalid Base64 encoded data")


def test_dataurl___init__w_explicit():
    import colander

    durl = colander.DataURL(
        url_err="Bad URL",
        mimetype_err="Bad MIMEtype",
        base64_err="Bad base64",
    )

    assert durl.url_err == "Bad URL"
    assert durl.mimetype_err == "Bad MIMEtype"
    assert durl.base64_err == "Bad base64"


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "foo",
        "data:foo"
        "data:foo;base64"
        "data:foo;base32,"
        "data:text/plain;charset=ASCII,foo",
    ],
)
def test_dataurl___call__miss_bad_url(bad_url):
    import colander

    node = object()
    durl = colander.DataURL(url_err="Bad URL")

    with pytest.raises(colander.Invalid) as exc:
        durl(node, bad_url)

    assert exc.value.node is node
    assert exc.value.msg == "Bad URL"


@pytest.mark.parametrize(
    "bad_mt",
    [
        "data:no/mime,foo",
        "data:no-mime;base64,Zm9vCg==",
    ],
)
def test_dataurl___call__miss_bad_mimetype(bad_mt):
    import colander

    node = object()
    durl = colander.DataURL(mimetype_err="Bad MIMEtype")

    with pytest.raises(colander.Invalid) as exc:
        durl(node, bad_mt)

    assert exc.value.node is node
    assert exc.value.msg == "Bad MIMEtype"


@pytest.mark.parametrize(
    "bad_b64",
    [
        "data:;base64,Zm9vCg",
        "data:text/plain;base64,Zm*vCg==",
    ],
)
def test_dataurl___call__miss_bad_base64(bad_b64):
    import colander

    node = object()
    durl = colander.DataURL(base64_err="Bad b64")

    with pytest.raises(colander.Invalid) as exc:
        durl(node, bad_b64)

    assert exc.value.node is node
    assert exc.value.msg == "Bad b64"


def test_dataurl___call__w_invalid_mimetype_and_b64data():
    import colander

    bad_mt_and_b64 = "data:no/mime;base64,Zm*vCg=="
    node = object()
    durl = colander.DataURL(mimetype_err="Bad MIMEtype", base64_err="Bad b64")

    with pytest.raises(colander.Invalid) as exc:
        durl(node, bad_mt_and_b64)

    assert exc.value.node is node
    assert "Bad MIMEtype" in exc.value.messages()
    assert "Bad b64" in exc.value.messages()


def test_range___init___w_defaults():
    import colander

    range_ = colander.Range()

    assert range_.min is None
    assert range_.max is None
    assert range_.min_err is colander.Range._MIN_ERR
    assert range_.max_err is colander.Range._MAX_ERR


def test_range___init___w_explicit():
    import colander

    range_ = colander.Range(-2, 13, "Min err", "Max err")

    assert range_.min == -2
    assert range_.max == 13
    assert range_.min_err == "Min err"
    assert range_.max_err == "Max err"


@pytest.mark.parametrize(
    "min_, max_, raises",
    [
        (None, None, False),
        (-5, None, False),
        (45, None, True),
        (None, 45, False),
        (None, 41, True),
        (-5, 45, False),
        (44, 55, True),
        (34, 35, True),
    ],
)
def test_range___call___w_min_none_w_max_none(min_, max_, raises):
    import colander

    node = object()
    value = 42
    range_ = colander.Range(min=min_, max=max_)

    if raises:
        with pytest.raises(colander.Invalid):
            range_(node, value)

    else:
        range_(node, value)  # no raise


def test_length___init___w_defaults():
    import colander

    length = colander.Length()

    assert length.min is None
    assert length.max is None
    assert length.min_err is colander.Length._MIN_ERR
    assert length.max_err is colander.Length._MAX_ERR


def test_length___init___w_explicit():
    import colander

    length = colander.Length(0, 13, "Min err", "Max err")

    assert length.min == 0
    assert length.max == 13
    assert length.min_err == "Min err"
    assert length.max_err == "Max err"


@pytest.mark.parametrize(
    "min_, max_, raises",
    [
        (None, None, False),
        (0, None, False),
        (45, None, True),
        (None, 15, False),
        (None, 4, True),
        (0, 15, False),
        (10, 15, True),
        (0, 4, True),
    ],
)
def test_length___call__(min_, max_, raises):
    import colander

    node = object()
    value = "ABCDEF"
    length = colander.Length(min=min_, max=max_)

    if raises:
        with pytest.raises(colander.Invalid):
            length(node, value)

    else:
        length(node, value)  # no raise


def test_oneof___init___w_defaults():
    import colander

    oneof = colander.OneOf(["a", "b", "c"])

    assert list(oneof.choices) == ["a", "b", "c"]
    assert oneof.msg_err is colander.OneOf._MSG_ERR


def test_oneof___init___w_explicit():
    import colander

    oneof = colander.OneOf(["a", "b", "c"], "Pick one")

    assert list(oneof.choices) == ["a", "b", "c"]
    assert oneof.msg_err == "Pick one"


def test_oneof___call___w_miss():
    import colander

    node = object()
    oneof = colander.OneOf(["a", "b", "c"])

    with pytest.raises(colander.Invalid):
        oneof(node, "nonesuch")


def test_oneof___call___w_hit():
    import colander

    node = object()
    oneof = colander.OneOf(["a", "b", "c"])

    oneof(node, "a")  # no raise


def test_noneof___init___w_defaults():
    import colander

    noneof = colander.NoneOf(["a", "b", "c"])

    assert list(noneof.forbidden) == ["a", "b", "c"]
    assert noneof.msg_err is colander.NoneOf._MSG_ERR


def test_noneof___init___w_explicit():
    import colander

    noneof = colander.NoneOf(["a", "b", "c"], "Pick another")

    assert list(noneof.forbidden) == ["a", "b", "c"]
    assert noneof.msg_err == "Pick another"


def test_noneof___call___w_miss():
    import colander

    node = object()
    noneof = colander.NoneOf(["a", "b", "c"])

    noneof(node, "nonesuch")  # no raise


def test_noneof___call___w_hit():
    import colander

    node = object()
    noneof = colander.NoneOf(["a", "b", "c"])

    with pytest.raises(colander.Invalid):
        noneof(node, "a")


def test_containsonly___init__():
    import colander

    containsonly = colander.ContainsOnly(["a", "b", "c"])

    assert list(containsonly.choices) == ["a", "b", "c"]


def test_containsonly___call___w_hit():
    import colander

    containsonly = colander.ContainsOnly(["a", "b", "c"])
    node = object()

    containsonly(node, set(["a", "b"]))  # no raise


def test_containsonly___call___w_miss():
    import colander

    containsonly = colander.ContainsOnly(["a", "b", "c"])
    node = object()

    with pytest.raises(colander.Invalid):
        containsonly(node, set(["a", "z"]))  # no raise


def test_luhnok_w_checksum_raises():
    import colander

    node = object()
    value = "ABC"

    with mock.patch("colander._luhnok") as checksum:
        checksum.side_effect = ValueError("testing")
        with pytest.raises(colander.Invalid):
            colander.luhnok(node, value)

    checksum.assert_called_once_with("ABC")


def test_luhnok_w_checksum_mod_10_not_0():
    import colander

    node = object()
    value = "ABC"

    with mock.patch("colander._luhnok") as checksum:
        checksum.return_value = 111
        with pytest.raises(colander.Invalid):
            colander.luhnok(node, value)

    checksum.assert_called_once_with("ABC")


def test_luhnok_hit():
    import colander

    node = object()
    value = "ABC"

    with mock.patch("colander._luhnok") as checksum:
        checksum.return_value = 1000

        colander.luhnok(node, value)  # no faise


@pytest.mark.parametrize(
    "value, checksum, raises",
    [
        ("ABC", None, ValueError),
        ("", 0, False),
        ("10", 2, False),
        ("100", 1, False),
        ("4111111111111111", 30, False),
        ("99999999999999999999999", 207, False),
    ],
)
def test__luhnok(value, checksum, raises):
    import colander

    if raises:
        with pytest.raises(raises):
            colander._luhnok(value)
    else:
        assert colander._luhnok(value) == checksum


# def test__make_url_regex_src # CAN'T, it is deleted after making URL_REGEX!


@pytest.mark.parametrize(
    "value",
    [
        "not-a-url",
        "file:///this/is/a/file.jpg",
        "http://.mysite.com",
        "http://www.mysite-.com",
        "http://www.-mysite.com",
        "http://mysite",
        "http://mysite.com:/path",
        "http://mysite.com:aaa",
        "http://mysite.com ",
    ],
)
def test_url_failures(value):
    import colander

    node = object()

    with pytest.raises(colander.Invalid) as exc:
        colander.url(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["Must be a URL"]


@pytest.mark.parametrize(
    "value",
    [
        "http://example.com",
        "http://www.mysite.com/(tttttttttttttttttttttt.jpg",
        "www.mysite.com",
        "http://user@mysite.com",
        "http://user:@mysite.com",
        "http://user:password@mysite.com",
        "http://user:pass%40word@mysite.com",
        "http://[2001:db8::0]/",
        "http://192.0.2.1/",
        "http://www.mysite.com.",
        "http://www.my-site.com",
        "http://xn--vck8cuc4a.com",
        str(
            b"http://\xe3\x82\xb5\xe3\x83\xb3\xe3\x83\x97\xe3\x83\xab.com",
            "utf-8",
        ),
        "http://localhost/",
        "http://mysite.com:8080",
        "http://mysite.com/path?k=v",
        "http://mysite.com/path#fragment",
        "http://mysite.com/path?k=v#fragment",
        "http://mysite.com?k=v",
        "http://mysite.com#fragment",
    ],
)
def test_url_successes(value):
    import colander

    node = object()

    assert colander.url(node, value) is None


@pytest.mark.parametrize(
    "value",
    [
        "not-a-uri",
        "file://",
    ],
)
def test_file_uri_failures(value):
    import colander

    node = object()

    with pytest.raises(colander.Invalid) as exc:
        colander.file_uri(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["Must be a file:// URI scheme"]


@pytest.mark.parametrize(
    "value",
    [
        "file:///",
        "file:///this/is/a/file.jpg",
        "file:///c:/is/a/file.jpg",
    ],
)
def test_file_uri_successes(value):
    import colander

    node = object()

    assert colander.file_uri(node, value) is None


@pytest.mark.parametrize(
    "value",
    [
        "not-a-uuid",
        "123zzzzz-uuuu-zzzz-uuuu-42665544zzzz",
        "88888888-333-4444-333-cccccccccccc",
        "urn:abcd:{123e4567-e89b-12d3-a456-426655440000}",
    ],
)
def test_uuid_failures(value):
    import colander

    node = object()

    with pytest.raises(colander.Invalid) as exc:
        colander.uuid(node, value)

    assert exc.value.node is node
    assert exc.value.messages() == ["Invalid UUID string"]


@pytest.mark.parametrize(
    "value",
    [
        "123e4567e89b12d3a456426655440000",
        "123e4567-e89b-12d3-a456-426655440000",
        "123E4567-E89B-12D3-A456-426655440000",
        "{123e4567-e89b-12d3-a456-426655440000}",
        "urn:uuid:{123e4567-e89b-12d3-a456-426655440000}",
    ],
)
def test_uuid_successes(value):
    import colander

    node = object()

    assert colander.uuid(node, value) is None
